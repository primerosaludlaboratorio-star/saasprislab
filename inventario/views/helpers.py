"""
INVENTARIO V8.0 — Helpers compartidos de vistas
"""
from functools import wraps
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.shortcuts import redirect
from core.utils.tenant_strict import empresa_desde_request


def _get_empresa(request):
    """Retorna la Empresa del usuario activo. None si no hay tenant resoluble."""
    return empresa_desde_request(request)


def _empresa_required(view_fn):
    """Decorator: requiere login + empresa válida."""
    @login_required
    @wraps(view_fn)
    def wrapper(request, *args, **kwargs):
        empresa = _get_empresa(request)
        if not empresa:
            messages.error(request, "No tienes una empresa asignada.")
            return redirect('home')
        return view_fn(request, empresa, *args, **kwargs)
    return wrapper
