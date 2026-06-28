"""
Registra en BackupInmutableLog los BackupRegistro COMPLETADO que aún no tienen log WORM.
Útil si BACKUP_IMMUTABLE_LOG_AUTO no estuvo activo o para backfill.
"""
from django.core.management.base import BaseCommand

from core.models import BackupRegistro, BackupInmutableLog
from core.utils.backup_inmutable import append_backup_inmutable_log


class Command(BaseCommand):
    help = 'Añade filas BackupInmutableLog para backups completados con hash SHA-256.'

    def handle(self, *args, **options):
        qs = BackupRegistro.objects.filter(estado='COMPLETADO').exclude(
            hash_verificacion__isnull=True
        ).exclude(hash_verificacion='').order_by('id')
        n = 0
        for br in qs:
            h = (br.hash_verificacion or '').strip()
            if BackupInmutableLog.objects.filter(sha256_manifest=h).exists():
                continue
            append_backup_inmutable_log(br)
            n += 1
        self.stdout.write(self.style.SUCCESS(f'Backups revisados={qs.count()}, logs WORM nuevos={n}'))
