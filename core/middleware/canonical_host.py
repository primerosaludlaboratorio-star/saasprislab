"""
Redireccion de host canonico para evitar sesiones divididas por dominio.

Problema: usuarios abren el sistema en distintos dominios o subdominios
(ej. dominios alternos) y la cookie de sesion no se comparte entre hosts.
Resultado: aparenta "error" aunque realmente es redireccion a login.
"""
from django.http import HttpResponseRedirect


class CanonicalHostMiddleware:
    """Fuerza un unico host publico para la app en produccion."""

    LEGACY_HOSTS = set()
    CANONICAL_HOST = 'prislab.local'

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        host = (request.get_host() or '').split(':')[0].lower()
        if host in self.LEGACY_HOSTS:
            target = f"https://{self.CANONICAL_HOST}{request.get_full_path()}"
            return HttpResponseRedirect(target)
        return self.get_response(request)
