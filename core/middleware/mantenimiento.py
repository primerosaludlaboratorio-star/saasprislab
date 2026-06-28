"""
core/middleware/mantenimiento.py
════════════════════════════════════════════════════════════════════════════════
FASE 5 — Modo Mantenimiento / Solo Lectura

Activar antes de la Migración Maestra para proteger integridad de datos.
Bloquea toda escritura (POST/PUT/PATCH/DELETE) y muestra mensaje institucional.

Activar:
  Producción env var:  SYSTEM_MAINTENANCE_MODE=true
  O desde settings:   SYSTEM_MAINTENANCE_MODE = True

Rutas exentas (siempre accesibles):
  - /admin/       → para el superusuario durante mantenimiento
  - /auth/        → login/logout
  - GET requests  → lectura permitida en todo momento
════════════════════════════════════════════════════════════════════════════════
"""
import logging
from django.conf import settings
from django.shortcuts import render
from django.http import JsonResponse

logger = logging.getLogger('core.mantenimiento')

_WRITE_METHODS = {'POST', 'PUT', 'PATCH', 'DELETE'}
_EXEMPT_PREFIXES = ['/admin/', '/auth/', '/static/', '/media/']


class MaintenanceModeMiddleware:
    """
    Si SYSTEM_MAINTENANCE_MODE=True:
      - Bloquea toda escritura con HTTP 503
      - Muestra página institucional de mantenimiento
      - Permite lectura (GET) para que el staff vea el sistema
      - Los superusuarios y el ADMIN pasan sin restricción
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        en_mantenimiento = getattr(settings, 'SYSTEM_MAINTENANCE_MODE', False)

        if en_mantenimiento and self._debe_bloquear(request):
            logger.info(
                f'[Mantenimiento] Solicitud bloqueada: {request.method} {request.path} '
                f'(usuario: {getattr(request.user, "username", "anon")})'
            )
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or \
               'application/json' in request.headers.get('Accept', ''):
                return JsonResponse({
                    'error': 'Sistema en mantenimiento',
                    'mensaje': 'El sistema está en modo de mantenimiento programado. '
                               'Las operaciones de escritura están temporalmente suspendidas.',
                    'modo': 'MANTENIMIENTO',
                }, status=503)

            return render(request, 'core/mantenimiento.html', {
                'mensaje_extra': getattr(settings, 'MAINTENANCE_MESSAGE', ''),
                'eta': getattr(settings, 'MAINTENANCE_ETA', ''),
            }, status=503)

        return self.get_response(request)

    def _debe_bloquear(self, request) -> bool:
        """Retorna True si la request debe ser bloqueada."""
        # Superusuarios nunca bloqueados
        if request.user.is_authenticated and (
            request.user.is_superuser or
            getattr(request.user, 'rol', '') == 'ADMIN'
        ):
            return False

        # Rutas exentas siempre pasan
        path = request.path_info
        if any(path.startswith(pfx) for pfx in _EXEMPT_PREFIXES):
            return False

        # Solo bloquear escrituras
        return request.method in _WRITE_METHODS
