"""
config/drive_credentials.py
════════════════════════════════════════════════════════════════════════════════
Cargador de credenciales Google Drive para PRISLAB SaaS.
Estrategia de resolución (prioridad descendente):

  1. GOOGLE_DRIVE_SERVICE_ACCOUNT_JSON  — JSON completo de SA en env var
  2. GOOGLE_APPLICATION_CREDENTIALS      — ruta al archivo .json del SA
  3. google.auth.default() con scopes    — ADC de Cloud Run / Workload Identity
  4. None                                — sin Drive, fallback a almacenamiento local

El backend GoogleDriveStorage en config/storage_backends.py usa el resultado
de esta función para autenticarse con Drive API v3.
════════════════════════════════════════════════════════════════════════════════
"""
import os
import json
import logging

logger = logging.getLogger('config.drive_credentials')

_DRIVE_SCOPES = [
    'https://www.googleapis.com/auth/drive',
    'https://www.googleapis.com/auth/drive.file',
]


def get_drive_credentials():
    """
    Resuelve y retorna credenciales válidas para Google Drive API v3.
    Retorna google.auth.credentials.Credentials o None si no hay credenciales.
    """

    # ── Estrategia 1: JSON completo de Service Account en variable de entorno ──
    sa_json_str = os.environ.get('GOOGLE_DRIVE_SERVICE_ACCOUNT_JSON', '').strip()
    if sa_json_str:
        try:
            from google.oauth2.service_account import Credentials
            sa_info = json.loads(sa_json_str)
            creds = Credentials.from_service_account_info(sa_info, scopes=_DRIVE_SCOPES)
            logger.info("[Drive Credentials] Usando Service Account desde GOOGLE_DRIVE_SERVICE_ACCOUNT_JSON")
            return creds
        except Exception as exc:
            logger.warning(f"[Drive Credentials] Fallo con GOOGLE_DRIVE_SERVICE_ACCOUNT_JSON: {exc}")

    # ── Estrategia 2: Ruta a archivo .json de Service Account ──────────────────
    sa_file = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS', '').strip()
    if sa_file and os.path.isfile(sa_file):
        try:
            from google.oauth2.service_account import Credentials
            creds = Credentials.from_service_account_file(sa_file, scopes=_DRIVE_SCOPES)
            logger.info(f"[Drive Credentials] Usando Service Account desde archivo: {sa_file}")
            return creds
        except Exception as exc:
            logger.warning(f"[Drive Credentials] Fallo con GOOGLE_APPLICATION_CREDENTIALS: {exc}")

    # ── Estrategia 3: Application Default Credentials (Cloud Run / GCE) ────────
    try:
        import google.auth
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials as OAuth2Credentials

        creds, project = google.auth.default(scopes=_DRIVE_SCOPES)
        # Refrescar para validar
        creds.refresh(Request())
        logger.info(f"[Drive Credentials] Usando Application Default Credentials (proyecto: {project})")
        return creds
    except Exception as exc:
        logger.warning(f"[Drive Credentials] ADC no disponible: {exc}")

    # ── Sin credenciales ────────────────────────────────────────────────────────
    logger.warning(
        "[Drive Credentials] No se encontraron credenciales para Google Drive. "
        "El almacenamiento usará el fallback local/GCS."
    )
    return None
