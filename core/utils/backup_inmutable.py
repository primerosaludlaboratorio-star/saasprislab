"""
Registro WORM de huellas de backup (post backup_nocturno).
"""
from django.db import IntegrityError

from core.models import BackupInmutableLog, BackupRegistro


def append_backup_inmutable_log(backup_registro: BackupRegistro) -> BackupInmutableLog | None:
    """
    Crea una fila de auditoría si el backup tiene hash. Idempotente por sha256 único.
    """
    h = (backup_registro.hash_verificacion or '').strip()
    if not h or len(h) != 64:
        return None
    ruta = (backup_registro.ruta_completa or '').strip()
    try:
        obj, created = BackupInmutableLog.objects.get_or_create(
            sha256_manifest=h,
            defaults={
                'backup_registro': backup_registro,
                'ruta_archivo': ruta,
            },
        )
        return obj
    except IntegrityError:
        return BackupInmutableLog.objects.filter(sha256_manifest=h).first()
