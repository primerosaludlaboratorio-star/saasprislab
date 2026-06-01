"""
Auditoría rápida: detecta ResultadoParametro aún ligados al analito placeholder core.0058.

Cumplimiento ISO / preflight: si existen huérfanos, corregir con remap_placeholder_resultados
tras ensamblar_lims_v75. Exit 1 con --fail si hay filas (útil en CI).
"""
import sys

from django.core.management.base import BaseCommand

PLACEHOLDER_CODIGO = '__PRISLAB_MIG_0058__'


class Command(BaseCommand):
    help = f'Lista ResultadoParametro con analito {PLACEHOLDER_CODIGO!r} (migración 0058).'

    def add_arguments(self, parser):
        parser.add_argument(
            '--fail',
            action='store_true',
            help='Salir con código 1 si existe al menos una fila huérfana.',
        )

    def handle(self, *args, **options):
        from core.models import ResultadoParametro
        from lims.models import Analito

        ph = Analito.objects.filter(codigo=PLACEHOLDER_CODIGO).only('pk').first()
        if not ph:
            self.stdout.write(self.style.SUCCESS('No existe analito placeholder; catálogo limpio.'))
            return

        n = ResultadoParametro.objects.filter(analito_id=ph.pk).count()
        if n == 0:
            self.stdout.write(self.style.SUCCESS('Sin ResultadoParametro en placeholder 0058.'))
            return

        self.stdout.write(
            self.style.WARNING(
                f'⚠ Hay {n} resultado(s) ligados al placeholder {PLACEHOLDER_CODIGO!r}. '
                'Ejecute: python manage.py ensamblar_lims_v75 && '
                'python manage.py remap_placeholder_resultados --dry-run'
            )
        )
        if options['fail']:
            sys.exit(1)
