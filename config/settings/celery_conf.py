"""
config/settings/celery_conf.py

Configuración de Celery: broker, result backend, serialización, timeouts,
Beat schedule y parámetros de Drive sync.
Depende de: cache.py (REDIS_URL), base.py (TIME_ZONE, MEDIA_ROOT)
"""
from celery.schedules import crontab

# Reutiliza REDIS_URL definido en cache.py (ya importado por __init__.py)
# Se accede vía importación diferida dentro del módulo para evitar referencias circulares.
import os as _os
_redis_url = _os.environ.get('REDIS_URL')

_celery_broker = _redis_url or 'memory://'
CELERY_BROKER_URL = _celery_broker
CELERY_TIMEZONE = _os.environ.get('TIME_ZONE', 'America/Mexico_City')
CELERY_RESULT_BACKEND = _redis_url if _redis_url else 'cache+memory://'

CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 600
CELERY_TASK_SOFT_TIME_LIMIT = 540
CELERY_WORKER_PREFETCH_MULTIPLIER = 1
CELERY_WORKER_MAX_TASKS_PER_CHILD = 50

# Sin Redis: ejecutar tasks síncronamente en el mismo proceso (dev / fallback)
CELERY_TASK_ALWAYS_EAGER = not bool(_redis_url)
CELERY_TASK_EAGER_PROPAGATES = True

# Reintentos Drive
DRIVE_SYNC_MAX_RETRIES = 5
DRIVE_SYNC_RETRY_COUNTDOWN = 60

# Celery Beat — tareas periódicas
CELERY_BEAT_SCHEDULE = {
    'verificaciones-automaticas-diarias': {
        'task': 'core.tasks.notificaciones_tasks.ejecutar_verificaciones_automaticas_todas_empresas',
        'schedule': crontab(hour=7, minute=0),
    },
}
