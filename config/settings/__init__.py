"""
config/settings/__init__.py

Ensamblador maestro del paquete config.settings.
DJANGO_SETTINGS_MODULE=config.settings resuelve a este archivo.

Orden de importación (respeta dependencias):
  1. base      — FLAGS, helpers, INSTALLED_APPS, MIDDLEWARE, TEMPLATES, AUTH, I18N,
                 PWA, EMAIL, umbrales, entorno, SECRET_KEY, CORS, ALLOWED_HOSTS (dev)
  2. database  — DATABASES
  3. security  — cookies, SSL, HSTS, ALLOWED_HOSTS final, tokens de servicio
  4. storage   — STATIC, MEDIA, Vultr, Google Drive, STORAGES
  5. ia        — GEMINI, DeepSeek, FACTURAMA, VAPID, GitHub token
  6. cache     — CACHES, SESSIONS, CSRF, CHANNELS
  7. celery_conf — CELERY_*, CELERY_BEAT_SCHEDULE
  8. logging_conf — LOGGING
  9. local / production — overrides condicionales
"""
import os as _os

# ── 1. Base ───────────────────────────────────────────────────────────────────
from .base import *  # noqa: F401, F403

# ── 2. Base de datos ──────────────────────────────────────────────────────────
from .database import *  # noqa: F401, F403

# ── 3. Seguridad ──────────────────────────────────────────────────────────────
from .security import *  # noqa: F401, F403

# ── 4. Almacenamiento ─────────────────────────────────────────────────────────
from .storage import *  # noqa: F401, F403

# ── 5. IA + claves externas ───────────────────────────────────────────────────
from .ia import *  # noqa: F401, F403

# ── 6. Caché + Sesiones + Channels ───────────────────────────────────────────
from .cache import *  # noqa: F401, F403

# Post-caché: CSRF_TRUSTED_ORIGINS necesita IS_PRODUCTION y PRISLAB_CANONICAL_HOST
# que vienen de base.py, y _build_csrf_origins está en cache.py.
from .cache import _build_csrf_origins  # noqa: F401
CSRF_TRUSTED_ORIGINS = _build_csrf_origins(IS_PRODUCTION, PRISLAB_CANONICAL_HOST)  # noqa: F405

# ── 7. Celery ─────────────────────────────────────────────────────────────────
from .celery_conf import *  # noqa: F401, F403

# ── 8. Logging ────────────────────────────────────────────────────────────────
from .logging_conf import *  # noqa: F401, F403

# ── 9. Overrides condicionales ───────────────────────────────────────────────
# Facturama: sandbox obligatorio en DEBUG y en IS_SANDBOX
if DEBUG or IS_SANDBOX:  # noqa: F405
    FACTURAMA_SANDBOX = True  # noqa: F405

# MEDIA_BUFFER_DIR depende de MEDIA_ROOT (storage.py)
MEDIA_BUFFER_DIR = _os.path.join(MEDIA_ROOT, 'buffer')  # noqa: F405

# staticfiles backend final (requiere _static_backend de storage.py)
from .storage import _static_backend  # noqa: F401, E402
STORAGES["staticfiles"] = {"BACKEND": _static_backend}  # noqa: F405

if IS_PRODUCTION:  # noqa: F405
    from .production import *  # noqa: F401, F403
elif not IS_PRODUCTION:  # noqa: F405
    from .local import *  # noqa: F401, F403
