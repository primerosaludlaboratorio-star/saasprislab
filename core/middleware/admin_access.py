"""
Bastión Django Admin: allowlist de IP y/o grupo ADMIN_SISTEMA.

Variables (settings, típicamente vía entorno):
  ADMIN_IP_RESTRICTION_ENABLED, ALLOWED_ADMIN_IPS
  ADMIN_GROUP_RESTRICTION_ENABLED
"""
from django.conf import settings
from django.http import HttpResponseForbidden


def _client_ip(request):
    forwarded = request.META.get('HTTP_X_FORWARDED_FOR', '') or ''
    if forwarded:
        return forwarded.split(',')[0].strip()
    return (request.META.get('REMOTE_ADDR') or '').strip()


class AdminAccessMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.path.startswith('/admin/'):
            if getattr(settings, 'ADMIN_IP_RESTRICTION_ENABLED', False):
                allowed = set(getattr(settings, 'ALLOWED_ADMIN_IPS', None) or [])
                if allowed:
                    ip = _client_ip(request)
                    if ip not in allowed:
                        return HttpResponseForbidden(
                            'Acceso al sitio de administración restringido por política de red.'
                        )
            user = getattr(request, 'user', None)
            if user is not None and user.is_authenticated and user.is_staff:
                if getattr(settings, 'ADMIN_GROUP_RESTRICTION_ENABLED', False):
                    if not user.is_superuser and not user.groups.filter(name='ADMIN_SISTEMA').exists():
                        return HttpResponseForbidden(
                            'Se requiere pertenencia al grupo ADMIN_SISTEMA para el panel de administración.'
                        )
        return self.get_response(request)
