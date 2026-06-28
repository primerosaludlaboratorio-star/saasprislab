"""
Archivo histórico de Google Drive.

Drive fue retirado del sistema. Este módulo permanece como shim para no
romper imports antiguos, pero ya no realiza archivado remoto.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class DriveUploadResult:
    ok: bool
    file_id: Optional[str] = None
    folder_id: Optional[str] = None
    error: Optional[str] = None


def drive_enabled() -> bool:
    return False


def _build_drive_service():
    """Compatibilidad histórica. Drive deshabilitado."""
    return None


def subir_archivo_a_drive(*, file_path: str, file_name: Optional[str] = None, folder_id: Optional[str] = None) -> DriveUploadResult:
    """
    Compatibilidad histórica. Drive deshabilitado.
    """
    return DriveUploadResult(ok=False, error="Google Drive deshabilitado", folder_id=folder_id)
