"""Tareas asíncronas Celery de PRISLAB."""
from .storage_tasks import sincronizar_archivo_drive

__all__ = ['sincronizar_archivo_drive']
