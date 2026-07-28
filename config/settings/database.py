"""
config/settings/database.py

Configuración de base de datos.
Consume: BASE_DIR, IS_PRODUCTION, _env_bool, _env_int (de base.py via namespace)
"""
import os
import sys
from pathlib import Path

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
            # Permite crear un staging aislado sin tocar la base local de trabajo.
            'NAME': Path(os.environ['PRISLAB_SQLITE_PATH']) if os.environ.get('PRISLAB_SQLITE_PATH', '').strip() else BASE_DIR / 'db.sqlite3',
            'OPTIONS': {'timeout': 60},
        }
    }

    # Los tests locales no deben reutilizar el SQLite operativo del workspace.
    # Esto aisla la suite de cualquier servidor de desarrollo abierto.
    if 'test' in sys.argv:
        DATABASES['default']['TEST'] = {'NAME': ':memory:'}


# Opt-in para pruebas unitarias locales que no necesitan ejecutar la historia
# completa de migraciones. Las pruebas de migraciones deben ejecutarse sin él.
if 'test' in sys.argv and os.environ.get('PRISLAB_TEST_NO_MIGRATIONS') == '1':
    class _DisableMigrations(dict):
        def __contains__(self, item):
            return True

        def __getitem__(self, item):
            return None

    MIGRATION_MODULES = _DisableMigrations()
