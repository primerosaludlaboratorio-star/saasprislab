"""
Tareas de mantenimiento y operación clínica.

Se activan desde Celery Beat para respaldos, limpieza del entorno y validación
del Escudo Clínico sin depender de cron externo.
"""
import logging
import os

from celery import shared_task
from django.conf import settings
from django.core.management import call_command

logger = logging.getLogger('core.tasks.maintenance')


def _skipped_response(task_name: str, reason: str):
    logger.info('%s omitida: %s', task_name, reason)
    return {'ok': False, 'skipped': True, 'reason': reason, 'task': task_name}


@shared_task(
    bind=True,
    name='core.tasks.maintenance_tasks.ejecutar_backup_database',
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_jitter=True,
    max_retries=3,
)
def ejecutar_backup_database(self, prefix: str = 'pgdump'):
    if not settings.IS_PRODUCTION:
        return _skipped_response('backup_database', 'entorno_no_produccion')

    bucket = getattr(settings, 'GCS_BACKUP_BUCKET', '') or os.environ.get('GCS_BACKUP_BUCKET', '')
    if not bucket:
        return _skipped_response('backup_database', 'gcs_backup_bucket_no_configurado')

    call_command('backup_database', prefix=prefix)
    return {'ok': True, 'task': 'backup_database'}


@shared_task(
    bind=True,
    name='core.tasks.maintenance_tasks.ejecutar_limpieza_entorno_prod',
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_jitter=True,
    max_retries=3,
)
def ejecutar_limpieza_entorno_prod(self, dry_run: bool = False):
    if not settings.IS_PRODUCTION:
        return _skipped_response('limpieza_entorno_prod', 'entorno_no_produccion')

    if dry_run:
        call_command('limpieza_entorno_prod', dry_run=True)
    else:
        call_command('limpieza_entorno_prod')
    return {'ok': True, 'task': 'limpieza_entorno_prod', 'dry_run': dry_run}


@shared_task(
    bind=True,
    name='core.tasks.maintenance_tasks.ejecutar_verificacion_escudo_clinico',
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_jitter=True,
    max_retries=3,
)
def ejecutar_verificacion_escudo_clinico(self):
    if not settings.IS_PRODUCTION:
        return _skipped_response('verificacion_escudo_clinico', 'entorno_no_produccion')

    call_command('verify_escudo_clinico')
    return {'ok': True, 'task': 'verificacion_escudo_clinico'}
