"""
Compatibilidad histórica: Google Drive fue retirado del sistema.

Las funciones públicas se conservan como no-op para no romper imports
viejos ni comandos heredados, pero ya no realizan llamadas a Drive.
"""

import logging

logger = logging.getLogger(__name__)


class DriveService:
    """Shim de compatibilidad. Drive deshabilitado."""

    def __init__(self):
        self._authenticated = False

    def get_service(self):
        return None

    def is_authenticated(self):
        return False

    def get_cached_folder_id(self, folder_path):
        return None

    def cache_folder_id(self, folder_path, folder_id):
        return None


def sync_to_drive(
    file_path: str,
    folder_name: str,
    subfolder_month: bool = True,
    timeout: int = 30
) -> dict:
    logger.info('[DRIVE] sync_to_drive deshabilitado. Archivo permanece local: %s', file_path)
    return {
        'success': False,
        'file_id': None,
        'web_view_link': None,
        'download_link': None,
        'error_message': 'Google Drive deshabilitado',
    }


def test_drive_connection() -> bool:
    logger.info('[DRIVE] test_drive_connection deshabilitado')
    return False
