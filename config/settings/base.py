"""
config/settings/base.py

Helpers, FLAGS de entorno, INSTALLED_APPS, MIDDLEWARE, TEMPLATES, AUTH,
I18N, TZ, PWA, LOGIN_URL, DEFAULT_AUTO_FIELD, EMAIL, umbrales operativos,
IoT, Hardware, Farmacia, Admin, CISO, Mantenimiento, Sandbox.

NO contiene: DATABASES, STORAGES, STATIC/MEDIA, CACHES, CELERY, CHANNELS,
LOGGING, API keys IA, CORS all-origins, cookies, SSL (esos van en sus módulos).
"""
import logging
import os
import sys
from importlib.util import find_spec
from pathlib import Path
from urllib.parse import urlparse

BASE_DIR = Path(__file__).resolve().parent.parent.parent


# ── Helpers de entorno ────────────────────────────────────────────────────────

def _env_bool(name, default=False):
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in ('1', 'true', 'yes', 'on')


def _env_list(name, default=None):
    raw = os.environ.get(name)
    if raw is None:
        return list(default or [])
    return [item.strip() for item in raw.split(',') if item.strip()]


def _env_int(name, default):
    raw = os.environ.get(name)
    if raw is None or raw == '':
        return default
    try:
        return int(raw)
    except (TypeError, ValueError):
        logging.getLogger('config').warning(
            'Variable %s=%r no es un entero valido; usando %s.',
            name,
            raw,
            default,
        )
        return default


def _host_from_url(value):
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


# ── ENV CORE ──────────────────────────────────────────────────────────────────

DEBUG = os.environ.get('DEBUG', 'False') == 'True'

_TESTING = 'test' in sys.argv or os.environ.get('DJANGO_TESTING', '') == 'True'
DEPLOYMENT_ENV = (
    os.environ.get('PRISLAB_ENV')
    or os.environ.get('DJANGO_ENV')
    or ('test' if _TESTING else 'development')
).strip().lower()
IS_PRODUCTION = DEPLOYMENT_ENV == 'production'

_SECRET_KEY_ENV = os.environ.get('SECRET_KEY', '').strip()
if not _SECRET_KEY_ENV:
    _SECRET_KEY_ENV = 'dev-only-fallback-key-not-for-production-prislab-2026-local'
SECRET_KEY = _SECRET_KEY_ENV

_CLAVES_INSEGURAS = {
    'django-insecure-prislab-saas-key-2025',
    'dev-only-fallback-key-not-for-production-prislab-2026-local',
    'generate-a-random-key-here-min-50-chars',
    '4k*0c0z8gacu(%_)ug*y*t9xp*u55(u*$rv+pou#b=#o!4p4eo',
}

# ── TENANT / NETWORK ──────────────────────────────────────────────────────────

_raw_def_emp = (os.environ.get('PRISLAB_DEFAULT_EMPRESA_ID') or '').strip()
PRISLAB_DEFAULT_EMPRESA_ID = int(_raw_def_emp) if _raw_def_emp.isdigit() else None

ACADEMIA_EMPRESAS_PERMITIDAS = _env_list('ACADEMIA_EMPRESAS_PERMITIDAS', default=['prislab'])

API_URL = (os.environ.get('API_URL') or os.environ.get('PRISLAB_SAAS_URL') or '').strip()

SITE_URL = (os.environ.get('SITE_URL') or API_URL or 'http://localhost:8000').strip().rstrip('/')

PRISLAB_CANONICAL_HOST = _host_from_url(
    os.environ.get('PRISLAB_CANONICAL_HOST') or SITE_URL
)
PRISLAB_LEGACY_HOSTS = [
    _host_from_url(item)
    for item in (os.environ.get('PRISLAB_LEGACY_HOSTS') or '').split(',')
    if _host_from_url(item)
]

# ── CORS headers list (solo la lista; CORS_ALLOW_ALL_ORIGINS et al. van en security.py) ──

CORS_ALLOW_HEADERS = [
    'accept',
    'accept-encoding',
    'authorization',
    'content-type',
    'dnt',
    'origin',
    'user-agent',
    'x-csrftoken',
    'x-cron-secret',
    'x-empresa-id',
    'x-frontend-log-token',
    'x-prislab-api-key',
    'x-prislab-api-token',
    'x-prislab-kiosco-token',
    'x-requested-with',
]

# ── INSTALLED_APPS ────────────────────────────────────────────────────────────

INSTALLED_APPS = [
    'corsheaders',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.humanize',

    # Apps de negocio PRISLAB
    'core',         # Farmacia, vistas generales actuales
    'farmacia',     # Módulo Farmacia ERP (Kardex + Proveedores)
    'pacientes',    # Núcleo de pacientes compartido
    'laboratorio',  # Módulo de laboratorio clínico
    'lims',         # LIMS 4 Niveles: Analito → Perfil → Paquete → Precio

    # Apps V 5.0 - Núcleo Pris-Valle
    'seguridad',    # Seguridad física y botón de pánico
    'iot',          # IoT y Kiosco de auto-verificación
    'ia',           # Inteligencia Artificial (OCR y Voz)
    'reglas_negocio',  # Reglas de negocio estrictas
    'marketing',    # Crecimiento, campañas éticas, cupones, academy
    'academia',     # Diplomados / video learning
    'recepcion',    # Recepción y agendamiento de citas
    'enfermeria',   # Triage y signos vitales (opcional)
    'consultorio',  # Consultorio / Agenda / Expediente clínico
    'logistica',    # Logística / Rutas / Visitas a domicilio
    'inventario',   # Silos de Inventario Federados V8.0 (Lab, Consultorio, Generales + Motor Compras)
    'mantenimiento', # CMMS V8.2 — Protocolos, Checklists, Diagnóstico, Tickets, TCO, QR
    'bienestar',    # Módulo 'Espacio Seguro' - Diario Emocional y Recursos
    'contabilidad', # Facturación CFDI 4.0 y Contabilidad

    # Storage local/Drive + PWA
    'storages',
    'pwa',

    # Real-Time Communication (Voice Commander)
    'channels',
]

if find_spec('django_extensions') is not None:
    INSTALLED_APPS.insert(8, 'django_extensions')  # Para runserver_plus con HTTPS cuando exista

# ── MIDDLEWARE ────────────────────────────────────────────────────────────────

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',  # Para servir archivos estáticos en producción
    'corsheaders.middleware.CorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'core.middleware.canonical_host.CanonicalHostMiddleware',  # Unifica dominio publico para evitar sesiones divididas
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'core.api_contracts.middleware.ApiRequestIdMiddleware',  # Fase 3: X-Request-ID / correlación API
    'core.middleware.read_only.ReadOnlyMiddleware',  # DRP Punto 14: contingencia solo lectura (PRISLAB_READ_ONLY=1)
    'core.middleware.admin_access.AdminAccessMiddleware',  # Bastión 4: /admin/ por IP y grupo
    'core.middleware.rate_limit.RateLimitMiddleware',  # BLINDAJE R104: Rate limiting
    'core.middleware.EmpresaIdentityMiddleware',  # V6.0: Identidad + set_current_empresa() para TenantManager ORM
    'core.middleware.feature_flags.FeatureFlagMiddleware',  # V6.0: Bloqueo HTTP por módulo apagado (403)
    'core.middleware.json_response.JSONResponseMiddleware',  # Asegura respuestas JSON para AJAX
    'core.middleware.actividad_usuario.ActividadUsuarioMiddleware',  # Rastreo de actividad y sugerencias de descanso
    'core.middleware.sentinel.SentinelTelemetryMiddleware',  # PRIS SENTINEL: Telemetría inteligente del consultorio
    'core.middleware.performance.PerformanceMiddleware',  # SENTINEL 2.0: Latencia y cuellos de botella
    'core.middleware.pris_context.PrisContextMiddleware',  # PRIS-JARVIS: Contexto de usuario por request
    'core.middleware.mantenimiento.MaintenanceModeMiddleware',  # FASE 5: Modo mantenimiento / Solo Lectura
    'core.middleware.seguridad.SessionTimeoutMiddleware',       # FASE 4: Auto-logout tras inactividad (8h)
    'core.middleware.seguridad.TenantStorageMiddleware',        # FASE 3: Inyecta empresa_slug en Drive storage
    # Kill-switch Punto 12 (2026-04): middleware confundía paciente_id vs historia_id vs orden_id.
    # Trazabilidad NOM-024 / expediente vía hooks explícitos + ForenseAcceso.
    # 'core.middleware.seguridad.LogAccesoExpedienteMiddleware',  # FASE 4: legacy (desactivado)
    # 🔒 Arquitectura de Blindaje v2.0 — Protección de Expedientes Médicos
    'core.middleware.blindaje_expediente.BlindajeExpedienteMiddleware',  # Bloquea modificaciones a notas selladas
    'core.middleware.blindaje_expediente.SnapshotMiddleware',  # Captura metadatos para snapshots SHA
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

# ── SENTINEL umbrales ─────────────────────────────────────────────────────────

SENTINEL_WARN_QUERY_COUNT = int(os.environ.get('SENTINEL_WARN_QUERY_COUNT', '50'))
SENTINEL_WARN_LATENCY_MS = int(os.environ.get('SENTINEL_WARN_LATENCY_MS', '800'))

# ── ROUTING ───────────────────────────────────────────────────────────────────

ROOT_URLCONF = 'config.urls'
WSGI_APPLICATION = 'config.wsgi.application'
ASGI_APPLICATION = 'config.asgi.application'

# ── TEMPLATES ─────────────────────────────────────────────────────────────────

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        # APP_DIRS no es compatible con 'loaders' — usamos loaders explícitos
        'APP_DIRS': False,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'core.context_processors.empresa_actual',
            ],
            'loaders': [
                'django.template.loaders.app_directories.Loader',
                'django.template.loaders.filesystem.Loader',
            ],
            # Registrar filtros matemáticos como builtins: disponibles en TODO el sistema
            # sin necesidad de {% load math_filters %} en cada template.
            'builtins': [
                'core.templatetags.math_filters',
                'core.templatetags.auth_extras',
            ],
        },
    },
]

# ── AUTH ──────────────────────────────────────────────────────────────────────

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
        'OPTIONS': {'min_length': 10},
    },
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

AUTH_USER_MODEL = 'core.Usuario'

# ── I18N / TZ ─────────────────────────────────────────────────────────────────

LANGUAGE_CODE = 'es-mx'
TIME_ZONE = 'America/Mexico_City'
USE_I18N = True
USE_TZ = True

# ── EMAIL ─────────────────────────────────────────────────────────────────────

_email_user = os.environ.get('EMAIL_HOST_USER', '')
_email_pass = os.environ.get('EMAIL_HOST_PASSWORD', '')

if _email_user and _email_pass:
    EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
    EMAIL_HOST = os.environ.get('EMAIL_HOST', 'smtp.gmail.com')
    EMAIL_PORT = int(os.environ.get('EMAIL_PORT', '587'))
    EMAIL_USE_TLS = os.environ.get('EMAIL_USE_TLS', 'True') == 'True'
    EMAIL_HOST_USER = _email_user
    EMAIL_HOST_PASSWORD = _email_pass
else:
    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

DEFAULT_FROM_EMAIL = os.environ.get('DEFAULT_FROM_EMAIL', 'PRISLAB <noreply@prislab.app>')
DIRECTOR_EMAIL = os.environ.get('DIRECTOR_EMAIL', '')

# ── SEGURIDAD CISO ────────────────────────────────────────────────────────────

CISO_EMAIL = os.environ.get('CISO_EMAIL', DIRECTOR_EMAIL)

PRISLAB_MASTER_RECOVERY_CODE = os.environ.get('PRISLAB_MASTER_RECOVERY_CODE', '')

TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN', '')
TELEGRAM_CISO_CHAT_ID = os.environ.get('TELEGRAM_CISO_CHAT_ID', '')

_ips_bypass_raw = os.environ.get('IPS_INTERNAS_2FA_BYPASS', '')
IPS_INTERNAS_2FA_BYPASS = [ip.strip() for ip in _ips_bypass_raw.split(',') if ip.strip()]

RESULTADOS_PUBLICOS_TOKEN_MAX_AGE_SECONDS = int(
    os.environ.get('RESULTADOS_PUBLICOS_TOKEN_MAX_AGE_SECONDS', str(60 * 60 * 24 * 7))
)

NOM024_ALERTA_ACCESOS_UMBRAL = int(os.environ.get('NOM024_ALERTA_ACCESOS_UMBRAL', '10'))

# ── FASE 5 — Modo mantenimiento ───────────────────────────────────────────────

SYSTEM_MAINTENANCE_MODE = os.environ.get('SYSTEM_MAINTENANCE_MODE', 'false').lower() == 'true'
MAINTENANCE_MESSAGE = os.environ.get('MAINTENANCE_MESSAGE', '')
MAINTENANCE_ETA = os.environ.get('MAINTENANCE_ETA', '')

# ── IoT ───────────────────────────────────────────────────────────────────────

_hl7_ips_raw = os.environ.get('HL7_ALLOWED_IPS', '')
HL7_ALLOWED_IPS = [ip.strip() for ip in _hl7_ips_raw.split(',') if ip.strip()]
HL7_API_KEY = os.environ.get('HL7_API_KEY', '')
HL7_ACTIVE = os.environ.get('HL7_ACTIVE', 'False').lower() in ('true', '1', 'yes')

# ── Hardware ──────────────────────────────────────────────────────────────────

ZEBRA_PRINTER_HOST = os.environ.get('ZEBRA_PRINTER_HOST', '')
ZEBRA_PRINTER_PORT = int(os.environ.get('ZEBRA_PRINTER_PORT', '9100'))

THERMAL_PRINTER_HOST = os.environ.get('THERMAL_PRINTER_HOST', '')
THERMAL_PRINTER_PORT = int(os.environ.get('THERMAL_PRINTER_PORT', '9100'))

# ── Umbrales farmacia ─────────────────────────────────────────────────────────

FARMACIA_DIAS_CADUCIDAD_CRITICO = int(os.environ.get('FARMACIA_DIAS_CADUCIDAD_CRITICO', 30))
FARMACIA_DIAS_CADUCIDAD_ALERTA = int(os.environ.get('FARMACIA_DIAS_CADUCIDAD_ALERTA', 90))

# ── Admin ─────────────────────────────────────────────────────────────────────

ADMIN_IP_RESTRICTION_ENABLED = os.environ.get('ADMIN_IP_RESTRICTION_ENABLED', 'False').lower() in ('true', '1', 'yes')
ALLOWED_ADMIN_IPS = [x.strip() for x in os.environ.get('ALLOWED_ADMIN_IPS', '').split(',') if x.strip()]
ADMIN_GROUP_RESTRICTION_ENABLED = os.environ.get('ADMIN_GROUP_RESTRICTION_ENABLED', 'False').lower() in ('true', '1', 'yes')

BACKUP_IMMUTABLE_LOG_AUTO = os.environ.get('BACKUP_IMMUTABLE_LOG_AUTO', 'False').lower() in ('true', '1', 'yes')

# ── PWA settings ──────────────────────────────────────────────────────────────

PWA_APP_NAME = os.environ.get('PWA_APP_NAME', 'PRISLAB')
PWA_APP_SHORT_NAME = os.environ.get('PWA_APP_SHORT_NAME', 'PRISLAB')
PWA_APP_DESCRIPTION = 'Plataforma clínica SaaS (Farmacia + Laboratorio) PRISLAB'
PWA_APP_THEME_COLOR = '#D9230F'
PWA_APP_BACKGROUND_COLOR = '#FFFFFF'
PWA_APP_DISPLAY = 'standalone'
PWA_APP_SCOPE = '/'
PWA_APP_ORIENTATION = 'portrait'
PWA_APP_START_URL = '/'
PWA_APP_STATUS_BAR_COLOR = 'default'
PWA_APP_ICONS = [
    {
        'src': '/static/img/icon-192.svg',
        'sizes': '192x192'
    },
    {
        'src': '/static/img/icon-512.svg',
        'sizes': '512x512'
    }
]
PWA_APP_SPLASH_SCREEN = [
    {
        'src': '/static/img/splash-640x1136.svg',
        'sizes': '640x1136'
    }
]
PWA_APP_DIR = 'ltr'
PWA_APP_LANG = 'es-MX'

# ── LOGIN / DEFAULT ───────────────────────────────────────────────────────────

LOGIN_URL = '/login/'
LOGIN_REDIRECT_URL = '/home/'  # Se sobrescribe por la redirección inteligente en CustomLoginView

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ── Punto 23 — Sandbox ────────────────────────────────────────────────────────

PRISLAB_DEPLOYMENT_MODE = (os.environ.get('PRISLAB_DEPLOYMENT_MODE') or '').strip().lower()
IS_SANDBOX = PRISLAB_DEPLOYMENT_MODE == 'training_sandbox'

# ── __all__ — Limpia el namespace de Django settings ─────────────────────────
# Los helpers con prefijo _ no son settings de Django pero se incluyen aquí
# porque los otros módulos del paquete los importan explícitamente.

__all__ = [
    'BASE_DIR', 'DEBUG', '_TESTING', 'DEPLOYMENT_ENV', 'IS_PRODUCTION',
    'SECRET_KEY', '_CLAVES_INSEGURAS',
    'PRISLAB_DEFAULT_EMPRESA_ID', 'ACADEMIA_EMPRESAS_PERMITIDAS',
    'API_URL', 'SITE_URL', 'PRISLAB_CANONICAL_HOST', 'PRISLAB_LEGACY_HOSTS',
    'CORS_ALLOW_HEADERS',
    'INSTALLED_APPS', 'MIDDLEWARE',
    'SENTINEL_WARN_QUERY_COUNT', 'SENTINEL_WARN_LATENCY_MS',
    'ROOT_URLCONF', 'WSGI_APPLICATION', 'ASGI_APPLICATION',
    'TEMPLATES', 'AUTH_PASSWORD_VALIDATORS', 'AUTH_USER_MODEL',
    'LANGUAGE_CODE', 'TIME_ZONE', 'USE_I18N', 'USE_TZ',
    'EMAIL_BACKEND', 'DEFAULT_FROM_EMAIL', 'DIRECTOR_EMAIL',
    'CISO_EMAIL', 'PRISLAB_MASTER_RECOVERY_CODE',
    'TELEGRAM_BOT_TOKEN', 'TELEGRAM_CISO_CHAT_ID',
    'IPS_INTERNAS_2FA_BYPASS', 'RESULTADOS_PUBLICOS_TOKEN_MAX_AGE_SECONDS',
    'NOM024_ALERTA_ACCESOS_UMBRAL',
    'SYSTEM_MAINTENANCE_MODE', 'MAINTENANCE_MESSAGE', 'MAINTENANCE_ETA',
    'HL7_ALLOWED_IPS', 'HL7_API_KEY', 'HL7_ACTIVE',
    'ZEBRA_PRINTER_HOST', 'ZEBRA_PRINTER_PORT',
    'THERMAL_PRINTER_HOST', 'THERMAL_PRINTER_PORT',
    'FARMACIA_DIAS_CADUCIDAD_CRITICO', 'FARMACIA_DIAS_CADUCIDAD_ALERTA',
    'ADMIN_IP_RESTRICTION_ENABLED', 'ALLOWED_ADMIN_IPS',
    'ADMIN_GROUP_RESTRICTION_ENABLED', 'BACKUP_IMMUTABLE_LOG_AUTO',
    'PWA_APP_NAME', 'PWA_APP_SHORT_NAME', 'PWA_APP_DESCRIPTION',
    'PWA_APP_THEME_COLOR', 'PWA_APP_BACKGROUND_COLOR', 'PWA_APP_DISPLAY',
    'PWA_APP_SCOPE', 'PWA_APP_ORIENTATION', 'PWA_APP_START_URL',
    'PWA_APP_STATUS_BAR_COLOR', 'PWA_APP_ICONS', 'PWA_APP_SPLASH_SCREEN',
    'PWA_APP_DIR', 'PWA_APP_LANG',
    'LOGIN_URL', 'LOGIN_REDIRECT_URL', 'DEFAULT_AUTO_FIELD',
    'PRISLAB_DEPLOYMENT_MODE', 'IS_SANDBOX',
    # Helpers expuestos deliberadamente para uso en otros módulos del paquete
    '_env_bool', '_env_int', '_env_list', '_host_from_url',
    # Internos usados por security.py
    '_SECRET_KEY_ENV',
]
