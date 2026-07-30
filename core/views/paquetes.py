"""
Vistas para gestión de paquetes con ordenamiento (REGLA 4).
Catálogo: laboratorio.Estudio (perfiles/paquetes legacy UI). core.Estudio fue retirado en core.0073.
"""
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods


@login_required
@require_http_methods(["POST"])
def api_actualizar_orden_paquete(request, paquete_id):
    """
    API para actualizar el orden de estudios en un paquete.
    REGLA 4: UX de Paquetes (Ordenamiento)
    """
    # El catálogo `laboratorio.Estudio` es legado y no tiene FK de empresa.
    # No debe existir una mutación autenticada sobre datos globales: el flujo
    # vigente usa el catálogo tenant-scoped de LIMS. Mantener el endpoint
    # cerrado evita que una URL histórica vuelva a habilitar un write global.
    return JsonResponse({
        'status': 'gone',
        'mensaje': 'Endpoint legado retirado; use el catálogo LIMS de la empresa.',
    }, status=410)
