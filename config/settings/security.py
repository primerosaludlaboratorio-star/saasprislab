"""
config/settings/security.py

Seguridad: validaciones de arranque en producción, CORS, CSRF, SESSION,
cookies, SSL, HSTS, headers, ALLOWED_HOSTS, PRISLAB_READ_ONLY, TENANT,
health-checks de arranque.
Consume: IS_PRODUCTION, DEBUG, _TESTING, _env_bool, _env_list, _env_int,
         PRISLAB_CANONICAL_HOST, SECRET_KEY, _CLAVES_INSEGURAS (de base.py)
"""
import logging
import os

from .base import (
    IS_PRODUCTION, DEBUG, _TESTING,
    _env_bool, _env_list, _env_int,
    PRISLAB_CANONICAL_HOST,
    SECRET_KEY, _CLAVES_INSEGURAS,
)

# ── Validaciones de arranque en producción ────────────────────────────────────

if IS_PRODUCTION:
    if not os.environ.get('SECRET_KEY') or SECRET_KEY in _CLAVES_INSEGURAS:
        raise RuntimeError(
            '🔴 PRISLAB SEGURIDAD: SECRET_KEY no está configurada o usa un valor inseguro en producción.\n'
            'Defina la variable de entorno SECRET_KEY con una clave segura de al menos 50 caracteres.\n'
            'Genere una con: python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"'
        )
    if len(SECRET_KEY) < 50:
        raise RuntimeError(
            '🔴 PRISLAB SEGURIDAD: SECRET_KEY en producción debe tener al menos 50 caracteres.'
        )
    if not (os.environ.get('GOOGLE_API_KEY') or os.environ.get('DEEPSEEK_API_KEY')):
        logging.getLogger('core').warning(
            'No hay API key de IA configurada. Defina GOOGLE_API_KEY o DEEPSEEK_API_KEY para activar Prisci.'
        )
    # Validar tokens de servicio requeridos en produccion
    _TOKENS_REQUERIDOS = {
        'PRISLAB_API_TOKEN': os.environ.get('PRISLAB_API_TOKEN', ''),
        'PRISLAB_FRONTEND_LOG_TOKEN': os.environ.get('PRISLAB_FRONTEND_LOG_TOKEN', ''),
        'CRON_SECRET': os.environ.get('CRON_SECRET', ''),
    }
    _tokens_faltantes = [k for k, v in _TOKENS_REQUERIDOS.items() if not v or v.startswith('replace-with')]
    if _tokens_faltantes:
        logging.getLogger('core').warning(
            f'🔴 PRISLAB SEGURIDAD: Tokens de servicio no configurados en produccion: {_tokens_faltantes}. '
            'Los endpoints protegidos por estos tokens retornarán 503.'
        )

# ── LAB_VALIDATION_PIN ────────────────────────────────────────────────────────

LAB_VALIDATION_PIN = os.environ.get("LAB_VALIDATION_PIN", "").strip()
if IS_PRODUCTION and not LAB_VALIDATION_PIN:
    raise RuntimeError(
        '🔴 PRISLAB SEGURIDAD: LAB_VALIDATION_PIN no está configurado en producción.\n'
        'Configure LAB_VALIDATION_PIN vía una variable de entorno segura con un PIN seguro.'
    )
if IS_PRODUCTION and len(LAB_VALIDATION_PIN) < 8:
    raise RuntimeError(
        '🔴 PRISLAB SEGURIDAD: en producción LAB_VALIDATION_PIN debe tener al menos 8 caracteres '
        '(auditoría ISO / gobierno de acceso). Actualice el valor en el servidor.'
    )

# ── PRISLAB_ESCUDO_USUARIO_ID ─────────────────────────────────────────────────

_raw_escudo = (os.environ.get('PRISLAB_ESCUDO_USUARIO_ID') or '').strip()
PRISLAB_ESCUDO_USUARIO_ID = None
if _raw_escudo:
    try:
        PRISLAB_ESCUDO_USUARIO_ID = int(_raw_escudo)
    except ValueError:
        PRISLAB_ESCUDO_USUARIO_ID = None
if IS_PRODUCTION and not PRISLAB_ESCUDO_USUARIO_ID:
    raise RuntimeError(
        '🔴 PRISLAB SEGURIDAD: PRISLAB_ESCUDO_USUARIO_ID es obligatoria en producción.\n'
        'Defina el ID numérico del usuario de sistema que firmará acciones del Escudo Clínico (HL7 / LIMS).'
    )

# ── FERNET_KEY ────────────────────────────────────────────────────────────────

FERNET_KEY = os.environ.get("FERNET_KEY", None)
if IS_PRODUCTION and not FERNET_KEY:
    raise RuntimeError(
        '🔴 PRISLAB SEGURIDAD: FERNET_KEY no está configurada en producción.\n'
        'Defina FERNET_KEY (env). Genere una con:\n'
        '  python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"'
    )

# ── CORS ──────────────────────────────────────────────────────────────────────

_cors_allow_raw = (os.environ.get('CORS_ALLOW_ALL_ORIGINS') or '').strip().lower()
if _cors_allow_raw:
    CORS_ALLOW_ALL_ORIGINS = _cors_allow_raw in ('true', '1', 'yes', 'on')
else:
    CORS_ALLOW_ALL_ORIGINS = False

_default_local_cors_origins = (
    'http://127.0.0.1:8000,http://localhost:8000,'
    'http://127.0.0.1:3000,http://localhost:3000'
)
_cors_origins_raw = os.environ.get('CORS_ALLOWED_ORIGINS')
if _cors_origins_raw is None and not IS_PRODUCTION:
    _cors_origins_raw = _default_local_cors_origins
CORS_ALLOWED_ORIGINS = [
    x.strip() for x in (_cors_origins_raw or '').split(',') if x.strip()
]
if IS_PRODUCTION and not CORS_ALLOW_ALL_ORIGINS and not CORS_ALLOWED_ORIGINS:
    logging.getLogger('config').warning(
        'CORS: en producción CORS_ALLOW_ALL_ORIGINS está en False y CORS_ALLOWED_ORIGINS está vacío. '
        'Las peticiones desde otros orígenes pueden fallar. '
        'Defina CORS_ALLOWED_ORIGINS o, temporalmente, CORS_ALLOW_ALL_ORIGINS=true.'
    )

CORS_ALLOW_CREDENTIALS = os.environ.get('CORS_ALLOW_CREDENTIALS', 'False').lower() in ('true', '1', 'yes', 'on')

# ── SESSION ───────────────────────────────────────────────────────────────────
# Nota: SESSION_ENGINE va en async_workers.py (decisión de infraestructura DB vs Redis).

SESSION_COOKIE_AGE = int(os.environ.get('SESSION_COOKIE_AGE_SECONDS', str(60 * 60 * 24 * 30)))  # 30 días
SESSION_SHORT_COOKIE_AGE = int(os.environ.get('SESSION_SHORT_COOKIE_AGE_SECONDS', str(60 * 60 * 10)))  # 10 horas
SESSION_SAVE_EVERY_REQUEST = True          # Renueva la sesión con cada request
SESSION_EXPIRE_AT_BROWSER_CLOSE = False    # Persistir aunque se cierre el navegador
SESSION_COOKIE_HTTPONLY = True             # BLINDAJE: No accesible via JS
SESSION_COOKIE_SAMESITE = 'Lax'           # BLINDAJE: Proteccion CSRF adicional
SESSION_COOKIE_SECURE = _env_bool('SESSION_COOKIE_SECURE', IS_PRODUCTION)

SESSION_COOKIE_DOMAIN = (
    os.environ.get('SESSION_COOKIE_DOMAIN')
    or os.environ.get('PRISLAB_SESSION_COOKIE_DOMAIN')
    or None
)

# ── CSRF ──────────────────────────────────────────────────────────────────────

CSRF_COOKIE_HTTPONLY = True              # BLINDAJE: Cookie CSRF no accesible via JS
CSRF_COOKIE_SECURE = _env_bool('CSRF_COOKIE_SECURE', IS_PRODUCTION)
CSRF_COOKIE_DOMAIN = (
    os.environ.get('CSRF_COOKIE_DOMAIN')
    or os.environ.get('PRISLAB_CSRF_COOKIE_DOMAIN')
    or None
)

CSRF_TRUSTED_ORIGINS = []
_extra_csrf = [
    x.strip()
    for x in (
        os.environ.get('CSRF_TRUSTED_ORIGINS')
        or os.environ.get('CSRF_TRUSTED_ORIGINS_EXTRA', '')
    ).split(',')
    if x.strip()
]
if IS_PRODUCTION and PRISLAB_CANONICAL_HOST:
    _canonical_origin = f'https://{PRISLAB_CANONICAL_HOST}'
    if _canonical_origin not in _extra_csrf:
        _extra_csrf.append(_canonical_origin)
for _o in _extra_csrf:
    if _o not in CSRF_TRUSTED_ORIGINS:
        CSRF_TRUSTED_ORIGINS.append(_o)

# ── SSL / HTTPS ───────────────────────────────────────────────────────────────

if IS_PRODUCTION:
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

SECURE_SSL_REDIRECT = _env_bool('SECURE_SSL_REDIRECT', False)
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'
SECURE_REFERRER_POLICY = 'strict-origin-when-cross-origin'

PERMISSIONS_POLICY = {
    'geolocation': [],
    'camera': [],
    'microphone': [],
    'payment': [],
    'usb': [],
    'fullscreen': ['self'],
}

SECURE_HSTS_SECONDS = int(os.environ.get(
    'SECURE_HSTS_SECONDS',
    '31536000' if IS_PRODUCTION else '0',
))
SECURE_HSTS_INCLUDE_SUBDOMAINS = _env_bool('SECURE_HSTS_INCLUDE_SUBDOMAINS', IS_PRODUCTION)
SECURE_HSTS_PRELOAD = _env_bool('SECURE_HSTS_PRELOAD', IS_PRODUCTION)

# ── Bloque not DEBUG — fuerza HTTPS y endurecimiento en staging/prod ──────────
# Disable SSL for E2E testing with: E2E_DISABLE_SSL=1

_e2e_disable_ssl = os.environ.get('E2E_DISABLE_SSL', '') == '1'
if not DEBUG and not _e2e_disable_ssl and not _TESTING:
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True

# ── ALLOWED_HOSTS ─────────────────────────────────────────────────────────────

_allowed_hosts_env = os.environ.get('ALLOWED_HOSTS', '')
if _allowed_hosts_env:
    ALLOWED_HOSTS = [host.strip() for host in _allowed_hosts_env.split(',') if host.strip()]
elif IS_PRODUCTION:
    _server_name = (os.environ.get('SERVER_NAME') or os.environ.get('DOMAIN_NAME') or '').strip()
    ALLOWED_HOSTS = [x for x in [_server_name, 'localhost', '127.0.0.1'] if x]
else:
    ALLOWED_HOSTS = ['localhost', '127.0.0.1', 'testserver']

# ── PRISLAB_READ_ONLY ─────────────────────────────────────────────────────────

PRISLAB_READ_ONLY = os.environ.get('PRISLAB_READ_ONLY', '').strip().lower() in ('1', 'true', 'yes', 'on')

PRISLAB_READ_ONLY_AUDIT_ALLOWED_PATH_PREFIXES = _env_list(
    'PRISLAB_READ_ONLY_AUDIT_ALLOWED_PATH_PREFIXES',
    default=['/farmacia/', '/inventario/', '/pdv/', '/pdv-farmacia/'],
)
PRISLAB_READ_ONLY_AUDIT_ALLOWED_USERNAMES = _env_list(
    'PRISLAB_READ_ONLY_AUDIT_ALLOWED_USERNAMES',
    default=[],
)
PRISLAB_READ_ONLY_AUDIT_ALLOWED_ROLES = _env_list(
    'PRISLAB_READ_ONLY_AUDIT_ALLOWED_ROLES',
    default=['ADMIN', 'DIRECTOR', 'GERENTE'],
)
PRISLAB_READ_ONLY_ALLOW_SUPERUSERS = _env_bool('PRISLAB_READ_ONLY_ALLOW_SUPERUSERS', False)

# ── TENANT ────────────────────────────────────────────────────────────────────

_raw_tenant_shadow = (os.environ.get('PRISLAB_TENANT_SHADOW_MODE') or '1').strip().lower()
PRISLAB_TENANT_SHADOW_MODE = _raw_tenant_shadow not in ('0', 'false', 'no', 'off')
PRISLAB_TENANT_STRICT_MODE = _env_bool('PRISLAB_TENANT_STRICT_MODE', IS_PRODUCTION)
PRISLAB_TENANT_SHADOW_LOG_CLI = os.environ.get('PRISLAB_TENANT_SHADOW_LOG_CLI', '').strip().lower() in (
    '1', 'true', 'yes', 'on',
)

# ── Health-checks de arranque ─────────────────────────────────────────────────

_log_sec = logging.getLogger('core.seguridad.startup')

# HC-1: PRISLAB_EMERGENCY_TENANT_BYPASS no debe estar activo en producción.
if os.environ.get('PRISLAB_EMERGENCY_TENANT_BYPASS', '').strip().lower() in ('1', 'true', 'yes', 'on'):
    _log_sec.critical(
        '🚨 PRISLAB_EMERGENCY_TENANT_BYPASS=1 está activo en este proceso. '
        'El filtro multi-tenant ORM está DESACTIVADO. '
        'Desactivar esta variable en cuanto sea seguro.'
    )

# HC-2: PRISLAB_DEFAULT_EMPRESA_ID debe estar configurado en entornos con más de una empresa.
if IS_PRODUCTION and not os.environ.get('PRISLAB_DEFAULT_EMPRESA_ID', '').strip():
    _log_sec.warning(
        'PRISLAB_DEFAULT_EMPRESA_ID no está configurado. '
        'En entornos con múltiples empresas, usuarios sin empresa asignada serán bloqueados '
        'si PRISLAB_TENANT_STRICT_MODE está activo.'
    )
