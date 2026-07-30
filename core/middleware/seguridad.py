"""
core/middleware/seguridad.py
════════════════════════════════════════════════════════════════════════════════
Middlewares de Seguridad PRISLAB — FASE 4

1. SessionTimeoutMiddleware   — Fuerza logout tras N horas de inactividad
2. TenantStorageMiddleware    — Inyecta empresa_slug en contexto Drive (multi-tenant)
3. Trazabilidad clínica — implementada por hooks explícitos y blindaje de expediente.
════════════════════════════════════════════════════════════════════════════════
"""
import logging
import re
from datetime import datetime, timedelta

from django.conf import settings
from django.contrib.auth import logout
from django.utils import timezone

logger = logging.getLogger('core.seguridad')


# ══════════════════════════════════════════════════════════════════════════════
# 1. SESSION TIMEOUT — Protección de turnos clínicos (8 horas)
# ══════════════════════════════════════════════════════════════════════════════

SESSION_TIMEOUT_SECONDS = getattr(settings, 'SESSION_TIMEOUT_SECONDS', 8 * 3600)  # 8h default

# Rutas que nunca deben disparar el timeout check (login, static, etc.)
_TIMEOUT_EXEMPT_PATTERNS = [
    r'^/static/', r'^/media/', r'^/favicon', r'^/__debug__/',
    r'^/accounts/login/', r'^/login/',
]
_TIMEOUT_EXEMPT_RE = [re.compile(p) for p in _TIMEOUT_EXEMPT_PATTERNS]


class SessionTimeoutMiddleware:
    """
    Cierra automáticamente la sesión de un usuario autenticado que lleva
    más de SESSION_TIMEOUT_SECONDS sin actividad.

    Default: 8 horas (un turno clínico completo).
    Ajustable por empresa en settings: SESSION_TIMEOUT_SECONDS.

    Al expirar, redirige a login con mensaje informativo.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            # Verificar si la ruta está exenta
            path = request.path_info
            if not any(p.match(path) for p in _TIMEOUT_EXEMPT_RE):
                self._check_timeout(request)

        response = self.get_response(request)

        # Actualizar timestamp de última actividad (solo para usuarios autenticados)
        if request.user.is_authenticated:
            request.session['_last_activity'] = timezone.now().isoformat()

        return response

    def _check_timeout(self, request):
        last_activity_str = request.session.get('_last_activity')
        if not last_activity_str:
            # Primera request de la sesión — inicializar
            request.session['_last_activity'] = timezone.now().isoformat()
            return

        try:
            last_activity = datetime.fromisoformat(last_activity_str)
            if timezone.is_naive(last_activity):
                last_activity = timezone.make_aware(last_activity)

            inactividad = (timezone.now() - last_activity).total_seconds()
            if inactividad > SESSION_TIMEOUT_SECONDS:
                horas = SESSION_TIMEOUT_SECONDS // 3600
                username = request.user.username
                logout(request)
                logger.info(
                    f"SessionTimeout: usuario '{username}' cerrado por inactividad "
                    f"({inactividad/3600:.1f}h > {horas}h límite)"
                )
                # Django redirect — el middleware lo interceptará antes de continuar
                # Nota: para que funcione correctamente, el middleware debe estar ANTES
                # de MessageMiddleware si quieres mostrar un mensaje.
                request.session['timeout_message'] = (
                    f'Tu sesión se cerró automáticamente por inactividad de más de {horas} horas.'
                )
        except Exception as exc:
            logger.warning(f"SessionTimeoutMiddleware error: {exc}")


# ══════════════════════════════════════════════════════════════════════════════
# 2. TENANT STORAGE — Inyecta empresa_slug en contexto Drive
# ══════════════════════════════════════════════════════════════════════════════

class TenantStorageMiddleware:
    """
    Inyecta el slug de la empresa del usuario autenticado en el contexto
    de Thread-local de TenantDriveStorage, de forma que cada archivo
    subido quede en su carpeta correspondiente en Drive:
      PRISLAB_Media/{empresa_slug}/...
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        empresa_slug = None
        if request.user.is_authenticated:
            empresa = getattr(request.user, 'empresa', None)
            if empresa:
                # Normalizar slug: nombre → slug seguro para carpeta
                nombre = getattr(empresa, 'nombre', '') or ''
                empresa_slug = (
                    nombre.lower()
                    .replace(' ', '_')
                    .replace('/', '_')
                    .replace('\\', '_')
                )[:50]

        # Inyectar en thread-local del storage
        try:
            from config.storage_backends import set_tenant_context
            set_tenant_context(empresa_slug or 'default')
        except Exception:
            logging.getLogger(__name__).exception("Error inesperado en __call__ (seguridad.py)")
            pass

        return self.get_response(request)
