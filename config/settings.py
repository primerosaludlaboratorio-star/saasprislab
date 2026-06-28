import logging
import os
import sys
from importlib.util import find_spec
from pathlib import Path
from urllib.parse import urlparse

BASE_DIR = Path(__file__).resolve().parent.parent

# Variables de entorno (estándar)
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "").strip()
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY", "").strip().replace('\r', '').replace('\n', '')
GOOGLE_GEMINI_API_KEY = os.environ.get("GOOGLE_GEMINI_API_KEY", "").strip().replace('\r', '').replace('\n', '')
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "").strip().replace('\r', '').replace('\n', '')
AI_PROVIDER = os.environ.get("AI_PROVIDER", "").strip().lower()
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "").strip().replace('\r', '').replace('\n', '')
DEEPSEEK_MODEL = os.environ.get("DEEPSEEK_MODEL", "deepseek-chat").strip()
DEEPSEEK_API_URL = os.environ.get(
    "DEEPSEEK_API_URL",
    "https://api.deepseek.com/v1/chat/completions",
).strip()
PRISCI_WEBHOOK_TOKEN = os.environ.get("PRISCI_WEBHOOK_TOKEN", "").strip()
PRISCI_WEBHOOK_VERIFY_TOKEN = os.environ.get("PRISCI_WEBHOOK_VERIFY_TOKEN", "").strip()

# Canonicalización: una sola clave puede alimentar Gemini.
# Orden de preferencia: GOOGLE_API_KEY -> GOOGLE_GEMINI_API_KEY -> GEMINI_API_KEY
if not GOOGLE_API_KEY:
    GOOGLE_API_KEY = GOOGLE_GEMINI_API_KEY or GEMINI_API_KEY
if not GOOGLE_GEMINI_API_KEY:
    GOOGLE_GEMINI_API_KEY = GOOGLE_API_KEY
if not GEMINI_API_KEY:
    GEMINI_API_KEY = GOOGLE_API_KEY

# PRIS Sentinel -> GitHub Auto-Reporte
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")
GITHUB_REPO = os.environ.get("GITHUB_REPO", "")  # formato: owner/repo

# Configuración de entorno (producción vs desarrollo)
# En local, si no se especifica nada, usamos desarrollo para no bloquear herramientas.
DEBUG = os.environ.get('DEBUG', 'False') == 'True'

# Detectar si estamos corriendo tests (manage.py test o call_command / CI)
_TESTING = 'test' in sys.argv or os.environ.get('DJANGO_TESTING', '') == 'True'
DEPLOYMENT_ENV = (
    os.environ.get('PRISLAB_ENV')
    or os.environ.get('DJANGO_ENV')
    or ('test' if _TESTING else 'development')
).strip().lower()
IS_PRODUCTION = DEPLOYMENT_ENV == 'production'
# SECRET_KEY: obligatoria via variable de entorno. En dev local usa fallback solo si no esta definida.
_SECRET_KEY_ENV = os.environ.get('SECRET_KEY', '').strip()
if not _SECRET_KEY_ENV:
    # Fallback solo en desarrollo local — NUNCA usar en produccion
    _SECRET_KEY_ENV = 'dev-only-fallback-key-not-for-production-prislab-2026-local'
SECRET_KEY = _SECRET_KEY_ENV


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

# Tenant por defecto (PRISLAB mononodo / rescate). Opcional: entero explícito.
_raw_def_emp = (os.environ.get('PRISLAB_DEFAULT_EMPRESA_ID') or '').strip()
PRISLAB_DEFAULT_EMPRESA_ID = int(_raw_def_emp) if _raw_def_emp.isdigit() else None

# Módulos de academia permitidos por empresa.
# Por defecto solo PRISLAB; para abrir a otros laboratorios, agregar nombre, slug o ID en el entorno.
ACADEMIA_EMPRESAS_PERMITIDAS = _env_list('ACADEMIA_EMPRESAS_PERMITIDAS', default=['prislab'])

# URL pública del backend SaaS para integraciones internas o frontend separado
API_URL = (os.environ.get('API_URL') or os.environ.get('PRISLAB_SAAS_URL') or '').strip()

# URL pública del sitio — usada en QR de resultados de laboratorio, links en PDF, etc.
# En producción VPS: SITE_URL=https://tu-dominio.com
SITE_URL = (os.environ.get('SITE_URL') or API_URL or 'http://localhost:8000').strip().rstrip('/')


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


PRISLAB_CANONICAL_HOST = _host_from_url(
    os.environ.get('PRISLAB_CANONICAL_HOST') or SITE_URL
)
PRISLAB_LEGACY_HOSTS = [
    _host_from_url(item)
    for item in (os.environ.get('PRISLAB_LEGACY_HOSTS') or '').split(',')
    if _host_from_url(item)
]

# CORS: restrictivo por defecto. En local se permite solo localhost explicito.
# Explícito: CORS_ALLOW_ALL_ORIGINS=true|false | Lista: CORS_ALLOWED_ORIGINS=https://a.com,https://b.com
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

# ── Validación de seguridad en producción ────────────────────────────────────
_CLAVES_INSEGURAS = {
    'django-insecure-prislab-saas-key-2025',
    'dev-only-fallback-key-not-for-production-prislab-2026-local',
    'generate-a-random-key-here-min-50-chars',
    '4k*0c0z8gacu(%_)ug*y*t9xp*u55(u*$rv+pou#b=#o!4p4eo',
}
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
        import logging as _log
        _log.getLogger('core').warning(
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
        import logging as _log_tok
        _log_tok.getLogger('core').warning(
            f'🔴 PRISLAB SEGURIDAD: Tokens de servicio no configurados en produccion: {_tokens_faltantes}. '
            'Los endpoints protegidos por estos tokens retornarán 503.'
        )


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
    'suscripciones', # Módulo 1 Fase II: Facturación Multi-Tenant

    # Storage local/Drive + PWA
    'storages',
    'pwa',

    # Real-Time Communication (Voice Commander)
    'channels',
]

if find_spec('django_extensions') is not None:
    INSTALLED_APPS.insert(8, 'django_extensions')  # Para runserver_plus con HTTPS cuando exista

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

# Punto 19 — PerformanceMiddleware: conteo SQL (execute_wrapper) + alertas GCP
SENTINEL_WARN_QUERY_COUNT = int(os.environ.get('SENTINEL_WARN_QUERY_COUNT', '50'))
SENTINEL_WARN_LATENCY_MS = int(os.environ.get('SENTINEL_WARN_LATENCY_MS', '800'))

ROOT_URLCONF = 'config.urls'

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

WSGI_APPLICATION = 'config.wsgi.application'

# Configuración de Base de Datos
if os.environ.get('DB_HOST'):
    # PostgreSQL local o remoto en Vultr
    db_host = os.environ.get('DB_HOST', '')
    db_conn_max_age = _env_int('DB_CONN_MAX_AGE', 0 if IS_PRODUCTION else 60)
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': os.environ.get('DB_NAME', 'prislab_db'),
            'USER': os.environ.get('DB_USER', 'postgres'),
            'PASSWORD': os.environ.get('DB_PASSWORD', ''),
            'HOST': db_host,
            'PORT': os.environ.get('DB_PORT', '5432'),
            'CONN_MAX_AGE': db_conn_max_age,
            'CONN_HEALTH_CHECKS': _env_bool('DB_CONN_HEALTH_CHECKS', True),
        }
    }
    # Sin print en producción
else:
    # SQLite para desarrollo local (timeout 60s para evitar "database is locked" en carga masiva)
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
            'OPTIONS': {'timeout': 60},
        }
    }

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
        'OPTIONS': {'min_length': 10},
    },
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# --- CONFIGURACIÓN SAAS PRISLAB ---
AUTH_USER_MODEL = 'core.Usuario'
LANGUAGE_CODE = 'es-mx'
TIME_ZONE = 'America/Mexico_City'
USE_I18N = True
USE_TZ = True

# ==============================================================================
# ESTRATEGIA DE ALMACENAMIENTO (WhiteNoise + Google Drive opcional)
# ==============================================================================

# ------------------------------------------------------------------------------
# ARCHIVOS ESTÁTICOS (STATIC) - WHITENOISE
# ------------------------------------------------------------------------------
# Estos archivos se sirven rápido desde WhiteNoise / Nginx
# Incluye: logos, iconos, CSS, JavaScript, fuentes, imágenes del tema
STATIC_URL = '/static/'
STATICFILES_DIRS = [os.path.join(BASE_DIR, 'static')]
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')

# WhiteNoise: Compresión y cache automático
# Ventajas: Ultra rápido, sin latencia, sin costos adicionales
# USE_MANIFEST_STORAGE se usa durante Docker build para que collectstatic
# genere el manifest (staticfiles.json) que la producción necesita.
_static_backend = (
    'whitenoise.storage.CompressedManifestStaticFilesStorage'
    if (IS_PRODUCTION or os.environ.get('USE_MANIFEST_STORAGE'))
    else 'django.contrib.staticfiles.storage.StaticFilesStorage'
)

# Configuración de WhiteNoise
WHITENOISE_MAX_AGE = 31536000  # 1 año de cache para archivos estáticos
WHITENOISE_COMPRESS_OFFLINE = True  # Pre-comprimir archivos
WHITENOISE_USE_FINDERS = True  # Buscar archivos automáticamente

# ------------------------------------------------------------------------------
# ARCHIVOS MEDIA (DINÁMICOS) - DISCO LOCAL + GOOGLE DRIVE OPCIONAL
# ------------------------------------------------------------------------------
# Audios de PRIS-Chat, fotos de pacientes, PDFs, recetas OCR, etc.
# En producción se guardan localmente en la VPS y pueden sincronizarse a Drive.

MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

# CICLO 10: File upload security — limit size (20MB)
FILE_UPLOAD_MAX_MEMORY_SIZE = 20 * 1024 * 1024
DATA_UPLOAD_MAX_MEMORY_SIZE = 20 * 1024 * 1024

# Carpeta maestra en Google Drive (ID de la carpeta PRISLAB_Media)
# Sin valor por defecto en código: evita filtrar IDs de carpeta y fuerza configuración explícita (.env)
GOOGLE_DRIVE_FOLDER_ID = (
    os.environ.get('GOOGLE_DRIVE_FOLDER_ID') or
    os.environ.get('DRIVE_FOLDER_ID') or
    ''
).strip()

# Credenciales: OAuth 2.0 (prioridad) o Service Account legacy
GOOGLE_DRIVE_CREDENTIALS = None
_DRIVE_STORAGE_ACTIVO = False  # pylint: disable=invalid-name
GOOGLE_DRIVE_DIRECT_STORAGE = (
    os.environ.get('GOOGLE_DRIVE_DIRECT_STORAGE', '')
    .strip()
    .lower() in ('1', 'true', 'yes', 'on')
)

# Vultr Object Storage (S3-compatible) para media operativa del SaaS
VULTR_OBJECT_STORAGE_ENABLED = _env_bool('VULTR_OBJECT_STORAGE_ENABLED', False)
VULTR_S3_ACCESS_KEY_ID = (os.environ.get('VULTR_S3_ACCESS_KEY_ID') or '').strip()
VULTR_S3_SECRET_ACCESS_KEY = (os.environ.get('VULTR_S3_SECRET_ACCESS_KEY') or '').strip()
VULTR_S3_ENDPOINT_URL = (os.environ.get('VULTR_S3_ENDPOINT_URL') or '').strip().rstrip('/')
VULTR_S3_BUCKET_NAME = (os.environ.get('VULTR_S3_BUCKET_NAME') or '').strip()
VULTR_S3_CUSTOM_DOMAIN = (os.environ.get('VULTR_S3_CUSTOM_DOMAIN') or '').strip()
VULTR_S3_QUERYSTRING_AUTH = _env_bool('VULTR_S3_QUERYSTRING_AUTH', True)
VULTR_S3_FILE_OVERWRITE = _env_bool('VULTR_S3_FILE_OVERWRITE', False)
VULTR_S3_DEFAULT_ACL = (os.environ.get('VULTR_S3_DEFAULT_ACL') or '').strip() or None

if VULTR_OBJECT_STORAGE_ENABLED:
    AWS_ACCESS_KEY_ID = VULTR_S3_ACCESS_KEY_ID
    AWS_SECRET_ACCESS_KEY = VULTR_S3_SECRET_ACCESS_KEY
    AWS_STORAGE_BUCKET_NAME = VULTR_S3_BUCKET_NAME
    AWS_S3_ENDPOINT_URL = VULTR_S3_ENDPOINT_URL
    AWS_S3_REGION_NAME = None
    AWS_S3_SIGNATURE_VERSION = 's3v4'
    AWS_S3_ADDRESSING_STYLE = 'virtual'
    AWS_DEFAULT_ACL = VULTR_S3_DEFAULT_ACL
    AWS_QUERYSTRING_AUTH = VULTR_S3_QUERYSTRING_AUTH
    AWS_S3_FILE_OVERWRITE = VULTR_S3_FILE_OVERWRITE
    AWS_S3_CUSTOM_DOMAIN = VULTR_S3_CUSTOM_DOMAIN or None
    AWS_S3_VERIFY = True

# STORAGES base (puede ser sobreescrito por Drive abajo)
STORAGES = {
    "default": {"BACKEND": "config.storage_backends.BufferLocalStorage"},
    "staticfiles": {"BACKEND": 'django.contrib.staticfiles.storage.StaticFilesStorage'},
}

if VULTR_OBJECT_STORAGE_ENABLED:
    _faltantes_vultr = [
        nombre for nombre, valor in {
            'VULTR_S3_ACCESS_KEY_ID': VULTR_S3_ACCESS_KEY_ID,
            'VULTR_S3_SECRET_ACCESS_KEY': VULTR_S3_SECRET_ACCESS_KEY,
            'VULTR_S3_ENDPOINT_URL': VULTR_S3_ENDPOINT_URL,
            'VULTR_S3_BUCKET_NAME': VULTR_S3_BUCKET_NAME,
        }.items() if not valor
    ]
    if _faltantes_vultr:
        logging.getLogger('config').warning(
            '[STORAGE] Vultr Object Storage habilitado pero incompleto. '
            'Faltan variables: %s. Se mantiene BufferLocalStorage.',
            ', '.join(_faltantes_vultr),
        )
    else:
        STORAGES["default"] = {"BACKEND": "config.storage_backends.TenantS3Storage"}
        logging.getLogger('config').info(
            '[STORAGE] Vultr Object Storage activo como backend default (%s / %s)',
            VULTR_S3_BUCKET_NAME,
            VULTR_S3_ENDPOINT_URL,
        )

try:
    from config.drive_credentials import get_drive_credentials
    _drive_creds = get_drive_credentials()
    if _drive_creds and GOOGLE_DRIVE_FOLDER_ID:
        GOOGLE_DRIVE_CREDENTIALS = _drive_creds
        import logging as _log_drive
        if GOOGLE_DRIVE_DIRECT_STORAGE:
            if VULTR_OBJECT_STORAGE_ENABLED:
                _log_drive.getLogger('config').info(
                    "[STORAGE] Google Drive directo solicitado, pero Vultr Object Storage conserva prioridad como backend default."
                )
            else:
                STORAGES["default"] = {"BACKEND": "config.storage_backends.GoogleDriveStorage"}
                _DRIVE_STORAGE_ACTIVO = True
                _log_drive.getLogger('config').info("[STORAGE] Google Drive directo activo para archivos media")
        else:
            _log_drive.getLogger('config').info(
                "[STORAGE] Credenciales Drive resueltas. "
                "Se mantiene BufferLocalStorage como backend por defecto hasta habilitar "
                "GOOGLE_DRIVE_DIRECT_STORAGE explícitamente."
            )
    elif GOOGLE_DRIVE_FOLDER_ID and not _drive_creds:
        import logging as _log_drive
        _log_drive.getLogger('config').warning(
            "[STORAGE] GOOGLE_DRIVE_FOLDER_ID configurado pero credenciales no disponibles. "
            "Configure GOOGLE_DRIVE_TOKEN_PATH/GOOGLE_DRIVE_CREDENTIALS_PATH "
            "o, transitoriamente, GOOGLE_DRIVE_SERVICE_ACCOUNT_JSON/GOOGLE_APPLICATION_CREDENTIALS."
        )
except (ImportError, OSError, ValueError) as e:
    import logging as _log_drive
    _log_drive.getLogger('config').warning(f"Error configurando Google Drive: {e}. Usando almacenamiento local.")

# ==============================================================================
# EMAIL - NOTIFICACIONES AL DIRECTOR
# ==============================================================================
# En producción: configurar EMAIL_HOST_USER y EMAIL_HOST_PASSWORD como env vars
# En desarrollo: se usa consola (los emails se imprimen en terminal)

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

# ==============================================================================
# SEGURIDAD CISO — FASE 4 ÉLITE
# ==============================================================================
# Email del CISO (Director Jonathan) para alertas de seguridad
CISO_EMAIL = os.environ.get('CISO_EMAIL', DIRECTOR_EMAIL)

# Código maestro de recuperación 2FA (CISO bypass de emergencia)
# Configurar como variable de entorno segura: PRISLAB_MASTER_RECOVERY_CODE
PRISLAB_MASTER_RECOVERY_CODE = os.environ.get('PRISLAB_MASTER_RECOVERY_CODE', '')

# Telegram Bot para alertas en tiempo real
TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN', '')
TELEGRAM_CISO_CHAT_ID = os.environ.get('TELEGRAM_CISO_CHAT_ID', '')

# Reglas explícitas de bypass 2FA (lista separada por comas).
# Acepta IP exacta, prefijo que termine en "." o red CIDR (ej. 192.168.1.23, 192.168.1., 10.0.0.0/24).
_ips_bypass_raw = os.environ.get('IPS_INTERNAS_2FA_BYPASS', '')
IPS_INTERNAS_2FA_BYPASS = [ip.strip() for ip in _ips_bypass_raw.split(',') if ip.strip()]

# Caducidad de enlaces públicos de resultados.
# Ajustable por entorno para endurecer o relajar el acceso temporal.
RESULTADOS_PUBLICOS_TOKEN_MAX_AGE_SECONDS = int(
    os.environ.get('RESULTADOS_PUBLICOS_TOKEN_MAX_AGE_SECONDS', str(60 * 60 * 24 * 7))
)

# Umbral de alerta NOM-024: >N accesos a expedientes en 1 hora notifica al CISO
NOM024_ALERTA_ACCESOS_UMBRAL = int(os.environ.get('NOM024_ALERTA_ACCESOS_UMBRAL', '10'))

# ==============================================================================
# FASE 5 — MODO MANTENIMIENTO (activa antes de Migración Maestra)
# ==============================================================================
# Activar vía env var en producción:  SYSTEM_MAINTENANCE_MODE=true
SYSTEM_MAINTENANCE_MODE = os.environ.get('SYSTEM_MAINTENANCE_MODE', 'false').lower() == 'true'
MAINTENANCE_MESSAGE = os.environ.get('MAINTENANCE_MESSAGE', '')
MAINTENANCE_ETA = os.environ.get('MAINTENANCE_ETA', '')

# ==============================================================================
# FASE 6 — IoT HL7/ASTM (Analizadores de laboratorio)
# ==============================================================================
# IPs de los equipos autorizados para enviar resultados (separadas por comas)
_hl7_ips_raw = os.environ.get('HL7_ALLOWED_IPS', '')
HL7_ALLOWED_IPS = [ip.strip() for ip in _hl7_ips_raw.split(',') if ip.strip()]
HL7_API_KEY = os.environ.get('HL7_API_KEY', '')

# ==============================================================================
# FASE 7 — Impresoras de red
# ==============================================================================
ZEBRA_PRINTER_HOST = os.environ.get('ZEBRA_PRINTER_HOST', '')
ZEBRA_PRINTER_PORT = int(os.environ.get('ZEBRA_PRINTER_PORT', '9100'))

# ==============================================================================
# FASE 8 — Impresora térmica ESC/POS y Corte de Caja
# ==============================================================================
THERMAL_PRINTER_HOST = os.environ.get('THERMAL_PRINTER_HOST', '')
THERMAL_PRINTER_PORT = int(os.environ.get('THERMAL_PRINTER_PORT', '9100'))

# ==============================================================================
# RESUMEN DE LA ESTRATEGIA:
# ==============================================================================
# 1. STATIC (WhiteNoise):
#    - Carga instantánea
#    - Sin latencia
#    - Sin costos adicionales
#    - Perfecto para UI/UX
#
# 2. MEDIA (Google Drive):
#    - 10TB de espacio (ya pagado)
#    - Backup automático de Google
#    - Compartir archivos fácilmente
#    - Perfecto para documentos grandes
# ==============================================================================

# ------------------------------------------------------------------------------
# PWA settings (django-pwa)
# ------------------------------------------------------------------------------
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

# Redirección de seguridad (Corrección de la Auditoría)
LOGIN_URL = '/login/'
LOGIN_REDIRECT_URL = '/home/'  # Se sobrescribe por la redirección inteligente en CustomLoginView 

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ==============================================================================
# CACHÉ — Redis (Producción) / LocMem (Desarrollo)
# ==============================================================================
REDIS_URL = os.environ.get('REDIS_URL')
_cache_logger = logging.getLogger('config')
if REDIS_URL:
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.redis.RedisCache',
            'LOCATION': REDIS_URL,
            'OPTIONS': {
                'db': '0',
            },
            'KEY_PREFIX': 'prislab',
            'TIMEOUT': 300,  # 5 minutos por defecto
        }
    }
    _cache_logger.info('[CACHE] Backend Redis activo (ubicación omitida en logs por seguridad)')
else:
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
            'LOCATION': 'prislab-locmem',
        }
    }
    _cache_logger.info('[CACHE] LocMem (desarrollo)')

# ── SESIONES: Siempre en DB (persisten entre deploys y reinicios) ──
SESSION_ENGINE = 'django.contrib.sessions.backends.db'
# Mantener sesiones extensas para operación diaria continua.
# Ajustable por variable de entorno sin tocar código.
SESSION_COOKIE_AGE = int(os.environ.get('SESSION_COOKIE_AGE_SECONDS', str(60 * 60 * 24 * 30)))  # 30 días
SESSION_SHORT_COOKIE_AGE = int(os.environ.get('SESSION_SHORT_COOKIE_AGE_SECONDS', str(60 * 60 * 10)))  # 10 horas
SESSION_SAVE_EVERY_REQUEST = True          # Renueva la sesión con cada request
SESSION_EXPIRE_AT_BROWSER_CLOSE = False    # Persistir aunque se cierre el navegador
SESSION_COOKIE_HTTPONLY = True             # BLINDAJE: No accesible via JS
SESSION_COOKIE_SAMESITE = 'Lax'           # BLINDAJE: Proteccion CSRF adicional
CSRF_COOKIE_HTTPONLY = True              # BLINDAJE: Cookie CSRF no accesible via JS

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

# Cookies de sesión/CSRF: si el entorno define un dominio común, úsalo.
# En caso contrario se deja el comportamiento por-host de Django.
SESSION_COOKIE_DOMAIN = (
    os.environ.get('SESSION_COOKIE_DOMAIN')
    or os.environ.get('PRISLAB_SESSION_COOKIE_DOMAIN')
    or None
)
CSRF_COOKIE_DOMAIN = (
    os.environ.get('CSRF_COOKIE_DOMAIN')
    or os.environ.get('PRISLAB_CSRF_COOKIE_DOMAIN')
    or None
)

# ── Umbrales de caducidad de farmacia (días) ──────────────────────────────────
# Configurable por entorno; modifique aquí o mediante variables de entorno.
# ROJO  (CRÍTICO): lotes que caducan en menos de FARMACIA_DIAS_CADUCIDAD_CRITICO días
# AMARILLO (ALERTA): lotes que caducan entre CRITICO y ALERTA días
# VERDE (NORMAL): lotes que caducan en más de ALERTA días
FARMACIA_DIAS_CADUCIDAD_CRITICO = int(os.environ.get('FARMACIA_DIAS_CADUCIDAD_CRITICO', 30))
FARMACIA_DIAS_CADUCIDAD_ALERTA = int(os.environ.get('FARMACIA_DIAS_CADUCIDAD_ALERTA', 90))

# Receptor HL7/ASTM para analizadores de laboratorio.
# Mantener en False (Standby) hasta recibir manuales de protocolo de los fabricantes
# y completar la configuración de la interfaz con los analizadores físicos.
HL7_ACTIVE = os.environ.get('HL7_ACTIVE', 'False').lower() in ('true', '1', 'yes')

# Bastión 4 — Panel Django Admin: allowlist IP y/o grupo ADMIN_SISTEMA (desactivado por defecto)
ADMIN_IP_RESTRICTION_ENABLED = os.environ.get('ADMIN_IP_RESTRICTION_ENABLED', 'False').lower() in ('true', '1', 'yes')
ALLOWED_ADMIN_IPS = [x.strip() for x in os.environ.get('ALLOWED_ADMIN_IPS', '').split(',') if x.strip()]
ADMIN_GROUP_RESTRICTION_ENABLED = os.environ.get('ADMIN_GROUP_RESTRICTION_ENABLED', 'False').lower() in ('true', '1', 'yes')

# Tras cada backup_nocturno exitoso, registrar huella en BackupInmutableLog (WORM)
BACKUP_IMMUTABLE_LOG_AUTO = os.environ.get('BACKUP_IMMUTABLE_LOG_AUTO', 'False').lower() in ('true', '1', 'yes')

# PIN de validación de resultados — OBLIGATORIO configurar en producción
# FASE SECRETOS (VPS): FERNET_KEY, LAB_VALIDATION_PIN, PRISLAB_ESCUDO_USUARIO_ID
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

# Escudo clínico LIMS (HL7 / notificaciones automáticas sin sesión): PK de usuario activo
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

# Clave Fernet para cifrado de campos sensibles (NOM-035, Bienestar, Expedientes)
# En producción se inyecta desde variables de entorno seguras; en local puede omitirse
FERNET_KEY = os.environ.get("FERNET_KEY", None)
if IS_PRODUCTION and not FERNET_KEY:
    raise RuntimeError(
        '🔴 PRISLAB SEGURIDAD: FERNET_KEY no está configurada en producción.\n'
        'Defina FERNET_KEY (env). Genere una con:\n'
        '  python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"'
    )

# DRP Punto 14: kill switch de solo lectura (sin excepción admin/superuser en escrituras)
PRISLAB_READ_ONLY = os.environ.get('PRISLAB_READ_ONLY', '').strip().lower() in ('1', 'true', 'yes', 'on')

# Auditoría controlada: excepción deliberada para pruebas funcionales de farmacia/inventario.
# Se activa solo si el entorno lo define explícitamente y para usuarios/rutas permitidos.
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

# Fase 1 v8.5 — Shadow Mode ORM: log de consultas TenantModel sin filtro por empresa (sin bloquear).
# Desactivar con PRISLAB_TENANT_SHADOW_MODE=0 solo tras auditoría y blindaje estricto.
_raw_tenant_shadow = (os.environ.get('PRISLAB_TENANT_SHADOW_MODE') or '1').strip().lower()
PRISLAB_TENANT_SHADOW_MODE = _raw_tenant_shadow not in ('0', 'false', 'no', 'off')
PRISLAB_TENANT_STRICT_MODE = _env_bool('PRISLAB_TENANT_STRICT_MODE', IS_PRODUCTION)
# En management commands sin HTTP, registrar stacks solo si=1 (evita ruido en migrate/cron).
PRISLAB_TENANT_SHADOW_LOG_CLI = os.environ.get('PRISLAB_TENANT_SHADOW_LOG_CLI', '').strip().lower() in (
    '1', 'true', 'yes', 'on',
)

# Configuración para que Django entienda el HTTPS detrás de Nginx / reverse proxy
# Solo activo en producción para evitar forzar HTTPS en desarrollo local
if IS_PRODUCTION:
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# Configuración de cookies seguras (solo en PROD para no bloquear DEV en http)
SESSION_COOKIE_SECURE = _env_bool('SESSION_COOKIE_SECURE', IS_PRODUCTION)
CSRF_COOKIE_SECURE = _env_bool('CSRF_COOKIE_SECURE', IS_PRODUCTION)

# No redirigir SSL en local; en staging/prod se puede forzar por entorno.
SECURE_SSL_REDIRECT = _env_bool('SECURE_SSL_REDIRECT', False)

# Headers de seguridad adicionales (clínica: protección de datos sensibles)
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'
SECURE_REFERRER_POLICY = 'strict-origin-when-cross-origin'

# Permissions-Policy: deshabilitar geolocalización/cámara/micrófono por defecto
# El sistema solo activa audio cuando el usuario lo solicita explícitamente
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

# ==============================================================================
# SISTEMA DE AUDITORÍA Y LOGGING INTEGRAL
# VPS/Prod → stdout o logs locales; Bankguard → logs/bankguard_audit.log
# ==============================================================================
_LOG_DIR = BASE_DIR / 'logs'
_LOG_DIR.mkdir(parents=True, exist_ok=True)

PRISLAB_DISABLE_FILE_LOG_HANDLERS = _env_bool(
    'PRISLAB_DISABLE_FILE_LOG_HANDLERS',
    _TESTING,
)

_LOG_HANDLERS = ['console']
_EXTRA_HANDLERS = {}
# Bankguard v1.14: auditoría CLI, backfill y errores de concurrencia en caja (protocolo despliegue)
_BANKGUARD_HANDLERS = {}
if not PRISLAB_DISABLE_FILE_LOG_HANDLERS:
    _BANKGUARD_HANDLERS = {
        'file_bankguard': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': str(_LOG_DIR / 'bankguard_audit.log'),
            'maxBytes': 10 * 1024 * 1024,
            'backupCount': 10,
            'formatter': 'detailed',
            'encoding': 'utf-8',
        },
    }

if not IS_PRODUCTION and not PRISLAB_DISABLE_FILE_LOG_HANDLERS:
    _EXTRA_HANDLERS = {
        'file_errors': {
            'level': 'WARNING',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': str(_LOG_DIR / 'prislab_errors.log'),
            'maxBytes': 5 * 1024 * 1024,   # 5 MB por archivo
            'backupCount': 5,               # Guarda 5 archivos históricos (25 MB máx)
            'formatter': 'detailed',
            'encoding': 'utf-8',
        },
        'file_audit': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': str(_LOG_DIR / 'prislab_audit.log'),
            'maxBytes': 10 * 1024 * 1024,  # 10 MB por archivo
            'backupCount': 10,             # Guarda 10 archivos históricos (100 MB máx)
            'formatter': 'detailed',
            'encoding': 'utf-8',
        },
    }
    _LOG_HANDLERS = ['console', 'file_errors']

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'detailed': {
            'format': '[%(asctime)s] %(levelname)s [%(name)s:%(lineno)s] %(message)s',
            'datefmt': '%Y-%m-%d %H:%M:%S',
        },
        'simple': {
            'format': '%(levelname)s %(message)s',
        },
    },
    'filters': {
        'require_debug_false': {
            '()': 'django.utils.log.RequireDebugFalse',
        },
    },
    'handlers': {
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
        **_EXTRA_HANDLERS,
        **_BANKGUARD_HANDLERS,
    },
    'loggers': {
        'django': {
            'handlers': _LOG_HANDLERS,
            'level': 'INFO',
            'propagate': False,
        },
        'django.request': {
            'handlers': _LOG_HANDLERS,
            'level': 'ERROR',
            'propagate': False,
        },
        'django.db.backends': {
            'handlers': ['console'],
            'level': 'ERROR',
            'propagate': False,
        },
        'django.security.csrf': {
            'handlers': _LOG_HANDLERS,
            'level': 'WARNING',
            'propagate': False,
        },
        'core': {
            'handlers': _LOG_HANDLERS,
            'level': 'DEBUG',
            'propagate': False,
        },
        'core.tenant': {
            'handlers': _LOG_HANDLERS,
            'level': 'DEBUG' if DEBUG else 'INFO',
            'propagate': False,
        },
        'prislab.frontend': {
            'handlers': _LOG_HANDLERS,
            'level': 'ERROR',
            'propagate': False,
        },
        'sentinel': {
            'handlers': _LOG_HANDLERS,
            'level': 'INFO',
            'propagate': False,
        },
        'sentinel.github': {
            'handlers': ['console'],
            'level': 'DEBUG',
            'propagate': False,
        },
        'sentinel.performance': {
            'handlers': _LOG_HANDLERS,
            'level': 'WARNING',
            'propagate': False,
        },
        'audit': {
            'handlers': ['console', *(['file_audit'] if 'file_audit' in _EXTRA_HANDLERS else [])],
            'level': 'INFO',
            'propagate': False,
        },
        'bankguard': {
            'handlers': ['console', *(['file_bankguard'] if 'file_bankguard' in _BANKGUARD_HANDLERS else [])],
            'level': 'INFO',
            'propagate': False,
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'WARNING',
    },
}

# ============================================================================
# Punto 23 — Sandbox de capacitación (perfil lógico de despliegue)
# ============================================================================
PRISLAB_DEPLOYMENT_MODE = (os.environ.get('PRISLAB_DEPLOYMENT_MODE') or '').strip().lower()
IS_SANDBOX = PRISLAB_DEPLOYMENT_MODE == 'training_sandbox'

# ============================================================================
# CONFIGURACIÓN DE FACTURACIÓN ELECTRÓNICA (CFDI 4.0)
# ============================================================================
FACTURAMA_USER = os.environ.get('FACTURAMA_USER', '')
FACTURAMA_PASSWORD = os.environ.get('FACTURAMA_PASSWORD', '')
FACTURAMA_SANDBOX = os.environ.get('FACTURAMA_SANDBOX', 'True') == 'True'
if IS_SANDBOX:
    FACTURAMA_SANDBOX = True
# Hito 16 — en desarrollo local nunca consumir timbres productivos por error de .env
if DEBUG:
    FACTURAMA_SANDBOX = True

# ============================================================================
# PRIS SENTINEL V4: WEB PUSH NOTIFICATIONS (VAPID)
# ============================================================================
VAPID_PRIVATE_KEY = os.environ.get('VAPID_PRIVATE_KEY', '')
VAPID_PUBLIC_KEY = os.environ.get('VAPID_PUBLIC_KEY', '')
VAPID_CLAIMS = {
    'sub': 'mailto:admin@prislab.com'
}

# ============================================================================
# CHANNELS (WebSockets) - Solo si hay Redis disponible
# ============================================================================
ASGI_APPLICATION = 'config.asgi.application'

# Usar la REDIS_URL ya definida arriba (None si no hay Redis)
if REDIS_URL:
    CHANNEL_LAYERS = {
        'default': {
            'BACKEND': 'channels_redis.core.RedisChannelLayer',
            'CONFIG': {
                "hosts": [REDIS_URL],
                "capacity": 1500,
                "expiry": 10,
            },
        },
    }
else:
    # Sin Redis: backend en memoria (desarrollo o VPS sin Redis)
    CHANNEL_LAYERS = {
        'default': {
            'BACKEND': 'channels.layers.InMemoryChannelLayer'
        }
    }

# ==============================================================================
# CELERY — Worker asíncrono para tareas en segundo plano
# ==============================================================================
# Broker: mismo Redis de Cache/Channels. Si no hay Redis → modo "eager" (síncrono).
# Queues:
#   drive_sync  — Sincronización de archivos a Google Drive (FASE 3)
#   default     — Tareas generales
#   backup      — Backup nocturno de DB
# ==============================================================================
_celery_broker = REDIS_URL or 'memory://'
CELERY_BROKER_URL = _celery_broker
CELERY_RESULT_BACKEND = REDIS_URL if REDIS_URL else 'cache+memory://'

CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TIMEZONE = TIME_ZONE
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 600          # 10 min máximo por tarea
CELERY_TASK_SOFT_TIME_LIMIT = 540     # Aviso a los 9 min
CELERY_WORKER_PREFETCH_MULTIPLIER = 1  # Un task a la vez por worker (seguro para Drive)
CELERY_WORKER_MAX_TASKS_PER_CHILD = 50 # Reiniciar worker tras 50 tareas (evitar mem leaks)

# Sin Redis: ejecutar tasks síncronamente en el mismo proceso (dev / fallback)
CELERY_TASK_ALWAYS_EAGER = not bool(REDIS_URL)
CELERY_TASK_EAGER_PROPAGATES = True

# Reintentos Drive
DRIVE_SYNC_MAX_RETRIES = 5
DRIVE_SYNC_RETRY_COUNTDOWN = 60  # segundos entre reintentos

# Celery Beat — tareas periódicas
from celery.schedules import crontab  # noqa: E402

CELERY_BEAT_SCHEDULE = {
    'verificaciones-automaticas-diarias': {
        'task': 'core.tasks.notificaciones_tasks.ejecutar_verificaciones_automaticas_todas_empresas',
        'schedule': crontab(hour=7, minute=0),
    },
}

# Buffer local para archivos en tránsito (antes de sincronizar con Drive)
MEDIA_BUFFER_DIR = os.path.join(MEDIA_ROOT, 'buffer')

# ==============================================================================
# FASE 3 — STORAGE HÍBRIDO ASÍNCRONO
# ==============================================================================
# BufferLocalStorage: guarda en /media/buffer/ instantáneamente y encola
# Celery task para subir a Drive en background.
#
# Flujo:
#   Usuario sube archivo → _save() guarda local → Celery task encolada → ✓ Éxito
#   Celery worker: lee local → sube a Drive → elimina buffer → cache.set(sync=True)
#   Si Drive falla: archivo queda en buffer, task reintenta hasta 5 veces.
# ==============================================================================
STORAGES["staticfiles"] = {"BACKEND": _static_backend}

# ==============================================================================
# 🔐 CONFIGURACIONES DE SEGURIDAD PARA PRODUCCIÓN
# ==============================================================================
# Correcciones post-auditoría - Bloque 1.2
# Disable SSL for E2E testing with: E2E_DISABLE_SSL=1
_e2e_disable_ssl = os.environ.get('E2E_DISABLE_SSL', '') == '1'
if not DEBUG and not _e2e_disable_ssl and not _TESTING:
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = 31536000  # 1 año
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True

# ==============================================================================
# 🔐 ALLOWED_HOSTS CONFIGURACIÓN SEGURA
# ==============================================================================
# Correcciones post-auditoría - Bloque 1.3
_allowed_hosts_env = os.environ.get('ALLOWED_HOSTS', '')
if _allowed_hosts_env:
    ALLOWED_HOSTS = [host.strip() for host in _allowed_hosts_env.split(',') if host.strip()]
elif IS_PRODUCTION:
    _server_name = (os.environ.get('SERVER_NAME') or os.environ.get('DOMAIN_NAME') or '').strip()
    ALLOWED_HOSTS = [x for x in [_server_name, 'localhost', '127.0.0.1'] if x]
else:
    ALLOWED_HOSTS = ['localhost', '127.0.0.1', 'testserver']

# ==============================================================================
# 🚨 HEALTH-CHECKS DE ARRANQUE — Configuración de seguridad crítica
# ==============================================================================
import logging as _log_startup
_log_sec = _log_startup.getLogger('core.seguridad.startup')

# HC-1: PRISLAB_EMERGENCY_TENANT_BYPASS no debe estar activo en producción.
# Si está encendido al arrancar, emitir crítico para que aparezca en Sentry/logs.
if os.environ.get('PRISLAB_EMERGENCY_TENANT_BYPASS', '').strip().lower() in ('1', 'true', 'yes', 'on'):
    _log_sec.critical(
        '🚨 PRISLAB_EMERGENCY_TENANT_BYPASS=1 está activo en este proceso. '
        'El filtro multi-tenant ORM está DESACTIVADO. '
        'Desactivar esta variable en cuanto sea seguro.'
    )

# HC-2: PRISLAB_DEFAULT_EMPRESA_ID debe estar configurado en entornos con más de una empresa.
# Sin este valor, usuarios sin FK empresa asignada quedarán sin tenant (strict mode los bloqueará).
if IS_PRODUCTION and not os.environ.get('PRISLAB_DEFAULT_EMPRESA_ID', '').strip():
    _log_sec.warning(
        'PRISLAB_DEFAULT_EMPRESA_ID no está configurado. '
        'En entornos con múltiples empresas, usuarios sin empresa asignada serán bloqueados '
        'si PRISLAB_TENANT_STRICT_MODE está activo.'
    )
