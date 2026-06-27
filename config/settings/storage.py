"""
config/settings/storage.py

Almacenamiento: Static (WhiteNoise), Media (local/Vultr S3).
Consume: BASE_DIR, IS_PRODUCTION, DEBUG, _env_bool (de base.py)
Expone: STORAGES, MEDIA_ROOT, STATIC_ROOT, _static_backend
"""
import logging
import os

from .base import BASE_DIR, IS_PRODUCTION, DEBUG, _env_bool

# ── STATIC ────────────────────────────────────────────────────────────────────

STATIC_URL = '/static/'
STATICFILES_DIRS = [os.path.join(BASE_DIR, 'static')]
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')

# USE_MANIFEST_STORAGE se usa durante Docker build para que collectstatic
# genere el manifest (staticfiles.json) que la producción necesita.
_static_backend = (
    'whitenoise.storage.CompressedManifestStaticFilesStorage'
    if (IS_PRODUCTION or os.environ.get('USE_MANIFEST_STORAGE'))
    else 'django.contrib.staticfiles.storage.StaticFilesStorage'
)

WHITENOISE_MAX_AGE = 31536000  # 1 año de cache para archivos estáticos
WHITENOISE_COMPRESS_OFFLINE = True  # Pre-comprimir archivos
WHITENOISE_USE_FINDERS = True  # Buscar archivos automáticamente

# ── MEDIA ─────────────────────────────────────────────────────────────────────

MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

FILE_UPLOAD_MAX_MEMORY_SIZE = 20 * 1024 * 1024
DATA_UPLOAD_MAX_MEMORY_SIZE = 20 * 1024 * 1024

# ── VULTR S3 ──────────────────────────────────────────────────────────────────

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

# ── STORAGES base ─────────────────────────────────────────────────────────────

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

# ── STORAGES["staticfiles"] — se fija aquí (corrección de ubicación del monolito) ──

STORAGES["staticfiles"] = {"BACKEND": _static_backend}
