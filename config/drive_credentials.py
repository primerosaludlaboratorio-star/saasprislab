"""
config/drive_credentials.py
===============================================================================
Compatibilidad temporal para el antiguo flujo de Google Drive.

Drive fue retirado del flujo activo de almacenamiento del sistema.
Estas funciones se conservan como shims de compatibilidad para no romper
imports históricos, pero ya no resuelven credenciales ni activan subida real.
===============================================================================
"""
import logging

logger = logging.getLogger('config.drive_credentials')


def get_drive_credentials():
    """
    Drive fue retirado del flujo activo de almacenamiento.
    Retorna None para forzar almacenamiento local/Vultr.
    """
    logger.info('[Drive Credentials] Google Drive deshabilitado. Se usa almacenamiento local/Vultr.')
    return None


def get_drive_service():
    """
    Compatibilidad temporal. Google Drive ya no está activo.
    """
    return None
