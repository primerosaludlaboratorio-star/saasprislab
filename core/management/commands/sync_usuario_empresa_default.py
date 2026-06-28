"""
Asigna empresa por defecto a usuarios con empresa_id NULL (rescate post blindaje).

  python manage.py sync_usuario_empresa_default
  python manage.py sync_usuario_empresa_default --dry-run
"""
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction

from core.utils.default_empresa import resolve_default_empresa_sistema

User = get_user_model()


class Command(BaseCommand):
    help = 'UPDATE masivo: usuarios sin empresa → empresa principal del sistema.'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true')

    def handle(self, *args, **options):
        dry = options['dry_run']
        de = resolve_default_empresa_sistema()
        if not de:
            self.stdout.write(self.style.ERROR('No hay Empresa activa para usar como default. Cree una o defina PRISLAB_DEFAULT_EMPRESA_ID.'))
            return

        nul = User.objects.filter(empresa__isnull=True).count()
        self.stdout.write(f'Empresa default: id={de.pk} ({de.nombre}) | usuarios sin empresa: {nul}')

        if dry:
            self.stdout.write(self.style.WARNING('[DRY-RUN] Sin cambios.'))
            return

        with transaction.atomic():
            updated = User.objects.filter(empresa__isnull=True).update(empresa_id=de.pk)

        self.stdout.write(self.style.SUCCESS(f'Usuarios actualizados: {updated}'))
