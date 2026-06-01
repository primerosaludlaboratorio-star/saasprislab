"""
Management Command: Test de conexión a Google Drive
====================================================
Sube un archivo .txt de prueba y un PDF de verificación a la carpeta maestra.
Ejecutar: python manage.py test_drive_connection
"""
import os
from datetime import datetime
from io import BytesIO

from django.core.management.base import BaseCommand
from django.conf import settings
from django.core.files.base import ContentFile


class Command(BaseCommand):
    help = 'Prueba la conexión a Google Drive subiendo un archivo .txt y un PDF de verificación'

    def add_arguments(self, parser):
        parser.add_argument(
            '--solo-txt',
            action='store_true',
            help='Solo subir el archivo .txt de prueba (sin PDF)',
        )
        parser.add_argument(
            '--guardar-backup',
            action='store_true',
            help='Tras verificar, guardar backup de credenciales en carpeta _PRISLAB_CONFIG_BACKUP',
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE('\n=== TEST DE CONEXIÓN GOOGLE DRIVE ===\n'))

        if not getattr(settings, 'GOOGLE_DRIVE_CREDENTIALS', None):
            self.stdout.write(self.style.ERROR(
                'ERROR: No hay credenciales de Google Drive configuradas.\n'
                'Configure OAuth2 (GOOGLE_DRIVE_CLIENT_ID, CLIENT_SECRET, REFRESH_TOKEN) o Service Account.'
            ))
            return

        if not getattr(settings, 'GOOGLE_DRIVE_FOLDER_ID', None):
            self.stdout.write(self.style.ERROR(
                'ERROR: GOOGLE_DRIVE_FOLDER_ID no está configurado.'
            ))
            return

        from django.core.files.storage import default_storage
        storage = default_storage
        # Si el default no es Drive, instanciar explícitamente
        if not hasattr(storage, 'folder_id') and getattr(settings, 'GOOGLE_DRIVE_CREDENTIALS', None):
            try:
                from config.storage_backends import GoogleDriveStorage
                storage = GoogleDriveStorage()
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'ERROR: No se pudo obtener GoogleDriveStorage: {e}'))
                return

        # 1. Subir archivo .txt de prueba
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        txt_path = f'multimedia/test_conexion_{timestamp}.txt'
        txt_content = (
            f"PRISLAB V5 - Test de conexión Google Drive\n"
            f"Fecha: {datetime.now().isoformat()}\n"
            f"Si ves este archivo en la carpeta PRISLAB_Media/multimedia/, la conexión funciona.\n"
        )
        try:
            storage.save(txt_path, ContentFile(txt_content.encode('utf-8')))
            txt_url = storage.url(txt_path) if hasattr(storage, 'url') else '(guardado)'
            self.stdout.write(self.style.SUCCESS(f'  [OK] Archivo TXT subido: {txt_path}'))
            self.stdout.write(f'       URL: {txt_url}\n')
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'  [X] Error subiendo TXT: {e}'))
            return

        # 2. Subir PDF de verificación
        if not options.get('solo_txt'):
            pdf_path = f'resultados_pdf/PRUEBA_DRIVE_OK_{timestamp}.pdf'
            pdf_bytes = self._generar_pdf_verificacion()
            try:
                storage.save(pdf_path, ContentFile(pdf_bytes))
                pdf_url = storage.url(pdf_path) if hasattr(storage, 'url') else '(guardado)'
                self.stdout.write(self.style.SUCCESS(f'  [OK] PDF de verificación subido: {pdf_path}'))
                self.stdout.write(f'       URL: {pdf_url}\n')
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'  [X] Error subiendo PDF: {e}'))

        self.stdout.write(self.style.SUCCESS(
            '\n=== CONEXIÓN EXITOSA ===\n'
            'Revisa la carpeta PRISLAB_Media en Google Drive:\n'
            '  - multimedia/test_conexion_*.txt\n'
            '  - resultados_pdf/PRUEBA_DRIVE_OK_*.pdf\n'
        ))

        # Guardar backup de credenciales en carpeta especial (si se solicita)
        if options.get('guardar_backup'):
            self.stdout.write(self.style.NOTICE('\nGuardando backup de credenciales en _PRISLAB_CONFIG_BACKUP...'))
            try:
                from django.core.management import call_command
                call_command('guardar_backup_config_drive', '--sin-verificar')
                self.stdout.write(self.style.SUCCESS('Backup guardado correctamente.'))
            except Exception as e:
                self.stdout.write(self.style.WARNING(f'No se pudo guardar backup: {e}'))

    def _generar_pdf_verificacion(self):
        """Genera un PDF con el mensaje de verificación."""
        from reportlab.lib.pagesizes import letter
        from reportlab.pdfgen import canvas

        buffer = BytesIO()
        p = canvas.Canvas(buffer, pagesize=letter)
        width, height = letter

        p.setFont("Helvetica-Bold", 24)
        p.drawCentredString(width / 2, height - 150, "PRISLAB V5")
        p.setFont("Helvetica", 16)
        p.drawCentredString(width / 2, height - 200, "Test de almacenamiento Google Drive")
        p.setFont("Helvetica-Bold", 20)
        p.setFillColorRGB(0, 0.5, 0)
        p.drawCentredString(width / 2, height / 2, "Listo jefe ya funciona el almacenamiento")
        p.setFillColorRGB(0, 0, 0)
        p.setFont("Helvetica", 10)
        p.drawCentredString(width / 2, height - 300, f"Generado: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        p.showPage()
        p.save()
        buffer.seek(0)
        return buffer.getvalue()
