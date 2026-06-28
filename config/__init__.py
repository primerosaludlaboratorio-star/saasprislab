# Garantiza que Celery se inicializa con Django para que los signals de @shared_task funcionen
from .celery import app as celery_app

__all__ = ('celery_app',)
