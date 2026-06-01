"""
core/management/commands/backup_db_drive.py
════════════════════════════════════════════════════════════════════════════════
Comando: python manage.py backup_db_drive

Genera un dump comprimido de PostgreSQL y lo sube automáticamente a Google Drive
en la carpeta:  PRISLAB_Media/backups/YYYY/MM/YYYYMMDD_HHMMSS_prislab.sql.gz

Diseñado para ejecutarse desde Cloud Scheduler (CRON diario) o manualmente.
Registra el evento en core.BackupRegistro para trazabilidad.

Uso:
  python manage.py backup_db_drive
  python manage.py backup_db_drive --dry-run   (solo verifica conexión, no dumpa)
════════════════════════════════════════════════════════════════════════════════
"""
import os
import gzip
import subprocess
import tempfile
import logging
from datetime import datetime

from django.core.management.base import BaseCommand
from django.conf import settings
from django.utils import timezone

logger = logging.getLogger('core.backup')


class Command(BaseCommand):
    help = 'Backup de PostgreSQL a Google Drive. Ejecutar con Cloud Scheduler diariamente.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Verifica credenciales Drive y conexión DB sin hacer backup.',
        )
        parser.add_argument(
            '--folder-id',
            type=str,
            default='',
            help='ID de carpeta Drive destino (default: PRISLAB_Media/backups/).',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        custom_folder = options.get('folder_id', '')

        self.stdout.write(self.style.HTTP_INFO('═' * 60))
        self.stdout.write(self.style.HTTP_INFO('  PRISLAB — Backup DB → Google Drive'))
        self.stdout.write(self.style.HTTP_INFO('═' * 60))

        # ── 1. Verificar credenciales Drive ───────────────────────────────────
        self.stdout.write('Verificando credenciales Drive...')
        try:
            from config.drive_credentials import get_drive_credentials
            creds = get_drive_credentials()
            if not creds:
                self.stderr.write(self.style.ERROR('Sin credenciales Drive. Abortando.'))
                return
            self.stdout.write(self.style.SUCCESS('  ✓ Credenciales Drive OK'))
        except Exception as exc:
            self.stderr.write(self.style.ERROR(f'Error credenciales Drive: {exc}'))
            return

        folder_id = custom_folder or getattr(settings, 'GOOGLE_DRIVE_FOLDER_ID', '')
        if not folder_id:
            self.stderr.write(self.style.ERROR('GOOGLE_DRIVE_FOLDER_ID no configurado.'))
            return

        if dry_run:
            self.stdout.write(self.style.SUCCESS('--dry-run: verificación completada. Sin backup.'))
            return

        # ── 2. Obtener parámetros de DB ───────────────────────────────────────
        db_conf = settings.DATABASES.get('default', {})
        db_name = db_conf.get('NAME', '')
        db_user = db_conf.get('USER', '')
        db_pass = db_conf.get('PASSWORD', '')
        db_host = db_conf.get('HOST', '127.0.0.1')
        db_port = str(db_conf.get('PORT', '5432'))

        if not db_name:
            self.stderr.write(self.style.ERROR('DB NAME no encontrado en settings.'))
            return

        # ── 3. Generar dump comprimido ─────────────────────────────────────────
        timestamp = timezone.localtime(timezone.now()).strftime('%Y%m%d_%H%M%S')
        year_month = timezone.localtime(timezone.now()).strftime('%Y/%m')
        filename = f'{timestamp}_prislab.sql.gz'
        drive_path = f'backups/{year_month}/{filename}'

        self.stdout.write(f'Generando dump: {filename}')

        env = os.environ.copy()
        if db_pass:
            env['PGPASSWORD'] = db_pass

        pg_dump_cmd = [
            'pg_dump',
            '-h', db_host,
            '-p', db_port,
            '-U', db_user,
            '-Fp',           # formato plano (legible y restaurable)
            '--no-password',
            db_name,
        ]

        with tempfile.NamedTemporaryFile(suffix='.sql.gz', delete=False) as tmp_file:
            tmp_path = tmp_file.name

        try:
            # pg_dump → gzip en memoria
            result = subprocess.run(
                pg_dump_cmd,
                env=env,
                capture_output=True,
                timeout=300,
            )
            if result.returncode != 0:
                err = result.stderr.decode('utf-8', errors='replace')[:500]
                self.stderr.write(self.style.ERROR(f'pg_dump falló: {err}'))
                self._registrar_backup(False, filename, 0, f'pg_dump error: {err}')
                return

            sql_bytes = result.stdout
            with gzip.open(tmp_path, 'wb') as gz_file:
                gz_file.write(sql_bytes)

            size_mb = os.path.getsize(tmp_path) / (1024 * 1024)
            self.stdout.write(f'  Dump generado: {size_mb:.2f} MB')

            # ── 4. Subir a Drive ─────────────────────────────────────────────
            self.stdout.write(f'Subiendo a Drive: {drive_path}')
            from config.storage_backends import GoogleDriveStorage
            storage = GoogleDriveStorage(credentials=creds, folder_id=folder_id)

            with open(tmp_path, 'rb') as f:
                from django.core.files.base import File
                storage._save(drive_path, File(f))

            self.stdout.write(self.style.SUCCESS(f'  ✓ Backup subido: {drive_path} ({size_mb:.2f} MB)'))
            self._registrar_backup(True, filename, size_mb, '')

        except subprocess.TimeoutExpired:
            self.stderr.write(self.style.ERROR('pg_dump: timeout (300s). DB muy grande?'))
            self._registrar_backup(False, filename, 0, 'Timeout en pg_dump')
        except Exception as exc:
            self.stderr.write(self.style.ERROR(f'Error al subir backup: {exc}'))
            logger.error(f'backup_db_drive error: {exc}', exc_info=True)
            self._registrar_backup(False, filename, 0, str(exc)[:500])
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)

    def _registrar_backup(self, exitoso: bool, nombre: str, tamano_mb: float, error: str):
        """Registra el resultado en core.BackupRegistro para trazabilidad."""
        try:
            from core.models import BackupRegistro
            BackupRegistro.objects.create(
                ruta_completa=f'backups/{nombre}',
                tamanio_mb=round(tamano_mb, 2) if tamano_mb else 0,
                archivado_en_drive=exitoso,
                drive_error=error[:500] if error else None,
                estado='COMPLETADO' if exitoso else 'FALLIDO',
                tipo_backup='DIARIO',
                encriptado_aes256=False,
            )
        except Exception as exc:
            logger.warning(f'No se pudo registrar BackupRegistro: {exc}')
