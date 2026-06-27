"""
config/settings/local.py

Overrides para entorno de desarrollo local.
Solo se activa cuando DEPLOYMENT_ENV != 'production'.
No debe importarse en producción.
"""
import os

# Email → consola en local (ya cubierto por base.py cuando no hay SMTP vars,
# pero se reafirma aquí como override explícito).
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# Relajar HSTS en desarrollo
SECURE_HSTS_SECONDS = 0
SECURE_HSTS_INCLUDE_SUBDOMAINS = False
SECURE_HSTS_PRELOAD = False
SECURE_SSL_REDIRECT = False

# Cookies no seguras en HTTP local
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False

# django-debug-toolbar (opcional — solo si está instalado)
try:
    import debug_toolbar  # noqa: F401
    # Insertar justo después de WhiteNoise
    _DTB_MIDDLEWARE = 'debug_toolbar.middleware.DebugToolbarMiddleware'
    INTERNAL_IPS = ['127.0.0.1']
except ImportError:
    pass

# Mostrar SQL en consola (desactivar en producción)
# Para activar: export DJANGO_LOG_SQL=1
if os.environ.get('DJANGO_LOG_SQL') == '1':
    LOGGING = {
        'version': 1,
        'disable_existing_loggers': False,
        'handlers': {'console': {'class': 'logging.StreamHandler'}},
        'loggers': {
            'django.db.backends': {
                'handlers': ['console'],
                'level': 'DEBUG',
                'propagate': False,
            },
        },
    }
