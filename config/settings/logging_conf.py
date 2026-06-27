"""
config/settings/logging_conf.py

Configuración completa de LOGGING para PRISLAB.
Depende de: base.py (BASE_DIR, IS_PRODUCTION, _TESTING, DEBUG)
"""
import os as _os
from pathlib import Path as _Path

# ── Helpers locales (no importa de base para evitar ciclos) ──────────────────
def _env_bool(name, default=False):
    raw = _os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in ('1', 'true', 'yes', 'on')


_BASE_DIR = _Path(__file__).resolve().parent.parent.parent
_TESTING = 'test' in __import__('sys').argv or _os.environ.get('DJANGO_TESTING', '') == 'True'
_IS_PRODUCTION = (_os.environ.get('PRISLAB_ENV') or _os.environ.get('DJANGO_ENV') or '').strip().lower() == 'production'
_DEBUG = _os.environ.get('DEBUG', 'False') == 'True'

_LOG_DIR = _BASE_DIR / 'logs'
_LOG_DIR.mkdir(parents=True, exist_ok=True)

PRISLAB_DISABLE_FILE_LOG_HANDLERS = _env_bool(
    'PRISLAB_DISABLE_FILE_LOG_HANDLERS',
    _TESTING,
)

_LOG_HANDLERS = ['console']
_EXTRA_HANDLERS = {}
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

if not _IS_PRODUCTION and not PRISLAB_DISABLE_FILE_LOG_HANDLERS:
    _EXTRA_HANDLERS = {
        'file_errors': {
            'level': 'WARNING',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': str(_LOG_DIR / 'prislab_errors.log'),
            'maxBytes': 5 * 1024 * 1024,
            'backupCount': 5,
            'formatter': 'detailed',
            'encoding': 'utf-8',
        },
        'file_audit': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': str(_LOG_DIR / 'prislab_audit.log'),
            'maxBytes': 10 * 1024 * 1024,
            'backupCount': 10,
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
            'level': 'DEBUG' if _DEBUG else 'INFO',
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
