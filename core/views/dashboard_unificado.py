"""
Dashboard unificado de PRISLAB.

Consolida KPIs operativos de farmacia, laboratorio, nomina, marketing,
logistica y auditoria sin depender de datos simulados.
"""
from datetime import datetime, timedelta
from decimal import Decimal
import json

from django.contrib.auth.decorators import login_required
from django.db.models import Count, DecimalField, ExpressionWrapper, F, Sum, Value
from django.db.models.functions import Coalesce
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.utils import timezone

from core.models import (
    AuditLog,
    DetalleVenta,
    Empresa,
    OrdenDeServicio,
    Paciente,
    Producto,
    ReciboNomina,
    Venta,
)
import logging

try:
    from marketing.models import CuponUso, ProspectoCRM
    MARKETING_AVAILABLE = True
except ImportError:
    CuponUso = None
    ProspectoCRM = None
    MARKETING_AVAILABLE = False

try:
    from logistica.models import TransferenciaInventario
    LOGISTICA_AVAILABLE = True
except ImportError:
    TransferenciaInventario = None
    LOGISTICA_AVAILABLE = False

LABORATORIO_AVAILABLE = True


def _parse_fecha_segura(valor, default):
    """Convierte yyyy-mm-dd sin romper el dashboard por filtros manuales."""
    if not valor:
        return default
    try:
        return datetime.strptime(valor, '%Y-%m-%d').date()
    except (TypeError, ValueError):
        return default


def _sumar_costo_ventas(empresa, fecha_inicio, fecha_fin=None):
    filtros = {
        'venta__empresa': empresa,
        'venta__estado': 'COMPLETADA',
    }
    if fecha_fin is None:
        filtros['venta__fecha__date'] = fecha_inicio
    else:
        filtros['venta__fecha__date__range'] = [fecha_inicio, fecha_fin]

    costo_unitario = Coalesce(
        F('costo_unitario_momento'),
        Value(Decimal('0.00')),
        output_field=DecimalField(max_digits=10, decimal_places=2),
    )
    costo_partida = ExpressionWrapper(
        costo_unitario * F('cantidad'),
        output_field=DecimalField(max_digits=12, decimal_places=2),
    )

    return DetalleVenta.objects.filter(**filtros).aggregate(
        total=Coalesce(
            Sum(costo_partida),
            Value(Decimal('0.00')),
            output_field=DecimalField(max_digits=12, decimal_places=2),
        )
    )['total'] or Decimal('0.00')


@login_required
def dashboard_unificado(request):
    """
    Dashboard unificado con KPIs de todos los modulos.
    Vista centralizada para toma de decisiones ejecutivas.
    """
    empresa = getattr(request.user, 'empresa', None)
    if not empresa:
        from django.contrib import messages

        messages.error(request, 'Usuario no tiene empresa asignada.')
        return redirect('home')

    hoy = timezone.localdate()
    fecha_inicio_dt = _parse_fecha_segura(
        request.GET.get('fecha_inicio'),
        hoy - timedelta(days=30),
    )
    fecha_fin_dt = _parse_fecha_segura(request.GET.get('fecha_fin'), hoy)
    if fecha_inicio_dt > fecha_fin_dt:
        fecha_inicio_dt, fecha_fin_dt = fecha_fin_dt, fecha_inicio_dt

    fecha_inicio = fecha_inicio_dt.strftime('%Y-%m-%d')
    fecha_fin = fecha_fin_dt.strftime('%Y-%m-%d')

    ventas = Venta.objects.filter(
        empresa=empresa,
        fecha__date__range=[fecha_inicio_dt, fecha_fin_dt],
        estado='COMPLETADA',
    )
    total_ventas = ventas.aggregate(
        total=Coalesce(
            Sum('total'),
            Value(Decimal('0.00')),
            output_field=DecimalField(max_digits=12, decimal_places=2),
        )
    )['total'] or Decimal('0.00')

    total_compras = _sumar_costo_ventas(empresa, fecha_inicio_dt, fecha_fin_dt)
    utilidad_bruta = total_ventas - total_compras
    margen_bruto = (utilidad_bruta / total_ventas * 100) if total_ventas > 0 else Decimal('0.00')

    ordenes_lab = OrdenDeServicio.objects.filter(
        empresa=empresa,
        fecha_creacion__date__range=[fecha_inicio_dt, fecha_fin_dt],
    )
    total_ordenes_lab = ordenes_lab.count()
    ordenes_validadas = ordenes_lab.filter(estado__in=['RESULTADOS_LISTOS', 'ENTREGADO']).count()
    tasa_validacion = (
        ordenes_validadas / total_ordenes_lab * 100
    ) if total_ordenes_lab > 0 else Decimal('0.00')

    total_polizas = 0

    recibos_nomina = ReciboNomina.objects.filter(
        empresa=empresa,
        periodo__fecha_inicio__lte=fecha_fin_dt,
        periodo__fecha_fin__gte=fecha_inicio_dt,
    )
    total_nominas = recibos_nomina.count()
    total_pagado_nomina = recibos_nomina.filter(pagado=True).aggregate(
        total=Coalesce(
            Sum('neto_pagar'),
            Value(Decimal('0.00')),
            output_field=DecimalField(max_digits=12, decimal_places=2),
        )
    )['total'] or Decimal('0.00')

    total_clientes = Paciente.objects.filter(empresa=empresa).count()
    if MARKETING_AVAILABLE and ProspectoCRM is not None:
        oportunidades = ProspectoCRM.objects.filter(empresa=empresa).exclude(estado__in=['GANADO', 'PERDIDO'])
        oportunidades_abiertas = oportunidades.count()
        valor_pipeline = oportunidades.aggregate(
            total=Coalesce(
                Sum('valor_estimado'),
                Value(Decimal('0.00')),
                output_field=DecimalField(max_digits=12, decimal_places=2),
            )
        )['total'] or Decimal('0.00')
    else:
        oportunidades_abiertas = 0
        valor_pipeline = Decimal('0.00')

    if MARKETING_AVAILABLE and CuponUso is not None:
        usos_cupon = CuponUso.objects.filter(
            empresa=empresa,
            creado_en__date__range=[fecha_inicio_dt, fecha_fin_dt],
        )
        cantidad_cupones_usados = usos_cupon.count()
        ventas_cupon_ids = usos_cupon.filter(venta__isnull=False).values_list('venta_id', flat=True).distinct()
        total_ventas_cupon = Venta.objects.filter(id__in=ventas_cupon_ids).aggregate(
            total=Coalesce(
                Sum('total'),
                Value(Decimal('0.00')),
                output_field=DecimalField(max_digits=12, decimal_places=2),
            )
        )['total'] or Decimal('0.00')
        porcentaje_ventas_marketing = (
            total_ventas_cupon / total_ventas * 100
        ) if total_ventas > 0 else Decimal('0.00')
    else:
        total_ventas_cupon = Decimal('0.00')
        cantidad_cupones_usados = 0
        porcentaje_ventas_marketing = Decimal('0.00')

    if LOGISTICA_AVAILABLE and TransferenciaInventario is not None:
        transferencias = TransferenciaInventario.objects.filter(
            empresa=empresa,
            fecha_creacion__date__range=[fecha_inicio_dt, fecha_fin_dt],
        )
        total_transferencias = transferencias.count()
        transferencias_completadas = transferencias.filter(
            estado=TransferenciaInventario.ESTADO_COMPLETADA,
        ).count()
        tasa_completitud_transferencias = (
            transferencias_completadas / total_transferencias * 100
        ) if total_transferencias > 0 else Decimal('0.00')
    else:
        total_transferencias = 0
        transferencias_completadas = 0
        tasa_completitud_transferencias = Decimal('0.00')

    total_operaciones = AuditLog.objects.filter(
        empresa=empresa,
        fecha_cierta__date__range=[fecha_inicio_dt, fecha_fin_dt],
    ).count()

    ultimos_7_dias = []
    fecha_actual = fecha_fin_dt - timedelta(days=6)
    while fecha_actual <= fecha_fin_dt:
        ventas_dia = Venta.objects.filter(
            empresa=empresa,
            fecha__date=fecha_actual,
            estado='COMPLETADA',
        ).aggregate(
            total=Coalesce(
                Sum('total'),
                Value(Decimal('0.00')),
                output_field=DecimalField(max_digits=12, decimal_places=2),
            )
        )['total'] or Decimal('0.00')
        compras_dia = _sumar_costo_ventas(empresa, fecha_actual)

        ultimos_7_dias.append({
            'fecha': fecha_actual.strftime('%Y-%m-%d'),
            'ventas': float(ventas_dia),
            'compras': float(compras_dia),
            'utilidad': float(ventas_dia - compras_dia),
        })
        fecha_actual += timedelta(days=1)

    operaciones_por_modulo = [
        {'modulo': item['modelo_afectado'] or 'General', 'total': item['total']}
        for item in AuditLog.objects.filter(
            empresa=empresa,
            fecha_cierta__date__range=[fecha_inicio_dt, fecha_fin_dt],
        ).values('modelo_afectado').annotate(total=Count('id')).order_by('-total')[:8]
    ]

    datos_operaciones_modulo = {
        'labels': [op['modulo'] for op in operaciones_por_modulo],
        'valores': [op['total'] for op in operaciones_por_modulo],
    }

    alertas = []

    productos_bajo_stock = Producto.objects.filter(
        empresa=empresa,
        stock__gt=0,
        stock__lt=F('stock_minimo'),
    ).count()
    if productos_bajo_stock > 0:
        alertas.append({
            'tipo': 'warning',
            'modulo': 'FARMACIA',
            'mensaje': f'{productos_bajo_stock} productos con stock bajo',
            'accion': 'Revisar inventario y realizar compras',
        })

    if LOGISTICA_AVAILABLE and TransferenciaInventario is not None:
        transferencias_pendientes = TransferenciaInventario.objects.filter(
            empresa=empresa,
            estado__in=[
                TransferenciaInventario.ESTADO_BORRADOR,
                TransferenciaInventario.ESTADO_ENVIADA,
                TransferenciaInventario.ESTADO_EN_TRANSITO,
            ],
        ).count()
        if transferencias_pendientes > 0:
            alertas.append({
                'tipo': 'info',
                'modulo': 'LOGISTICA',
                'mensaje': f'{transferencias_pendientes} transferencias pendientes',
                'accion': 'Revisar monitor de transferencias',
            })

    return render(request, 'core/dashboard_unificado.html', {
        'empresa': empresa,
        'fecha_inicio': fecha_inicio,
        'fecha_fin': fecha_fin,
        'total_ventas': total_ventas,
        'total_compras': total_compras,
        'utilidad_bruta': utilidad_bruta,
        'margen_bruto': margen_bruto,
        'total_ordenes_lab': total_ordenes_lab,
        'ordenes_validadas': ordenes_validadas,
        'tasa_validacion': tasa_validacion,
        'total_polizas': total_polizas,
        'total_nominas': total_nominas,
        'total_pagado_nomina': total_pagado_nomina,
        'total_clientes': total_clientes,
        'oportunidades_abiertas': oportunidades_abiertas,
        'valor_pipeline': valor_pipeline,
        'total_ventas_cupon': total_ventas_cupon,
        'cantidad_cupones_usados': cantidad_cupones_usados,
        'porcentaje_ventas_marketing': porcentaje_ventas_marketing,
        'marketing_available': MARKETING_AVAILABLE,
        'total_transferencias': total_transferencias,
        'transferencias_completadas': transferencias_completadas,
        'tasa_completitud_transferencias': tasa_completitud_transferencias,
        'total_operaciones': total_operaciones,
        'ultimos_7_dias': json.dumps(ultimos_7_dias),
        'datos_operaciones_modulo': json.dumps(datos_operaciones_modulo),
        'alertas': alertas,
    })


@login_required
def api_kpis_tiempo_real(request):
    """API para obtener KPIs en tiempo real."""
    empresa = getattr(request.user, 'empresa', None)
    if not empresa:
        return JsonResponse({
            'ventas_hoy': 0,
            'cantidad_ventas_hoy': 0,
            'operaciones_hoy': 0,
            'ordenes_lab_hoy': 0,
            'timestamp': timezone.now().isoformat(),
        })

    hoy = timezone.localdate()
    ventas_hoy = Venta.objects.filter(
        empresa=empresa,
        fecha__date=hoy,
        estado='COMPLETADA',
    ).aggregate(
        total=Coalesce(
            Sum('total'),
            Value(Decimal('0.00')),
            output_field=DecimalField(max_digits=12, decimal_places=2),
        ),
        cantidad=Count('id'),
    )

    operaciones_hoy = AuditLog.objects.filter(
        empresa=empresa,
        fecha_cierta__date=hoy,
    ).count()

    if LABORATORIO_AVAILABLE:
        try:
            ordenes_hoy = OrdenDeServicio.objects.filter(
                empresa=empresa,
                fecha_creacion__date=hoy,
            ).count()
        except Exception:
            logging.getLogger(__name__).exception("Error inesperado en api_kpis_tiempo_real (dashboard_unificado.py)")
            ordenes_hoy = 0
    else:
        ordenes_hoy = 0

    return JsonResponse({
        'ventas_hoy': float(ventas_hoy['total'] or 0),
        'cantidad_ventas_hoy': ventas_hoy['cantidad'] or 0,
        'operaciones_hoy': operaciones_hoy,
        'ordenes_lab_hoy': ordenes_hoy,
        'timestamp': timezone.now().isoformat(),
    })