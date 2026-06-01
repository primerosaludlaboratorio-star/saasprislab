"""
Redireccion de host canonico para evitar sesiones divididas por dominio.

Problema: usuarios abren el sistema en distintos dominios de Cloud Run
(ej. *.run.app alternos) y la cookie de sesion no se comparte entre hosts.
Resultado: aparenta "error" aunque realmente es redireccion a login.
"""
from django.http import HttpResponseRedirect


class CanonicalHostMiddleware:
    """Fuerza un unico host publico para la app en produccion."""

    LEGACY_HOSTS = {
        'prislab-v5-811785477499.us-central1.run.app',
    }
    CANONICAL_HOST = 'prislab-v5-oswjakz55a-uc.a.run.app'

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        host = (request.get_host() or '').split(':')[0].lower()
        if host in self.LEGACY_HOSTS:
            target = f"https://{self.CANONICAL_HOST}{request.get_full_path()}"
            return HttpResponseRedirect(target)
        return self.get_response(request)

