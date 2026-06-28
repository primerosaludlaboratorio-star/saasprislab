"""
Tickets, cobros, historial de pagos, cancelaciones.
"""
import json
import logging
from decimal import Decimal, ROUND_HALF_UP, InvalidOperation
from datetime import timedelta

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.http import require_http_methods
from django.db import transaction, IntegrityError
from django.db import models

from core.models import (
    OrdenDeServicio, PagoOrden,
)
from core.services.lims import parse_optional_client_mutation_uuid

logger = logging.getLogger('core')
logger_core = logging.getLogger('core')


@login_required
def imprimir_ticket_lab(request, orden_id):
    """Genera el ticket térmico de impresión para una orden de laboratorio."""
    empresa = getattr(request.user, 'empresa', None)
    if not empresa:
        return redirect('home')
    try:
        orden = OrdenDeServicio.objects.select_related('paciente', 'empresa').prefetch_related(
            'detalles__analito', 'detalles__perfil_lims', 'detalles__paquete_lims'
        ).get(id=orden_id, empresa=empresa)
    except OrdenDeServicio.DoesNotExist:
        return render(request, 'core/error.html', {
            'mensaje': 'Orden no encontrada'
        }, status=404)

    mayor_dias_entrega = 0
    fecha_entrega_estimada = timezone.localtime(timezone.now()) + timedelta(days=mayor_dias_entrega)
    # Ajustar a las 5:00 PM del día de entrega
    fecha_entrega_estimada = fecha_entrega_estimada.replace(hour=17, minute=0, second=0, microsecond=0)

    detalles = orden.detalles.select_related(
        'analito', 'perfil_lims', 'paquete_lims'
    ).all()

    # Calcular saldo pendiente
    pagado = orden.anticipo or Decimal('0.00')
    saldo_pendiente = (orden.total or Decimal('0.00')) - pagado

    # Obtener informacion de pago
    pago_info = None
    try:
        pago_info = PagoOrden.objects.filter(orden=orden).order_by('-fecha_pago').first()
    except PagoOrden.DoesNotExist:
        pass

    return render(request, 'core/ticket_lab.html', {
        'orden': orden,
        'detalles': detalles,
        'fecha_entrega': fecha_entrega_estimada,
        'fecha_entrega_estimada': fecha_entrega_estimada,
        'pagado': pagado,
        'saldo_pendiente': saldo_pendiente,
        'pago_info': pago_info,
        'empresa': empresa,
    })


@login_required
@require_http_methods(["POST"])
def api_cobrar_orden(request, orden_id):
    """
    API para cobrar una orden de laboratorio (cobro inmediato desde Recepción).
    Actualiza el anticipo y estado de pago.
    """
    empresa = getattr(request.user, 'empresa', None)
    if not empresa:
        return JsonResponse({'status': 'error', 'mensaje': 'Usuario sin empresa asignada'}, status=403)
    usuario = request.user

    try:
        # Validar que el request tenga body
        if not request.body:
            return JsonResponse({'status': 'error', 'mensaje': 'No se recibieron datos'}, status=400)

        # Parsear JSON
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError as e:
            return JsonResponse({'status': 'error', 'mensaje': f'Error al procesar los datos JSON: {str(e)}'}, status=400)

        try:
            cmid_pay = parse_optional_client_mutation_uuid(data.get('client_mutation_id'))
        except ValueError:
            return JsonResponse(
                {'status': 'error', 'mensaje': 'client_mutation_id no es un UUID válido'},
                status=400,
            )

        # Obtener la orden
        try:
            orden = OrdenDeServicio.objects.select_related('paciente', 'empresa').get(id=orden_id, empresa=empresa)
        except OrdenDeServicio.DoesNotExist:
            return JsonResponse({'status': 'error', 'mensaje': 'Orden no encontrada'}, status=404)

        if cmid_pay:
            dup = PagoOrden.objects.filter(orden=orden, client_mutation_id=cmid_pay, cancelado=False).first()
            if dup:
                orden.refresh_from_db()
                return JsonResponse({
                    'status': 'success',
                    'mensaje': 'Pago ya registrado (idempotencia).',
                    'orden_id': orden.id,
                    'anticipo_actual': float(orden.anticipo),
                    'saldo_pendiente': float(orden.total - orden.anticipo),
                    'estado_pago': orden.estado_pago,
                    'idempotent_replay': True,
                }, status=200)

        # CICLO 14: Normalizar montos a 2 decimales y validar rango (evitar overflow DecimalField)
        _max_monto = Decimal('99999999.99')
        def _moneto(s, default=0):
            try:
                d = Decimal(str(s))
            except (InvalidOperation, TypeError):
                return Decimal(str(default))
            return d.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        monto_pago = _moneto(data.get('monto', 0))
        monto_efectivo = _moneto(data.get('monto_efectivo', 0))
        monto_tarjeta = _moneto(data.get('monto_tarjeta', 0))
        monto_transferencia = _moneto(data.get('monto_transferencia', 0))
        if monto_pago > _max_monto or monto_efectivo > _max_monto or monto_tarjeta > _max_monto or monto_transferencia > _max_monto:
            return JsonResponse({'status': 'error', 'mensaje': 'Algún monto excede el rango permitido (máx. 99,999,999.99)'}, status=400)
        referencia_pago = data.get('referencia_pago', '').strip() if data.get('referencia_pago') else ''
        if monto_efectivo < 0 or monto_tarjeta < 0 or monto_transferencia < 0:
            return JsonResponse({'status': 'error', 'mensaje': 'Los montos de pago no pueden ser negativos.'}, status=400)

        # BITÁCORA DE TRANSACCIÓN CRÍTICA: Inicio de cobro
        try:
            logger_core.info(
                f"Iniciando intento de cobro (LABORATORIO) - "
                f"Usuario: {usuario.username} (ID: {usuario.id}) - "
                f"Orden ID: {orden_id} - "
                f"Monto: ${monto_pago:.2f} - "
                f"Empresa: {empresa.nombre}"
            )
        except (OSError, ValueError, TypeError):
            pass

        # Si no hay monto total pero sí hay montos multimodales, calcular el total
        if monto_pago == 0:
            monto_pago = monto_efectivo + monto_tarjeta + monto_transferencia

        # Validar que el monto sea mayor a cero
        if monto_pago <= 0:
            return JsonResponse({'status': 'error', 'mensaje': 'El monto debe ser mayor a cero'}, status=400)

        # Validar que los montos multimodales sumen correctamente (si se proporcionaron)
        suma_modos = monto_efectivo + monto_tarjeta + monto_transferencia
        if suma_modos > 0 and abs(suma_modos - monto_pago) > Decimal('0.01'):  # Tolerancia de 1 centavo
            return JsonResponse({
                'status': 'error',
                'mensaje': f'Los montos multimodales (${suma_modos}) no coinciden con el monto total (${monto_pago})'
            }, status=400)

        # Si no se proporcionaron montos multimodales, asumir que todo es efectivo
        if suma_modos == 0:
            monto_efectivo = monto_pago
            monto_tarjeta = Decimal('0')
            monto_transferencia = Decimal('0')

        # Actualizar anticipo y estado con transacción atómica + bloqueo de fila para evitar cobro doble
        try:
            with transaction.atomic():
                orden = OrdenDeServicio.objects.select_for_update().get(id=orden_id, empresa=empresa)
                nuevo_anticipo = orden.anticipo + monto_pago

                # Determinar estado de pago
                if nuevo_anticipo >= orden.total:
                    estado_pago = 'PAGADO'
                    estado_orden = 'PAGADO'
                elif nuevo_anticipo > 0:
                    estado_pago = 'PARCIAL'
                    estado_orden = 'PENDIENTE_PAGO'
                else:
                    estado_pago = 'PENDIENTE'
                    estado_orden = 'PENDIENTE_PAGO'

                # Actualizar orden
                orden.anticipo = nuevo_anticipo
                orden.estado_pago = estado_pago
                orden.estado = estado_orden
                orden.save()

                # Registrar el pago multimodal en la base de datos para auditoría
                from contabilidad.services.cfdi_borrador_auto import (
                    crear_borrador_cfdi_desde_pago_orden,
                )

                pago_reg = PagoOrden.objects.create(
                    orden=orden,
                    monto_efectivo=monto_efectivo,
                    monto_tarjeta=monto_tarjeta,
                    monto_transferencia=monto_transferencia,
                    referencia_pago=referencia_pago if referencia_pago else None,
                    usuario_registro=request.user,
                    client_mutation_id=cmid_pay,
                )
                crear_borrador_cfdi_desde_pago_orden(pago_reg, request.user)
        except IntegrityError:
            if cmid_pay:
                dup = PagoOrden.objects.filter(
                    orden_id=orden_id, client_mutation_id=cmid_pay, cancelado=False
                ).first()
                if dup:
                    orden = OrdenDeServicio.objects.get(id=orden_id, empresa=empresa)
                    return JsonResponse({
                        'status': 'success',
                        'mensaje': 'Pago ya registrado (idempotencia).',
                        'orden_id': orden.id,
                        'anticipo_actual': float(orden.anticipo),
                        'saldo_pendiente': float(orden.total - orden.anticipo),
                        'estado_pago': orden.estado_pago,
                        'idempotent_replay': True,
                    }, status=200)
            raise

        return JsonResponse({
            'status': 'success',
            'mensaje': 'Pago registrado correctamente',
            'orden_id': orden.id,
            'anticipo_actual': float(nuevo_anticipo),
            'saldo_pendiente': float(orden.total - nuevo_anticipo),
            'estado_pago': estado_pago
        })

    except OrdenDeServicio.DoesNotExist:
        return JsonResponse({'status': 'error', 'mensaje': 'Orden no encontrada'}, status=404)
    except json.JSONDecodeError as e:
        # BITÁCORA DE TRANSACCIÓN CRÍTICA: Fallo en cobro
        try:
            logger_core.error(
                f"FALLO EN COBRO (LABORATORIO) - "
                f"Usuario: {usuario.username} (ID: {usuario.id}) - "
                f"Orden ID: {orden_id} - "
                f"Error: JSON inválido - {str(e)} - "
                f"Empresa: {empresa.nombre}"
            )
        except (OSError, ValueError, TypeError):
            pass
        return JsonResponse({'status': 'error', 'mensaje': f'Error al procesar los datos JSON: {str(e)}'}, status=400)
    except ValueError as e:
        # BITÁCORA DE TRANSACCIÓN CRÍTICA: Fallo en cobro
        try:
            logger_core.error(
                f"FALLO EN COBRO (LABORATORIO) - "
                f"Usuario: {usuario.username} (ID: {usuario.id}) - "
                f"Orden ID: {orden_id} - "
                f"Error: Validación - {str(e)} - "
                f"Empresa: {empresa.nombre}"
            )
        except (OSError, ValueError, TypeError):
            pass
        return JsonResponse({'status': 'error', 'mensaje': f'Error de validación: {str(e)}'}, status=400)
    except (IntegrityError, OperationalError, ValueError, TypeError) as e:
        import traceback
        error_details = traceback.format_exc()

        # BITÁCORA DE TRANSACCIÓN CRÍTICA: Fallo en cobro — handler de último recurso de transacción financiera
        try:
            logger_core.error(
                f"FALLO EN COBRO (LABORATORIO) - "
                f"Usuario: {usuario.username} (ID: {usuario.id}) - "
                f"Orden ID: {orden_id} - "
                f"Error: {str(e)} - "
                f"Tipo: {type(e).__name__} - "
                f"Traceback: {error_details[:500]} - "
                f"Empresa: {empresa.nombre}"
            )
        except (OSError, ValueError, TypeError):
            pass

        logger_core.error(f"Error en api_cobrar_orden: {error_details}")
        return JsonResponse({
            'status': 'error',
            'mensaje': f'Error inesperado al procesar el pago: {str(e)}',
            'detalle': error_details if settings.DEBUG else None
        }, status=500)


@login_required
@require_http_methods(["GET"])
def api_historial_pagos(request, orden_id):
    """Devuelve todos los pagos (activos y cancelados) de una OrdenDeServicio."""
    empresa = getattr(request.user, 'empresa', None)
    if not empresa:
        return JsonResponse({'status': 'error', 'mensaje': 'Sin empresa'}, status=403)

    orden = get_object_or_404(OrdenDeServicio, id=orden_id, empresa=empresa)

    pagos = orden.pagos_realizados.select_related('usuario_registro', 'cancelado_por').all()
    resultado = []
    for p in pagos:
        resultado.append({
            'id': p.id,
            'fecha': timezone.localtime(p.fecha_pago).strftime('%d/%m/%Y %H:%M'),
            'usuario': p.usuario_registro.get_full_name() if p.usuario_registro else '—',
            'efectivo': float(p.monto_efectivo),
            'credito':  float(p.monto_credito),
            'debito':   float(p.monto_debito),
            'transferencia': float(p.monto_transferencia),
            'total': float(p.monto_bruto),
            'cancelado': p.cancelado,
            'cancelado_por': p.cancelado_por.get_full_name() if p.cancelado_por else None,
            'fecha_cancelacion': timezone.localtime(p.fecha_cancelacion).strftime('%d/%m/%Y %H:%M') if p.fecha_cancelacion else None,
            'motivo_cancelacion': p.motivo_cancelacion or '',
        })

    saldo_actual = max(
        orden.total - sum(
            Decimal(str(p.monto_bruto)) for p in pagos if not p.cancelado
        ),
        Decimal('0.00')
    )

    return JsonResponse({
        'status': 'success',
        'pagos': resultado,
        'total_orden': float(orden.total),
        'saldo_actual': float(saldo_actual),
        'anticipo_registrado': float(orden.anticipo),
    })


@login_required
@require_http_methods(["POST"])
def api_cancelar_pago(request, pago_id):
    """
    Cancela un PagoOrden y recalcula el anticipo de la OrdenDeServicio.
    Requiere rol con permiso (staff o admin).
    """
    if not (request.user.is_staff or request.user.is_superuser or
            getattr(request.user, 'rol', '') in ['ADMIN', 'DIRECTOR', 'QUIMICO']):
        return JsonResponse({'ok': False, 'error': 'Sin permisos para cancelar pagos'}, status=403)

    empresa = getattr(request.user, 'empresa', None)
    if not empresa:
        return JsonResponse({'ok': False, 'error': 'Sin empresa'}, status=403)

    try:
        pago = PagoOrden.objects.select_related('orden').get(
            id=pago_id, orden__empresa=empresa
        )
    except PagoOrden.DoesNotExist:
        return JsonResponse({'ok': False, 'error': 'Pago no encontrado'}, status=404)

    if pago.cancelado:
        return JsonResponse({'ok': False, 'error': 'Este pago ya estaba cancelado'}, status=400)

    try:
        data = json.loads(request.body or '{}')
    except (json.JSONDecodeError, UnicodeDecodeError):
        data = {}
    motivo = data.get('motivo', '').strip() or 'Sin motivo especificado'

    from django.db import transaction as _tx
    with _tx.atomic():
        pago.cancelado = True
        pago.cancelado_por = request.user
        pago.fecha_cancelacion = timezone.now()
        pago.motivo_cancelacion = motivo
        pago.save(update_fields=['cancelado', 'cancelado_por', 'fecha_cancelacion', 'motivo_cancelacion'])

        # Recalcular anticipo de la orden
        orden = pago.orden
        nuevo_anticipo = orden.pagos_realizados.filter(cancelado=False).aggregate(
            total=models.Sum(
                models.ExpressionWrapper(
                    models.F('monto_efectivo') + models.F('monto_tarjeta') + models.F('monto_transferencia'),
                    output_field=models.DecimalField()
                )
            )
        )['total'] or Decimal('0.00')

        orden.anticipo = nuevo_anticipo
        # Actualizar estado_pago
        saldo = max(orden.total - nuevo_anticipo, Decimal('0.00'))
        if saldo <= Decimal('0.01'):
            orden.estado_pago = 'PAGADO'
        elif nuevo_anticipo > 0:
            orden.estado_pago = 'PARCIAL'
        else:
            orden.estado_pago = 'PENDIENTE'
        orden.save(update_fields=['anticipo', 'estado_pago'])

    return JsonResponse({
        'ok': True,
        'mensaje': 'Pago cancelado correctamente. Saldo recalculado.',
        'nuevo_anticipo': float(nuevo_anticipo),
        'nuevo_saldo': float(saldo),
        'candado_activo': saldo > Decimal('0.01'),
    })
