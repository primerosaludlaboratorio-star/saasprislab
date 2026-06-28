"""
core/fields.py
══════════════════════════════════════════════════════════════════════
Campo de base de datos con cifrado AES-256 (Fernet) compatible
con Django 5+. Reemplaza django-cryptography que no soporta Django 5.

Uso:
    from core.fields import EncryptedTextField
    contenido = EncryptedTextField(blank=True, default='')

La clave se lee de settings.FERNET_KEY o se deriva de SECRET_KEY.
══════════════════════════════════════════════════════════════════════
"""
import base64
import hashlib
import logging

from django.conf import settings
from django.db import models

logger = logging.getLogger(__name__)

try:
    from cryptography.fernet import Fernet, InvalidToken
    _FERNET_AVAILABLE = True
except ImportError:
    _FERNET_AVAILABLE = False
    logger.warning('cryptography no instalada — EncryptedTextField sin cifrado activo')


def _get_fernet():
    """Devuelve instancia Fernet usando FERNET_KEY o derivando de SECRET_KEY."""
    if not _FERNET_AVAILABLE:
        return None
    raw = getattr(settings, 'FERNET_KEY', None)
    if raw:
        key = raw.encode() if isinstance(raw, str) else raw
    else:
        # Derivar clave de 32 bytes desde SECRET_KEY
        digest = hashlib.sha256(settings.SECRET_KEY.encode()).digest()
        key = base64.urlsafe_b64encode(digest)
    return Fernet(key)


class EncryptedTextField(models.TextField):
    """
    TextField con cifrado transparente AES-256 (Fernet).
    - Los datos se cifran antes de escribir en DB.
    - Los datos se descifran al leer desde DB.
    - El campo DB almacena el token Fernet como texto base64.
    """

    def from_db_value(self, value, expression, connection):
        return self.decrypt(value)

    def to_python(self, value):
        return self.decrypt(value)

    def get_prep_value(self, value):
        if value is None:
            return value
        return self.encrypt(str(value))

    @staticmethod
    def encrypt(text: str) -> str:
        fernet = _get_fernet()
        if fernet is None:
            # En producción, esto no debería ocurrir nunca
            if not getattr(settings, 'DEBUG', True):
                logger.critical(
                    'SEGURIDAD CRÍTICA: EncryptedTextField intentando guardar texto plano '
                    'en producción. Instalar cryptography y configurar FERNET_KEY.'
                )
            return text
        try:
            return fernet.encrypt(text.encode('utf-8')).decode('utf-8')
        except Exception as exc:
            logger.error('Error cifrando campo: %s', exc, exc_info=True)
            return text

    @staticmethod
    def decrypt(text: str) -> str:
        if text is None:
            return text
        fernet = _get_fernet()
        if fernet is None:
            return text
        try:
            return fernet.decrypt(text.encode('utf-8')).decode('utf-8')
        except (InvalidToken, Exception):
            # Si no está cifrado (datos legacy), devuelve tal cual
            return text


def encrypt(field_instance):
    """
    Decorador de compatibilidad para imitar django_cryptography.fields.encrypt().
    Recibe un models.TextField y devuelve un EncryptedTextField con los mismos kwargs.
    """
    kwargs = {
        'blank': field_instance.blank,
        'null': field_instance.null,
        'default': field_instance.default if field_instance.default is not models.fields.NOT_PROVIDED else '',
        'help_text': field_instance.help_text,
    }
    return EncryptedTextField(**kwargs)
