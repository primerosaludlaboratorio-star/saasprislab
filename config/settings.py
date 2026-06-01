import logging
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

# Variables de entorno (estándar)
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "").strip()
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY", "").strip().replace('\r', '').replace('\n', '')

# PRIS Sentinel -> GitHub Auto-Reporte
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")
GITHUB_REPO = os.environ.get("GITHUB_REPO", "")  # formato: owner/repo

# Configuración de entorno (producción vs desarrollo)
# En local (sin GOOGLE_CLOUD_PROJECT) DEBUG=True por defecto
# En producción (Cloud Run) DEBUG=False por defecto
_is_cloud_env = bool(os.environ.get('GOOGLE_CLOUD_PROJECT') or os.environ.get('GAE_ENV', '').startswith('standard'))
DEBUG = os.environ.get('DEBUG', str(not _is_cloud_env)) == 'True'
SECRET_KEY = os.environ.get('SECRET_KEY', 'django-insecure-prislab-saas-key-2025')

# Tenant por defecto (PRISLAB mononodo / rescate). Opcional: entero explícito.
_raw_def_emp = (os.environ.get('PRISLAB_DEFAULT_EMPRESA_ID') or '').strip()
PRISLAB_DEFAULT_EMPRESA_ID = int(_raw_def_emp) if _raw_def_emp.isdigit() else None

# URL pública del backend SaaS (p. ej. llamadas desde otro servicio Cloud Run / integraciones)
API_URL = (os.environ.get('API_URL') or os.environ.get('PRISLAB_SAAS_URL') or '').strip()

# CORS: en cloud el valor por defecto es restrictivo; en local permisivo para desarrollo.
# Explícito: CORS_ALLOW_ALL_ORIGINS=true|false | Lista: CORS_ALLOWED_ORIGINS=https://a.com,https://b.com
_cors_allow_raw = (os.environ.get('CORS_ALLOW_ALL_ORIGINS') or '').strip().lower()
if _cors_allow_raw:
    CORS_ALLOW_ALL_ORIGINS = _cors_allow_raw in ('true', '1', 'yes', 'on')
else:
    CORS_ALLOW_ALL_ORIGINS = not _is_cloud_env

CORS_ALLOWED_ORIGINS = [
    x.strip() for x in (os.environ.get('CORS_ALLOWED_ORIGINS') or '').split(',') if x.strip()
]
if _is_cloud_env and not CORS_ALLOW_ALL_ORIGINS and not CORS_ALLOWED_ORIGINS:
    logging.getLogger('config').warning(
        'CORS: en producción CORS_ALLOW_ALL_ORIGINS está en False y CORS_ALLOWED_ORIGINS está vacío. '
        'Las peticiones desde otros orígenes (p. ej. otro servicio Cloud Run) pueden fallar. '
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
    'x-requested-with',
]

# ── Validación de seguridad en producción ────────────────────────────────────
_SECRET_INSEGURA = 'django-insecure-prislab-saas-key-2025'
if _is_cloud_env:
    if not os.environ.get('SECRET_KEY') or SECRET_KEY == _SECRET_INSEGURA:
        raise RuntimeError(
            '🔴 PRISLAB SEGURIDAD: SECRET_KEY no está configurada en producción.\n'
            'Defina la variable de entorno SECRET_KEY con una clave segura de al menos 50 caracteres.\n'
            'Genere una con: python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"'
        )
    if not os.environ.get('GOOGLE_API_KEY'):
        import logging as _log
        _log.getLogger('core').warning(
            'GOOGLE_API_KEY no está configurada. Las funciones de IA (dictado, OCR, análisis) no estarán disponibles.'
        )

# BLINDAJE R104: Hosts restringidos por entorno
if _is_cloud_env:
    ALLOWED_HOSTS = [
        'prislab-v5-oswjakz55a-uc.a.run.app',
        'prislab-v5-811785477499.us-central1.run.app',
        '.run.app',
        'localhost',
    ]
else:
    ALLOWED_HOSTS = ['*']  # Solo en desarrollo local

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
    'recepcion',    # Recepción y agendamiento de citas
    'enfermeria',   # Triage y signos vitales (opcional)
    'consultorio',  # Consultorio / Agenda / Expediente clínico
    'logistica',    # Logística / Rutas / Visitas a domicilio
    'inventario',   # Silos de Inventario Federados V8.0 (Lab, Consultorio, Generales + Motor Compras)
    'mantenimiento', # CMMS V8.2 — Protocolos, Checklists, Diagnóstico, Tickets, TCO, QR
    'bienestar',    # Módulo 'Espacio Seguro' - Diario Emocional y Recursos
    'contabilidad', # Facturación CFDI 4.0 y Contabilidad

    # Storage Cloud + PWA
    'storages',
    'pwa',
    
    # Real-Time Communication (Voice Commander)
    'channels',
]

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
# Detectar si estamos en Google Cloud PRIMERO
IS_CLOUD = os.getenv('GAE_ENV', '').startswith('standard') or os.getenv('GOOGLE_CLOUD_PROJECT')

if IS_CLOUD:
    # PRODUCCIÓN: Usar Cloud SQL (PostgreSQL) via socket Unix
    # CONN_MAX_AGE: conexiones persistentes para reducir overhead bajo carga (stress test)
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': os.environ.get('DB_NAME', 'prislab_v5'),
            'USER': os.environ.get('DB_USER', 'prislab_user'),
            'PASSWORD': os.environ.get('DB_PASSWORD', ''),
            'HOST': os.environ.get('DB_HOST', '/cloudsql/' + os.environ.get('CLOUD_SQL_CONNECTION_NAME', 'prislab-v5-ai:us-central1:prislab-db')),
            'PORT': '',
            'CONN_MAX_AGE': 60,  # Conexiones persistentes: reduce overhead bajo 1000+ req concurrentes
        }
    }
    # Sin print en producción (evitar ruido I/O bajo carga)
elif os.environ.get('DB_HOST'):
    # DESARROLLO con PostgreSQL remoto
    db_host = os.environ.get('DB_HOST', '')
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': os.environ.get('DB_NAME', 'prislab_db'),
            'USER': os.environ.get('DB_USER', 'postgres'),
            'PASSWORD': os.environ.get('DB_PASSWORD', ''),
            'HOST': db_host,
            'PORT': os.environ.get('DB_PORT', '5432'),
            'CONN_MAX_AGE': 60,
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
# ESTRATEGIA HÍBRIDA DE ALMACENAMIENTO (WHITENOISE + GOOGLE DRIVE)
# ==============================================================================
# STATIC (CSS, JS, imágenes del sistema) → WhiteNoise (en memoria de Cloud Run)
# MEDIA (PDFs, recetas, audio) → Google Drive (10TB)
# ==============================================================================

# Usar la variable IS_CLOUD definida anteriormente para configuración de almacenamiento
IS_GOOGLE_CLOUD = IS_CLOUD

# ------------------------------------------------------------------------------
# ARCHIVOS ESTÁTICOS (STATIC) - WHITENOISE
# ------------------------------------------------------------------------------
# Estos archivos se sirven RÁPIDO desde la memoria de Cloud Run
# Incluye: logos, iconos, CSS, JavaScript, fuentes, imágenes del tema
STATIC_URL = '/static/'
STATICFILES_DIRS = [os.path.join(BASE_DIR, 'static')]
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')

# WhiteNoise: Compresión y cache automático
# Ventajas: Ultra rápido, sin latencia, sin costos adicionales
# USE_MANIFEST_STORAGE se usa durante Docker build para que collectstatic
# genere el manifest (staticfiles.json) que la producción necesita.
if IS_GOOGLE_CLOUD or os.environ.get('USE_MANIFEST_STORAGE'):
    STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'
else:
    # En desarrollo local, usar storage simple para evitar errores de manifest
    STATICFILES_STORAGE = 'django.contrib.staticfiles.storage.StaticFilesStorage'

# Configuración de WhiteNoise
WHITENOISE_MAX_AGE = 31536000  # 1 año de cache para archivos estáticos
WHITENOISE_COMPRESS_OFFLINE = True  # Pre-comprimir archivos
WHITENOISE_USE_FINDERS = True  # Buscar archivos automáticamente

# ------------------------------------------------------------------------------
# ARCHIVOS MEDIA (DINÁMICOS) - GOOGLE CLOUD STORAGE
# ------------------------------------------------------------------------------
# Audios de PRIS-Chat, fotos de pacientes, PDFs, recetas OCR, etc.
# En producción se suben al Bucket GCS. En local se usa carpeta media/.

MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

# CICLO 10: File upload security — limit size (20MB)
FILE_UPLOAD_MAX_MEMORY_SIZE = 20 * 1024 * 1024
DATA_UPLOAD_MAX_MEMORY_SIZE = 20 * 1024 * 1024

# ==============================================================================
# ALMACENAMIENTO MEDIA: Google Drive (2 TB) - OBLIGATORIO EN PRODUCCIÓN
# ==============================================================================
# El cliente configuró la carpeta maestra PRISLAB_Media y otorgó permisos de
# Editor a prislab-drive@prislab-v5-ai.iam.gserviceaccount.com
# ==============================================================================
GS_BUCKET_NAME = os.environ.get('GS_BUCKET_NAME', '')  # Legacy: solo fallback si Drive no está

# Carpeta maestra en Google Drive (ID de la carpeta PRISLAB_Media)
# Sin valor por defecto en código: evita filtrar IDs de carpeta y fuerza configuración explícita (.env / Secret Manager).
GOOGLE_DRIVE_FOLDER_ID = (
    os.environ.get('GOOGLE_DRIVE_FOLDER_ID') or
    os.environ.get('DRIVE_FOLDER_ID') or
    ''
).strip()

# Credenciales: resolver desde env vars (JSON, Base64 o archivo)
GOOGLE_DRIVE_CREDENTIALS = None
_DRIVE_STORAGE_ACTIVO = False  # pylint: disable=invalid-name

try:
    from config.drive_credentials import get_drive_credentials
    _drive_creds = get_drive_credentials()
    if _drive_creds and GOOGLE_DRIVE_FOLDER_ID:
        GOOGLE_DRIVE_CREDENTIALS = _drive_creds
        DEFAULT_FILE_STORAGE = 'config.storage_backends.GoogleDriveStorage'
        _DRIVE_STORAGE_ACTIVO = True
        if IS_GOOGLE_CLOUD:
            import logging as _log_drive
            _log_drive.getLogger('config').info(
                f"[PRODUCCION] Google Drive configurado -> Carpeta ID: {GOOGLE_DRIVE_FOLDER_ID[:20]}..."
            )
        elif GOOGLE_DRIVE_FOLDER_ID:
            import logging as _log_drive
            _log_drive.getLogger('config').info("[DEV] Google Drive configurado (carpeta maestra)")
    elif IS_GOOGLE_CLOUD and GOOGLE_DRIVE_FOLDER_ID and not _drive_creds:
        import logging as _log_drive
        _log_drive.getLogger('config').warning(
            "[PRODUCCION] GOOGLE_DRIVE_FOLDER_ID configurado pero credenciales no disponibles. "
            "Configure OAuth2 (GOOGLE_DRIVE_CLIENT_ID, CLIENT_SECRET, REFRESH_TOKEN) o Service Account."
        )
except Exception as e:
    import logging as _log_drive
    _log_drive.getLogger('config').warning(f"Error configurando Google Drive: {e}")

# Fallback: GCS solo si Drive NO está activo (compatibilidad legacy)
if not _DRIVE_STORAGE_ACTIVO and IS_GOOGLE_CLOUD and GS_BUCKET_NAME:
    try:
        DEFAULT_FILE_STORAGE = 'storages.backends.gcloud.GoogleCloudStorage'
        GS_DEFAULT_ACL = 'publicRead'
        GS_QUERYSTRING_AUTH = False
        GS_FILE_OVERWRITE = False
        GS_LOCATION = 'media'
        import logging as _log_gcs
        _log_gcs.getLogger('config').info(f"[PRODUCCION] Fallback GCS: gs://{GS_BUCKET_NAME}/media/")
    except Exception as e:
        import logging as _log_gcs
        _log_gcs.getLogger('config').warning(f"Error GCS: {e}. Usando almacenamiento local (efímero)")
elif not _DRIVE_STORAGE_ACTIVO and IS_GOOGLE_CLOUD:
    import logging as _log_warn
    _log_warn.getLogger('config').warning(
        "Almacenamiento MEDIA: Configure GOOGLE_DRIVE_FOLDER_ID + credenciales para usar Drive."
    )

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
# Configurar en Cloud Run como secret: PRISLAB_MASTER_RECOVERY_CODE
PRISLAB_MASTER_RECOVERY_CODE = os.environ.get('PRISLAB_MASTER_RECOVERY_CODE', '')

# Telegram Bot para alertas en tiempo real
TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN', '')
TELEGRAM_CISO_CHAT_ID = os.environ.get('TELEGRAM_CISO_CHAT_ID', '')

# IPs internas que no requieren 2FA (lista separada por comas, e.g. '192.168.1.')
_ips_bypass_raw = os.environ.get('IPS_INTERNAS_2FA_BYPASS', '')
IPS_INTERNAS_2FA_BYPASS = [ip.strip() for ip in _ips_bypass_raw.split(',') if ip.strip()]

# Umbral de alerta NOM-024: >N accesos a expedientes en 1 hora notifica al CISO
NOM024_ALERTA_ACCESOS_UMBRAL = int(os.environ.get('NOM024_ALERTA_ACCESOS_UMBRAL', '10'))

# ==============================================================================
# FASE 5 — MODO MANTENIMIENTO (activa antes de Migración Maestra)
# ==============================================================================
# Activar vía env var en Cloud Run:  SYSTEM_MAINTENANCE_MODE=true
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

# Configuración CSRF para Google Cloud Run
CSRF_TRUSTED_ORIGINS = [
    # Cloud Run — dominios de producción PRISLAB (actualizados)
    'https://prislab-saas-811785477499.us-central1.run.app',
    'https://prislab-farmacia-811785477499.us-central1.run.app',
    'https://prislab-v5-oswjakz55a-uc.a.run.app',
    'https://prislab-v5-811785477499.us-central1.run.app',
    # Wildcard para futuras revisiones de Cloud Run
    'https://*.run.app',
    'https://*.a.run.app',
]
_extra_csrf = [x.strip() for x in os.environ.get('CSRF_TRUSTED_ORIGINS_EXTRA', '').split(',') if x.strip()]
for _o in _extra_csrf:
    if _o not in CSRF_TRUSTED_ORIGINS:
        CSRF_TRUSTED_ORIGINS.append(_o)

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
# FASE SECRETS (Cloud Run / GAE / VPS): FERNET_KEY, LAB_VALIDATION_PIN, PRISLAB_ESCUDO_USUARIO_ID
LAB_VALIDATION_PIN = os.environ.get("LAB_VALIDATION_PIN", "1234")
if _is_cloud_env and LAB_VALIDATION_PIN == "1234":
    raise RuntimeError(
        '🔴 PRISLAB SEGURIDAD: LAB_VALIDATION_PIN usa el valor por defecto "1234" en producción.\n'
        'Configure LAB_VALIDATION_PIN vía Secret Manager (p. ej. lab-validation-pin) con un PIN seguro.'
    )
_pin_stripped = (LAB_VALIDATION_PIN or "").strip()
if _is_cloud_env and _pin_stripped and len(_pin_stripped) < 8:
    raise RuntimeError(
        '🔴 PRISLAB SEGURIDAD: en producción LAB_VALIDATION_PIN debe tener al menos 8 caracteres '
        '(auditoría ISO / gobierno de acceso). Actualice el secreto lab-validation-pin en GCP.'
    )

# Escudo clínico LIMS (HL7 / notificaciones automáticas sin sesión): PK de usuario activo
_raw_escudo = (os.environ.get('PRISLAB_ESCUDO_USUARIO_ID') or '').strip()
PRISLAB_ESCUDO_USUARIO_ID = None
if _raw_escudo:
    try:
        PRISLAB_ESCUDO_USUARIO_ID = int(_raw_escudo)
    except ValueError:
        PRISLAB_ESCUDO_USUARIO_ID = None
if _is_cloud_env and not PRISLAB_ESCUDO_USUARIO_ID:
    raise RuntimeError(
        '🔴 PRISLAB SEGURIDAD: PRISLAB_ESCUDO_USUARIO_ID es obligatoria en producción.\n'
        'Defina el ID numérico del usuario de sistema que firmará acciones del Escudo Clínico (HL7 / LIMS).'
    )

# Clave Fernet para cifrado de campos sensibles (NOM-035, Bienestar, Expedientes)
# En Cloud Run se inyecta desde Secret Manager; en local puede omitirse según uso de features cifradas
FERNET_KEY = os.environ.get("FERNET_KEY", None)
if _is_cloud_env and not FERNET_KEY:
    raise RuntimeError(
        '🔴 PRISLAB SEGURIDAD: FERNET_KEY no está configurada en producción.\n'
        'Defina FERNET_KEY (env / Secret Manager). Genere una con:\n'
        '  python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"'
    )

# DRP Punto 14: kill switch de solo lectura (sin excepción admin/superuser en escrituras)
PRISLAB_READ_ONLY = os.environ.get('PRISLAB_READ_ONLY', '').strip().lower() in ('1', 'true', 'yes', 'on')

# Fase 1 v8.5 — Shadow Mode ORM: log de consultas TenantModel sin filtro por empresa (sin bloquear).
# Desactivar con PRISLAB_TENANT_SHADOW_MODE=0 solo tras auditoría y blindaje estricto.
_raw_tenant_shadow = (os.environ.get('PRISLAB_TENANT_SHADOW_MODE') or '1').strip().lower()
PRISLAB_TENANT_SHADOW_MODE = _raw_tenant_shadow not in ('0', 'false', 'no', 'off')
# En management commands sin HTTP, registrar stacks solo si=1 (evita ruido en migrate/cron).
PRISLAB_TENANT_SHADOW_LOG_CLI = os.environ.get('PRISLAB_TENANT_SHADOW_LOG_CLI', '').strip().lower() in (
    '1', 'true', 'yes', 'on',
)

# Bucket GCS dedicado a volcados pg_dump cifrados (manage.py backup_database); opcional hasta usar el comando
GCS_BACKUP_BUCKET = os.environ.get('GCS_BACKUP_BUCKET', '').strip()

# Configuración para que Django entienda que Google maneja el HTTPS
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# Configuración de cookies seguras (solo en PROD para no bloquear DEV en http)
SESSION_COOKIE_SECURE = IS_GOOGLE_CLOUD
CSRF_COOKIE_SECURE = IS_GOOGLE_CLOUD

# No redirigir SSL (Cloud Run ya maneja HTTPS)
SECURE_SSL_REDIRECT = False

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

if IS_GOOGLE_CLOUD:
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True

# ==============================================================================
# SISTEMA DE AUDITORÍA Y LOGGING INTEGRAL
# Cloud Run → stdout capturado por Cloud Logging
# Local → prislab_*.log rotados; Bankguard → logs/bankguard_audit.log (también VPS/Cloud con FS escribible)
# ==============================================================================
_LOG_DIR = BASE_DIR / 'logs'
_LOG_DIR.mkdir(parents=True, exist_ok=True)

_LOG_HANDLERS = ['console']
_EXTRA_HANDLERS = {}
# Bankguard v1.14: auditoría CLI, backfill y errores de concurrencia en caja (protocolo despliegue)
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

if not _is_cloud_env:
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
            'handlers': ['console', 'file_bankguard'],
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
# Punto 23 — Sandbox de capacitación (servicio Cloud Run dedicado)
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
    # Sin Redis: backend en memoria (desarrollo / Cloud Run sin Redis)
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
DEFAULT_FILE_STORAGE = 'config.storage_backends.BufferLocalStorage'
