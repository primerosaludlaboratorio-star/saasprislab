"""
Prueba de restauración en seco: descifra un .encrypted de backup_nocturno y valida que el tar.gz interno sea legible.
No modifica la base de datos ni escribe fuera de un directorio temporal.

  python manage.py verificar_backup_cifrado --ruta media/backups/archivo.encrypted
"""
import io
import os
import sys
import tarfile

from django.core.management.base import BaseCommand
from django.conf import settings

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.backends import default_backend
import base64


def _clave_fernet():
    password = settings.SECRET_KEY.encode('utf-8')
    salt = b'prislab_backup_salt_2025'
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100000,
        backend=default_backend(),
    )
    return Fernet(base64.urlsafe_b64encode(kdf.derive(password)))


class Command(BaseCommand):
    help = 'Verifica integridad de backup .encrypted (descifrado + tar.gz legible).'

    def add_arguments(self, parser):
        parser.add_argument('--ruta', type=str, required=True, help='Ruta al archivo .encrypted')

    def handle(self, *args, **options):
        ruta = options['ruta'].strip()
        if not os.path.isfile(ruta):
            self.stdout.write(self.style.ERROR(f'Archivo no encontrado: {ruta}'))
            sys.exit(1)
        fernet = _clave_fernet()
        with open(ruta, 'rb') as f:
            cifrado = f.read()
        try:
            plano = fernet.decrypt(cifrado)
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Descifrado fallido (¿SECRET_KEY distinta?): {e}'))
            sys.exit(2)
        bio = io.BytesIO(plano)
        try:
            with tarfile.open(fileobj=bio, mode='r:gz') as tar:
                nombres = tar.getnames()
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'TAR inválido tras descifrar: {e}'))
            sys.exit(3)
        tiene_sql = any('database.sql' in n or n.endswith('database.sql') for n in nombres)
        self.stdout.write(self.style.SUCCESS(
            f'OK: descifrado válido, {len(nombres)} entradas en tar, database.sql={"sí" if tiene_sql else "no localizado"}'
        ))
