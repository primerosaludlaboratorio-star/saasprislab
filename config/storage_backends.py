"""
config/storage_backends.py
═══════════════════════════════════════════════════════════════════════════════
PRISLAB — Sistema de Almacenamiento Híbrido Asíncrono

Arquitectura:
  ┌─────────────────────────────────────────────────────────────────────┐
  │  Usuario sube archivo                                               │
  │       ↓                                                             │
  │  BufferLocalStorage._save()  →  /media/buffer/{tenant}/{ruta}      │
  │       ↓  (instantáneo, <5ms)                                        │
  │  ✅ Respuesta de éxito al usuario                                   │
  │       ↓                                                             │
  │  Archivo permanece en buffer local o se publica vía storage activo  │
  └─────────────────────────────────────────────────────────────────────┘

Estructura de carpetas en Drive:
  PRISLAB_Media/  [histórico; Google Drive ya no es ruta activa]
  ├── {empresa_slug}/          ← Aislamiento por tenant (multi-tenant SaaS)
  │   ├── resultados/          ← PDFs de resultados de laboratorio
  │   ├── expedientes/         ← Archivos clínicos (NOM-004)
  │   ├── recetas_ocr/         ← Imágenes de recetas
  │   ├── audio_consultas/     ← Audio PRIS dictaciones
  │   ├── fotos_muestras/      ← Evidencia toma de muestra
  │   ├── facturas_cfdi/       ← XMLs y PDFs CFDI
  │   └── logos/               ← Logotipos institucionales
  └── backups/
      └── YYYY/MM/             ← Backups DB organizados por fecha
═══════════════════════════════════════════════════════════════════════════════
"""
import os
import io
import socket
import logging
import mimetypes
import threading

from django.core.files.storage import FileSystemStorage, Storage
from django.core.files.base import ContentFile
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.utils.deconstruct import deconstructible

try:
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaIoBaseUpload, MediaIoBaseDownload
    from googleapiclient.errors import HttpError
except Exception:  # pragma: no cover - dependencia legacy opcional
    build = None
    MediaIoBaseUpload = None
    MediaIoBaseDownload = None

    class HttpError(Exception):
        """Shim legacy cuando googleapiclient no está instalado."""


try:
    from storages.backends.s3 import S3Storage
except Exception as exc:  # pragma: no cover - depende del entorno local
    _s3_import_error = exc

    class S3Storage(Storage):
        def __init__(self, *args, **kwargs):
            raise ImproperlyConfigured(
                "Vultr Object Storage / S3 está habilitado en configuración, "
                "pero faltan dependencias S3. Instala boto3 y django-storages "
                f"correctamente. Detalle original: {_s3_import_error}"
            )

logger = logging.getLogger('config.storage')
DRIVE_REQUEST_TIMEOUT = 30


def _drive_http_error_message(exc: HttpError, contexto: str) -> str:
    """Devuelve un mensaje útil para HttpError de Drive, especialmente 403."""
    status = getattr(getattr(exc, 'resp', None), 'status', None)
    try:
        raw = exc.content.decode() if getattr(exc, 'content', None) else str(exc)
    except Exception:
        raw = str(exc)
    raw_lower = raw.lower()
    if status == 403 or 'forbidden' in raw_lower or 'insufficient permissions' in raw_lower:
        return (
            f'Drive devolvió 403/Forbidden durante {contexto}. '
            'Revisa que la carpeta o Shared Drive esté compartida con la identidad activa '
            '(OAuth o Service Account) y que el archivo o parent ID pertenezca a la zona autorizada. '
            f'Detalle técnico: {raw}'
        )
    if status == 404:
        return f'Drive devolvió 404 durante {contexto}. Verifica el ID de carpeta o archivo. Detalle técnico: {raw}'
    return f'Drive devolvió error HTTP durante {contexto}: {raw}'


# ═══════════════════════════════════════════════════════════════════════════════
# 1. BUFFER LOCAL — Almacenamiento inmediato (respuesta <5ms al usuario)
# ═══════════════════════════════════════════════════════════════════════════════

@deconstructible
class BufferLocalStorage(FileSystemStorage):
    """
    PASO 1 del flujo asíncrono.

    Guarda el archivo en el buffer local (/media/buffer/) de forma instantánea
    y encola una Celery task para sincronizarlo a Google Drive en background.

    El usuario recibe confirmación de éxito en milisegundos.
    Drive es actualizado en background sin bloquear la experiencia.

    flag `archivo_sincronizado_drive`:
      - Tracked en cache Redis con clave: 'drive_sync:{nombre}'
      - True = sincronizado en Drive
      - False / ausente = pendiente o fallido (aún en buffer local)
    """

    def __init__(self, **kwargs):
        buffer_dir = getattr(settings, 'MEDIA_BUFFER_DIR',
                             os.path.join(settings.MEDIA_ROOT, 'buffer'))
        os.makedirs(buffer_dir, exist_ok=True)
        super().__init__(location=buffer_dir, base_url=settings.MEDIA_URL)

    def _save(self, name, content):
        """
        1. Inserta el tenant slug en la ruta del archivo.
        2. Guarda localmente (instantáneo).
        3. No encola sincronización a Google Drive: Drive fue retirado del flujo activo.
        """
        nombre_con_tenant = _insertar_tenant_en_ruta(name)
        saved_name = super()._save(nombre_con_tenant, content)
        return saved_name

    def url(self, name):
        """Retorna URL local del buffer."""
        return super().url(name)

    def exists(self, name):
        """Verifica si el archivo existe en el buffer local."""
        return super().exists(name)


# ═══════════════════════════════════════════════════════════════════════════════
# 2. GOOGLE DRIVE STORAGE — Almacenamiento definitivo en Drive 20TB
# ═══════════════════════════════════════════════════════════════════════════════

@deconstructible
class GoogleDriveStorage(Storage):
    """
    Compatibilidad histórica.

    Google Drive fue retirado del flujo activo del sistema. Esta clase se
    conserva únicamente para no romper imports legados o migraciones viejas.
    """

    def __init__(self, credentials=None, folder_id=None):
        self.credentials = credentials or getattr(settings, 'GOOGLE_DRIVE_CREDENTIALS', None)
        self.folder_id = folder_id or getattr(settings, 'GOOGLE_DRIVE_FOLDER_ID', '')
        self._service = None
        self._folder_cache = {}

    @property
    def service(self):
        """Lazy loading del servicio Drive API v3."""
        if self._service is None:
            self._service = build(
                'drive',
                'v3',
                credentials=self.credentials,
                cache_discovery=False,
            )
        return self._service

    @staticmethod
    def _shared_drive_kwargs(include_items: bool = False):
        kwargs = {'supportsAllDrives': True}
        if include_items:
            kwargs['includeItemsFromAllDrives'] = True
        return kwargs

    def _save(self, name, content):
        folder_path = os.path.dirname(name)
        filename = os.path.basename(name)
        parent_folder_id = self._get_or_create_folder_path(folder_path)

        mime_type, _ = mimetypes.guess_type(filename)
        if mime_type is None:
            mime_type = 'application/octet-stream'

        file_metadata = {'name': filename, 'parents': [parent_folder_id]}

        if hasattr(content, 'read'):
            content.seek(0)
            media = MediaIoBaseUpload(content, mimetype=mime_type, resumable=True)
        else:
            media = MediaIoBaseUpload(io.BytesIO(content), mimetype=mime_type, resumable=True)

        old_timeout = socket.getdefaulttimeout()
        socket.setdefaulttimeout(DRIVE_REQUEST_TIMEOUT)
        try:
            file = self.service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id, name, webViewLink',
                **self._shared_drive_kwargs(),
            ).execute()

            return name
        except socket.timeout:
            raise Exception('Drive: timeout al subir archivo. Reintentando...')
        except HttpError as exc:
            raise Exception(_drive_http_error_message(exc, f'subida de {name}'))
        finally:
            socket.setdefaulttimeout(old_timeout)

    def _open(self, name, mode='rb'):
        file_id = self._get_file_id_by_path(name)
        if file_id is None:
            raise FileNotFoundError(f'Archivo no encontrado en Drive: {name}')
        old_timeout = socket.getdefaulttimeout()
        socket.setdefaulttimeout(DRIVE_REQUEST_TIMEOUT)
        try:
            request = self.service.files().get_media(
                fileId=file_id,
                **self._shared_drive_kwargs(),
            )
            fh = io.BytesIO()
            from googleapiclient.http import MediaIoBaseDownload
            downloader = MediaIoBaseDownload(fh, request)
            done = False
            while not done:
                _, done = downloader.next_chunk()
            fh.seek(0)
            return ContentFile(fh.read(), name=name)
        finally:
            socket.setdefaulttimeout(old_timeout)

    def exists(self, name):
        return self._get_file_id_by_path(name) is not None

    def size(self, name):
        file_id = self._get_file_id_by_path(name)
        if not file_id:
            return 0
        try:
            f = self.service.files().get(
                fileId=file_id,
                fields='size',
                **self._shared_drive_kwargs(),
            ).execute()
            return int(f.get('size', 0))
        except HttpError:
            return 0

    def url(self, name):
        file_id = self._get_file_id_by_path(name)
        if not file_id:
            return ''
        return f'https://drive.google.com/uc?export=download&id={file_id}'

    def delete(self, name):
        file_id = self._get_file_id_by_path(name)
        if file_id:
            try:
                self.service.files().delete(
                    fileId=file_id,
                    **self._shared_drive_kwargs(),
                ).execute()
            except HttpError as exc:
                logger.warning(f'Drive: error al eliminar {name}: {exc}')

    def listdir(self, path):
        folder_id = self._get_or_create_folder_path(path)
        try:
            results = self.service.files().list(
                q=f"'{folder_id}' in parents and trashed=false",
                fields='files(id, name, mimeType)',
                pageSize=1000,
                corpora='allDrives',
                **self._shared_drive_kwargs(include_items=True),
            ).execute()
            files = results.get('files', [])
            dirs = [f['name'] for f in files if 'folder' in f['mimeType']]
            fnames = [f['name'] for f in files if 'folder' not in f['mimeType']]
            return dirs, fnames
        except HttpError:
            return [], []

    def get_available_name(self, name, max_length=None):
        return name

    def get_accessed_time(self, name):
        return None

    def get_created_time(self, name):
        file_id = self._get_file_id_by_path(name)
        if not file_id:
            return None
        try:
            f = self.service.files().get(
                fileId=file_id,
                fields='createdTime',
                **self._shared_drive_kwargs(),
            ).execute()
            from datetime import datetime
            return datetime.fromisoformat(f['createdTime'].replace('Z', '+00:00'))
        except HttpError as exc:
            logger.warning(_drive_http_error_message(exc, f'búsqueda de carpeta {name}'))
            return None

    def get_modified_time(self, name):
        file_id = self._get_file_id_by_path(name)
        if not file_id:
            return None
        try:
            f = self.service.files().get(
                fileId=file_id,
                fields='modifiedTime',
                **self._shared_drive_kwargs(),
            ).execute()
            from datetime import datetime
            return datetime.fromisoformat(f['modifiedTime'].replace('Z', '+00:00'))
        except HttpError:
            return None

    def _get_file_id_by_path(self, path):
        folder_path = os.path.dirname(path)
        filename = os.path.basename(path)
        parent_id = self._get_or_create_folder_path(folder_path)
        try:
            results = self.service.files().list(
                q=f"name='{filename}' and '{parent_id}' in parents and trashed=false",
                fields='files(id)',
                pageSize=1,
                corpora='allDrives',
                **self._shared_drive_kwargs(include_items=True),
            ).execute()
            files = results.get('files', [])
            return files[0]['id'] if files else None
        except HttpError:
            return None

    def _get_or_create_folder_path(self, path):
        if not path or path == '.':
            return self.folder_id
        if path in self._folder_cache:
            return self._folder_cache[path]
        parts = path.split('/')
        parent_id = self.folder_id
        for part in parts:
            if not part:
                continue
            folder_id = self._find_folder(part, parent_id)
            if not folder_id:
                folder_id = self._create_folder(part, parent_id)
            parent_id = folder_id
        self._folder_cache[path] = parent_id
        return parent_id

    def _find_folder(self, name, parent_id):
        try:
            results = self.service.files().list(
                q=f"name='{name}' and mimeType='application/vnd.google-apps.folder' "
                  f"and '{parent_id}' in parents and trashed=false",
                fields='files(id)',
                pageSize=1,
                corpora='allDrives',
                **self._shared_drive_kwargs(include_items=True),
            ).execute()
            folders = results.get('files', [])
            return folders[0]['id'] if folders else None
        except HttpError:
            return None

    def _create_folder(self, name, parent_id):
        try:
            folder = self.service.files().create(
                body={'name': name,
                      'mimeType': 'application/vnd.google-apps.folder',
                      'parents': [parent_id]},
                fields='id',
                **self._shared_drive_kwargs(),
            ).execute()
            return folder['id']
        except HttpError as exc:
            raise Exception(_drive_http_error_message(exc, f'creación de carpeta {name}'))


# ═══════════════════════════════════════════════════════════════════════════════
# 3. TENANT DRIVE STORAGE — Variante multi-tenant con subcarpeta por empresa
# ═══════════════════════════════════════════════════════════════════════════════

@deconstructible
class TenantDriveStorage(GoogleDriveStorage):
    """
    Compatibilidad histórica del storage por tenant en Drive.
    Ya no se usa en el flujo activo.
    """

    def __init__(self, tenant_slug: str = '', **kwargs):
        super().__init__(**kwargs)
        self._tenant_slug = tenant_slug or _get_thread_tenant_slug()

    def _get_or_create_folder_path(self, path):
        slug = self._tenant_slug or 'default'
        tenant_path = f'{slug}/{path}' if path and path != '.' else slug
        return super()._get_or_create_folder_path(tenant_path)


# ═══════════════════════════════════════════════════════════════════════════════
# 3-B. TENANT S3 STORAGE — Vultr Object Storage (S3 compatible)
# ═══════════════════════════════════════════════════════════════════════════════

@deconstructible
class TenantS3Storage(S3Storage):
    """
    Backend S3-compatible para Vultr Object Storage con prefijo automático por tenant.

    Mantiene el mismo aislamiento lógico que Drive:
      {empresa_slug}/resultados/...
      {empresa_slug}/expedientes/...
      {empresa_slug}/logos/...
    """

    default_acl = None
    file_overwrite = False

    def __init__(self, tenant_slug: str = '', **kwargs):
        super().__init__(**kwargs)
        self._tenant_slug = tenant_slug or _get_thread_tenant_slug()

    def _normalizar_nombre_tenant(self, name: str) -> str:
        return _insertar_tenant_en_ruta(name)

    def _save(self, name, content):
        return super()._save(self._normalizar_nombre_tenant(name), content)

    def get_available_name(self, name, max_length=None):
        return super().get_available_name(self._normalizar_nombre_tenant(name), max_length=max_length)


# ═══════════════════════════════════════════════════════════════════════════════
# 4. HELPERS — Thread-local, cache de sync, encolado de tasks
# ═══════════════════════════════════════════════════════════════════════════════

_tenant_context = threading.local()

SYNC_CACHE_PREFIX = 'drive_sync:'
SYNC_CACHE_TTL = 60 * 60 * 24 * 90  # 90 días


def set_tenant_context(empresa_slug: str):
    """Establece el tenant activo para el thread actual (llamar desde middleware)."""
    _tenant_context.empresa_slug = empresa_slug


def _get_thread_tenant_slug() -> str:
    return getattr(_tenant_context, 'empresa_slug', 'default') or 'default'


def _insertar_tenant_en_ruta(name: str) -> str:
    """
    Inserta el slug del tenant al inicio de la ruta si no está ya presente.
    Ejemplo: 'resultados/2026/archivo.pdf' → 'prislab/resultados/2026/archivo.pdf'
    """
    slug = _get_thread_tenant_slug()
    if name.startswith(f'{slug}/'):
        return name
    return f'{slug}/{name}'


def _encolar_sync_drive(nombre: str):
    """
    Compatibilidad histórica. Drive fue retirado del flujo activo.
    """
    logger.debug('[Buffer] Sincronización Drive deshabilitada para %s', nombre)


def _sync_drive_threaded(nombre: str, tenant_slug: str):
    """Compatibilidad histórica. No realiza acción."""
    logger.debug('[Buffer/Thread] Sync Drive deshabilitado para %s (%s)', nombre, tenant_slug)


def _marcar_sincronizado(nombre: str, success: bool = True,
                         drive_url: str = ''):
    """Compatibilidad histórica. Drive ya no usa cache de sincronización."""
    return None


def _esta_sincronizado_en_drive(nombre: str) -> bool:
    """Compatibilidad histórica. Siempre False porque Drive está desactivado."""
    return False


def _obtener_url_drive(nombre: str) -> str:
    """Compatibilidad histórica. Google Drive ya no entrega URL."""
    return ''


def get_tenant_storage():
    """Callable para usar como `storage=` en modelos de forma lazy."""
    from django.core.files.storage import default_storage
    if getattr(settings, 'VULTR_OBJECT_STORAGE_ENABLED', False):
        return TenantS3Storage(tenant_slug=_get_thread_tenant_slug())
    return default_storage
