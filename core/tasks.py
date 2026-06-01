"""
Tareas Celery del app core (autodiscover_tasks).
"""
import logging

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(ignore_result=True, name='core.registrar_rastro_forense_task')
def registrar_rastro_forense_task(**kwargs):
    """Persiste un ForenseAcceso desde payload serializable (JSON)."""
    try:
        from core.models import ForenseAcceso

        ForenseAcceso.objects.create(**kwargs)
    except Exception as exc:
        logger.warning('registrar_rastro_forense_task falló: %s', exc, exc_info=True)
