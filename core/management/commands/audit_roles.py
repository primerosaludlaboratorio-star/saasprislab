"""
Verifica que existan grupos críticos de blindaje (creación manual en admin o fixture).
Uso: python manage.py audit_roles
      python manage.py audit_roles --strict  → exit 1 si falta alguno
"""
import sys

from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group


GRUPOS_RECOMENDADOS = (
    'ADMIN_SISTEMA',
    'DIRECTOR_QC',
    'QUIMICO_RESPONSABLE',
)


class Command(BaseCommand):
    help = 'Audita grupos Django requeridos para políticas de blindaje.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--strict',
            action='store_true',
            help='Código de salida 1 si falta algún grupo recomendado',
        )

    def handle(self, *args, **options):
        strict = options['strict']
        existentes = set(Group.objects.filter(name__in=GRUPOS_RECOMENDADOS).values_list('name', flat=True))
        faltantes = [g for g in GRUPOS_RECOMENDADOS if g not in existentes]
        for g in GRUPOS_RECOMENDADOS:
            ok = g in existentes
            self.stdout.write(f'  [{"OK" if ok else "!!"}] {g}')
        if faltantes:
            self.stdout.write(self.style.WARNING(
                f'Faltan grupos: {", ".join(faltantes)}. Créelos en Admin → Grupos o vía migración de datos.'
            ))
            if strict:
                sys.exit(1)
        else:
            self.stdout.write(self.style.SUCCESS('Todos los grupos recomendados existen.'))
