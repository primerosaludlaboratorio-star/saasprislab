"""
core/tasks/storage_tasks.py
════════════════════════════════════════════════════════════════════════════════
Tareas Celery para sincronización asíncrona de archivos con Google Drive.

Queue: 'drive_sync'
Retries: hasta 5 reintentos con backoff exponencial (60s, 120s, 240s, 480s, 960s)

Flujo:
  1. BufferLocalStorage._save() guarda en /media/buffer/ y encola esta task
  2. Task lee el archivo del buffer local
  3. Sube a TenantDriveStorage (Drive API v3)
  4. Si éxito: elimina buffer local, marca sync en cache
  5. Si falla: reintento automático (respeta DRIVE_SYNC_MAX_RETRIES)
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
    Sincroniza un archivo del buffer local a Google Drive.

    Args:
        nombre: Ruta relativa del archivo en el buffer (ej: 'prislab/resultados/2026/archivo.pdf')
        tenant_slug: Slug de la empresa para subcarpeta en Drive
    """
    logger.info(f'[Drive Sync] Iniciando: {nombre} (tenant: {tenant_slug}, intento {self.request.retries + 1}/6)')

    # ── 1. Localizar archivo en buffer ────────────────────────────────────────
    buffer_dir = getattr(settings, 'MEDIA_BUFFER_DIR',
                         os.path.join(settings.MEDIA_ROOT, 'buffer'))
    archivo_local = os.path.join(buffer_dir, nombre.replace('/', os.sep))

    if not os.path.isfile(archivo_local):
        logger.warning(f'[Drive Sync] Archivo no encontrado en buffer: {archivo_local}')
        return {'ok': False, 'razon': 'archivo_no_encontrado', 'nombre': nombre}

    tamano_mb = os.path.getsize(archivo_local) / (1024 * 1024)

    # ── 2. Obtener credenciales Drive ─────────────────────────────────────────
    try:
        from config.drive_credentials import get_drive_credentials
        creds = get_drive_credentials()
        if not creds:
            raise ValueError('Sin credenciales Drive disponibles')
    except Exception as exc:
        logger.warning(f'[Drive Sync] Sin credenciales: {exc}')
        _manejar_reintento(self, exc, nombre)
        return

    # ── 3. Subir a Drive ──────────────────────────────────────────────────────
    try:
        from config.storage_backends import TenantDriveStorage
        folder_id = settings.GOOGLE_DRIVE_FOLDER_ID

        storage = TenantDriveStorage(
            tenant_slug=tenant_slug,
            credentials=creds,
            folder_id=folder_id,
        )

        with open(archivo_local, 'rb') as f:
            from django.core.files.base import File
            storage._save(nombre, File(f, name=os.path.basename(nombre)))

        # Obtener URL de Drive
        drive_url = storage.url(nombre)
        logger.info(f'[Drive Sync] Subido exitosamente: {nombre} ({tamano_mb:.2f} MB) → {drive_url}')

    except Exception as exc:
        logger.error(f'[Drive Sync] Error al subir {nombre}: {exc}')
        _manejar_reintento(self, exc, nombre)
        return

    # ── 4. Limpiar buffer local ───────────────────────────────────────────────
    try:
        os.remove(archivo_local)
        _limpiar_directorio_vacio(os.path.dirname(archivo_local))
        logger.debug(f'[Drive Sync] Buffer limpiado: {archivo_local}')
    except OSError as exc:
        logger.warning(f'[Drive Sync] No se pudo limpiar buffer: {exc}')

    # ── 5. Marcar como sincronizado en cache ──────────────────────────────────
    _marcar_sincronizado_cache(nombre, drive_url=drive_url)

    return {
        'ok': True,
        'nombre': nombre,
        'tamano_mb': round(tamano_mb, 2),
        'drive_url': drive_url,
    }


@shared_task(
    name='core.tasks.storage_tasks.resinc_buffer_pendiente',
    queue='drive_sync',
)
def resinc_buffer_pendiente():
    """
    Task periódica (Cloud Scheduler / Celery Beat): reencola archivos que
    llevan más de 10 minutos en el buffer sin sincronizarse.
    Actúa como red de seguridad si algún task se perdió.
    """
    import time
    buffer_dir = getattr(settings, 'MEDIA_BUFFER_DIR',
                         os.path.join(settings.MEDIA_ROOT, 'buffer'))

    if not os.path.isdir(buffer_dir):
        return {'reencol': 0}

    ahora = time.time()
    reencol = 0

    for raiz, _, archivos in os.walk(buffer_dir):
        for archivo in archivos:
            ruta_completa = os.path.join(raiz, archivo)
            edad_seg = ahora - os.path.getmtime(ruta_completa)
            if edad_seg > 600:  # más de 10 minutos en buffer
                # Calcular nombre relativo para Drive
                nombre_relativo = os.path.relpath(ruta_completa, buffer_dir).replace(os.sep, '/')
                # Inferir tenant del primer segmento de la ruta
                parts = nombre_relativo.split('/')
                tenant_slug = parts[0] if len(parts) > 1 else 'default'

                if not _esta_sincronizado_cache(nombre_relativo):
                    sincronizar_archivo_drive.apply_async(
                        args=[nombre_relativo, tenant_slug],
                        countdown=5,
                        queue='drive_sync',
                    )
                    reencol += 1
                    logger.info(f'[Resync] Reencolado: {nombre_relativo} (edad: {edad_seg/60:.1f} min)')

    logger.info(f'[Resync] Archivos reencolados: {reencol}')
    return {'reencol': reencol}


# ─── Helpers internos ─────────────────────────────────────────────────────────

def _manejar_reintento(task, exc, nombre: str):
    """Lanza el reintento con backoff exponencial."""
    max_retries = getattr(settings, 'DRIVE_SYNC_MAX_RETRIES', 5)
    base_delay = getattr(settings, 'DRIVE_SYNC_RETRY_COUNTDOWN', 60)

    if task.request.retries < max_retries:
        countdown = base_delay * (2 ** task.request.retries)
        logger.warning(
            f'[Drive Sync] Reintento {task.request.retries + 1}/{max_retries} '
            f'para {nombre} en {countdown}s: {exc}'
        )
        raise task.retry(exc=exc, countdown=countdown, max_retries=max_retries)
    else:
        logger.error(
            f'[Drive Sync] FALLO DEFINITIVO tras {max_retries} reintentos: {nombre}. '
            f'Archivo permanece en buffer local.'
        )
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
        pass


def _esta_sincronizado_cache(nombre: str) -> bool:
    try:
        from django.core.cache import cache
        estado = cache.get(f'drive_sync:{nombre}')
        return bool(estado and estado.get('ok'))
    except Exception:
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
