"""
Prueba de restauración en seco: descifra un .encrypted de backup_nocturno y valida que el tar.gz interno sea legible.
No modifica la base de datos ni escribe fuera de un directorio temporal.

  python manage.py verificar_backup_cifrado --ruta media/backups/archivo.encrypted
"""
import io
import os
import sys
import tarfile

from django.core.management.base import BaseCommand, CommandError
from cryptography.fernet import Fernet
import logging


def _clave_fernet():
    raw_key = os.environ.get('PRISLAB_BACKUP_ENCRYPTION_KEY', '').strip()
    if not raw_key:
        raise CommandError('Configura PRISLAB_BACKUP_ENCRYPTION_KEY para verificar backups.')
    try:
        return Fernet(raw_key.encode('ascii'))
    except Exception as exc:
        raise CommandError('PRISLAB_BACKUP_ENCRYPTION_KEY no es una clave Fernet válida.') from exc


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
            logging.getLogger(__name__).exception("Error inesperado en handle (verificar_backup_cifrado.py)")
            self.stdout.write(self.style.ERROR(f'Descifrado fallido (¿clave de backup distinta?): {e}'))
            sys.exit(2)
        bio = io.BytesIO(plano)
        try:
            with tarfile.open(fileobj=bio, mode='r:gz') as tar:
                nombres = tar.getnames()
        except Exception as e:
            logging.getLogger(__name__).exception("Error inesperado en handle (verificar_backup_cifrado.py)")
            self.stdout.write(self.style.ERROR(f'TAR inválido tras descifrar: {e}'))
            sys.exit(3)
        tiene_sql = any('database.sql' in n or n.endswith('database.sql') for n in nombres)
        self.stdout.write(self.style.SUCCESS(
            f'OK: descifrado válido, {len(nombres)} entradas en tar, database.sql={"sí" if tiene_sql else "no localizado"}'
        ))
