"""
config/settings/cache.py

CACHES, SESSIONS, CSRF cookies, CHANNELS (WebSockets).
Depende de: base.py (IS_PRODUCTION, PRISLAB_CANONICAL_HOST)
"""
import logging
import os

# ── Redis URL (compartida por cache, Channels y Celery) ───────────────────────
REDIS_URL = os.environ.get('REDIS_URL')

# ── CACHÉ — Redis (Producción) / LocMem (Desarrollo) ─────────────────────────
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
            'TIMEOUT': 300,
        }
    }
    _cache_logger.info('[CACHE] Backend Redis activo (ubicación omitida en logs por seguridad)')
    SESSION_ENGINE = 'django.contrib.sessions.backends.cache'
    SESSION_CACHE_ALIAS = 'default'
else:
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
            'LOCATION': 'prislab-locmem',
        }
    }
    _cache_logger.info('[CACHE] LocMem (desarrollo)')
    SESSION_ENGINE = 'django.contrib.sessions.backends.db'

# ── SESIONES ──────────────────────────────────────────────────────────────────
SESSION_COOKIE_AGE = int(os.environ.get('SESSION_COOKIE_AGE_SECONDS', str(60 * 60 * 24 * 30)))
SESSION_SHORT_COOKIE_AGE = int(os.environ.get('SESSION_SHORT_COOKIE_AGE_SECONDS', str(60 * 60 * 10)))
SESSION_SAVE_EVERY_REQUEST = True
SESSION_EXPIRE_AT_BROWSER_CLOSE = False
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'
CSRF_COOKIE_HTTPONLY = True

# ── CSRF Trusted Origins ──────────────────────────────────────────────────────
CSRF_TRUSTED_ORIGINS = []
_extra_csrf = [
    x.strip()
    for x in (
        os.environ.get('CSRF_TRUSTED_ORIGINS')
        or os.environ.get('CSRF_TRUSTED_ORIGINS_EXTRA', '')
    ).split(',')
    if x.strip()
]

# IS_PRODUCTION y PRISLAB_CANONICAL_HOST llegan del __init__.py que importa base.py primero
def _build_csrf_origins(is_production, canonical_host):
    extra = list(_extra_csrf)
    if is_production and canonical_host:
        _canonical_origin = f'https://{canonical_host}'
        if _canonical_origin not in extra:
            extra.append(_canonical_origin)
    result = []
    for _o in extra:
        if _o not in result:
            result.append(_o)
    return result


# Cookies de sesión/CSRF
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

# ── CHANNELS (WebSockets) ────────────────────────────────────────────────────
ASGI_APPLICATION = 'config.asgi.application'

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
    CHANNEL_LAYERS = {
        'default': {
            'BACKEND': 'channels.layers.InMemoryChannelLayer'
        }
    }
