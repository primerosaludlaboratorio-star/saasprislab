"""
Redireccion de host canonico para evitar sesiones divididas por dominio.

Problema: usuarios abren el sistema en distintos dominios o subdominios
(ej. dominios alternos) y la cookie de sesion no se comparte entre hosts.
Resultado: aparenta "error" aunque realmente es redireccion a login.
"""
import os
from urllib.parse import urlparse

from django.conf import settings
from django.http import HttpResponseRedirect


def _normalize_host(value):
    raw = (value or '').strip()
    if not raw:
        return ''
    if '://' not in raw:
        raw = f'https://{raw}'
    parsed = urlparse(raw)
    host = parsed.netloc or parsed.path
    if '@' in host:
        host = host.rsplit('@', 1)[-1]
    return host.split(':', 1)[0].lower().strip()


class CanonicalHostMiddleware:
    """Fuerza un unico host publico para la app en produccion."""

    def __init__(self, get_response):
        self.get_response = get_response
        site_url = getattr(settings, 'SITE_URL', '')
        self.canonical_host = _normalize_host(
            os.environ.get('PRISLAB_CANONICAL_HOST') or site_url
        )
        legacy_hosts = os.environ.get('PRISLAB_LEGACY_HOSTS', '')
        self.legacy_hosts = {
            _normalize_host(item)
            for item in legacy_hosts.split(',')
            if _normalize_host(item)
        }
        if self.canonical_host in self.legacy_hosts:
            self.legacy_hosts.discard(self.canonical_host)

    def _should_redirect(self, host):
        if not self.canonical_host:
            return False
        if host == self.canonical_host:
            return False
        if host in self.legacy_hosts:
            return True
        return bool(getattr(settings, 'IS_PRODUCTION', False) and host not in {'localhost', '127.0.0.1', '::1'})

    def __call__(self, request):
        host = _normalize_host(request.get_host())
        if self._should_redirect(host):
            target = f"https://{self.canonical_host}{request.get_full_path()}"
            return HttpResponseRedirect(target)
        return self.get_response(request)
