import csv
from decimal import Decimal, InvalidOperation
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from laboratorio.models import Equipo, MetodoEquipo
from lims.models import Analito


def volume(value):
    raw = (value or '').strip().lower().replace('μl', '').replace('µl', '').replace('ul', '').replace(',', '.')
    try:
        return Decimal(raw)
    except (InvalidOperation, ValueError):
        raise CommandError(f'Volumen inválido: {value!r}')


class Command(BaseCommand):
    help = 'Previsualiza o carga métodos INCCA validados; nunca activa métodos clínicos automáticamente.'

    def add_arguments(self, parser):
        parser.add_argument('--file', default='')
        parser.add_argument('--map', dest='mapping_file', default='')
        parser.add_argument('--empresa-id', type=int)
        parser.add_argument('--equipo-id', type=int)
        parser.add_argument('--apply', action='store_true', help='Escribe registros solo si todos los mapeos están CONFIRMADO.')

    def handle(self, *args, **options):
        source_path = Path(options['file']) if options['file'] else Path(settings.BASE_DIR) / 'datos_lims' / 'INCCA_metodos_fuente.csv'
        mapping_path = Path(options['mapping_file']) if options['mapping_file'] else Path(settings.BASE_DIR) / 'datos_lims' / 'INCCA_mapeo_catalogo.csv'
        if not source_path.exists() or not mapping_path.exists():
            raise CommandError('No se encontraron la fuente de métodos y/o el mapa de catálogo.')

        with source_path.open(encoding='utf-8-sig', newline='') as fh:
            source_rows = {row['metodo_incca']: row for row in csv.DictReader(fh)}
        with mapping_path.open(encoding='utf-8-sig', newline='') as fh:
            mapping_rows = list(csv.DictReader(fh))

        unresolved = [row['metodo_incca'] for row in mapping_rows if row.get('estado_mapeo') != 'CONFIRMADO' or not row.get('codigo_candidato')]
        if unresolved:
            self.stdout.write(self.style.WARNING(
                f'{len(unresolved)} método(s) requieren validación: {", ".join(unresolved)}'
            ))
        if not options['apply']:
            self.stdout.write(f'Simulación: {len(source_rows)} método(s) fuente, {len(mapping_rows) - len(unresolved)} mapeo(s) confirmado(s).')
            self.stdout.write('No se modificó la base de datos.')
            return
        if unresolved:
            raise CommandError('Carga bloqueada: todos los mapeos deben estar CONFIRMADO.')
        if not options.get('empresa_id') or not options.get('equipo_id'):
            raise CommandError('--empresa-id y --equipo-id son obligatorios con --apply.')

        empresa_id = options['empresa_id']
        equipo = Equipo.objects.get(pk=options['equipo_id'])
        with transaction.atomic():
            for mapping in mapping_rows:
                source = source_rows.get(mapping['metodo_incca'])
                if not source:
                    raise CommandError(f'Método ausente en fuente: {mapping["metodo_incca"]}')
                analito = Analito.objects.get(empresa_id=empresa_id, codigo=mapping['codigo_candidato'])
                MetodoEquipo.objects.update_or_create(
                    empresa_id=empresa_id,
                    equipo=equipo,
                    nombre_metodo_equipo=source['metodo_incca'],
                    defaults={
                        'analito': analito,
                        'codigo_metodo_equipo': mapping['codigo_candidato'],
                        'volumen_muestra': volume(source['volumen_muestra']),
                        'volumen_r1': volume(source['volumen_r1']),
                        'volumen_r2': volume(source['volumen_r2']),
                        'fuente_documental': source['fuente'],
                        'estado_validacion': 'PENDIENTE_VALIDACION',
                        'activo': False,
                    },
                )
        self.stdout.write(self.style.SUCCESS('Métodos INCCA cargados como PENDIENTE_VALIDACION e inactivos.'))
