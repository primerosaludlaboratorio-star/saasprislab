"""
Dashboard Unificado - PRISLAB
Vista centralizada que muestra KPIs de todos los módulos en un solo lugar.
"""
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.db.models import Sum, Count, Q, F
from django.db.models.functions import Coalesce
from django.db.models import DecimalField
from django.utils import timezone
from decimal import Decimal
from datetime import datetime, timedelta
import json

from core.models import (
    Empresa, Venta, Pago, GastoCaja, Producto
    # NOTA: Modelos Compra, Nomina, ClienteCRM, OportunidadCRM, TransferenciaInventario, TrazabilidadOperacion y PolizaContable pendientes de migración.
    # Compra, Nomina, ClienteCRM, OportunidadCRM, TransferenciaInventario, TrazabilidadOperacion, PolizaContable
)

# Importar módulos externos si existen
try:
    from marketing.models import CampanaMarketing, CuponMarketing
    MARKETING_AVAILABLE = True
except ImportError:
    MARKETING_AVAILABLE = False

LABORATORIO_AVAILABLE = True  # KPIs lab vía core.OrdenDeServicio


@login_required
def dashboard_unificado(request):
    """
    Dashboard unificado con KPIs de todos los módulos.
    Vista centralizada para toma de decisiones ejecutivas.
    """
    empresa = getattr(request.user, 'empresa', None)
    if not empresa:
        from django.contrib import messages
        messages.error(request, 'Usuario no tiene empresa asignada.')
        return redirect('home')
    
    # Filtros de fecha
    fecha_inicio = request.GET.get('fecha_inicio', '')
    fecha_fin = request.GET.get('fecha_fin', '')
    
    # Por defecto, último mes
    if not fecha_inicio:
        fecha_inicio = (timezone.now() - timedelta(days=30)).strftime('%Y-%m-%d')
    if not fecha_fin:
        fecha_fin = timezone.now().strftime('%Y-%m-%d')
    
    fecha_inicio_dt = datetime.strptime(fecha_inicio, '%Y-%m-%d').date()
    fecha_fin_dt = datetime.strptime(fecha_fin, '%Y-%m-%d').date()
    
    # ========================================================================
    # KPIs PRINCIPALES (TODOS LOS MÓDULOS)
    # ========================================================================
    
    # FARMACIA
    ventas = Venta.objects.filter(
        empresa=empresa,
        fecha__date__range=[fecha_inicio_dt, fecha_fin_dt],
        estado='COMPLETADA'
    )
    total_ventas = ventas.aggregate(
        total=Coalesce(Sum('total'), Decimal('0.00'), output_field=DecimalField())
    )['total'] or Decimal('0.00')
    
    # Modelo Compra no migrado aún - usar placeholder
    total_compras = Decimal('0.00')
    
    utilidad_bruta = total_ventas - total_compras
    margen_bruto = (utilidad_bruta / total_ventas * 100) if total_ventas > 0 else Decimal('0.00')
    
    # LABORATORIO
    try:
        from core.models import OrdenDeServicio
        ordenes_lab = OrdenDeServicio.objects.filter(
            empresa=empresa,
            fecha_creacion__date__range=[fecha_inicio_dt, fecha_fin_dt]
        )
        total_ordenes_lab = ordenes_lab.count()
        ordenes_validadas = ordenes_lab.filter(estado='ENTREGADO').count()
        tasa_validacion = (ordenes_validadas / total_ordenes_lab * 100) if total_ordenes_lab > 0 else Decimal('0.00')
    except Exception:
        total_ordenes_lab = 0
        ordenes_validadas = 0
        tasa_validacion = Decimal('0.00')
    
    # CONTABILIDAD (PolizaContable no migrado aún)
    total_polizas = 0

    # NÓMINA (Nomina no migrado aún)
    total_nominas = 0
    total_pagado_nomina = Decimal('0.00')
    
    # CRM (ClienteCRM/OportunidadCRM no migrados aún)
    total_clientes = 0
    oportunidades_abiertas = 0
    valor_pipeline = Decimal('0.00')

    # MARKETING (cupon_marketing/campana_marketing no existe en Venta aún)
    total_ventas_cupon = Decimal('0.00')
    cantidad_cupones_usados = 0
    porcentaje_ventas_marketing = Decimal('0.00')

    # TRANSFERENCIAS (TransferenciaInventario no migrado)
    total_transferencias = 0
    transferencias_completadas = 0
    tasa_completitud_transferencias = Decimal('0.00')

    # TRAZABILIDAD (TrazabilidadOperacion no migrado)
    total_operaciones = 0
    
    # ========================================================================
    # GRÁFICAS INTEGRADAS
    # ========================================================================
    
    # Ventas vs Compras (últimos 7 días)
    ultimos_7_dias = []
    fecha_actual = fecha_fin_dt - timedelta(days=6)
    while fecha_actual <= fecha_fin_dt:
        ventas_dia = Venta.objects.filter(
            empresa=empresa,
            fecha__date=fecha_actual,
            estado='COMPLETADA'
        ).aggregate(
            total=Coalesce(Sum('total'), Decimal('0.00'), output_field=DecimalField())
        )['total'] or Decimal('0.00')
        
        compras_dia = Decimal('0.00')  # Modelo Compra no migrado aún
        
        ultimos_7_dias.append({
            'fecha': fecha_actual.strftime('%Y-%m-%d'),
            'ventas': float(ventas_dia),
            'compras': float(compras_dia),
            'utilidad': float(ventas_dia - compras_dia),
        })
        fecha_actual += timedelta(days=1)
    
    # Operaciones por módulo (TrazabilidadOperacion no migrado)
    operaciones_por_modulo = []
    
    datos_operaciones_modulo = {
        'labels': [op['modulo'] for op in operaciones_por_modulo],
        'valores': [op['total'] for op in operaciones_por_modulo],
    }
    
    # ========================================================================
    # ALERTAS Y RECOMENDACIONES
    # ========================================================================
    alertas = []
    
    # Alerta de stock bajo
    productos_bajo_stock = Producto.objects.filter(empresa=empresa, stock__gt=0, stock__lt=F('stock_minimo')).count()
    if productos_bajo_stock > 0:
        alertas.append({
            'tipo': 'warning',
            'modulo': 'FARMACIA',
            'mensaje': f'{productos_bajo_stock} productos con stock bajo (≤10 unidades)',
            'accion': 'Revisar inventario y realizar compras'
        })
    
    # Alerta de transferencias pendientes (TransferenciaInventario no migrado)
    transferencias_pendientes = 0
    
    # Alerta de oportunidades próximas a cerrar (OportunidadCRM no migrado)
    oportunidades_proximas = 0
    
    return render(request, 'core/dashboard_unificado.html', {
        'empresa': empresa,
        'fecha_inicio': fecha_inicio,
        'fecha_fin': fecha_fin,
        
        # KPIs Farmacia
        'total_ventas': total_ventas,
        'total_compras': total_compras,
        'utilidad_bruta': utilidad_bruta,
        'margen_bruto': margen_bruto,
        
        # KPIs Laboratorio
        'total_ordenes_lab': total_ordenes_lab,
        'ordenes_validadas': ordenes_validadas,
        'tasa_validacion': tasa_validacion,
        
        # KPIs Contabilidad
        'total_polizas': total_polizas,
        
        # KPIs Nómina
        'total_nominas': total_nominas,
        'total_pagado_nomina': total_pagado_nomina,
        
        # KPIs CRM
        'total_clientes': total_clientes,
        'oportunidades_abiertas': oportunidades_abiertas,
        'valor_pipeline': valor_pipeline,
        
        # KPIs Marketing
        'total_ventas_cupon': total_ventas_cupon,
        'cantidad_cupones_usados': cantidad_cupones_usados,
        'porcentaje_ventas_marketing': porcentaje_ventas_marketing,
        'marketing_available': MARKETING_AVAILABLE,
        
        # KPIs Transferencias
        'total_transferencias': total_transferencias,
        'transferencias_completadas': transferencias_completadas,
        'tasa_completitud_transferencias': tasa_completitud_transferencias,
        
        # KPIs Trazabilidad
        'total_operaciones': total_operaciones,
        
        # Gráficas
        'ultimos_7_dias': json.dumps(ultimos_7_dias),
        'datos_operaciones_modulo': json.dumps(datos_operaciones_modulo),
        
        # Alertas
        'alertas': alertas,
    })


@login_required
def api_kpis_tiempo_real(request):
    """API para obtener KPIs en tiempo real (para actualización automática)."""
    empresa = getattr(request.user, 'empresa', None)
    if not empresa:
        return JsonResponse({'ventas_hoy': {'total': 0, 'cantidad': 0}, 'operaciones_hoy': 0, 'ordenes_hoy': 0})
    hoy = timezone.now().date()
    
    # Ventas de hoy
    ventas_hoy = Venta.objects.filter(
        empresa=empresa,
        fecha__date=hoy,
        estado='COMPLETADA'
    ).aggregate(
        total=Coalesce(Sum('total'), Decimal('0.00'), output_field=DecimalField()),
        cantidad=Count('id')
    )
    
    # Operaciones de hoy (TrazabilidadOperacion no migrado)
    operaciones_hoy = 0
    
    # Ordenes de laboratorio de hoy
    if LABORATORIO_AVAILABLE:
        try:
            from core.models import OrdenDeServicio
            ordenes_hoy = OrdenDeServicio.objects.filter(
                empresa=empresa,
                fecha_creacion__date=hoy
            ).count()
        except Exception:
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
