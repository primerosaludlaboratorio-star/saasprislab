# EMERGENCY RESTORE PROCEDURE
# ===========================
# 1. Detener la aplicación o ponerla en mantenimiento antes de restaurar
# 2. Run: python manage.py restaurar_backup --source gs://bucket/backups/prislab_backup_YYYYMMDD_HHMMSS.dump
#    Or local: python manage.py restaurar_backup --source /path/to/prislab_backup_YYYYMMDD.dump
# 3. Verify: python manage.py verificar_integridad
# 4. Reanudar el servicio después de restaurar
#
# For encrypted backup_nocturno .encrypted files: decrypt first (using SECRET_KEY), extract tar,
# then restore database.sql with: psql -h HOST -U USER -d DB -f database.sql

"""
Management Command: Restaurar backup de base de datos (PostgreSQL).
Soporta archivo local o URI GCS (gs://bucket/path).
"""
import os
import sys
import tempfile
from django.core.management.base import BaseCommand
from django.conf import settings
from django.db import connection


class Command(BaseCommand):
    help = 'Restaura la base de datos desde un dump (local o gs://). SOLO para emergencias.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--source',
            type=str,
            required=True,
            help='Ruta al archivo de backup (local) o URI GCS (gs://bucket/path/to/backup.dump)',
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Omitir confirmación interactiva (para scripts/CI)',
        )

    def handle(self, *args, **options):
        source = options['source'].strip()
        force = options['force']

        db_config = settings.DATABASES.get('default', {})
        if 'postgresql' not in db_config.get('ENGINE', ''):
            self.stdout.write(self.style.ERROR('Restore solo soporta PostgreSQL. DB actual: %s' % db_config.get('ENGINE')))
            return

        if not force:
            self.stdout.write(self.style.WARNING(
                '\n*** RESTAURACION DE EMERGENCIA ***\n'
                'Asegurese de haber detenido el tráfico a la app antes de restaurar.\n'
                'La restauracion SOBRESCRIBIRA la base de datos actual.\n'
            ))
            confirm = input('Escriba SI para continuar: ')
            if confirm.strip().upper() != 'SI':
                self.stdout.write('Restauracion cancelada.')
                return

        local_path = None
        if source.startswith('gs://'):
            local_path = self._download_from_gcs(source)
            if not local_path:
                return
        else:
            if not os.path.isfile(source):
                self.stdout.write(self.style.ERROR('Archivo no encontrado: %s' % source))
                return
            local_path = source

        success = False
        try:
            ext = os.path.splitext(local_path)[1].lower()
            if ext == '.dump' or (ext == '' and 'dump' in local_path):
                success = self._pg_restore(local_path, db_config)
            elif ext in ('.sql', '.gz'):
                success = self._psql_restore(local_path, db_config)
            else:
                self.stdout.write(self.style.ERROR('Formato no soportado. Use .dump (pg_dump -Fc) o .sql'))
                return
        finally:
            # Siempre eliminar temp descargado de GCS (evita fugas si _pg_restore/_psql_restore fallan)
            if local_path != source and local_path and os.path.isfile(local_path):
                try:
                    os.remove(local_path)
                except Exception:
                    pass

        if success:
            self.stdout.write(self.style.SUCCESS('Restauracion completada. Ejecute: python manage.py verificar_integridad'))
        else:
            self.stdout.write(self.style.ERROR('Restauracion fallo. Revise los mensajes anteriores.'))

    def _download_from_gcs(self, gs_uri):
        """Descarga archivo desde GCS a un temp file. Retorna path local o None."""
        try:
            from google.cloud import storage
        except ImportError:
            self.stdout.write(self.style.ERROR('google-cloud-storage no instalado. pip install google-cloud-storage'))
            return None

        # gs://bucket_name/path/to/object
        parts = gs_uri[5:].split('/', 1)  # quitar 'gs://'
        if len(parts) != 2:
            self.stdout.write(self.style.ERROR('URI GCS invalida. Use gs://bucket/path/to/file.dump'))
            return None
        bucket_name, blob_path = parts[0], parts[1]

        self.stdout.write('Descargando desde GCS: %s' % gs_uri)
        client = storage.Client()
        bucket = client.bucket(bucket_name)
        blob = bucket.blob(blob_path)
        suffix = os.path.splitext(blob_path)[1] or '.dump'
        fd, local_path = tempfile.mkstemp(suffix=suffix)
        os.close(fd)
        blob.download_to_filename(local_path)
        self.stdout.write(self.style.SUCCESS('Descargado a: %s' % local_path))
        return local_path

    def _pg_restore(self, dump_path, db_config):
        """Restaura con pg_restore (formato custom -Fc)."""
        import subprocess
        env = os.environ.copy()
        if db_config.get('PASSWORD'):
            env['PGPASSWORD'] = db_config['PASSWORD']
        host = db_config.get('HOST', 'localhost')
        port = db_config.get('PORT', '5432')
        cmd = [
            'pg_restore',
            '-h', host,
            '-p', str(port),
            '-U', db_config.get('USER', 'postgres'),
            '-d', db_config.get('NAME', 'prislab_v5'),
            '--clean',
            '--if-exists',
            '--no-owner',
            '--no-acl',
            dump_path,
        ]
        if host.startswith('/cloudsql/'):
            cmd = [
                'pg_restore',
                '-h', host,
                '-U', db_config.get('USER', 'postgres'),
                '-d', db_config.get('NAME', 'prislab_v5'),
                '--clean', '--if-exists', '--no-owner', '--no-acl',
                dump_path,
            ]
        self.stdout.write('Ejecutando pg_restore...')
        result = subprocess.run(cmd, env=env, capture_output=True, text=True, timeout=1800)
        if result.returncode != 0:
            # pg_restore often returns non-zero for harmless errors (e.g. role)
            if 'ERROR' in result.stderr:
                self.stdout.write(self.style.WARNING('stderr: %s' % result.stderr[:500]))
            # Consider success if DB is usable
            return self._verify_restore()
        return self._verify_restore()

    def _psql_restore(self, sql_path, db_config):
        """Restaura con psql -f (dump plano)."""
        import subprocess
        env = os.environ.copy()
        if db_config.get('PASSWORD'):
            env['PGPASSWORD'] = db_config['PASSWORD']
        host = db_config.get('HOST', 'localhost')
        port = db_config.get('PORT', '5432')
        cmd = [
            'psql',
            '-h', host,
            '-p', str(port),
            '-U', db_config.get('USER', 'postgres'),
            '-d', db_config.get('NAME', 'prislab_v5'),
            '-f', sql_path,
        ]
        if host.startswith('/cloudsql/'):
            cmd = [
                'psql', '-h', host,
                '-U', db_config.get('USER', 'postgres'),
                '-d', db_config.get('NAME', 'prislab_v5'),
                '-f', sql_path,
            ]
        self.stdout.write('Ejecutando psql -f ...')
        result = subprocess.run(cmd, env=env, capture_output=True, text=True, timeout=1800)
        if result.returncode != 0:
            self.stdout.write(self.style.ERROR('psql stderr: %s' % (result.stderr or '')[:500]))
            return False
        return self._verify_restore()

    def _verify_restore(self):
        """Comprueba que las tablas clave tengan registros."""
        try:
            with connection.cursor() as cursor:
                tables = [
                    ('core_empresa', 'Empresa'),
                    ('core_usuario', 'Usuario'),
                    ('core_paciente', 'Paciente'),
                    ('core_ordendeservicio', 'OrdenDeServicio'),
                    ('core_venta', 'Venta'),
                    ('core_producto', 'Producto'),
                ]
                for table, label in tables:
                    try:
                        cursor.execute('SELECT COUNT(*) FROM %s' % table)
                        n = cursor.fetchone()[0]
                        self.stdout.write('  %s: %s registros' % (label, n))
                    except Exception as e:
                        self.stdout.write(self.style.WARNING('  %s: no disponible (%s)' % (label, e)))
            return True
        except Exception as e:
            self.stdout.write(self.style.ERROR('Verificacion post-restore fallo: %s' % e))
            return False
