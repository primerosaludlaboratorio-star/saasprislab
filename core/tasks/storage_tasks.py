"""
core/tasks/storage_tasks.py
════════════════════════════════════════════════════════════════════════════════
Tareas históricas de sincronización a Google Drive.

Drive fue retirado del flujo activo de almacenamiento. Estas tareas quedan
como compatibilidad pasiva para evitar errores en referencias antiguas, pero
ya no realizan subida ni sincronización remota.
════════════════════════════════════════════════════════════════════════════════
"""
import os
import logging

from celery import shared_task
from django.conf import settings

logger = logging.getLogger('core.tasks.storage')


@shared_task(
    bind=True,
    name='core.tasks.storage_tasks.sincronizar_archivo_drive',
    queue='drive_sync',
    max_retries=5,
    default_retry_delay=60,  # primer reintento en 60s
    acks_late=True,          # confirmar solo cuando la task termina (no al inicio)
    reject_on_worker_lost=True,
)
def sincronizar_archivo_drive(self, nombre: str, tenant_slug: str = 'default'):
    """
    Compatibilidad histórica. Drive fue retirado del flujo activo.

    Args:
        nombre: Ruta relativa del archivo en el buffer (ej: 'prislab/resultados/2026/archivo.pdf')
        tenant_slug: Slug de la empresa para subcarpeta en Drive
    """
    logger.info('[Drive Sync] Deshabilitado. No se sincroniza %s (tenant: %s)', nombre, tenant_slug)
    return {'ok': False, 'razon': 'drive_deshabilitado', 'nombre': nombre}


@shared_task(
    name='core.tasks.storage_tasks.resinc_buffer_pendiente',
    queue='drive_sync',
)
def resinc_buffer_pendiente():
    """
    Compatibilidad histórica. Drive ya no sincroniza buffer.
    """
    return {'reencol': 0, 'drive_deshabilitado': True}


# ─── Helpers internos ─────────────────────────────────────────────────────────

def _manejar_reintento(task, exc, nombre: str):
    """Lanza el reintento con backoff exponencial."""
    logger.warning('[Drive Sync] Reintento deshabilitado para %s: %s', nombre, exc)
    _marcar_sincronizado_cache(nombre, drive_url='', fallido=True)


def _marcar_sincronizado_cache(nombre: str, drive_url: str = '', fallido: bool = False):
    try:
        from django.core.cache import cache
        ttl = 60 * 60 * 24 * 90  # 90 días
        cache.set(
            f'drive_sync:{nombre}',
            {'ok': not fallido, 'url': drive_url, 'fallido': fallido},
            timeout=ttl,
        )
    except Exception:
        logging.getLogger(__name__).exception("Error inesperado en _marcar_sincronizado_cache (storage_tasks.py)")
        pass


def _esta_sincronizado_cache(nombre: str) -> bool:
    try:
        from django.core.cache import cache
        estado = cache.get(f'drive_sync:{nombre}')
        return bool(estado and (estado.get('ok') or estado.get('fallido')))
    except Exception:
        logging.getLogger(__name__).exception("Error inesperado en _esta_sincronizado_cache (storage_tasks.py)")
        return False


def _limpiar_directorio_vacio(directorio: str):
    """Elimina recursivamente directorios vacíos del buffer (limpieza)."""
    buffer_dir = getattr(settings, 'MEDIA_BUFFER_DIR', '')
    if not buffer_dir or directorio == buffer_dir:
        return
    try:
        if os.path.isdir(directorio) and not os.listdir(directorio):
            os.rmdir(directorio)
            _limpiar_directorio_vacio(os.path.dirname(directorio))
    except OSError:
        pass