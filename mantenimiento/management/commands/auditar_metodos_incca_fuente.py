import csv
import re
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError


REQUIRED_COLUMNS = {
    'metodo_incca', 'analito_prueba', 'codigo_catalogo', 'volumen_muestra',
    'volumen_r1', 'volumen_r2', 'equipo', 'fabricante', 'fuente',
    'estado_validacion',
}
VOLUME_RE = re.compile(r'^\d+(?:[.,]\d+)?(?:μl|µl|ul)$', re.IGNORECASE)


class Command(BaseCommand):
    help = 'Audita la fuente estructurada de métodos y consumos del INCCA sin modificar datos.'

    def add_arguments(self, parser):
        parser.add_argument('--file', default='', help='Ruta alternativa al CSV fuente.')

    def handle(self, *args, **options):
        path = Path(options['file']) if options['file'] else Path(settings.BASE_DIR) / 'datos_lims' / 'INCCA_metodos_fuente.csv'
        if not path.exists():
            raise CommandError(f'No existe la fuente INCCA: {path}')

        with path.open('r', encoding='utf-8-sig', newline='') as fh:
            reader = csv.DictReader(fh)
            columns = set(reader.fieldnames or [])
            missing = REQUIRED_COLUMNS - columns
            if missing:
                raise CommandError(f'Columnas faltantes: {", ".join(sorted(missing))}')
            rows = list(reader)

        errors = []
        methods = set()
        for line, row in enumerate(rows, start=2):
            method = (row['metodo_incca'] or '').strip()
            if not method:
                errors.append(f'fila {line}: metodo_incca vacío')
            elif method in methods:
                errors.append(f'fila {line}: método duplicado: {method}')
            methods.add(method)

            for field in ('analito_prueba', 'equipo', 'fabricante', 'fuente', 'estado_validacion'):
                if not (row[field] or '').strip():
                    errors.append(f'fila {line}: {field} vacío')
            for field in ('volumen_muestra', 'volumen_r1', 'volumen_r2'):
                value = (row[field] or '').strip()
                if not VOLUME_RE.fullmatch(value):
                    errors.append(f'fila {line}: {field} inválido: {value!r}')

        if errors:
            for error in errors:
                self.stderr.write(self.style.ERROR(error))
            raise CommandError(f'Fuente INCCA inválida: {len(errors)} error(es)')

        self.stdout.write(self.style.SUCCESS(
            f'Fuente INCCA válida: {len(rows)} métodos, nombres únicos y volúmenes estructurados.'
        ))
        self.stdout.write('Estado actual: PENDIENTE_VALIDACION; no se modificó la base de datos.')
