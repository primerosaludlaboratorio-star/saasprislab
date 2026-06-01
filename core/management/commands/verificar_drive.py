"""
core/management/commands/verificar_drive.py
════════════════════════════════════════════
Comando: python manage.py verificar_drive

Verifica la conexión a Google Drive y lista la carpeta raíz PRISLAB_Media.
Útil para confirmar que el storage está funcionando antes de un deploy.
"""
from django.core.management.base import BaseCommand
from django.conf import settings


class Command(BaseCommand):
    help = 'Verifica conexión a Google Drive y acceso a carpeta PRISLAB_Media.'

    def handle(self, *args, **options):
        self.stdout.write('\n📁  Verificación Google Drive Storage\n' + '─' * 40)

        # 1. Credenciales
        try:
            from config.drive_credentials import get_drive_credentials
            creds = get_drive_credentials()
            if not creds:
                self.stderr.write(self.style.ERROR('Sin credenciales. Configura GOOGLE_DRIVE_SERVICE_ACCOUNT_JSON o ADC.'))
                return
            self.stdout.write(self.style.SUCCESS('✓ Credenciales resueltas'))
        except Exception as exc:
            self.stderr.write(self.style.ERROR(f'Error credenciales: {exc}'))
            return

        # 2. Carpeta raíz
        folder_id = getattr(settings, 'GOOGLE_DRIVE_FOLDER_ID', '')
        if not folder_id:
            self.stderr.write(self.style.ERROR('GOOGLE_DRIVE_FOLDER_ID no configurado en settings.'))
            return
        self.stdout.write(f'✓ FOLDER_ID: {folder_id}')

        # 3. Listar contenido
        try:
            from googleapiclient.discovery import build
            service = build('drive', 'v3', credentials=creds)
            results = service.files().list(
                q=f"'{folder_id}' in parents and trashed=false",
                fields='files(id, name, mimeType, size)',
                pageSize=20,
            ).execute()
            files = results.get('files', [])
            self.stdout.write(f'\nContenido de PRISLAB_Media ({len(files)} elementos):')
            for f in files:
                tipo = '📁' if 'folder' in f['mimeType'] else '📄'
                size = f' ({int(f.get("size", 0)) // 1024} KB)' if 'size' in f else ''
                self.stdout.write(f'  {tipo} {f["name"]}{size}')
            self.stdout.write(self.style.SUCCESS('\n✅ Drive operativo. Storage listo para producción.'))
            self.stdout.write(f'   Drive activo en settings: {getattr(settings, "_DRIVE_STORAGE_ACTIVO", False)}')
        except Exception as exc:
            self.stderr.write(self.style.ERROR(f'Error listando Drive: {exc}'))
