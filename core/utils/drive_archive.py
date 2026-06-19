"""
Archivo Muerto (Google Drive API)

Objetivo: almacenar archivos pesados (backups, manuales históricos, expedientes) en el Drive del cliente
para reducir costos de nube y aprovechar almacenamiento existente.

Diseño:
- NO rompe local/dev: si faltan credenciales/paquetes, simplemente devuelve (ok=False) y deja el archivo local.
- Activación por env:
  - DRIVE_ARCHIVE_ENABLED=true
  - GOOGLE_DRIVE_SERVICE_ACCOUNT_JSON=/ruta/sa.json   (recomendado)
  - DRIVE_FOLDER_ID=... (opcional)
"""

from __future__ import annotations

import os
import socket
from dataclasses import dataclass
from typing import Optional, Dict, Any
from config.drive_credentials import get_drive_credentials

# Timeout para operaciones de red (modo supervivencia)
DRIVE_NETWORK_TIMEOUT = 30


@dataclass
class DriveUploadResult:
    ok: bool
    file_id: Optional[str] = None
    folder_id: Optional[str] = None
    error: Optional[str] = None


def drive_enabled() -> bool:
    return (os.getenv("DRIVE_ARCHIVE_ENABLED", "") or "").strip().lower() in ("1", "true", "yes", "on")


def _build_drive_service():
    """
    Construye cliente Drive v3 usando Service Account.
    """
    try:
        from googleapiclient.discovery import build
    except Exception as e:
        raise RuntimeError(
            "Faltan dependencias de Google Drive. Instala google-api-python-client y google-auth."
        ) from e

    creds = get_drive_credentials()
    if not creds:
        raise RuntimeError(
            "No se resolvieron credenciales de Google Drive. "
            "Configura GOOGLE_APPLICATION_CREDENTIALS o GOOGLE_DRIVE_SERVICE_ACCOUNT_JSON."
        )
    return build("drive", "v3", credentials=creds, cache_discovery=False)


def subir_archivo_a_drive(*, file_path: str, file_name: Optional[str] = None, folder_id: Optional[str] = None) -> DriveUploadResult:
    """
    Sube un archivo al Drive. Retorna DriveUploadResult.
    """
    if not drive_enabled():
        return DriveUploadResult(ok=False, error="DRIVE_ARCHIVE_ENABLED no activo")

    folder_id = folder_id or (os.getenv("DRIVE_FOLDER_ID", "") or "").strip() or None

    try:
        service = _build_drive_service()
        try:
            from googleapiclient.http import MediaFileUpload
        except Exception as e:
            raise RuntimeError("No se pudo importar MediaFileUpload") from e

        nombre = file_name or os.path.basename(file_path)
        metadata: Dict[str, Any] = {"name": nombre}
        if folder_id:
            metadata["parents"] = [folder_id]

        media = MediaFileUpload(file_path, resumable=True)
        old_timeout = socket.getdefaulttimeout()
        try:
            socket.setdefaulttimeout(DRIVE_NETWORK_TIMEOUT)
            created = service.files().create(body=metadata, media_body=media, fields="id").execute()
            file_id = created.get("id")
            return DriveUploadResult(ok=True, file_id=file_id, folder_id=folder_id)
        finally:
            socket.setdefaulttimeout(old_timeout)
    except socket.timeout:
        return DriveUploadResult(
            ok=False,
            error=f"Tiempo de espera agotado ({DRIVE_NETWORK_TIMEOUT}s). Drive no respondió.",
            folder_id=folder_id,
        )
    except Exception as e:
        return DriveUploadResult(ok=False, error=str(e), folder_id=folder_id)
