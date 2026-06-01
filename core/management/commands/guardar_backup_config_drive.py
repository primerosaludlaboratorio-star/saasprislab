"""
Management Command: Guardar backup de credenciales Drive en carpeta especial
=============================================================================
Cuando la configuración de Drive está correcta, guarda una copia de seguridad
de las credenciales OAuth en la carpeta _PRISLAB_CONFIG_BACKUP dentro del Drive.

Ejecutar: python manage.py guardar_backup_config_drive

Requisitos: Drive debe estar configurado y funcionando (OAuth2 o Service Account).
"""
import json
import os
from datetime import datetime

from django.core.management.base import BaseCommand
from django.conf import settings
from django.core.files.base import ContentFile


# Carpeta especial en Drive para backups de configuración (no tocar)
CARPETA_BACKUP = '_PRISLAB_CONFIG_BACKUP'


class Command(BaseCommand):
    help = 'Guarda backup de credenciales Drive en carpeta _PRISLAB_CONFIG_BACKUP'

    def add_arguments(self, parser):
        parser.add_argument(
            '--verificar-primero',
            action='store_true',
            default=True,
            help='Verificar conexión antes de guardar (default: True)',
        )
        parser.add_argument(
            '--sin-verificar',
            action='store_true',
            help='Guardar sin verificar conexión',
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE('\n=== GUARDAR BACKUP CONFIG DRIVE ===\n'))

        if not getattr(settings, 'GOOGLE_DRIVE_CREDENTIALS', None):
            self.stdout.write(self.style.ERROR(
                'ERROR: No hay credenciales de Google Drive configuradas.'
            ))
            return

        if not getattr(settings, 'GOOGLE_DRIVE_FOLDER_ID', None):
            self.stdout.write(self.style.ERROR('ERROR: GOOGLE_DRIVE_FOLDER_ID no configurado.'))
            return

        # Obtener storage
        from django.core.files.storage import default_storage
        storage = default_storage
        if not hasattr(storage, 'folder_id') and getattr(settings, 'GOOGLE_DRIVE_CREDENTIALS', None):
            try:
                from config.storage_backends import GoogleDriveStorage
                storage = GoogleDriveStorage()
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'ERROR: No se pudo obtener GoogleDriveStorage: {e}'))
                return

        # Verificar conexión (opcional)
        if not options.get('sin_verificar'):
            self.stdout.write('Verificando conexión a Drive...')
            try:
                test_path = f'{CARPETA_BACKUP}/_test_{datetime.now().strftime("%Y%m%d_%H%M%S")}.txt'
                storage.save(test_path, ContentFile(b'OK'))
                self.stdout.write(self.style.SUCCESS('  [OK] Conexión verificada'))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'  [X] Error de conexión: {e}'))
                return

        # Recopilar datos de backup (solo variables OAuth; no exponer Service Account)
        backup = {
            '_nota': 'Backup de configuración PRISLAB Drive. Archivo sensible. Mantener privado.',
            '_fecha': datetime.now().isoformat(),
            '_carpeta_drive': getattr(settings, 'GOOGLE_DRIVE_FOLDER_ID', ''),
            'GOOGLE_DRIVE_CLIENT_ID': os.environ.get('GOOGLE_DRIVE_CLIENT_ID', '').strip() or '(no configurado)',
            'GOOGLE_DRIVE_CLIENT_SECRET': os.environ.get('GOOGLE_DRIVE_CLIENT_SECRET', '').strip() or '(no configurado)',
            'GOOGLE_DRIVE_REFRESH_TOKEN': os.environ.get('GOOGLE_DRIVE_REFRESH_TOKEN', '').strip() or '(no configurado)',
            'GOOGLE_DRIVE_FOLDER_ID': os.environ.get('GOOGLE_DRIVE_FOLDER_ID', '').strip() or getattr(settings, 'GOOGLE_DRIVE_FOLDER_ID', ''),
        }

        # Si hay Service Account (fallback), indicar pero no guardar el JSON completo
        if not backup['GOOGLE_DRIVE_REFRESH_TOKEN'] or backup['GOOGLE_DRIVE_REFRESH_TOKEN'] == '(no configurado)':
            backup['_modo'] = 'Service Account (GOOGLE_DRIVE_CREDENTIALS_JSON o archivo)'
            backup['_nota_modo'] = 'Para OAuth2, configure las 3 variables y vuelva a ejecutar.'
        else:
            backup['_modo'] = 'OAuth2 (Drive personal 2 TB)'

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'credenciales_drive_{timestamp}.json'
        ruta = f'{CARPETA_BACKUP}/{filename}'

        try:
            contenido = json.dumps(backup, indent=2, ensure_ascii=False)
            storage.save(ruta, ContentFile(contenido.encode('utf-8')))
            url = storage.url(ruta) if hasattr(storage, 'url') else '(guardado)'
            self.stdout.write(self.style.SUCCESS(f'\n[OK] Backup guardado en Drive:'))
            self.stdout.write(f'     Carpeta: {CARPETA_BACKUP}/')
            self.stdout.write(f'     Archivo: {filename}')
            self.stdout.write(f'     URL: {url}')
            self.stdout.write(self.style.NOTICE(
                f'\nRevisa en Google Drive: PRISLAB_Media/{CARPETA_BACKUP}/\n'
            ))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'\n[X] Error guardando backup: {e}'))
