import csv
import os
from decimal import Decimal, InvalidOperation

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from laboratorio.models import PerfilLaboratorio


def _clean(val):
    if val is None:
        return ''
    s = str(val).strip()
    return '' if s.lower() in ('nan', 'none') else s


def _parse_price(raw):
    try:
        txt = _clean(raw).replace(',', '').replace('$', '')
        if not txt:
            return Decimal('0')
        return Decimal(txt)
    except (InvalidOperation, ValueError):
        return Decimal('0')


def _load_tarifas_map(ruta_csv):
    rows = []
    for enc in ('latin-1', 'utf-8-sig', 'cp1252', 'utf-8'):
        try:
            with open(ruta_csv, encoding=enc, newline='') as f:
                reader = csv.reader(f)
                for line in reader:
                    if line and _clean(line[0]).lower() == 'tipo':
                        break
                for line in reader:
                    if line and len(line) >= 5:
                        rows.append(line)
            break
        except (UnicodeDecodeError, UnicodeError):
            continue

    tarifas = {}
    for line in rows:
        codigo = _clean(line[1]).upper()
        abre = _clean(line[2]).upper() if len(line) > 2 else ''
        precio = _parse_price(line[4] if len(line) > 4 else '')
        if precio <= 0:
            continue
        if codigo:
            tarifas[codigo] = precio
        if abre:
            tarifas[abre] = precio
    return tarifas


class Command(BaseCommand):
    help = 'Repara catálogo de estudios/perfiles con precios inválidos usando tarifas.csv (modo seguro por defecto).'

    def add_arguments(self, parser):
        parser.add_argument('--archivo', type=str, default='tarifas.csv', help='CSV de tarifas (relativo a BASE_DIR)')
        parser.add_argument('--ejecutar', action='store_true', help='Aplica cambios. Sin esto, solo simula.')

    def handle(self, *args, **options):
        raise CommandError(
            "DEPRECATED: Este comando opera sobre el catálogo legacy. "
            "Usa 'importar_catalogo_lims' para LIMS v7.5."
        )
        ruta_csv = os.path.join(settings.BASE_DIR, options['archivo'])
        ejecutar = bool(options.get('ejecutar'))

        if not os.path.isfile(ruta_csv):
            self.stderr.write(self.style.ERROR(f'No se encontró: {ruta_csv}'))
            return

        self.stdout.write(self.style.WARNING(f'Leyendo tarifas: {ruta_csv}'))
        tarifas = _load_tarifas_map(ruta_csv)
        self.stdout.write(f'Tarifas útiles: {len(tarifas)}')

        total_core = 0
        core_candidatos = 0
        core_actualizados = 0
        core_sin_match = 0

        for est in Estudio.objects.all().only('id', 'codigo', 'abreviatura', 'nombre', 'precio'):
            total_core += 1
            precio_actual = est.precio or Decimal('0')
            if precio_actual > 0:
                continue

            codigo = (est.codigo or '').strip().upper()
            abre = (est.abreviatura or '').strip().upper()
            nuevo_precio = tarifas.get(codigo) or tarifas.get(abre)

            core_candidatos += 1
            if not nuevo_precio or nuevo_precio <= 0:
                core_sin_match += 1
                continue

            if ejecutar:
                est.precio = nuevo_precio
                est.save(update_fields=['precio'])
            core_actualizados += 1

        perfiles_total = 0
        perfiles_candidatos = 0
        perfiles_actualizados = 0
        perfiles_sin_pruebas = 0

        for perfil in PerfilLaboratorio.objects.prefetch_related('pruebas').all():
            perfiles_total += 1
            if (perfil.precio or Decimal('0')) > 0:
                continue

            pruebas = list(perfil.pruebas.all())
            if not pruebas:
                perfiles_sin_pruebas += 1
                continue

            perfiles_candidatos += 1
            suma = Decimal('0')
            for p in pruebas:
                suma += (p.precio_base or Decimal('0'))

            if suma <= 0:
                continue

            if ejecutar:
                perfil.precio = suma
                perfil.save(update_fields=['precio'])
            perfiles_actualizados += 1

        self.stdout.write(self.style.SUCCESS('-' * 80))
        self.stdout.write(self.style.SUCCESS('REPORTE REPARACIÓN CATÁLOGO'))
        self.stdout.write(self.style.SUCCESS(f'Modo: {"EJECUCIÓN" if ejecutar else "SIMULACIÓN"}'))
        self.stdout.write(f'Core.Estudio totales: {total_core}')
        self.stdout.write(f'Core con precio <= 0: {core_candidatos}')
        self.stdout.write(f'Core actualizables con CSV: {core_actualizados}')
        self.stdout.write(f'Core sin match en CSV: {core_sin_match}')
        self.stdout.write(f'PerfilLaboratorio totales: {perfiles_total}')
        self.stdout.write(f'Perfiles precio <= 0 con pruebas: {perfiles_candidatos}')
        self.stdout.write(f'Perfiles actualizables por suma pruebas: {perfiles_actualizados}')
        self.stdout.write(f'Perfiles sin pruebas: {perfiles_sin_pruebas}')
