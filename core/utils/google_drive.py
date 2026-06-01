"""
Google Drive Storage Layer (API v3) - Integración Empresarial.

Patrón: Singleton + Fire & Forget + Cache de Carpetas.
Objetivo: Subir PDFs a Drive sin bloquear flujo principal del sistema.

Estructura de carpetas: PRISLAB_ROOT / folder_name / AÑO / MES
Ejemplo: PRISLAB_ROOT / Recetas / 2026 / 01

Autor: PRISLAB Engineering Team
Última actualización: 2026-01-25
"""
import os
from datetime import datetime
from threading import Lock
from typing import Dict, Optional
import logging

from django.conf import settings
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from googleapiclient.errors import HttpError
import socket

logger = logging.getLogger(__name__)

# ==============================================================================
# SINGLETON: DriveService (Una instancia por ciclo de vida del servidor)
# ==============================================================================

class DriveService:
    """
    Servicio de conexión a Google Drive con patrón Singleton.
    Incluye cache de carpetas para minimizar hits a la API.
    """
    _instance = None
    _lock = Lock()

    def __new__(cls):
        """Garantiza una única instancia (thread-safe)."""
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._service = None
                cls._instance._folder_cache = {}  # Cache: {folder_path: folder_id}
                cls._instance._authenticated = False
                cls._instance._authenticate()
        return cls._instance

    def _authenticate(self):
        """
        Autenticación usando Service Account.
        Scope mínimo: drive.file (solo archivos creados por esta app).
        """
        try:
            # Buscar credenciales en .env
            sa_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
            
            if not sa_path:
                logger.warning(
                    "[DRIVE] GOOGLE_APPLICATION_CREDENTIALS no configurado. "
                    "Storage Layer deshabilitado. Sistema funcionará localmente."
                )
                return
            
            if not os.path.exists(sa_path):
                logger.error(
                    f"[DRIVE] Archivo de credenciales no encontrado: {sa_path}. "
                    "Verificar ruta en .env"
                )
                return

            # Crear credenciales con scope mínimo
            creds = service_account.Credentials.from_service_account_file(
                sa_path,
                scopes=["https://www.googleapis.com/auth/drive.file"]
            )
            
            # Construir servicio (cache_discovery=False para evitar warnings)
            self._service = build(
                "drive", 
                "v3", 
                credentials=creds, 
                cache_discovery=False
            )
            self._authenticated = True
            
            logger.info("[DRIVE] Servicio autenticado correctamente (Singleton activo)")
            
            # Test de conectividad opcional
            try:
                self._service.about().get(fields="user").execute()
                logger.info("[DRIVE] Test de conectividad exitoso")
            except Exception as e:
                logger.warning(f"[DRIVE] Advertencia en test de conectividad: {e}")
            
        except Exception as e:
            logger.error(f"[DRIVE] Error crítico en autenticación: {e}")
            self._service = None
            self._authenticated = False

    def get_service(self):
        """Retorna la instancia del servicio de Drive (None si no está autenticado)."""
        return self._service

    def is_authenticated(self):
        """Verifica si el servicio está autenticado."""
        return self._authenticated

    def get_cached_folder_id(self, folder_path: str) -> Optional[str]:
        """Obtiene ID de carpeta desde cache."""
        return self._folder_cache.get(folder_path)

    def cache_folder_id(self, folder_path: str, folder_id: str):
        """Guarda ID de carpeta en cache."""
        self._folder_cache[folder_path] = folder_id
        logger.debug(f"[DRIVE CACHE] Carpeta cacheada: {folder_path} -> {folder_id}")


# ==============================================================================
# FUNCIONES AUXILIARES (Gestión de Carpetas)
# ==============================================================================

def _find_or_create_folder(service, folder_name: str, parent_folder_id: Optional[str] = None) -> Optional[str]:
    """
    Busca una carpeta en Drive. Si no existe, la crea.
    
    Args:
        service: Servicio de Drive autenticado
        folder_name: Nombre de la carpeta
        parent_folder_id: ID de carpeta padre (None = raíz)
    
    Returns:
        str: ID de la carpeta (existente o nueva)
        None: Si falla la operación
    """
    try:
        # Construir query de búsqueda
        query = f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
        if parent_folder_id:
            query += f" and '{parent_folder_id}' in parents"
        
        # Buscar carpeta existente
        response = service.files().list(
            q=query, 
            fields="files(id, name)",
            pageSize=10
        ).execute()
        
        files = response.get('files', [])
        
        if files:
            # Carpeta encontrada
            folder_id = files[0]['id']
            logger.debug(f"[DRIVE] Carpeta existente encontrada: {folder_name} (ID: {folder_id})")
            return folder_id
        else:
            # Crear carpeta nueva
            file_metadata = {
                'name': folder_name,
                'mimeType': 'application/vnd.google-apps.folder'
            }
            if parent_folder_id:
                file_metadata['parents'] = [parent_folder_id]
            
            folder = service.files().create(
                body=file_metadata, 
                fields='id'
            ).execute()
            
            folder_id = folder.get('id')
            logger.info(f"[DRIVE] Carpeta creada: {folder_name} (ID: {folder_id})")
            return folder_id
            
    except HttpError as e:
        logger.error(f"[DRIVE] Error HTTP al gestionar carpeta '{folder_name}': {e}")
        return None
    except Exception as e:
        logger.error(f"[DRIVE] Error inesperado al gestionar carpeta '{folder_name}': {e}")
        return None


def _build_folder_structure(service, base_folder_name: str, subfolder_month: bool = True) -> Optional[str]:
    """
    Construye estructura de carpetas: base_folder / AÑO / MES.
    Usa cache para evitar hits repetidos a la API.
    
    Args:
        service: Servicio de Drive
        base_folder_name: Carpeta base (ej: 'Recetas', 'Ordenes')
        subfolder_month: Si es True, crea subcarpetas AÑO/MES
    
    Returns:
        str: ID de la carpeta final donde subir el archivo
        None: Si falla
    """
    drive_instance = DriveService()
    
    # Si no se requiere estructura mensual, solo crear carpeta base
    if not subfolder_month:
        folder_path = f"PRISLAB/{base_folder_name}"
        cached_id = drive_instance.get_cached_folder_id(folder_path)
        
        if cached_id:
            return cached_id
        
        # Crear PRISLAB_ROOT
        prislab_root_id = _find_or_create_folder(service, "PRISLAB")
        if not prislab_root_id:
            return None
        
        # Crear carpeta base
        base_folder_id = _find_or_create_folder(service, base_folder_name, prislab_root_id)
        if base_folder_id:
            drive_instance.cache_folder_id(folder_path, base_folder_id)
        
        return base_folder_id
    
    # Estructura mensual: PRISLAB / base_folder / AÑO / MES
    now = datetime.now()
    year_str = str(now.year)
    month_str = f"{now.month:02d}"  # 01, 02, ..., 12
    
    folder_path = f"PRISLAB/{base_folder_name}/{year_str}/{month_str}"
    cached_id = drive_instance.get_cached_folder_id(folder_path)
    
    if cached_id:
        logger.debug(f"[DRIVE CACHE] Usando carpeta cacheada: {folder_path}")
        return cached_id
    
    # Crear estructura completa
    prislab_root_id = _find_or_create_folder(service, "PRISLAB")
    if not prislab_root_id:
        return None
    
    base_folder_id = _find_or_create_folder(service, base_folder_name, prislab_root_id)
    if not base_folder_id:
        return None
    
    year_folder_id = _find_or_create_folder(service, year_str, base_folder_id)
    if not year_folder_id:
        return None
    
    month_folder_id = _find_or_create_folder(service, month_str, year_folder_id)
    if not month_folder_id:
        return None
    
    # Cachear ruta completa
    drive_instance.cache_folder_id(folder_path, month_folder_id)
    
    logger.info(f"[DRIVE] Estructura creada/verificada: {folder_path}")
    return month_folder_id


# ==============================================================================
# FUNCIÓN MAESTRA: sync_to_drive (Fire & Forget Pattern)
# ==============================================================================

def sync_to_drive(
    file_path: str, 
    folder_name: str, 
    subfolder_month: bool = True,
    timeout: int = 30
) -> Dict[str, any]:
    """
    Sube un archivo PDF a Google Drive de forma no bloqueante.
    
    Patrón Fire & Forget: Si falla, retorna error pero NO rompe el flujo.
    
    Args:
        file_path: Ruta absoluta al archivo local
        folder_name: Nombre de carpeta destino (ej: 'Recetas', 'Ordenes')
        subfolder_month: Si es True, organiza en subcarpetas AÑO/MES
        timeout: Timeout en segundos para operaciones de red
    
    Returns:
        dict: {
            'success': bool,
            'file_id': str | None,
            'web_view_link': str | None,
            'download_link': str | None,
            'error_message': str | None
        }
    
    Ejemplo:
        >>> result = sync_to_drive('/tmp/receta.pdf', 'Recetas', subfolder_month=True)
        >>> if result['success']:
        >>>     print(f"URL: {result['web_view_link']}")
        >>> else:
        >>>     print(f"Error: {result['error_message']}")
    """
    # Configurar timeout global para sockets
    original_timeout = socket.getdefaulttimeout()
    socket.setdefaulttimeout(timeout)
    
    try:
        # 1. Validaciones iniciales
        if not os.path.exists(file_path):
            error_msg = f"Archivo no encontrado: {file_path}"
            logger.error(f"[DRIVE] {error_msg}")
            return {
                'success': False,
                'file_id': None,
                'web_view_link': None,
                'download_link': None,
                'error_message': error_msg
            }
        
        # 2. Obtener servicio (Singleton)
        drive_instance = DriveService()
        service = drive_instance.get_service()
        
        if not service or not drive_instance.is_authenticated():
            error_msg = "Servicio de Drive no disponible (credenciales no configuradas)"
            logger.warning(f"[DRIVE] {error_msg}")
            return {
                'success': False,
                'file_id': None,
                'web_view_link': None,
                'download_link': None,
                'error_message': error_msg
            }
        
        # 3. Construir estructura de carpetas
        target_folder_id = _build_folder_structure(service, folder_name, subfolder_month)
        
        if not target_folder_id:
            error_msg = f"No se pudo crear/acceder a la carpeta '{folder_name}'"
            logger.error(f"[DRIVE] {error_msg}")
            return {
                'success': False,
                'file_id': None,
                'web_view_link': None,
                'download_link': None,
                'error_message': error_msg
            }
        
        # 4. Preparar archivo para subida
        file_name = os.path.basename(file_path)
        file_metadata = {
            'name': file_name,
            'parents': [target_folder_id]
        }
        
        media = MediaFileUpload(
            file_path, 
            mimetype='application/pdf', 
            resumable=True
        )
        
        # 5. Verificar si ya existe (evitar duplicados)
        existing_files = service.files().list(
            q=f"name='{file_name}' and '{target_folder_id}' in parents and trashed=false",
            fields="files(id, webViewLink, webContentLink)",
            pageSize=5
        ).execute().get('files', [])
        
        if existing_files:
            # Actualizar archivo existente
            file_id = existing_files[0]['id']
            uploaded_file = service.files().update(
                fileId=file_id,
                media_body=media,
                fields='id, webViewLink, webContentLink'
            ).execute()
            logger.info(f"[DRIVE] Archivo actualizado: {file_name} (ID: {file_id})")
        else:
            # Subir archivo nuevo
            uploaded_file = service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id, webViewLink, webContentLink'
            ).execute()
            file_id = uploaded_file.get('id')
            logger.info(f"[DRIVE] Archivo nuevo subido: {file_name} (ID: {file_id})")
        
        # 6. Retorno exitoso
        return {
            'success': True,
            'file_id': uploaded_file.get('id'),
            'web_view_link': uploaded_file.get('webViewLink'),
            'download_link': uploaded_file.get('webContentLink'),
            'error_message': None
        }
    
    except HttpError as e:
        error_msg = f"Error HTTP de Google API: {e.resp.status} - {e.content.decode()}"
        logger.error(f"[DRIVE] {error_msg}")
        return {
            'success': False,
            'file_id': None,
            'web_view_link': None,
            'download_link': None,
            'error_message': error_msg
        }
    
    except socket.timeout:
        error_msg = f"Timeout de red ({timeout}s) al subir archivo"
        logger.error(f"[DRIVE] {error_msg}")
        return {
            'success': False,
            'file_id': None,
            'web_view_link': None,
            'download_link': None,
            'error_message': error_msg
        }
    
    except Exception as e:
        error_msg = f"Error inesperado: {type(e).__name__} - {str(e)}"
        logger.error(f"[DRIVE] {error_msg}")
        return {
            'success': False,
            'file_id': None,
            'web_view_link': None,
            'download_link': None,
            'error_message': error_msg
        }
    
    finally:
        # Restaurar timeout original
        socket.setdefaulttimeout(original_timeout)


# ==============================================================================
# FUNCIONES DE UTILIDAD
# ==============================================================================

def test_drive_connection() -> bool:
    """
    Prueba la conexión a Google Drive.
    
    Returns:
        bool: True si la conexión es exitosa, False en caso contrario
    """
    try:
        drive_instance = DriveService()
        service = drive_instance.get_service()
        
        if not service:
            logger.error("[DRIVE TEST] Servicio no disponible")
            return False
        
        # Test simple: obtener información del usuario
        about = service.about().get(fields="user").execute()
        user_email = about.get('user', {}).get('emailAddress', 'Desconocido')
        
        logger.info(f"[DRIVE TEST] Conexión exitosa. Usuario: {user_email}")
        return True
        
    except Exception as e:
        logger.error(f"[DRIVE TEST] Fallo en test de conexión: {e}")
        return False
