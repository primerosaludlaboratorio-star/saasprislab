"""
Creación de órdenes de laboratorio desde recepción (LIMS).
Toda la persistencia crítica (folio, orden, detalles, preorden, pago inicial) vive en transaction.atomic().
"""
import json
import logging
import random
import uuid
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP

from django.conf import settings
from django.db import transaction, IntegrityError
from django.db.models import Q
from django.utils import timezone

from core.lims_cart import (
    aplicar_precio_convenio,
    convenio_precio_map,
    resolve_lims_cart_ids,
)
from core.models import (
    Convenio,
    DetalleOrden,
    Medico,
    OrdenDeServicio,
    Paciente,
    PagoOrden,
    PreOrdenLaboratorio,
)
from core.services.audit_service import registrar_auditoria

logger_core = logging.getLogger('core')


def parse_optional_client_mutation_uuid(raw):
    if raw is None or raw == '':
        return None
    return uuid.UUID(str(raw))


def _convenio_desde_tarifa_orden(orden, empresa):
    t = orden.tarifa or ''
    if not str(t).startswith('CONVENIO_'):
        return None
    try:
        cid = int(str(t).replace('CONVENIO_', '', 1))
    except ValueError:
        return None
    return Convenio.objects.filter(id=cid, empresa=empresa, activo=True).first()


def _crear_orden_success_body(
    orden,
    *,
    preorden_id=None,
    convenio=None,
    medico_referidor=None,
    mensaje=None,
    idempotent=False,
):
    return {
        'status': 'success',
        'mensaje': mensaje or 'Orden creada correctamente',
        'orden_id': orden.id,
        'folio': orden.folio_orden,
        'total': float(orden.total),
        'anticipo': float(orden.anticipo),
        'saldo': float(orden.total - orden.anticipo),
        'preorden_cobrada': preorden_id,
        'convenio_aplicado': convenio.id if convenio else None,
        'medico_referidor': medico_referidor.id if medico_referidor else None,
        'idempotent_replay': idempotent,
    }


def _generar_folio_orden(empresa, hoy):
    """Genera folio único por empresa para la fecha local dada (debe llamarse dentro de atomic)."""
    fecha_str = hoy.strftime('%Y%m%d')
    max_intentos = 10
    ultima_orden_hoy = OrdenDeServicio.objects.filter(
        empresa=empresa,
        fecha_creacion__date=hoy.date(),
    ).order_by('-id').first()

    if ultima_orden_hoy and ultima_orden_hoy.folio_orden:
        try:
            partes = ultima_orden_hoy.folio_orden.split('-')
            if len(partes) >= 3:
                ultimo_num = int(partes[-1])
                nuevo_num = ultimo_num + 1
            else:
                nuevo_num = 1
        except (ValueError, IndexError):
            nuevo_num = 1
    else:
        nuevo_num = 1

    folio_orden = None
    for intento in range(max_intentos):
        folio_candidato = f'LAB-{fecha_str}-{str(nuevo_num + intento).zfill(3)}'
        if not OrdenDeServicio.objects.filter(folio_orden=folio_candidato, empresa=empresa).exists():
            folio_orden = folio_candidato
            break

    if not folio_orden:
        folio_orden = f'LAB-{fecha_str}-{random.randint(100, 999)}'
    return folio_orden


class OrdenServicioLims:
    """Servicio de creación de órdenes desde recepción LIMS."""

    @staticmethod
    def crear_desde_recepcion(request, empresa):
        """
        Crea OrdenDeServicio + DetalleOrden (+ preorden / pago inicial si aplica).
        Devuelve {'http_status': int, 'body': dict}.
        """
        try:
            raw = request.body
            data = json.loads(raw) if raw else {}
            try:
                cmid = parse_optional_client_mutation_uuid(data.get('client_mutation_id'))
            except ValueError:
                return {
                    'http_status': 400,
                    'body': {'status': 'error', 'mensaje': 'client_mutation_id no es un UUID válido'},
                }

            if cmid:
                exist = OrdenDeServicio.objects.filter(
                    empresa=empresa, client_mutation_id=cmid
                ).select_related('medico_referente').first()
                if exist:
                    pre_vinc = PreOrdenLaboratorio.objects.filter(
                        orden_vinculada=exist
                    ).values_list('id', flat=True).first()
                    return {
                        'http_status': 200,
                        'body': _crear_orden_success_body(
                            exist,
                            preorden_id=pre_vinc,
                            convenio=_convenio_desde_tarifa_orden(exist, empresa),
                            medico_referidor=exist.medico_referente,
                            mensaje='Orden ya registrada (idempotencia).',
                            idempotent=True,
                        ),
                    }

            paciente_id = data.get('paciente_id')
            estudio_ids = data.get('estudio_ids') or data.get('lims_lineas') or []
            total = Decimal(str(data.get('total', 0)))
            anticipo = Decimal(str(data.get('anticipo', 0)))

            init_pago_efectivo = Decimal(str(data.get('init_pago_efectivo', 0)))
            init_pago_tarjeta = Decimal(str(data.get('init_pago_tarjeta', 0)))
            init_pago_transferencia = Decimal(str(data.get('init_pago_transferencia', 0)))

            if not paciente_id:
                return {
                    'http_status': 400,
                    'body': {'status': 'error', 'mensaje': 'Debe seleccionar un paciente'},
                }

            if not estudio_ids or len(estudio_ids) == 0:
                return {
                    'http_status': 400,
                    'body': {
                        'status': 'error',
                        'mensaje': (
                            'Debe agregar al menos un ítem del catálogo LIMS '
                            '(analito/perfil/paquete)'
                        ),
                    },
                }

            try:
                paciente = Paciente.objects.get(id=paciente_id, empresa=empresa)
            except Paciente.DoesNotExist:
                return {
                    'http_status': 404,
                    'body': {'status': 'error', 'mensaje': 'Paciente no encontrado'},
                }

            if isinstance(estudio_ids, (str, int)):
                estudio_ids = [estudio_ids]
            lineas = resolve_lims_cart_ids(list(estudio_ids), empresa=empresa)
            if len(lineas) != len(estudio_ids):
                return {
                    'http_status': 404,
                    'body': {
                        'status': 'error',
                        'mensaje': (
                            'No se pudieron resolver todos los ítems del catálogo LIMS. '
                            'Use los identificadores del buscador (analito:ID, perfil:ID, paquete:ID).'
                        ),
                    },
                }

            preorden_id = data.get('preorden_id')
            preorden = None
            if preorden_id:
                try:
                    preorden = PreOrdenLaboratorio.objects.get(
                        id=preorden_id,
                        empresa=empresa,
                        paciente=paciente,
                        estado='PENDIENTE',
                    )
                except PreOrdenLaboratorio.DoesNotExist:
                    pass

            tipo_servicio = data.get('tipo_servicio', 'RUTINA')
            tarifa = data.get('tarifa', 'PUBLICO_GENERAL')
            descuento_monto = Decimal(str(data.get('descuento_monto', 0)))
            folio_cliente_externo = data.get('folio_cliente_externo', '')
            diagnostico = data.get('diagnostico', '')
            notas_internas = data.get('notas_internas', '')
            hora_toma_muestra = data.get('hora_toma_muestra')
            hora_entrega_prometida = data.get('hora_entrega_prometida')

            req_factura = bool(data.get('req_factura', False))

            es_cxc = bool(data.get('es_abono_parcial', False))
            motivo_cxc = data.get('motivo_cxc', '') or ''
            nota_cxc = data.get('nota_cxc', '') or ''

            init_pago_credito = Decimal(str(data.get('init_pago_credito', 0)))
            init_pago_debito = Decimal(str(data.get('init_pago_debito', 0)))

            es_cortesia = data.get('es_cortesia', False)
            motivo_cortesia = data.get('motivo_cortesia', '')
            autorizado_por_cortesia = data.get('autorizado_por_cortesia', '')

            medico_referidor_id = data.get('medico_referidor_id')
            convenio_id = data.get('convenio_id')
            medico_referidor = None
            convenio = None

            if medico_referidor_id:
                try:
                    medico_referidor = Medico.objects.filter(
                        Q(empresa=empresa) | Q(empresa__isnull=True),
                        id=int(medico_referidor_id),
                    ).first()
                except Exception:
                    logging.getLogger(__name__).exception("Error inesperado en crear_desde_recepcion (orden_recepcion_service.py)")
                    medico_referidor = None

            if convenio_id:
                try:
                    convenio = Convenio.objects.filter(
                        empresa=empresa, activo=True, id=int(convenio_id)
                    ).first()
                except Exception:
                    logging.getLogger(__name__).exception("Error inesperado en crear_desde_recepcion (orden_recepcion_service.py)")
                    convenio = None

            precios_especiales = convenio_precio_map(convenio) if convenio else {}
            descuento_pct = Decimal('0.00')
            if convenio:
                descuento_pct = Decimal(str(convenio.descuento_porcentaje or 0))

            total_calculado = Decimal('0.00')
            for row in lineas:
                precio = aplicar_precio_convenio(
                    row['precio_base'], row['precio_key'], precios_especiales, descuento_pct
                )
                total_calculado += precio
            total_calculado = total_calculado.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

            total_original = total_calculado

            if es_cortesia:
                if not motivo_cortesia or not autorizado_por_cortesia:
                    return {
                        'http_status': 400,
                        'body': {
                            'status': 'error',
                            'mensaje': 'Cortesía requiere motivo y autorizador',
                        },
                    }
                total = Decimal('0.00')
                anticipo = Decimal('0.00')
                estado_pago = 'PAGADO'
                estado_orden = 'PAGADO'
            else:
                total = total_calculado
                if anticipo > total:
                    anticipo = total
                if anticipo >= total:
                    estado_pago = 'PAGADO'
                    estado_orden = 'PAGADO'
                elif anticipo > 0:
                    estado_pago = 'PARCIAL'
                    estado_orden = 'PENDIENTE_PAGO'
                else:
                    estado_pago = 'PENDIENTE'
                    estado_orden = 'PENDIENTE_PAGO'

            hora_toma = None
            hora_entrega = None
            if hora_toma_muestra:
                try:
                    hora_toma = datetime.fromisoformat(
                        hora_toma_muestra.replace('Z', '+00:00')
                    )
                    if timezone.is_naive(hora_toma):
                        hora_toma = timezone.make_aware(hora_toma)
                except (ValueError, TypeError):
                    hora_toma = timezone.localtime(timezone.now())
            if hora_entrega_prometida:
                try:
                    hora_entrega = datetime.fromisoformat(
                        hora_entrega_prometida.replace('Z', '+00:00')
                    )
                    if timezone.is_naive(hora_entrega):
                        hora_entrega = timezone.make_aware(hora_entrega)
                except (ValueError, TypeError):
                    pass

            orden = None
            folio_orden = None
            try:
                with transaction.atomic():
                    hoy = timezone.localtime(timezone.now())
                    folio_orden = _generar_folio_orden(empresa, hoy)

                    orden = OrdenDeServicio.objects.create(
                        empresa=empresa,
                        paciente=paciente,
                        total=total,
                        anticipo=anticipo,
                        estado=estado_orden,
                        estado_pago=estado_pago,
                        responsable_ingreso=request.user,
                        folio_orden=folio_orden,
                        tipo_servicio=tipo_servicio,
                        tarifa=(f'CONVENIO_{convenio.id}' if convenio else tarifa),
                        descuento_monto=descuento_monto,
                        folio_cliente_externo=folio_cliente_externo or None,
                        diagnostico=diagnostico or None,
                        notas_internas=notas_internas or None,
                        requiere_factura=req_factura,
                        hora_toma_muestra=hora_toma,
                        hora_entrega_prometida=hora_entrega,
                        medico_referente=medico_referidor,
                        es_cortesia=es_cortesia,
                        motivo_cortesia=motivo_cortesia or None,
                        autorizado_por_cortesia=autorizado_por_cortesia or None,
                        total_original=total_original if es_cortesia else None,
                        es_cxc=es_cxc,
                        motivo_cxc=motivo_cxc or None,
                        nota_cxc=nota_cxc or None,
                        client_mutation_id=cmid,
                    )

                    for row in lineas:
                        precio_momento = aplicar_precio_convenio(
                            row['precio_base'],
                            row['precio_key'],
                            precios_especiales,
                            descuento_pct,
                        )
                        desc = (row.get('descripcion_linea') or '')[:300]
                        DetalleOrden.objects.create(
                            orden=orden,
                            analito=row['analito'],
                            perfil_lims=row['perfil_lims'],
                            paquete_lims=row['paquete_lims'],
                            descripcion_linea=desc,
                            precio_momento=precio_momento,
                        )

                    if preorden:
                        preorden.estado = 'COBRADA'
                        preorden.orden_vinculada = orden
                        preorden.save()

                    if anticipo > 0:
                        from contabilidad.services.cfdi_borrador_auto import (
                            crear_borrador_cfdi_desde_pago_orden,
                        )

                        pago_inicial = PagoOrden.objects.create(
                            orden=orden,
                            usuario_registro=request.user,
                            monto_efectivo=init_pago_efectivo,
                            monto_credito=init_pago_credito,
                            monto_debito=init_pago_debito,
                            monto_tarjeta=init_pago_tarjeta,
                            monto_transferencia=init_pago_transferencia,
                            referencia_pago=None,
                        )
                        crear_borrador_cfdi_desde_pago_orden(pago_inicial, request.user)

                    registrar_auditoria(
                        accion='CREATE',
                        modelo='OrdenDeServicio',
                        objeto_id=str(orden.id),
                        datos_nuevos={
                            'folio_orden': orden.folio_orden or folio_orden,
                            'paciente_id': orden.paciente_id,
                            'total': str(orden.total),
                            'estado': orden.estado,
                        },
                        request=request,
                    )
            except IntegrityError:
                if cmid:
                    exist_o = OrdenDeServicio.objects.filter(
                        empresa=empresa, client_mutation_id=cmid
                    ).select_related('medico_referente').first()
                    if exist_o:
                        pre_vinc = PreOrdenLaboratorio.objects.filter(
                            orden_vinculada=exist_o
                        ).values_list('id', flat=True).first()
                        return {
                            'http_status': 200,
                            'body': _crear_orden_success_body(
                                exist_o,
                                preorden_id=pre_vinc,
                                convenio=_convenio_desde_tarifa_orden(exist_o, empresa),
                                medico_referidor=exist_o.medico_referente,
                                mensaje='Orden ya registrada (idempotencia).',
                                idempotent=True,
                            ),
                        }
                raise

            return {
                'http_status': 200,
                'body': _crear_orden_success_body(
                    orden,
                    preorden_id=preorden.id if preorden else None,
                    convenio=convenio,
                    medico_referidor=medico_referidor,
                ),
            }

        except json.JSONDecodeError as e:
            import traceback

            error_details = traceback.format_exc()
            logger_core.error(f'Error JSON en crear_desde_recepcion: {error_details}')
            return {
                'http_status': 400,
                'body': {
                    'status': 'error',
                    'mensaje': f'Error al procesar los datos JSON: {str(e)}',
                },
            }
        except Exception as e:
            logging.getLogger(__name__).exception("Error inesperado en crear_desde_recepcion (orden_recepcion_service.py)")
            import traceback

            error_details = traceback.format_exc()
            logger_core.error(f'Error en crear_desde_recepcion: {error_details}')
            error_msg = str(e)
            if (
                'unique constraint' in error_msg.lower()
                or 'duplicate' in error_msg.lower()
                or 'folio_orden' in error_msg.lower()
            ):
                error_msg = (
                    'Ya existe una orden con este folio. '
                    'El sistema intentará generar uno nuevo automáticamente.'
                )
            elif 'not null' in error_msg.lower():
                error_msg = f'Falta un campo requerido: {error_msg}'
            elif 'foreign key' in error_msg.lower():
                error_msg = (
                    'Error de referencia: Verifica que el paciente y los ítems LIMS existan.'
                )
            elif 'IntegrityError' in str(type(e)):
                error_msg = f'Error de integridad en la base de datos: {error_msg}'
            return {
                'http_status': 500,
                'body': {
                    'status': 'error',
                    'mensaje': error_msg,
                    'detalle': error_details if settings.DEBUG else None,
                },
            }