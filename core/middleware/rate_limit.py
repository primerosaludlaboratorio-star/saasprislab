"""
PRISLAB V5 - Rate Limiting Middleware (BLINDAJE R104)
=====================================================
Protege endpoints sensibles contra ataques de fuerza bruta.
- Login: Max 5 intentos por IP cada 5 minutos.
- APIs: Max 120 requests por IP cada minuto.
"""
import time
import logging
import ipaddress

from django.http import JsonResponse
from django.core.cache import cache
from django.conf import settings

logger = logging.getLogger('core.security')


class RateLimitMiddleware:
    """
    Rate limiting basado en IP para rutas sensibles.
    Usa Django cache (LocMem en dev, puede ser Redis en prod).
    """

    # Configuracion por ruta
    RATE_LIMITS = {
        # Rutas de login — app usa /login/ (no /accounts/login/)
        '/login/': {'max_requests': 5, 'window_seconds': 300, 'scope': 'login'},
        '/accounts/login/': {'max_requests': 5, 'window_seconds': 300, 'scope': 'login'},
        '/admin/login/': {'max_requests': 5, 'window_seconds': 300, 'scope': 'admin_login'},
        '/crear-admin-rescate/': {'max_requests': 1, 'window_seconds': 3600, 'scope': 'rescate'},
        '/ingreso-magico/': {'max_requests': 1, 'window_seconds': 3600, 'scope': 'magico'},
        '/contabilidad/api/autofactura/generar/': {
            'max_requests': 5,
            'window_seconds': 600,
            'scope': 'public_autofactura',
        },
    }

    # Limite global para APIs
    API_LIMIT = {'max_requests': 120, 'window_seconds': 60}

    # Límite especial para chat PRIS (previene saturación de la API de Gemini)
    CHAT_LIMIT = {'max_requests': 20, 'window_seconds': 60}

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        path = request.path_info

        # Solo verificar POST en login y rutas sensibles
        config = self.RATE_LIMITS.get(path)
        if config and request.method == 'POST':
            ip = self._get_client_ip(request)
            key = f"rl:{config['scope']}:{ip}"
            if self._is_rate_limited(key, config['max_requests'], config['window_seconds']):
                logger.warning(
                    f"Rate limit alcanzado: {path} desde {ip} "
                    f"(max {config['max_requests']}/{config['window_seconds']}s)"
                )
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({
                        'error': 'Demasiados intentos. Espera unos minutos.',
                        'retry_after': config['window_seconds']
                    }, status=429)
                from django.shortcuts import render
                return render(request, 'core/rate_limited.html', {
                    'wait_seconds': config['window_seconds'],
                    'mensaje': 'Has excedido el limite de intentos. Espera unos minutos.'
                }, status=429)

        # Limite global para API endpoints
        if path.startswith('/api/') and request.method == 'POST':
            ip = self._get_client_ip(request)
            key = f"rl:api:{ip}"
            if self._is_rate_limited(key, self.API_LIMIT['max_requests'], self.API_LIMIT['window_seconds']):
                return JsonResponse({
                    'error': 'Limite de peticiones excedido. Reintenta en 60 segundos.'
                }, status=429)

        # Límite específico para el chat de PRIS (/ia/)
        if path.startswith('/ia/') and request.method == 'POST':
            ip = self._get_client_ip(request)
            key = f"rl:ia:{ip}"
            if self._is_rate_limited(key, self.CHAT_LIMIT['max_requests'], self.CHAT_LIMIT['window_seconds']):
                return JsonResponse({
                    'error': 'Demasiadas solicitudes al asistente. Espera un momento.',
                    'retry_after': self.CHAT_LIMIT['window_seconds']
                }, status=429)

        return self.get_response(request)

    def _get_client_ip(self, request):
        """Obtiene la IP del cliente solo desde proxies explícitamente confiables."""
        remote_addr = (request.META.get('REMOTE_ADDR') or '0.0.0.0').strip()
        try:
            remote_ip = ipaddress.ip_address(remote_addr)
        except ValueError:
            return remote_addr

        trusted_cidrs = []
        for cidr in getattr(settings, 'PRISLAB_TRUSTED_PROXY_CIDRS', ()):
            try:
                trusted_cidrs.append(ipaddress.ip_network(cidr, strict=False))
            except ValueError:
                logger.error('CIDR de proxy confiable inválido: %s', cidr)

        if not any(remote_ip in network for network in trusted_cidrs):
            return remote_addr

        trusted_proxy_count = max(0, int(getattr(settings, 'PRISLAB_TRUSTED_PROXY_COUNT', 0)))
        if trusted_proxy_count == 0:
            return remote_addr

        xff = request.META.get('HTTP_X_FORWARDED_FOR')
        if xff:
            forwarded_ips = [ip.strip() for ip in xff.split(',') if ip.strip()]
            if len(forwarded_ips) >= trusted_proxy_count:
                candidate = forwarded_ips[-trusted_proxy_count]
                try:
                    return str(ipaddress.ip_address(candidate))
                except ValueError:
                    logger.warning('X-Forwarded-For contiene una IP inválida: %s', candidate)
        return remote_addr

    def _is_rate_limited(self, key, max_requests, window_seconds):
        """Verifica si la IP excedio el limite."""
        now = time.time()
        window_key = f"{key}:window"

        # Obtener historial de requests
        history = cache.get(window_key, [])

        # Filtrar solo requests dentro de la ventana
        history = [t for t in history if t > now - window_seconds]

        if len(history) >= max_requests:
            return True

        # Registrar este request
        history.append(now)
        cache.set(window_key, history, timeout=window_seconds)
        return False
