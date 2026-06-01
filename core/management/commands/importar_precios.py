"""
Actualización masiva de precios (tarifas) para Estudios y Paquetes.

Lee tarifas.csv (encoding latin1, doble encabezado) y actualiza
Estudio.precio buscando por codigo o abreviatura.

Uso:
    python manage.py importar_precios
    python manage.py importar_precios --archivo tarifas.csv
"""
import csv
import os
from decimal import Decimal, InvalidOperation

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError


def _clean(val):
    if val is None:
        return ''
    s = str(val).strip()
    return '' if s.lower() in ('nan', 'none') else s


class Command(BaseCommand):
    help = 'Actualiza precios de Estudios/Paquetes desde tarifas.csv'

    def add_arguments(self, parser):
        parser.add_argument(
            '--archivo', type=str, default='tarifas.csv',
            help='Nombre del CSV (relativo a BASE_DIR)',
        )

    def handle(self, *args, **options):
        raise CommandError(
            "DEPRECATED: Este comando opera sobre el catálogo legacy. "
            "Usa 'importar_catalogo_lims' para LIMS v7.5."
        )
        ruta = os.path.join(settings.BASE_DIR, options['archivo'])
        if not os.path.isfile(ruta):
            self.stderr.write(self.style.ERROR(f'No se encontró: {ruta}'))
            return

        self.stdout.write(self.style.WARNING(f'Leyendo {ruta}'))

        # ── Leer CSV (latin1, saltar 2 líneas de encabezado) ──
        rows = []
        for enc in ('latin-1', 'utf-8-sig', 'cp1252'):
            try:
                with open(ruta, encoding=enc, newline='') as f:
                    reader = csv.reader(f)
                    # Buscar la fila de encabezado real ("Tipo,Código,...")
                    for line in reader:
                        if line and line[0].strip().lower() == 'tipo':
                            break
                    # Leer filas de datos
                    for line in reader:
                        if line and len(line) >= 5:
                            rows.append(line)
                break
            except (UnicodeDecodeError, UnicodeError):
                continue

        if not rows:
            self.stderr.write(self.style.ERROR('No se encontraron filas de datos'))
            return

        self.stdout.write(f'  {len(rows)} filas de tarifas encontradas')

        # ── Construir índice de estudios por código ──
        estudios_idx = {}
        for est in Estudio.objects.only('id', 'codigo', 'abreviatura', 'precio'):
            if est.codigo:
                estudios_idx[est.codigo.strip()] = est
            if est.abreviatura:
                estudios_idx[est.abreviatura.strip()] = est

        actualizados = 0
        sin_match = []

        for line in rows:
            tipo = _clean(line[0])
            codigo = _clean(line[1])
            abreviatura = _clean(line[2]) if len(line) > 2 else ''
            descripcion = _clean(line[3]) if len(line) > 3 else ''
            importe_raw = _clean(line[4]) if len(line) > 4 else ''

            if not codigo and not abreviatura:
                continue

            # Parsear precio
            precio = Decimal('0.00')
            if importe_raw:
                try:
                    limpio = importe_raw.replace(',', '').replace('$', '').strip()
                    if limpio:
                        precio = Decimal(limpio)
                except (InvalidOperation, ValueError):
                    precio = Decimal('0.00')

            if precio <= 0:
                continue  # No actualizar con precio 0

            # Buscar estudio: primero por código, luego por abreviatura
            estudio = estudios_idx.get(codigo) or estudios_idx.get(abreviatura)

            if estudio:
                if estudio.precio != precio:
                    estudio.precio = precio
                    try:
                        estudio.save(update_fields=['precio'])
                        actualizados += 1
                    except Exception as e:
                        self.stderr.write(f'  Error guardando {codigo}: {e}')
            else:
                sin_match.append(f'{tipo} | {codigo} | {abreviatura} | {descripcion} | ${importe_raw}')

        # ── Reporte ──
        self.stdout.write(self.style.SUCCESS(f'\nPrecios actualizados: {actualizados}'))

        if sin_match:
            self.stdout.write(self.style.WARNING(f'\nAdvertencias: {len(sin_match)} códigos sin match en BD:'))
            for item in sin_match[:30]:  # Mostrar máximo 30
                self.stdout.write(f'  {item}')
            if len(sin_match) > 30:
                self.stdout.write(f'  ... y {len(sin_match) - 30} más')
