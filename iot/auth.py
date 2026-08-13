"""Autenticación por dispositivo para APIs públicas del kiosco."""
from functools import wraps

from django.http import JsonResponse

from core.decorators import _request_api_token
from .models import Kiosco, VerificacionKiosco


def require_kiosco_token(view_func):
    """Valida el token exclusivo del kiosco objetivo, nunca un token global."""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        token = _request_api_token(request)
        kiosco = None
        if 'kiosco_id' in kwargs:
            kiosco = Kiosco.objects.filter(id=kwargs['kiosco_id'], activo=True).first()
        elif 'verificacion_id' in kwargs:
            verificacion = VerificacionKiosco.objects.select_related('kiosco').filter(
                id=kwargs['verificacion_id'], kiosco__activo=True
            ).first()
            kiosco = verificacion.kiosco if verificacion else None
        if kiosco is None or not kiosco.verificar_token(token):
            return JsonResponse({'status': 'error', 'mensaje': 'No autorizado'}, status=401)
        request.kiosco_autenticado = kiosco
        return view_func(request, *args, **kwargs)
    return wrapper
