"""
Vista del Módulo de Inventario Predictivo
══════════════════════════════════════════
Dashboard y API para el reporte de IA de reabastecimiento.
"""
import logging
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_GET

logger = logging.getLogger('core')


@login_required
def reporte_prediccion_stock(request):
    """Dashboard de predicción de agotamiento de stock."""
    from core.services.feature_flags import flag_activo
    empresa = getattr(request.user, 'empresa', None)

    if not flag_activo('PREDICCION_STOCK_ACTIVO', empresa):
        from django.contrib import messages
        from django.shortcuts import redirect
        messages.info(request, 'El módulo de Inventario Predictivo está desactivado.')
        return redirect('dashboard')

    from core.services.prediccion_stock import reporte_inventario_predictivo
    reporte = reporte_inventario_predictivo(empresa, dias_umbral=7)

    return render(request, 'core/inventario/prediccion_stock.html', {
        'reporte': reporte,
        'titulo': 'IA de Reabastecimiento Predictivo',
    })


@login_required
@require_GET
def api_prediccion_stock(request):
    """API JSON para obtener datos de predicción de stock."""
    empresa = getattr(request.user, 'empresa', None)
    dias = int(request.GET.get('dias', 7))
    from core.services.prediccion_stock import reporte_inventario_predictivo
    return JsonResponse(reporte_inventario_predictivo(empresa, dias_umbral=dias))
