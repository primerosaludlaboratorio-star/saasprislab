"""
config/celery.py
════════════════════════════════════════════════════════════════════════════════
Configuración de Celery para PRISLAB SaaS.
Usa el mismo Redis configurado para Django Channels y Cache.

Worker de producción (VPS / systemd / supervisor):
  celery -A config worker --loglevel=info --concurrency=2

Scheduler de tareas periódicas (backup diario, etc.):
  celery -A config beat --loglevel=info
════════════════════════════════════════════════════════════════════════════════
"""
import os
from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

app = Celery('prislab')

# Cargar configuración desde settings.py (prefijo CELERY_)
app.config_from_object('django.conf:settings', namespace='CELERY')

# Autodiscover tasks en todas las apps instaladas
app.autodiscover_tasks()


@app.task(bind=True, ignore_result=True)
def debug_task(self):
    print(f'[Celery Debug] Request: {self.request!r}')
