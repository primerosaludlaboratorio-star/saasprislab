"""
config/drive_credentials.py
===============================================================================
Cargador de credenciales Google Drive para PRISLAB SaaS.

Estrategia de resolución (prioridad descendente):

  1. OAuth 2.0 User Token
     - GOOGLE_DRIVE_TOKEN_PATH
     - GOOGLE_DRIVE_CREDENTIALS_PATH
  2. Service Account legacy
     - GOOGLE_DRIVE_SERVICE_ACCOUNT_JSON
     - GOOGLE_APPLICATION_CREDENTIALS
  3. None
     - Fallback a almacenamiento local

La prioridad OAuth existe para resolver definitivamente el error 403
storageQuotaExceeded cuando el destino vive en My Drive personal.
===============================================================================
"""
import json
import logging
import os

logger = logging.getLogger('config.drive_credentials')

_OAUTH_SCOPES = [
    'https://www.googleapis.com/auth/drive.file',
]

_SERVICE_ACCOUNT_SCOPES = [
    'https://www.googleapis.com/auth/drive',
]


def _load_oauth_credentials():
    """
    Carga credenciales OAuth 2.0 desde token.json.
    Si expiraron y existe refresh token, las refresca y persiste el token renovado.
    """
    token_path = os.environ.get(
        'GOOGLE_DRIVE_TOKEN_PATH',
        '/opt/prislab/credentials/token.json',
    ).strip()
    client_secret_path = os.environ.get(
        'GOOGLE_DRIVE_CREDENTIALS_PATH',
        '/opt/prislab/credentials/credentials.json',
    ).strip()

    if not token_path or not os.path.isfile(token_path):
        return None

    try:
        from google.oauth2.credentials import Credentials
        from google.auth.transport.requests import Request

        creds = Credentials.from_authorized_user_file(token_path, _OAUTH_SCOPES)

        if creds and creds.expired and creds.refresh_token:
            logger.info('[Drive Credentials] Token OAuth expirado. Intentando refrescar...')
            creds.refresh(Request())
            with open(token_path, 'w', encoding='utf-8') as token_file:
                token_file.write(creds.to_json())
            logger.info('[Drive Credentials] Token OAuth refrescado y guardado correctamente')

        if creds and creds.valid:
            logger.info(
                '[Drive Credentials] Usando OAuth 2.0 desde token.json (%s)',
                token_path,
            )
            return creds

        if creds and not creds.valid:
            logger.warning(
                '[Drive Credentials] El token OAuth existe pero no es válido. '
                'Revise %s y %s.',
                token_path,
                client_secret_path or '[sin GOOGLE_DRIVE_CREDENTIALS_PATH]',
            )
    except Exception as exc:
        logger.warning(f'[Drive Credentials] Fallo con OAuth 2.0 token.json: {exc}')

    return None


def _load_service_account_credentials():
    """
    Compatibilidad transitoria con Service Account mientras se completa la migración.
    """
    sa_json_str = os.environ.get('GOOGLE_DRIVE_SERVICE_ACCOUNT_JSON', '').strip()
    if sa_json_str:
        try:
            from google.oauth2.service_account import Credentials

            sa_info = json.loads(sa_json_str)
            creds = Credentials.from_service_account_info(
                sa_info,
                scopes=_SERVICE_ACCOUNT_SCOPES,
            )
            logger.info(
                '[Drive Credentials] Usando Service Account desde '
                'GOOGLE_DRIVE_SERVICE_ACCOUNT_JSON'
            )
            return creds
        except Exception as exc:
            logger.warning(
                f'[Drive Credentials] Fallo con GOOGLE_DRIVE_SERVICE_ACCOUNT_JSON: {exc}'
            )

    sa_file = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS', '').strip()
    if sa_file and os.path.isfile(sa_file):
        try:
            from google.oauth2.service_account import Credentials

            creds = Credentials.from_service_account_file(
                sa_file,
                scopes=_SERVICE_ACCOUNT_SCOPES,
            )
            logger.info(
                '[Drive Credentials] Usando Service Account desde archivo: %s',
                sa_file,
            )
            return creds
        except Exception as exc:
            logger.warning(
                f'[Drive Credentials] Fallo con GOOGLE_APPLICATION_CREDENTIALS: {exc}'
            )

    return None


def get_drive_credentials():
    """
    Resuelve y retorna credenciales válidas para Google Drive API v3.
    Prioriza OAuth 2.0 y conserva fallback a Service Account por compatibilidad.
    """
    oauth_creds = _load_oauth_credentials()
    if oauth_creds:
        return oauth_creds

    sa_creds = _load_service_account_credentials()
    if sa_creds:
        return sa_creds

    logger.warning(
        '[Drive Credentials] No se encontraron credenciales válidas para Google Drive. '
        'El almacenamiento usará el fallback local.'
    )
    return None


def get_drive_service():
    """
    Construye y retorna el cliente v3 de Google Drive.
    """
    creds = get_drive_credentials()
    if not creds:
        return None

    try:
        from googleapiclient.discovery import build

        return build('drive', 'v3', credentials=creds, cache_discovery=False)
    except Exception as exc:
        logger.error(
            f'[Drive Credentials] No se pudo construir el servicio de Drive API: {exc}'
        )
        return None
