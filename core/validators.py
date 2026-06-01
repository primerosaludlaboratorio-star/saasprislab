"""
CICLO 10: File upload security validators.
Validates extension, size, content-type (HTTP header), and REAL file content (magic bytes).
Blocks dangerous file types even when renamed (e.g. .exe → .jpg).

Also: validate_fecha_nacimiento_razonable for Paciente.fecha_nacimiento (1900–hoy).
"""
import os
from datetime import date
from django.core.exceptions import ValidationError

ALLOWED_EXTENSIONS = {
    'image': ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg'],
    'document': ['.pdf', '.doc', '.docx', '.xls', '.xlsx', '.csv', '.txt'],
    'lab_result': ['.pdf', '.jpg', '.jpeg', '.png'],
    'audio': ['.webm', '.mp3', '.wav', '.ogg', '.m4a', '.opus'],
    'archive': ['.zip', '.tar', '.gz'],
}

BLOCKED_EXTENSIONS = [
    '.exe', '.bat', '.cmd', '.sh', '.py', '.php', '.js', '.html', '.htm',
    '.vbs', '.ps1', '.msi', '.dll', '.com', '.scr', '.jar', '.jsp', '.asp',
    '.aspx', '.cgi', '.pl', '.rb', '.htaccess',
]

# Magic bytes (first bytes of file) for safe types. Checked after dangerous.
# Keys are byte prefixes; value is MIME for reference.
MAGIC_BYTES = {
    b'\xff\xd8\xff': 'image/jpeg',           # JPEG
    b'\x89PNG\r\n\x1a\n': 'image/png',       # PNG
    b'GIF87a': 'image/gif',                  # GIF87
    b'GIF89a': 'image/gif',                  # GIF89
    b'%PDF': 'application/pdf',              # PDF
    b'PK\x03\x04': 'application/zip',        # ZIP/DOCX/XLSX
    b'\xd0\xcf\x11\xe0': 'application/msoffice',  # DOC/XLS (OLE2)
}
# Dangerous magic bytes — REJECT immediately regardless of extension.
DANGEROUS_MAGIC = {
    b'MZ': 'Windows executable (PE/EXE/DLL)',
    b'\x7fELF': 'Linux executable (ELF)',
    b'#!': 'Script (shell/python/perl)',
    b'<?php': 'PHP script',
    b'<?xml': 'XML (possible XSS/script)',
    b'<script': 'JavaScript/HTML injection',
    b'<html': 'HTML file',
    b'<!DOCTYPE': 'HTML file',
}

# Content-Type (HTTP header) whitelist — spoofable but adds a layer.
ALLOWED_CONTENT_TYPES = {
    'image': ('image/jpeg', 'image/png', 'image/gif', 'image/webp', 'image/svg+xml', 'image/x-icon'),
    'document': (
        'application/pdf', 'application/msword', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        'application/vnd.ms-excel', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        'text/plain', 'text/csv', 'application/csv',
    ),
    'lab_result': ('application/pdf', 'image/jpeg', 'image/png'),
    'audio': ('audio/webm', 'audio/mpeg', 'audio/wav', 'audio/ogg', 'audio/x-m4a', 'audio/opus', 'application/ogg'),
    'archive': ('application/zip', 'application/x-tar', 'application/gzip', 'application/x-gzip'),
}

# Content-Type values that must NEVER be accepted.
BLOCKED_CONTENT_TYPES = (
    'application/x-executable', 'application/x-msdownload', 'application/x-msdos-program',
    'application/vnd.microsoft.portable-executable',
    'text/x-python', 'text/x-php', 'application/x-php', 'application/javascript',
    'text/javascript', 'application/x-javascript', 'text/html', 'application/xhtml+xml',
)

MAX_FILE_SIZE_MB = 20  # 20MB max

# How many bytes to read from upload for magic check
MAGIC_READ_LEN = 16

# Max filename length (Windows path limits, DB/storage sanity)
MAX_FILENAME_LENGTH = 200


def _check_file_content_safety(value, allowed_categories=None):
    """
    Validates file content via magic bytes. Rejects dangerous types and ensures
    images/documents match declared type. Resets file position after read.
    """
    if not hasattr(value, 'read') or not hasattr(value, 'seek'):
        return
    try:
        head = value.read(MAGIC_READ_LEN)
    except (OSError, IOError):
        raise ValidationError('No se pudo leer el contenido del archivo.')
    finally:
        try:
            value.seek(0)
        except (OSError, IOError):
            pass

    if not head:
        raise ValidationError('El archivo está vacío.')

    # 1) Reject dangerous magic first
    for magic, desc in DANGEROUS_MAGIC.items():
        if head[:len(magic)] == magic:
            raise ValidationError(f'Tipo de archivo no permitido: {desc}.')

    # 2) If we have category restriction, verify content matches allowed type
    if not allowed_categories:
        return

    # Build set of allowed MIME from categories
    allowed_mimes = set()
    for cat in allowed_categories:
        allowed_mimes.update(ALLOWED_CONTENT_TYPES.get(cat, ()))

    # Detect MIME from magic
    detected = None
    for magic, mime in MAGIC_BYTES.items():
        if head[:len(magic)] == magic:
            detected = mime
            break
    if not detected and head[:4] == b'RIFF' and len(head) >= 12 and head[8:12] == b'WEBP':
        detected = 'image/webp'

    if not detected:
        # SVG is text; allow if extension was already validated and content_type allowed
        return
    if allowed_mimes and detected not in allowed_mimes:
        raise ValidationError(
            f'El contenido del archivo no coincide con el tipo declarado (detectado: {detected}).'
        )


def _check_content_type(value, allowed_categories=None):
    """Validates Content-Type header (spoofable but adds a layer)."""
    content_type = getattr(value, 'content_type', None) or ''
    content_type = content_type.split(';')[0].strip().lower()

    for blocked in BLOCKED_CONTENT_TYPES:
        if content_type == blocked or content_type.startswith(blocked + '/'):
            raise ValidationError(f'Tipo de contenido no permitido: {content_type}.')

    if not allowed_categories or not content_type:
        return

    allowed = set()
    for cat in allowed_categories:
        allowed.update(ALLOWED_CONTENT_TYPES.get(cat, ()))
    if allowed and content_type not in allowed:
        raise ValidationError(
            f'Tipo de contenido no permitido: {content_type}. Permitidos: {", ".join(sorted(allowed))}'
        )


def validate_file_upload(value, allowed_categories=None):
    """
    Validates file extension, size, content-type, and real content (magic bytes).
    Use for FileField. For ImageField use validate_image_upload.
    """
    if not value:
        return
    name = getattr(value, 'name', None)
    if not name:
        return
    # CICLO 14: Evitar nombres muy largos (path > 260 en Windows)
    if len(name) > MAX_FILENAME_LENGTH:
        raise ValidationError(
            f'El nombre del archivo es demasiado largo (máx. {MAX_FILENAME_LENGTH} caracteres).'
        )
    ext = os.path.splitext(name)[1].lower()

    if ext in BLOCKED_EXTENSIONS:
        raise ValidationError(f'Tipo de archivo no permitido: {ext}')

    if allowed_categories:
        allowed = []
        for cat in allowed_categories:
            allowed.extend(ALLOWED_EXTENSIONS.get(cat, []))
        if ext not in allowed:
            raise ValidationError(
                f'Extensión {ext} no permitida. Permitidas: {", ".join(sorted(set(allowed)))}'
            )

    size = getattr(value, 'size', 0)
    if size > MAX_FILE_SIZE_MB * 1024 * 1024:
        size_mb = size // (1024 * 1024)
        raise ValidationError(
            f'Archivo demasiado grande ({size_mb}MB). Máximo: {MAX_FILE_SIZE_MB}MB'
        )

    _check_content_type(value, allowed_categories)
    _check_file_content_safety(value, allowed_categories)


def validate_image_upload(value):
    """Use for ImageField (extra layer: extension + content-type + magic bytes)."""
    return validate_file_upload(value, allowed_categories=['image'])


def validate_document_upload(value):
    """Use for FileField that accepts documents (PDF, Office, etc.)."""
    return validate_file_upload(value, allowed_categories=['document', 'lab_result'])


def validate_audio_upload(value):
    """Use for FileField that accepts audio (voice notes, transcriptions)."""
    return validate_file_upload(value, allowed_categories=['audio'])


def validate_backup_upload(value):
    """Use for FileField that accepts backup archives (.zip, .tar, .gz)."""
    return validate_file_upload(value, allowed_categories=['archive'])


# -----------------------------------------------------------------------------
# Fecha de nacimiento razonable (Paciente, citas, etc.)
# -----------------------------------------------------------------------------
FECHA_NACIMIENTO_MIN = date(1900, 1, 1)


def validate_fecha_nacimiento_razonable(value):
    """
    Valida que la fecha de nacimiento esté en un rango razonable (1900 hasta hoy).
    Evita fechas absurdas que generen edad negativa o > 125 años.
    """
    if value is None:
        return
    if not isinstance(value, date):
        raise ValidationError('La fecha de nacimiento debe ser una fecha válida.')
    if value < FECHA_NACIMIENTO_MIN:
        raise ValidationError(
            f'La fecha de nacimiento no puede ser anterior a {FECHA_NACIMIENTO_MIN.isoformat()}.'
        )
    hoy = date.today()
    if value > hoy:
        raise ValidationError(
            f'La fecha de nacimiento no puede ser futura (máximo hoy: {hoy.isoformat()}).'
        )
