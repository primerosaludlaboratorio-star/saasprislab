"""
Redireccion de host canonico para evitar sesiones divididas por dominio.

Problema: usuarios abren el sistema en distintos dominios o subdominios
(ej. labcorecloud.com vs prislab.labcorecloud.com) y la cookie de sesion/CSRF
no se comparte entre hosts. Resultado: el login "falla" en la ventana normal
(cookie de otro host) pero funciona en incognito (contexto fresco, un solo host).

Configurable via settings (leidos de env), opt-in:
  PRISLAB_CANONICAL_HOST -> host canonico (ej. 'prislab.labcorecloud.com')
  PRISLAB_LEGACY_HOSTS   -> coma-separado de hosts a redirigir al canonico
Si PRISLAB_LEGACY_HOSTS no esta configurado, el middleware NO redirige (no-op),
preservando el comportamiento anterior.
"""
from django.conf import settings
from django.http import HttpResponseRedirect


class CanonicalHostMiddleware:
    """Fuerza un unico host publico para la app en produccion (opt-in por env)."""

    def __init__(self, get_response):
        self.get_response = get_response
        self.canonical_host = (getattr(settings, 'PRISLAB_CANONICAL_HOST', '') or '').strip().lower()
        raw = getattr(settings, 'PRISLAB_LEGACY_HOSTS', '') or ''
        self.legacy_hosts = {h.strip().lower() for h in raw.split(',') if h.strip()}

    def __call__(self, request):
        # Solo redirige si esta configurado (canonical + legacy) y el host actual
        # es legacy y distinto del canonico. Evita loops y no hace nada sin config.
        if self.canonical_host and self.legacy_hosts:
            host = (request.get_host() or '').split(':')[0].lower()
            if host in self.legacy_hosts and host != self.canonical_host:
                return HttpResponseRedirect(
                    f"https://{self.canonical_host}{request.get_full_path()}"
                )
        return self.get_response(request)
