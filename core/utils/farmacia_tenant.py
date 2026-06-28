"""
Resolución estricta de tenant para Farmacia / PDV.

No usar Empresa.objects.first() como fallback: mezcla datos entre clientes SaaS.
"""
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse
from django.shortcuts import redirect
from django.template.loader import render_to_string


def obtener_empresa_usuario_estricto(request):
    """
    Retorna la empresa del usuario autenticado o lanza PermissionDenied.

    Mensaje unificado para auditoría y soporte.
    """
    empresa = getattr(request.user, "empresa", None)
    if empresa is None:
        raise PermissionDenied("Usuario sin empresa asignada")
    return empresa


def respuesta_sin_empresa_json():
    """403 JSON para APIs del PDV cuando falta tenant."""
    from django.http import JsonResponse

    return JsonResponse(
        {"productos": [], "error": "Usuario sin empresa asignada"},
        status=403,
    )


def respuesta_sin_empresa_fragmento(request):
    """403 HTML parcial (HTMX) cuando falta tenant."""
    html = render_to_string(
        "core/partials/pdv_buscar_fragmento.html",
        {"error": "Usuario sin empresa asignada", "productos": [], "q": ""},
        request=request,
    )
    resp = HttpResponse(html, status=403)
    resp["Cache-Control"] = "no-store"
    return resp


def redirigir_sin_empresa_pdv(request):
    """Flujo navegador: mensaje y vuelta a inicio (equivalente a denegación de tenant)."""
    messages.error(request, "Usuario sin empresa asignada. Contacte al administrador.")
    return redirect("home")
