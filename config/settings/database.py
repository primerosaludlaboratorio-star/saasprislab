"""
config/settings/database.py

Configuración de base de datos.
Consume: BASE_DIR, IS_PRODUCTION, _env_bool, _env_int (de base.py via namespace)
"""
import os

from .base import BASE_DIR, IS_PRODUCTION, _env_bool, _env_int

if os.environ.get('DB_HOST'):
    db_host = os.environ.get('DB_HOST', '')
    db_conn_max_age = _env_int('DB_CONN_MAX_AGE', 60)  # 60s persistent connections (override via env)
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
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
            'OPTIONS': {'timeout': 60},
        }
    }
