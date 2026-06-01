"""
Vistas para impresión raw optimizada para QZ Tray.
Plantillas minimalistas sin dependencias externas para impresión térmica directa.
"""
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from core.models import OrdenDeServicio


@login_required
def imprimir_etiquetas_raw(request, orden_id):
    """
    Vista raw para etiquetas de 38x25mm optimizada para QZ Tray.
    Devuelve HTML minimalista sin márgenes.
    """
    empresa = getattr(request.user, 'empresa', None)
    
    try:
        orden = OrdenDeServicio.objects.select_related('paciente', 'empresa').prefetch_related(
            'detalles__estudio'
        ).get(id=orden_id, empresa=empresa)
    except OrdenDeServicio.DoesNotExist:
        return render(request, 'core/error.html', {
            'mensaje': 'Orden no encontrada'
        }, status=404)
    
    detalles = orden.detalles.select_related('estudio').all()
    
    return render(request, 'core/impresion/etiquetas_raw.html', {
        'orden': orden,
        'detalles': detalles,
    })


@login_required
def imprimir_ticket_raw(request, orden_id):
    """
    Vista raw para ticket de 80mm optimizada para QZ Tray.
    Devuelve HTML minimalista sin márgenes.
    """
    empresa = getattr(request.user, 'empresa', None)
    
    try:
        orden = OrdenDeServicio.objects.select_related('paciente', 'empresa', 'sucursal').prefetch_related(
            'detalles__estudio'
        ).get(id=orden_id, empresa=empresa)
    except OrdenDeServicio.DoesNotExist:
        return render(request, 'core/error.html', {
            'mensaje': 'Orden no encontrada'
        }, status=404)
    
    detalles = orden.detalles.select_related('estudio').all()
    saldo_pendiente = orden.total - orden.anticipo
    
    return render(request, 'core/impresion/ticket_raw.html', {
        'orden': orden,
        'detalles': detalles,
        'saldo_pendiente': saldo_pendiente,
        'empresa': empresa
    })
