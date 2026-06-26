"""Comando legado deshabilitado. Drive fue retirado del sistema."""
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Comando legado deshabilitado. Drive ya no está activo.'

    def add_arguments(self, parser):
        return None

    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING('backup_db_drive está deshabilitado: Google Drive fue retirado del sistema.'))

    def _registrar_backup(self, exitoso: bool, nombre: str, tamano_mb: float, error: str):
        return None
