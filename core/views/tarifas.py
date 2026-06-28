"""
Tarifas (legacy): la gestión de precios vive en LIMS v7.5 (`lims.PrecioItem`, `/lims/precios/`).
Este módulo conserva nombres de vista por compatibilidad pero ya no muta catálogo core.
"""
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import redirect
from django.urls import reverse
from django.views.decorators.http import require_http_methods


@login_required
def mostrar_configuracion_tarifas(request, tarifa_id=None):
    messages.info(
        request,
        "La gestión de tarifas se ha centralizado en el módulo LIMS v7.5.",
    )
    return redirect(reverse("lims_precios"))


@login_required
@require_http_methods(["POST"])
def api_importar_tarifas_excel(request):
    return JsonResponse(
        {
            "status": "deprecated",
            "mensaje": (
                "Esta API está descontinuada. Use el módulo LIMS: /lims/precios/ "
                "y el pipeline importar_catalogo_lims / ensamblar_lims_v75."
            ),
        },
        status=410,
    )
