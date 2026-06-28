"""
Tareas periódicas de Celery Beat para notificaciones automáticas.
"""
import logging

from celery import shared_task

logger = logging.getLogger('core.tasks.notificaciones')


@shared_task
def ejecutar_verificaciones_automaticas_todas_empresas():
    """
    Ejecuta verificaciones automáticas (stock bajo, caducidades) para
    todas las empresas activas. Programada vía CELERY_BEAT_SCHEDULE.
    """
    from core.models import Empresa
    from core.utils.notificaciones import ejecutar_verificaciones_automaticas

    total = 0
    for empresa in Empresa.objects.all():
        try:
            ejecutar_verificaciones_automaticas(empresa)
            total += 1
        except Exception as exc:
            logger.error(
                'Error en verificaciones automáticas empresa=%s: %s',
                empresa.id, exc,
            )
    logger.info('Verificaciones automáticas ejecutadas para %s empresas', total)
    return total
