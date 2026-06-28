"""
Vistas de cobros del consultorio: cobro_consulta, api_registrar_cobro,
api_liquidar_vale, reporte_liquidacion.
"""
import json
import logging
from datetime import datetime
from decimal import Decimal

from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.utils import timezone
from django.http import JsonResponse
from django.db import transaction
from django.db.utils import DatabaseError
from django.core.exceptions import ValidationError
from django.db.models import Sum
from django.views.decorators.http import require_http_methods
from django.contrib import messages

from core.models import ConsultaMedica
from core.utils.empresa_request import empresa_efectiva_request

logger = logging.getLogger('consultorio')


# ==============================================================================
# COBRO DE CONSULTA (Control flexible)
# ==============================================================================

@login_required
def cobro_consulta(request):
    """
    FASE 10: Blindaje de Cobros - Consultorio Médico Independiente.
    Caja virtual segregada por médico con soporte para cobros mixtos,
    dinero en tránsito y dashboard privado.
    """
    from consultorio.models import (
        ConfiguracionMedico, CajaConsultorio, CobroConsulta, ValeLiquidacion
    )

    empresa = empresa_efectiva_request(request)
    if not empresa:
        messages.error(request, 'Usuario no tiene empresa asignada.')
        return redirect('home')

    hoy = timezone.localdate()
    inicio_semana = hoy - timezone.timedelta(days=hoy.weekday())
    inicio_mes = hoy.replace(day=1)

    config, _ = ConfiguracionMedico.objects.get_or_create(
        medico=request.user, defaults={'empresa': empresa}
    )

    caja_hoy, _ = CajaConsultorio.objects.get_or_create(
        medico=request.user, fecha=hoy, defaults={'empresa': empresa}
    )

    pendientes_cobro = ConsultaMedica.objects.filter(
        empresa=empresa,
        fecha_consulta__date=hoy,
        estado='FINALIZADA',
        pagada=False,
    ).select_related('paciente').order_by('-fecha_consulta')

    cobros_hoy = CobroConsulta.objects.filter(
        caja=caja_hoy, estado='PAGADO',
    ).select_related('consulta', 'paciente').order_by('-fecha_cobro')

    vales_pendientes = ValeLiquidacion.objects.filter(
        medico=request.user, estado__in=['PENDIENTE', 'PARCIAL'],
    ).select_related('cobro', 'cobro__consulta', 'cobro__paciente').order_by('-fecha_creacion')

    agg_hoy = cobros_hoy.aggregate(
        total=Sum('monto_total'),
        efectivo=Sum('monto_efectivo'),
        tarjeta=Sum('monto_tarjeta'),
        transferencia=Sum('monto_transferencia'),
    )
    ingresos_hoy = agg_hoy['total'] or Decimal('0')
    count_hoy = cobros_hoy.count()
    en_transito_hoy = vales_pendientes.aggregate(total=Sum('monto_adeudado'))['total'] or Decimal('0')
    ya_liquidado = vales_pendientes.aggregate(total=Sum('monto_liquidado'))['total'] or Decimal('0')

    stats_hoy = {
        'ingresos': float(ingresos_hoy),
        'efectivo': float(agg_hoy['efectivo'] or 0),
        'tarjeta': float(agg_hoy['tarjeta'] or 0),
        'transferencia': float(agg_hoy['transferencia'] or 0),
        'pagadas': count_hoy,
        'pendientes_cobro': pendientes_cobro.count(),
        'ticket_promedio': round(float(ingresos_hoy) / count_hoy, 0) if count_hoy > 0 else 0,
        'en_transito': float(en_transito_hoy - ya_liquidado),
    }

    cobros_semana = CobroConsulta.objects.filter(
        medico=request.user, estado='PAGADO',
        fecha_cobro__date__gte=inicio_semana, fecha_cobro__date__lte=hoy,
    )
    stats_semana = cobros_semana.aggregate(total=Sum('monto_total'))['total'] or 0

    cobros_mes = CobroConsulta.objects.filter(
        medico=request.user, estado='PAGADO',
        fecha_cobro__date__gte=inicio_mes, fecha_cobro__date__lte=hoy,
    )
    stats_mes = cobros_mes.aggregate(total=Sum('monto_total'))['total'] or 0

    return render(request, 'consultorio/cobro_consulta.html', {
        'config': config,
        'caja_hoy': caja_hoy,
        'pendientes_cobro': pendientes_cobro,
        'cobros_hoy': cobros_hoy,
        'vales_pendientes': vales_pendientes,
        'stats_hoy': stats_hoy,
        'stats_semana': float(stats_semana),
        'stats_mes': float(stats_mes),
    })


@login_required
@require_http_methods(["POST"])
def api_registrar_cobro(request):
    """API para registrar un cobro de consulta con soporte de pago mixto."""
    from consultorio.models import (
        CajaConsultorio, CobroConsulta, ValeLiquidacion, ConfiguracionMedico
    )

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Datos inválidos'}, status=400)

    consulta_id = data.get('consulta_id')
    monto_total = Decimal(str(data.get('monto_total', '0')))
    monto_efectivo = Decimal(str(data.get('monto_efectivo', '0')))
    monto_tarjeta = Decimal(str(data.get('monto_tarjeta', '0')))
    monto_transferencia = Decimal(str(data.get('monto_transferencia', '0')))
    concepto = data.get('concepto', 'CONSULTA')
    cobrado_por = data.get('cobrado_por', 'MEDICO')
    referencia = data.get('referencia_pago', '')
    notas = data.get('notas', '')

    if not consulta_id or monto_total <= 0:
        return JsonResponse({'error': 'Consulta y monto son requeridos'}, status=400)

    suma_parciales = monto_efectivo + monto_tarjeta + monto_transferencia
    if suma_parciales != monto_total:
        return JsonResponse({
            'error': f'Los montos parciales (${suma_parciales}) no coinciden con el total (${monto_total})'
        }, status=400)

    empresa = empresa_efectiva_request(request)
    if not empresa:
        return JsonResponse({'error': 'Usuario sin empresa asignada'}, status=403)
    try:
        consulta = ConsultaMedica.objects.get(id=consulta_id, empresa=empresa)
    except ConsultaMedica.DoesNotExist:
        return JsonResponse({'error': 'Consulta no encontrada'}, status=404)

    hoy = timezone.localdate()

    with transaction.atomic():
        caja, _ = CajaConsultorio.objects.get_or_create(
            medico=request.user, fecha=hoy, defaults={'empresa': empresa}
        )

        cobro = CobroConsulta.objects.create(
            empresa=empresa,
            caja=caja,
            consulta=consulta,
            paciente=consulta.paciente,
            medico=request.user,
            concepto=concepto,
            monto_total=monto_total,
            monto_efectivo=monto_efectivo,
            monto_tarjeta=monto_tarjeta,
            monto_transferencia=monto_transferencia,
            cobrado_por=cobrado_por,
            usuario_cobro=request.user,
            referencia_pago=referencia,
            notas=notas,
            estado='PAGADO',
        )

        consulta.pagada = True
        consulta.precio_consulta = monto_total
        consulta.save(update_fields=['pagada', 'precio_consulta'])

        caja.total_efectivo += monto_efectivo
        caja.total_tarjeta += monto_tarjeta
        caja.total_transferencia += monto_transferencia
        caja.consultas_cobradas += 1
        caja.save()

        vale_data = None
        if cobrado_por == 'RECEPCION':
            vale = ValeLiquidacion.objects.create(
                empresa=empresa,
                cobro=cobro,
                medico=request.user,
                monto_adeudado=monto_total,
                estado='PENDIENTE',
            )
            caja.total_en_transito += monto_total
            caja.save(update_fields=['total_en_transito'])
            vale_data = {
                'folio_vale': vale.folio_vale,
                'monto': float(vale.monto_adeudado),
            }

    response_data = {
        'success': True,
        'cobro_id': cobro.id,
        'folio_consulta': consulta.folio_consulta,
        'monto_total': float(monto_total),
        'metodo': cobro.get_metodo_pago_display(),
        'es_mixto': cobro.es_mixto,
    }
    if vale_data:
        response_data['vale'] = vale_data

    return JsonResponse(response_data)


@login_required
@require_http_methods(["POST"])
def api_liquidar_vale(request):
    """API para marcar un vale como liquidado."""
    from consultorio.models import ValeLiquidacion

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Datos inválidos'}, status=400)

    vale_id = data.get('vale_id')
    monto = Decimal(str(data.get('monto', '0')))

    empresa = empresa_efectiva_request(request)
    if not empresa:
        return JsonResponse({'error': 'Usuario sin empresa asignada'}, status=403)

    try:
        vale = ValeLiquidacion.objects.get(id=vale_id, medico=request.user, empresa=empresa)
    except ValeLiquidacion.DoesNotExist:
        return JsonResponse({'error': 'Vale no encontrado'}, status=404)

    if vale.estado == 'LIQUIDADO':
        return JsonResponse({'error': 'Este vale ya fue liquidado'}, status=400)

    with transaction.atomic():
        if monto <= 0:
            return JsonResponse({'error': 'El monto debe ser mayor a 0'}, status=400)

        if monto >= vale.saldo_pendiente:
            vale.monto_liquidado = vale.monto_adeudado
            vale.estado = 'LIQUIDADO'
        else:
            vale.monto_liquidado += monto
            vale.estado = 'PARCIAL'

        vale.liquidado_por = request.user
        vale.fecha_liquidacion = timezone.now()
        vale.save()

        caja = vale.cobro.caja
        caja.total_liquidado += monto if monto > 0 else vale.monto_adeudado
        caja.save(update_fields=['total_liquidado'])

    return JsonResponse({
        'success': True,
        'vale_folio': vale.folio_vale,
        'estado': vale.get_estado_display(),
        'saldo_pendiente': float(vale.saldo_pendiente),
    })


@login_required
def reporte_liquidacion(request):
    """Reporte de liquidación diaria."""
    from consultorio.models import ValeLiquidacion, CobroConsulta, CajaConsultorio
    from django.db.models import Sum

    empresa = empresa_efectiva_request(request)
    if not empresa:
        messages.error(request, 'Usuario no tiene empresa asignada.')
        return redirect('home')

    hoy = timezone.localdate()

    fecha_str = request.GET.get('fecha')
    if fecha_str:
        try:
            fecha = datetime.strptime(fecha_str, '%Y-%m-%d').date()
        except ValueError:
            fecha = hoy
    else:
        fecha = hoy

    vales_pendientes = ValeLiquidacion.objects.filter(
        medico=request.user, estado__in=['PENDIENTE', 'PARCIAL'],
    ).select_related('cobro', 'cobro__consulta', 'cobro__paciente')

    cobros_dia = CobroConsulta.objects.filter(
        medico=request.user, estado='PAGADO', fecha_cobro__date=fecha,
    ).select_related('consulta', 'paciente')

    total_pendiente = sum(v.saldo_pendiente for v in vales_pendientes)
    total_dia = cobros_dia.aggregate(total=Sum('monto_total'))['total'] or 0

    cajas_recientes = CajaConsultorio.objects.filter(
        medico=request.user,
    ).order_by('-fecha')[:7]

    return render(request, 'consultorio/reporte_liquidacion.html', {
        'fecha': fecha,
        'hoy': hoy,
        'vales_pendientes': vales_pendientes,
        'cobros_dia': cobros_dia,
        'total_pendiente': float(total_pendiente),
        'total_dia': float(total_dia),
        'cajas_recientes': cajas_recientes,
    })
