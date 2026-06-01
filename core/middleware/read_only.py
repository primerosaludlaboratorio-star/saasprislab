"""
Búnker DRP — Modo solo lectura estricto (Punto 14).

Activación EXCLUSIVA: PRISLAB_READ_ONLY=1 (u otros truthy documentados en settings).

Regla: solo GET, HEAD y OPTIONS pasan sin filtro. Cualquier otro método se bloquea
salvo POST en allowlist de autenticación (login, logout, 2FA). Sin excepción para
/admin/ ni superusuarios: kill switch ciego ante corrupción o ransomware.

Debe ir después de CsrfViewMiddleware y AuthenticationMiddleware para que el login
POST pase validación CSRF.
"""
import logging

from django.conf import settings
from django.http import JsonResponse
from django.shortcuts import render

logger = logging.getLogger('core.read_only')

_ALLOWED_READ_METHODS = frozenset({'GET', 'HEAD', 'OPTIONS'})

# POST permitidos únicamente en estas rutas (path_info normalizado con slash final vía CommonMiddleware)
_POST_AUTH_PREFIXES = (
    '/login/',
    '/logout/',
    '/auth/2fa/verificar/',
    '/auth/2fa/configurar/',
    '/auth/2fa/desactivar/',
)


def _read_only_active() -> bool:
    return bool(getattr(settings, 'PRISLAB_READ_ONLY', False))


def _post_allowed_path(path: str) -> bool:
    p = path or '/'
    if not p.endswith('/'):
        p = p + '/'
    if p == '/':
        return True  # CustomLoginView en raíz (POST login)
    return any(p.startswith(pref) for pref in _POST_AUTH_PREFIXES)


class ReadOnlyMiddleware:
    """Intercepta mutaciones HTTP cuando PRISLAB_READ_ONLY está activo."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if not _read_only_active():
            return self.get_response(request)

        method = request.method.upper()

        if method in _ALLOWED_READ_METHODS:
            return self.get_response(request)

        if method == 'POST' and _post_allowed_path(request.path_info):
            return self.get_response(request)

        logger.warning(
            '[READ_ONLY] Bloqueado %s %s (user=%s)',
            method,
            request.path_info,
            getattr(request.user, 'username', 'anon'),
        )

        payload = {
            'modo': 'READ_ONLY',
            'mensaje': 'PRISLAB está en Modo de Contingencia (Solo Lectura).',
        }

        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse(payload, status=405)

        accept = (request.headers.get('Accept') or '').lower()
        if 'application/json' in accept and 'text/html' not in accept:
            return JsonResponse(payload, status=405)

        return render(
            request,
            'core/read_only_contingencia.html',
            {
                'mensaje': payload['mensaje'],
            },
            status=405,
        )
