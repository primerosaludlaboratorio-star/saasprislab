"""
Módulo de Analytics y Reportes Centralizados - PRISLAB
Dashboard centralizado con métricas integradas de todos los módulos.
"""
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.db.models import Sum, Count, Q, Avg, Max, Min, F
from django.db.models.functions import Coalesce, TruncDay, TruncMonth, TruncWeek
from django.db.models import DecimalField
from django.utils import timezone
from decimal import Decimal
from datetime import datetime, timedelta
import json

from core.models import (
    Empresa, Venta, Pago, GastoCaja, GastoOperativo, Producto, Lote, DetalleVenta
)
import logging
# Modelos opcionales (no migrados en todos los entornos)
try:
    from core.models import Compra
    COMPRA_AVAILABLE = True
except ImportError:
    Compra = None
    COMPRA_AVAILABLE = False
try:
    from core.models import PolizaContable
    POLIZA_AVAILABLE = True
except ImportError:
    PolizaContable = None
    POLIZA_AVAILABLE = False
try:
    from core.models import Nomina
    NOMINA_AVAILABLE = True
except ImportError:
    Nomina = None
    NOMINA_AVAILABLE = False
try:
    from core.models import ClienteCRM, OportunidadCRM
    CRM_AVAILABLE = True
except ImportError:
    ClienteCRM = OportunidadCRM = None
    CRM_AVAILABLE = False
try:
    from core.models import TransferenciaInventario
    TRANSFERENCIA_AVAILABLE = True
except ImportError:
    TransferenciaInventario = None
    TRANSFERENCIA_AVAILABLE = False
try:
    from core.models import TrazabilidadOperacion
    TRAZABILIDAD_AVAILABLE = True
except ImportError:
    TrazabilidadOperacion = None
    TRAZABILIDAD_AVAILABLE = False

# Importar módulos externos si existen
try:
    from marketing.models import CampanaMarketing, CuponMarketing
    MARKETING_AVAILABLE = True
except ImportError:
    MARKETING_AVAILABLE = False

LABORATORIO_AVAILABLE = True


@login_required
def dashboard_analytics(request):
    """Dashboard centralizado de analytics con métricas de todos los módulos."""
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
    # MÉTRICAS DE FARMACIA
    # ========================================================================
    ventas = Venta.objects.filter(
        empresa=empresa,
        fecha__date__range=[fecha_inicio_dt, fecha_fin_dt],
        estado='COMPLETADA'
    )
    total_ventas = ventas.aggregate(
        total=Coalesce(Sum('total'), Decimal('0.00'), output_field=DecimalField())
    )['total'] or Decimal('0.00')
    
    total_ventas_count = ventas.count()
    ticket_promedio = total_ventas / total_ventas_count if total_ventas_count > 0 else Decimal('0.00')
    
    if COMPRA_AVAILABLE and Compra:
        compras = Compra.objects.filter(
            empresa=empresa,
            fecha_compra__range=[fecha_inicio_dt, fecha_fin_dt]
        )
        total_compras = compras.aggregate(
            total=Coalesce(Sum('total'), Decimal('0.00'), output_field=DecimalField())
        )['total'] or Decimal('0.00')
    else:
        total_compras = Decimal('0.00')
    
    # Productos más vendidos
    from core.models import DetalleVenta
    productos_vendidos = DetalleVenta.objects.filter(
        venta__empresa=empresa,
        venta__fecha__date__range=[fecha_inicio_dt, fecha_fin_dt],
        venta__estado='COMPLETADA'
    ).values('producto__nombre').annotate(
        cantidad_vendida=Sum('cantidad'),
        total_vendido=Sum('subtotal')
    ).order_by('-cantidad_vendida')[:10]
    
    # ========================================================================
    # MÉTRICAS DE LABORATORIO
    # ========================================================================
    if LABORATORIO_AVAILABLE:
        try:
            # Filtrar por pacientes de la empresa (Orden no tiene campo empresa directo)
            from core.models import OrdenDeServicio
            ordenes_lab_core = OrdenDeServicio.objects.filter(
                empresa=empresa,
                fecha_creacion__date__range=[fecha_inicio_dt, fecha_fin_dt]
            )
            total_ordenes_lab = ordenes_lab_core.count()
            ordenes_validadas = ordenes_lab_core.filter(estado='ENTREGADO').count()
        except Exception:
            logging.getLogger(__name__).exception("Error inesperado en dashboard_analytics (analytics.py)")
            total_ordenes_lab = 0
            ordenes_validadas = 0
    else:
        total_ordenes_lab = 0
        ordenes_validadas = 0
    
    # ========================================================================
    # MÉTRICAS DE MARKETING (Integración con Ventas)
    # ========================================================================
    # Marketing: cupon_marketing/campana_marketing no existen en Venta aún
    total_ventas_cupon = Decimal('0.00')
    cantidad_cupones_usados = 0
    ventas_por_campana = []
    cupones_populares = []
    
    # ========================================================================
    # MÉTRICAS DE CONTABILIDAD
    # ========================================================================
    if POLIZA_AVAILABLE and PolizaContable:
        polizas = PolizaContable.objects.filter(
            empresa=empresa,
            fecha__range=[fecha_inicio_dt, fecha_fin_dt],
            estado='AUTORIZADA'
        )
        total_polizas = polizas.count()
    else:
        total_polizas = 0
    
    # ========================================================================
    # MÉTRICAS DE NÓMINA
    # ========================================================================
    if NOMINA_AVAILABLE and Nomina:
        nominas = Nomina.objects.filter(
            empresa=empresa,
            periodo__fecha_inicio__lte=fecha_fin_dt,
            periodo__fecha_fin__gte=fecha_inicio_dt
        )
        total_nominas = nominas.count()
        total_pagado_nomina = nominas.filter(estado='PAGADA').aggregate(
            total=Coalesce(Sum('neto_a_pagar'), Decimal('0.00'), output_field=DecimalField())
        )['total'] or Decimal('0.00')
    else:
        total_nominas = 0
        total_pagado_nomina = Decimal('0.00')
    
    # ========================================================================
    # MÉTRICAS DE CRM
    # ========================================================================
    if CRM_AVAILABLE and ClienteCRM and OportunidadCRM:
        total_clientes = ClienteCRM.objects.filter(empresa=empresa).count()
        oportunidades_abiertas = OportunidadCRM.objects.filter(
            empresa=empresa,
            etapa__in=['PROSPECTO', 'CALIFICADO', 'PROPUESTA', 'NEGOCIACION']
        ).count()
        valor_pipeline = OportunidadCRM.objects.filter(
            empresa=empresa,
            etapa__in=['PROSPECTO', 'CALIFICADO', 'PROPUESTA', 'NEGOCIACION']
        ).aggregate(
            total=Coalesce(Sum('valor_estimado'), Decimal('0.00'), output_field=DecimalField())
        )['total'] or Decimal('0.00')
    else:
        total_clientes = 0
        oportunidades_abiertas = 0
        valor_pipeline = Decimal('0.00')
    
    # ========================================================================
    # MÉTRICAS DE TRANSFERENCIAS
    # ========================================================================
    if TRANSFERENCIA_AVAILABLE and TransferenciaInventario:
        transferencias = TransferenciaInventario.objects.filter(
            empresa=empresa,
            fecha_solicitud__date__range=[fecha_inicio_dt, fecha_fin_dt]
        )
        total_transferencias = transferencias.count()
        transferencias_completadas = transferencias.filter(estado='RECIBIDA').count()
    else:
        total_transferencias = 0
        transferencias_completadas = 0
    
    # ========================================================================
    # MÉTRICAS DE TRAZABILIDAD
    # ========================================================================
    if TRAZABILIDAD_AVAILABLE and TrazabilidadOperacion:
        operaciones_trazadas = TrazabilidadOperacion.objects.filter(
            empresa=empresa,
            fecha_hora__date__range=[fecha_inicio_dt, fecha_fin_dt]
        )
        total_operaciones = operaciones_trazadas.count()
        operaciones_por_modulo = operaciones_trazadas.values('modulo').annotate(
            total=Count('id')
        ).order_by('-total')
    else:
        total_operaciones = 0
        operaciones_por_modulo = []
    
    # ========================================================================
    # GRÁFICAS DE TENDENCIAS
    # ========================================================================
    # Ventas diarias
    ventas_diarias = ventas.annotate(
        dia=TruncDay('fecha')
    ).values('dia').annotate(
        total=Coalesce(Sum('total'), Decimal('0.00'), output_field=DecimalField()),
        cantidad=Count('id')
    ).order_by('dia')
    
    datos_ventas_diarias = {
        'labels': [v['dia'].strftime('%Y-%m-%d') for v in ventas_diarias],
        'valores': [float(v['total']) for v in ventas_diarias],
        'cantidades': [v['cantidad'] for v in ventas_diarias],
    }
    
    # Operaciones por tipo (solo si trazabilidad disponible)
    if TRAZABILIDAD_AVAILABLE and TrazabilidadOperacion:
        operaciones_por_tipo = operaciones_trazadas.values('tipo_operacion').annotate(
            total=Count('id')
        ).order_by('-total')
    else:
        operaciones_por_tipo = []
    
    datos_operaciones_tipo = {
        'labels': [op['tipo_operacion'] for op in operaciones_por_tipo],
        'valores': [op['total'] for op in operaciones_por_tipo],
    }
    
    # ========================================================================
    # KPIs PRINCIPALES
    # ========================================================================
    utilidad_bruta = total_ventas - total_compras
    margen_bruto = (utilidad_bruta / total_ventas * 100) if total_ventas > 0 else Decimal('0.00')
    
    # ========================================================================
    # ANÁLISIS PREDICTIVO
    # ========================================================================
    # Proyección de ventas (basado en tendencia de últimos 7 días)
    ultimos_7_dias = ventas.filter(
        fecha__date__gte=(fecha_fin_dt - timedelta(days=7))
    ).annotate(
        dia=TruncDay('fecha')
    ).values('dia').annotate(
        total=Coalesce(Sum('total'), Decimal('0.00'), output_field=DecimalField())
    ).order_by('dia')
    
    if ultimos_7_dias:
        promedio_diario = sum(float(v['total']) for v in ultimos_7_dias) / len(ultimos_7_dias)
        proyeccion_mensual = promedio_diario * 30
        crecimiento_tendencia = 0.0
        if len(ultimos_7_dias) >= 2:
            # Calcular tendencia simple (último día vs primer día)
            primer_dia = float(ultimos_7_dias[0]['total'])
            ultimo_dia = float(ultimos_7_dias[-1]['total'])
            if primer_dia > 0:
                crecimiento_tendencia = ((ultimo_dia - primer_dia) / primer_dia) * 100
    else:
        proyeccion_mensual = 0.0
        crecimiento_tendencia = 0.0
    
    # Productos en riesgo de agotarse (stock bajo)
    productos_bajo_stock = Producto.objects.filter(
        empresa=empresa,
        stock__gt=0,
        stock__lt=F('stock_minimo')
    ).order_by('stock')[:10]
    
    # Predicción de demanda (basado en ventas históricas)
    productos_demanda = DetalleVenta.objects.filter(
        venta__empresa=empresa,
        venta__fecha__date__range=[fecha_inicio_dt, fecha_fin_dt],
        venta__estado='COMPLETADA'
    ).values('producto__nombre', 'producto__id').annotate(
        cantidad_vendida=Sum('cantidad'),
        promedio_diario=Avg('cantidad')
    ).order_by('-cantidad_vendida')[:10]
    
    return render(request, 'core/analytics/dashboard.html', {
        'empresa': empresa,
        'fecha_inicio': fecha_inicio,
        'fecha_fin': fecha_fin,
        
        # Farmacia
        'total_ventas': total_ventas,
        'total_ventas_count': total_ventas_count,
        'ticket_promedio': ticket_promedio,
        'total_compras': total_compras,
        'utilidad_bruta': utilidad_bruta,
        'margen_bruto': margen_bruto,
        'productos_vendidos': productos_vendidos,
        
        # Laboratorio
        'total_ordenes_lab': total_ordenes_lab,
        'ordenes_validadas': ordenes_validadas,
        
        # Contabilidad
        'total_polizas': total_polizas,
        
        # Nómina
        'total_nominas': total_nominas,
        'total_pagado_nomina': total_pagado_nomina,
        
        # CRM
        'total_clientes': total_clientes,
        'oportunidades_abiertas': oportunidades_abiertas,
        'valor_pipeline': valor_pipeline,
        
        # Transferencias
        'total_transferencias': total_transferencias,
        'transferencias_completadas': transferencias_completadas,
        
        # Trazabilidad
        'total_operaciones': total_operaciones,
        'operaciones_por_modulo': operaciones_por_modulo,
        
        # Gráficas
        'datos_ventas_diarias': json.dumps(datos_ventas_diarias),
        'datos_operaciones_tipo': json.dumps(datos_operaciones_tipo),
        
        # Marketing
        'total_ventas_cupon': total_ventas_cupon,
        'cantidad_cupones_usados': cantidad_cupones_usados,
        'ventas_por_campana': ventas_por_campana,
        'cupones_populares': cupones_populares,
        'marketing_available': MARKETING_AVAILABLE,
        
        # Análisis Predictivo
        'proyeccion_mensual': proyeccion_mensual,
        'crecimiento_tendencia': crecimiento_tendencia,
        'productos_bajo_stock': productos_bajo_stock,
        'productos_demanda': productos_demanda,
        'roi_marketing': (Decimal(str(total_ventas_cupon)) / Decimal(str(total_ventas)) * 100) if (MARKETING_AVAILABLE and total_ventas and total_ventas > 0) else Decimal('0.00'),
    })


@login_required
def reporte_trazabilidad(request):
    """Reporte completo de trazabilidad de operaciones."""
    empresa = getattr(request.user, 'empresa', None)
    if not empresa:
        from django.contrib import messages
        messages.error(request, 'Usuario no tiene empresa asignada.')
        return redirect('home')
    if not TRAZABILIDAD_AVAILABLE or TrazabilidadOperacion is None:
        from django.contrib import messages
        messages.warning(request, 'Módulo de trazabilidad no disponible en este entorno.')
        return redirect('home')
    
    # Filtros
    tipo_operacion = request.GET.get('tipo_operacion', '')
    modulo = request.GET.get('modulo', '')
    usuario_id = request.GET.get('usuario', '')
    fecha_desde = request.GET.get('fecha_desde', '')
    fecha_hasta = request.GET.get('fecha_hasta', '')
    
    operaciones = TrazabilidadOperacion.objects.filter(empresa=empresa).select_related(
        'usuario', 'sucursal'
    ).order_by('-fecha_hora')
    
    if tipo_operacion:
        operaciones = operaciones.filter(tipo_operacion=tipo_operacion)
    if modulo:
        operaciones = operaciones.filter(modulo=modulo)
    if usuario_id:
        operaciones = operaciones.filter(usuario_id=usuario_id)
    if fecha_desde:
        operaciones = operaciones.filter(fecha_hora__date__gte=fecha_desde)
    if fecha_hasta:
        operaciones = operaciones.filter(fecha_hora__date__lte=fecha_hasta)
    
    # Paginación
    from django.core.paginator import Paginator
    paginator = Paginator(operaciones, 50)
    page = request.GET.get('page')
    operaciones_pag = paginator.get_page(page)
    
    usuarios = empresa.usuarios.filter(is_active=True)
    
    return render(request, 'core/analytics/trazabilidad.html', {
        'empresa': empresa,
        'operaciones': operaciones_pag,
        'usuarios': usuarios,
        'tipo_operacion': tipo_operacion,
        'modulo': modulo,
        'usuario_id': usuario_id,
        'fecha_desde': fecha_desde,
        'fecha_hasta': fecha_hasta,
    })


@login_required
def api_metricas_tiempo_real(request):
    """API para obtener métricas en tiempo real."""
    empresa = getattr(request.user, 'empresa', None)
    if not empresa:
        return JsonResponse({'ventas_hoy': 0, 'cantidad_ventas_hoy': 0, 'operaciones_hoy': 0, 'timestamp': timezone.now().isoformat()})
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
    
    # Operaciones de hoy (solo si trazabilidad disponible)
    operaciones_hoy = 0
    if TRAZABILIDAD_AVAILABLE and TrazabilidadOperacion:
        operaciones_hoy = TrazabilidadOperacion.objects.filter(
            empresa=empresa,
            fecha_hora__date=hoy
        ).count()
    
    return JsonResponse({
        'ventas_hoy': float(ventas_hoy['total'] or 0),
        'cantidad_ventas_hoy': ventas_hoy['cantidad'] or 0,
        'operaciones_hoy': operaciones_hoy,
        'timestamp': timezone.now().isoformat(),
    })