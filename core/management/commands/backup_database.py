"""
Volcado PostgreSQL (pg_dump) → cifrado Fernet → almacenamiento seguro + huella WORM.

Requisitos:
  - ENGINE postgresql y pg_dump en PATH
  - FERNET_KEY (misma que producción)
  - Ruta local o credenciales de archivo si se integra con almacenamiento externo

Uso:
  python manage.py backup_database
  python manage.py backup_database --prefix prislab-dr/manual
"""
from __future__ import annotations

import hashlib
import os
import subprocess
import tempfile

from cryptography.fernet import Fernet
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from core.models import BackupInmutableLog


class Command(BaseCommand):
    help = 'pg_dump de PostgreSQL, cifrado con FERNET_KEY, subida a GCS y registro BackupInmutableLog (WORM).'

    def add_arguments(self, parser):
        parser.add_argument(
            '--prefix',
            type=str,
            default='pgdump',
            help='Prefijo de objeto dentro del bucket (default: pgdump)',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Solo ejecuta pg_dump y hash; no cifra ni sube (útil en diagnóstico)',
        )

    def handle(self, *args, **options):
        db = settings.DATABASES['default']
        engine = db.get('ENGINE', '')
        if 'postgresql' not in engine:
            raise CommandError(
                f'backup_database solo soporta PostgreSQL (ENGINE actual: {engine}). '
                'Use SQLite u otro motor solo para desarrollo sin este comando.'
            )

        fernet_raw = getattr(settings, 'FERNET_KEY', None) or os.environ.get('FERNET_KEY')
        if not fernet_raw:
            raise CommandError('FERNET_KEY no configurada: obligatoria para cifrar el dump.')

        try:
            fernet = Fernet(fernet_raw.encode() if isinstance(fernet_raw, str) else fernet_raw)
        except Exception as exc:
            raise CommandError(f'FERNET_KEY inválida: {exc}') from exc

        bucket = getattr(settings, 'GCS_BACKUP_BUCKET', '') or os.environ.get('GCS_BACKUP_BUCKET', '')
        if not options['dry_run'] and not bucket:
            raise CommandError(
                'Defina GCS_BACKUP_BUCKET en entorno o settings (bucket destino del volcado).'
            )

        db_name = db.get('NAME') or ''
        db_user = db.get('USER') or ''
        db_password = db.get('PASSWORD') or ''
        db_host = db.get('HOST') or 'localhost'
        db_port = db.get('PORT') or ''

        ts = timezone.now().strftime('%Y%m%d_%H%M%S')
        base_name = f'prislab_{db_name}_{ts}.sql'
        enc_name = base_name + '.fernet'

        env = os.environ.copy()
        if db_password:
            env['PGPASSWORD'] = str(db_password)

        self.stdout.write(self.style.NOTICE(f'Ejecutando pg_dump → {base_name} …'))

        with tempfile.TemporaryDirectory(prefix='prislab_pgdump_') as tmp:
            sql_path = os.path.join(tmp, base_name)
            enc_path = os.path.join(tmp, enc_name)

            cmd_pg = [
                'pg_dump',
                '-h', str(db_host),
                '-U', str(db_user),
                '-F', 'p',
                '--no-owner',
                '--no-acl',
                '-f', sql_path,
                str(db_name),
            ]
            if str(db_port).strip():
                cmd_pg.insert(3, '-p')
                cmd_pg.insert(4, str(db_port))

            try:
                subprocess.run(
                    cmd_pg,
                    env=env,
                    check=True,
                    capture_output=True,
                    text=True,
                )
            except FileNotFoundError as exc:
                raise CommandError(
                    'pg_dump no encontrado en PATH. Instale cliente PostgreSQL o use una imagen que lo incluya.'
                ) from exc
            except subprocess.CalledProcessError as exc:
                err = (exc.stderr or exc.stdout or '')[:2000]
                raise CommandError(f'pg_dump falló: {err}') from exc

            if not os.path.isfile(sql_path) or os.path.getsize(sql_path) == 0:
                raise CommandError('pg_dump no generó un archivo SQL válido.')

            with open(sql_path, 'rb') as f:
                plain = f.read()
            sha256 = hashlib.sha256(plain).hexdigest()

            self.stdout.write(self.style.SUCCESS(f'SHA-256 (pre-cifrado): {sha256}'))

            if options['dry_run']:
                self.stdout.write(self.style.WARNING('Dry-run: no se cifra ni sube.'))
                return

            token = fernet.encrypt(plain)
            with open(enc_path, 'wb') as f:
                f.write(token)

            prefix = (options['prefix'] or 'pgdump').strip('/').strip()
            date_part = timezone.now().strftime('%Y/%m/%d')
            object_name = f'{prefix}/{date_part}/{enc_name}'

            try:
                from google.cloud import storage
            except ImportError as exc:
                raise CommandError('Instale google-cloud-storage para subir al bucket.') from exc

            try:
                client = storage.Client()
                b = client.bucket(bucket)
                blob = b.blob(object_name)
                blob.upload_from_filename(enc_path, content_type='application/octet-stream')
            except Exception as exc:
                raise CommandError(f'Error subiendo a GCS gs://{bucket}/{object_name}: {exc}') from exc

            gcs_uri = f'gs://{bucket}/{object_name}'
            self.stdout.write(self.style.SUCCESS(f'Subido: {gcs_uri}'))

            obj, created = BackupInmutableLog.objects.get_or_create(
                sha256_manifest=sha256,
                defaults={
                    'backup_registro': None,
                    'ruta_archivo': gcs_uri,
                },
            )
            if not created:
                self.stdout.write(
                    self.style.WARNING(
                        'Huella SHA-256 ya existía en BackupInmutableLog (idempotente por WORM).'
                    )
                )
            else:
                self.stdout.write(self.style.SUCCESS('Registrado en BackupInmutableLog (WORM).'))
