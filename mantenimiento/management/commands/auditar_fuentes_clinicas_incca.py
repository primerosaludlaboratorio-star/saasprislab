import csv
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = 'Verifica que cada método INCCA tenga su inserto clínico trazable.'

    def add_arguments(self, parser):
        parser.add_argument('--strict', action='store_true', help='Falla si existe cualquier inserto faltante.')

    def handle(self, *args, **options):
        root = Path(settings.BASE_DIR) / 'docs' / 'manual' / 'fuentes' / 'incca'
        manifest = root / 'INCCA_METODOS_FUENTES_CLINICAS.csv'
        if not manifest.exists():
            raise CommandError(f'No existe el manifiesto: {manifest}')

        missing = []
        rows = list(csv.DictReader(manifest.open(encoding='utf-8-sig', newline='')))
        for row in rows:
            relative = (row.get('inserto_clinico') or '').strip()
            if not relative or not (root / relative).exists():
                missing.append(row.get('metodo_incca') or '<sin método>')

        self.stdout.write(f'Métodos auditados: {len(rows)}')
        self.stdout.write(f'Insertos disponibles: {len(rows) - len(missing)}')
        if missing:
            message = f'Insertos faltantes: {", ".join(missing)}'
            if options['strict']:
                raise CommandError(message)
            self.stdout.write(self.style.WARNING(message))
        else:
            self.stdout.write(self.style.SUCCESS('Todos los métodos tienen inserto clínico trazable.'))
