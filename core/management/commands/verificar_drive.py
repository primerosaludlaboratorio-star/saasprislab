"""Comando legado deshabilitado. Drive fue retirado del sistema."""

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Comando legado deshabilitado. Google Drive no está activo.'

    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING(
            'verificar_drive deshabilitado: Google Drive fue retirado del sistema.'
        ))
