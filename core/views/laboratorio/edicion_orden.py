"""
APIs de edición post-creación (datos y estudios), preórdenes.
"""
import json
import logging
from decimal import Decimal

from django.shortcuts import get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.db import transaction
from django.db.models import Q

from core.models import (
    OrdenDeServicio, DetalleOrden,
    PreOrdenLaboratorio,
)
from core.lims_cart import (
    aplicar_precio_convenio,
    convenio_precio_map,
    detalle_orden_etiqueta,
    resolve_lims_cart_ids,
    resolve_lims_line,
)

from ._helpers import (
    _convenio_desde_tarifa,
    _lims_line_key_detalle,
    _lims_line_key_row,
    _detalle_codigo_lista,
)

logger = logging.getLogger('core')


@login_required
@require_http_methods(["GET"])
def api_datos_orden(request, orden_id):
    """Devuelve los datos completos de una orden para el panel de edición."""
    empresa = getattr(request.user, 'empresa', None)
    orden = get_object_or_404(
        OrdenDeServicio.objects.select_related('paciente', 'medico_referente')
                               .prefetch_related(
                                   'detalles__analito', 'detalles__perfil_lims', 'detalles__paquete_lims'
                               ),
        id=orden_id, empresa=empresa
    )
    estudios = []
    for d in orden.detalles.all():
        k = _lims_line_key_detalle(d)
        if k[0] is None:
            tid = f'legacy:{d.id}'
            estudios.append({
                'id': tid,
                'nombre': (d.descripcion_linea or 'Estudio legacy')[:300],
                'codigo': _detalle_codigo_lista(d),
                'precio': float(d.precio_momento or 0),
                'legacy': True,
            })
            continue
        tid = f'{k[0]}:{k[1]}'
        estudios.append({
            'id': tid,
            'nombre': detalle_orden_etiqueta(d),
            'codigo': _detalle_codigo_lista(d),
            'precio': float(d.precio_momento or 0),
        })
    return JsonResponse({
        'status': 'success',
        'orden': {
            'id': orden.id,
            'folio': orden.folio_orden or f'#{orden.id}',
            'paciente': orden.paciente.nombre_completo,
            'tipo_servicio': orden.tipo_servicio,
            'diagnostico': orden.diagnostico or '',
            'notas_internas': orden.notas_internas or '',
            'requiere_factura': orden.requiere_factura,
            'medico_id': orden.medico_referente_id,
            'medico_nombre': orden.medico_referente.nombre_completo if orden.medico_referente else '',
            'estudios': estudios,
            'total': float(orden.total),
            'anticipo': float(orden.anticipo),
            'saldo': float(max(orden.total - orden.anticipo, Decimal('0.00'))),
            'estado': orden.estado,
        }
    })


@login_required
@require_http_methods(["POST"])
def api_editar_datos_orden(request, orden_id):
    """
    Edición de Datos Generales (no financieros).
    Permite cambiar: médico, diagnóstico, notas, tipo_servicio, req_factura.
    NO recalcula el total ni afecta el saldo.
    """
    empresa = getattr(request.user, 'empresa', None)
    orden = get_object_or_404(OrdenDeServicio, id=orden_id, empresa=empresa)

    try:
        data = json.loads(request.body or '{}')
    except json.JSONDecodeError:
        return JsonResponse({'ok': False, 'error': 'JSON inválido'}, status=400)

    # Solo campos no financieros
    campos_actualizados = []
    if 'tipo_servicio' in data:
        orden.tipo_servicio = data['tipo_servicio']
        campos_actualizados.append('tipo_servicio')
    if 'diagnostico' in data:
        orden.diagnostico = data['diagnostico'] or None
        campos_actualizados.append('diagnostico')
    if 'notas_internas' in data:
        orden.notas_internas = data['notas_internas'] or None
        campos_actualizados.append('notas_internas')
    if 'requiere_factura' in data:
        orden.requiere_factura = bool(data['requiere_factura'])
        campos_actualizados.append('requiere_factura')
    if 'medico_id' in data:
        try:
            from core.models import Medico
            medico = Medico.objects.get(id=data['medico_id'], empresa=empresa) if data['medico_id'] else None
            orden.medico_referente = medico
            campos_actualizados.append('medico_referente')
        except (Medico.DoesNotExist, ValueError, TypeError):
            pass

    if campos_actualizados:
        orden.save(update_fields=campos_actualizados)

    return JsonResponse({
        'ok': True,
        'mensaje': 'Datos de la orden actualizados correctamente.',
        'campos_actualizados': campos_actualizados,
    })


@login_required
@require_http_methods(["POST"])
def api_editar_estudios_orden(request, orden_id):
    """
    Edición de líneas LIMS (financiero).
    Elimina detalles sin resultado, conserva los que ya tienen captura y agrega
    líneas nuevas del carrito LIMS. Recalcula total y estado de pago.
    """
    empresa = getattr(request.user, 'empresa', None)
    orden = get_object_or_404(
        OrdenDeServicio.objects.prefetch_related(
            'detalles__analito', 'detalles__perfil_lims', 'detalles__paquete_lims'
        ),
        id=orden_id, empresa=empresa
    )

    try:
        data = json.loads(request.body or '{}')
    except json.JSONDecodeError:
        return JsonResponse({'ok': False, 'error': 'JSON inválido'}, status=400)

    raw = data.get('estudio_ids') or data.get('lims_lineas') or []
    if isinstance(raw, (str, int)):
        raw = [raw]
    raw = [str(x).strip() for x in raw if str(x).strip()]

    legacy_detail_ids = set()
    lims_ids = []
    for item in raw:
        if item.startswith('legacy:'):
            try:
                legacy_detail_ids.add(int(item.split(':', 1)[1]))
            except (TypeError, ValueError):
                continue
        else:
            lims_ids.append(item)

    lineas = resolve_lims_cart_ids(lims_ids, empresa=empresa)
    if not lineas and not legacy_detail_ids:
        return JsonResponse(
            {'ok': False, 'error': 'Debe incluir al menos una línea de catálogo LIMS válida'},
            status=400,
        )

    convenio = _convenio_desde_tarifa(orden, empresa)
    precios_especiales = convenio_precio_map(convenio) if convenio else {}
    descuento_pct = (
        Decimal(str(convenio.descuento_porcentaje or 0)) if convenio else Decimal('0')
    )

    from django.db import transaction as _tx

    with _tx.atomic():
        orden = OrdenDeServicio.objects.select_for_update().get(id=orden_id, empresa=empresa)
        detalles_actuales = DetalleOrden.objects.filter(orden=orden)
        eliminables = detalles_actuales.filter(Q(resultado__isnull=True) | Q(resultado=''))
        if legacy_detail_ids:
            eliminables = eliminables.exclude(id__in=legacy_detail_ids)
        eliminables.delete()
        preserved = list(
            DetalleOrden.objects.filter(orden=orden).select_related(
                'analito', 'perfil_lims', 'paquete_lims'
            )
        )
        nuevo_total = sum((d.precio_momento for d in preserved), Decimal('0.00'))
        existing_keys = {_lims_line_key_detalle(d) for d in preserved}

        for row in lineas:
            k = _lims_line_key_row(row)
            if k[0] is None or k in existing_keys:
                continue
            precio_momento = aplicar_precio_convenio(
                row['precio_base'], row['precio_key'], precios_especiales, descuento_pct
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
            existing_keys.add(k)
            nuevo_total += precio_momento

        orden.total = nuevo_total
        saldo = max(nuevo_total - orden.anticipo, Decimal('0.00'))
        if saldo <= Decimal('0.01'):
            orden.estado_pago = 'PAGADO'
        elif orden.anticipo > 0:
            orden.estado_pago = 'PARCIAL'
        else:
            orden.estado_pago = 'PENDIENTE'
        orden.save(update_fields=['total', 'estado_pago'])

    return JsonResponse({
        'ok': True,
        'mensaje': 'Líneas LIMS actualizadas. El total ha sido recalculado.',
        'nuevo_total': float(nuevo_total),
        'anticipo': float(orden.anticipo),
        'nuevo_saldo': float(saldo),
        'candado_activo': saldo > Decimal('0.01'),
        'alerta_saldo': (
            f'El total ha cambiado. Se requiere cubrir el nuevo saldo de '
            f'${saldo:.2f} para liberar resultados.'
            if saldo > Decimal('0.01') else None
        ),
    })


@login_required
def api_preordenes_pendientes(request):
    """
    API que busca si un paciente tiene pre-órdenes pendientes enviadas por el médico.
    Recibe: ?paciente_id=123
    """
    empresa = getattr(request.user, 'empresa', None)
    if not empresa:
        return JsonResponse({'status': 'error', 'mensaje': 'Usuario sin empresa asignada'}, status=403)
    paciente_id = request.GET.get('paciente_id')
    if not paciente_id:
        return JsonResponse({'status': 'error', 'mensaje': 'Falta paciente_id'}, status=400)

    try:
        # Busca pre-órdenes PENDIENTES del paciente
        preordenes = PreOrdenLaboratorio.objects.filter(
            paciente_id=paciente_id,
            empresa=empresa,
            estado='PENDIENTE'
        ).select_related('medico_solicitante').prefetch_related(
            'detalles__analito', 'detalles__perfil_lims', 'detalles__paquete_lims'
        ).order_by('-fecha_creacion')

        data = []
        for p in preordenes:
            estudios = [detalle_orden_etiqueta(d) for d in p.detalles.all()]
            medico_nombre = f"{p.medico_solicitante.get_full_name()}" if p.medico_solicitante else "N/A"

            data.append({
                'id': p.id,
                'medico': medico_nombre,
                'fecha': timezone.localtime(p.fecha_creacion).strftime('%d/%m/%Y %H:%M'),
                'estudios': estudios,
                'observaciones': p.observaciones or "",
                'fecha_creacion': p.fecha_creacion.isoformat()
            })

        return JsonResponse({'status': 'success', 'preordenes': data})

    except (PreOrdenLaboratorio.DoesNotExist, ValueError, TypeError) as e:
        return JsonResponse({'status': 'error', 'mensaje': str(e)}, status=500)


@login_required
def api_cargar_preorden(request):
    """
    API para cargar los estudios de una pre-orden en el formulario de recepción.
    Recibe: POST con preorden_id
    """
    from django.utils import timezone

    empresa = getattr(request.user, 'empresa', None)
    if not empresa:
        return JsonResponse({'status': 'error', 'mensaje': 'Usuario sin empresa asignada'}, status=403)
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'mensaje': 'Método no permitido'}, status=405)

    try:
        data = json.loads(request.body) if request.body else {}
        preorden_id = data.get('preorden_id')

        if not preorden_id:
            return JsonResponse({'status': 'error', 'mensaje': 'Falta preorden_id'}, status=400)

        # Buscar la pre-orden
        preorden = get_object_or_404(
            PreOrdenLaboratorio,
            id=preorden_id,
            empresa=empresa,
            estado='PENDIENTE'  # Solo cargar si está pendiente
        )

        detalles = preorden.detalles.select_related(
            'analito', 'perfil_lims', 'paquete_lims'
        ).all()
        estudios_ids = []
        estudios_data = []
        for d in detalles:
            row = None
            if d.analito_id:
                row = resolve_lims_line('analito', d.analito_id, empresa=empresa)
            elif d.perfil_lims_id:
                row = resolve_lims_line('perfil', d.perfil_lims_id, empresa=empresa)
            elif d.paquete_lims_id:
                row = resolve_lims_line('paquete', d.paquete_lims_id, empresa=empresa)
            if not row:
                continue
            tid = row['precio_key']
            estudios_ids.append(tid)
            codigo = ''
            nombre = row['descripcion_linea'] or ''
            if row['analito']:
                codigo = row['analito'].codigo or ''
                nombre = row['analito'].nombre
            elif row['perfil_lims']:
                nombre = row['perfil_lims'].nombre
            elif row['paquete_lims']:
                nombre = row['paquete_lims'].nombre
            estudios_data.append({
                'id': tid,
                'codigo': codigo,
                'nombre': nombre,
                'precio': float(row['precio_base']),
            })

        return JsonResponse({
            'status': 'success',
            'preorden_id': preorden.id,
            'estudios_ids': estudios_ids,
            'estudios': estudios_data,
            'medico': preorden.medico_solicitante.get_full_name() if preorden.medico_solicitante else "N/A",
            'observaciones': preorden.observaciones or "",
            'mensaje': f'Pre-orden cargada: {len(estudios_ids)} estudios del Dr. {preorden.medico_solicitante.get_full_name() if preorden.medico_solicitante else "N/A"}'
        })

    except PreOrdenLaboratorio.DoesNotExist:
        return JsonResponse({'status': 'error', 'mensaje': 'Pre-orden no encontrada o ya fue procesada'}, status=404)
    except (json.JSONDecodeError, ValueError, TypeError, KeyError) as e:
        return JsonResponse({'status': 'error', 'mensaje': str(e)}, status=500)
