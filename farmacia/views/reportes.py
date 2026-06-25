"""
Vistas de Reportes de Farmacia
Incluye: lista de ventas, facturación 4.0, reportes de ventas
"""

import logging
from datetime import datetime, timedelta
from decimal import Decimal

from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import DecimalField, Q, Sum, F
from django.db.models.functions import Coalesce
from django.utils import timezone

logger = logging.getLogger('farmacia.reportes')

from core.models import Venta, Empresa


def _empresa_desde_request(request):
    """Empresa efectiva: EmpresaIdentityMiddleware (fallback principal) o FK del usuario."""
    return getattr(request, 'empresa_actual', None) or getattr(request.user, 'empresa', None)


# ==============================================================================
# LISTA DE VENTAS FARMACIA
# ==============================================================================

@login_required
def lista_ventas_farmacia(request):
    """Vista para listar ventas de farmacia con filtros."""
    empresa = _empresa_desde_request(request)
    if not empresa:
        messages.error(request, 'Usuario no tiene empresa asignada.')
        return redirect('home')
    
    # Filtros
    fecha_desde = request.GET.get('fecha_desde')
    fecha_hasta = request.GET.get('fecha_hasta')
    folio = request.GET.get('folio', '').strip()
    cliente = request.GET.get('cliente', '').strip()
    estado = request.GET.get('estado', '')
    
    # Query base
    ventas = Venta.objects.filter(empresa=empresa).select_related('paciente', 'usuario')
    
    # Aplicar filtros
    if fecha_desde:
        try:
            fd = datetime.strptime(fecha_desde, '%Y-%m-%d')
            ventas = ventas.filter(fecha__gte=fd)
        except ValueError:
            pass
    
    if fecha_hasta:
        try:
            fh = datetime.strptime(fecha_hasta, '%Y-%m-%d')
            ventas = ventas.filter(fecha__lte=fh)
        except ValueError:
            pass
    
    if folio:
        ventas = ventas.filter(folio_operacion__icontains=folio)
    
    if cliente:
        ventas = ventas.filter(
            Q(paciente__nombre_completo__icontains=cliente) |
            Q(paciente_nombre__icontains=cliente)
        )
    
    if estado:
        ventas = ventas.filter(estado=estado)
    
    # Ordenar por fecha descendente
    ventas = ventas.order_by('-fecha')[:100]
    
    # Determinar filtro actual para mostrar en el template
    filtro_actual = {
        'fecha_desde': fecha_desde,
        'fecha_hasta': fecha_hasta,
        'folio': folio,
        'cliente': cliente,
        'estado': estado,
    }
    
    return render(request, 'core/lista_ventas_farmacia.html', {
        'ventas': ventas,
        'filtro_actual': filtro_actual,
    })


# ==============================================================================
# FACTURACIÓN 4.0
# ==============================================================================

@login_required
def facturacion_40(request):
    """Vista de Facturación 4.0 (CFDI)."""
    empresa = _empresa_desde_request(request)
    return render(request, 'core/facturacion_40.html', {'empresa': empresa})


# ==============================================================================
# REPORTE DE VENTAS POR FECHA
# ==============================================================================

@login_required
def reporte_ventas_fecha(request):
    """Reporte de ventas por fecha."""
    empresa = _empresa_desde_request(request)
    if not empresa:
        messages.error(request, 'Usuario no tiene empresa asignada.')
        return redirect('home')
    
    fecha_param = request.GET.get('fecha')
    hoy = timezone.now().date()
    
    if fecha_param:
        try:
            fecha_seleccionada = datetime.strptime(fecha_param, '%Y-%m-%d').date()
        except (ValueError, TypeError):
            fecha_seleccionada = hoy
    else:
        fecha_seleccionada = hoy
    
    inicio = timezone.make_aware(datetime.combine(fecha_seleccionada, datetime.min.time()))
    fin = timezone.make_aware(datetime.combine(fecha_seleccionada, datetime.max.time()))
    
    ventas = Venta.objects.filter(
        empresa=empresa,
        fecha__range=(inicio, fin)
    ).select_related('paciente', 'usuario').prefetch_related('detalles__producto').order_by('-fecha')
    
    # Totales
    total_ventas = ventas.aggregate(
        total=Coalesce(Sum('total'), Decimal('0.00'), output_field=DecimalField())
    )['total'] or Decimal('0.00')
    
    total_efectivo = ventas.aggregate(
        total=Coalesce(Sum('pagos__monto'), Decimal('0.00'), output_field=DecimalField())
    )['total'] or Decimal('0.00')
    
    cantidad_ventas = ventas.count()
    
    return render(request, 'core/lista_ventas_farmacia.html', {
        'empresa': empresa,
        'ventas': ventas,
        'filtro_actual': {
            'fecha_desde': fecha_seleccionada.strftime('%Y-%m-%d'),
            'fecha_hasta': fecha_seleccionada.strftime('%Y-%m-%d'),
            'folio': '',
            'cliente': '',
            'estado': '',
        },
        'fecha_seleccionada': fecha_seleccionada,
        'fecha_seleccionada_str': fecha_seleccionada.strftime('%Y-%m-%d'),
        'total_ventas': total_ventas,
        'total_efectivo': total_efectivo,
        'cantidad_ventas': cantidad_ventas,
    })


# ==============================================================================
# REPORTE DE PRODUCTOS MÁS VENDIDOS
# ==============================================================================

@login_required
def reporte_productos_mas_vendidos(request):
    """Reporte de productos más vendidos."""
    empresa = _empresa_desde_request(request)
    if not empresa:
        messages.error(request, 'Usuario no tiene empresa asignada.')
        return redirect('home')
    
    fecha_desde = request.GET.get('fecha_desde')
    fecha_hasta = request.GET.get('fecha_hasta')
    
    # Query base
    query = Venta.objects.filter(empresa=empresa, estado='COMPLETADA')
    
    # Filtros de fecha
    if fecha_desde:
        try:
            fd = datetime.strptime(fecha_desde, '%Y-%m-%d')
            query = query.filter(fecha__gte=fd)
        except ValueError:
            pass
    
    if fecha_hasta:
        try:
            fh = datetime.strptime(fecha_hasta, '%Y-%m-%d')
            query = query.filter(fecha__lte=fh)
        except ValueError:
            pass
    
    # Agrupar por producto
    from django.db.models import Count
    productos_vendidos = (
        query.values('detalles__producto__nombre', 'detalles__producto__id')
        .annotate(
            total_cantidad=Sum('detalles__cantidad'),
            total_ventas=Count('id'),
            total_monto=Sum('detalles__subtotal')
        )
        .order_by('-total_cantidad')[:50]
    )
    
    return render(request, 'core/reporte_productos_mas_vendidos.html', {
        'empresa': empresa,
        'productos_vendidos': productos_vendidos,
        'fecha_desde': fecha_desde,
        'fecha_hasta': fecha_hasta,
    })


# ==============================================================================
# REPORTE DE VENTAS POR MÉTODO DE PAGO
# ==============================================================================

@login_required
def reporte_ventas_metodo_pago(request):
    """Reporte de ventas por método de pago."""
    empresa = _empresa_desde_request(request)
    if not empresa:
        messages.error(request, 'Usuario no tiene empresa asignada.')
        return redirect('home')
    
    fecha_param = request.GET.get('fecha')
    hoy = timezone.now().date()
    
    if fecha_param:
        try:
            fecha_seleccionada = datetime.strptime(fecha_param, '%Y-%m-%d').date()
        except (ValueError, TypeError):
            fecha_seleccionada = hoy
    else:
        fecha_seleccionada = hoy
    
    inicio = timezone.make_aware(datetime.combine(fecha_seleccionada, datetime.min.time()))
    fin = timezone.make_aware(datetime.combine(fecha_seleccionada, datetime.max.time()))
    
    from core.models import Pago
    
    # Agrupar por método de pago
    ventas_por_metodo = (
        Pago.objects.filter(
            venta__empresa=empresa,
            venta__fecha__range=(inicio, fin),
            venta__estado='COMPLETADA'
        )
        .values('metodo')
        .annotate(
            total_monto=Sum('monto'),
            cantidad=Count('id')
        )
        .order_by('-total_monto')
    )
    
    return render(request, 'core/reporte_ventas_metodo_pago.html', {
        'empresa': empresa,
        'ventas_por_metodo': ventas_por_metodo,
        'fecha_seleccionada': fecha_seleccionada,
        'fecha_seleccionada_str': fecha_seleccionada.strftime('%Y-%m-%d'),
    })
