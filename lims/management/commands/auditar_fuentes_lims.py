"""Audita la integridad estructural de las fuentes canónicas de LIMS."""

import csv
from collections import Counter
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from lims.veterinary_catalog import is_veterinary_catalog_text


class Command(BaseCommand):
    help = 'Audita fuentes CSV canónicas de LIMS sin escribir en la base de datos.'

    def handle(self, *args, **options):
        base = Path(settings.BASE_DIR) / 'datos_lims'
        required = (
            'Parametros.csv', 'Valores_normalidad.csv', 'Examenes.csv',
            'Examenes_Perfil.csv', 'Paquetes.csv', 'Paquetes_Perfil.csv',
            'Tarifa_estudios de laboratorio.csv',
        )
        missing = [name for name in required if not (base / name).is_file()]
        if missing:
            raise CommandError(f'Fuentes faltantes: {", ".join(missing)}')

        params = self._dict_rows(base / 'Parametros.csv')
        values = self._dict_rows(base / 'Valores_normalidad.csv')
        exams = self._dict_rows(base / 'Examenes.csv')
        packages = self._dict_rows(base / 'Paquetes.csv')
        exam_profile = self._double_header_rows(base / 'Examenes_Perfil.csv')
        package_profile = self._double_header_rows(base / 'Paquetes_Perfil.csv')
        tariff = self._tariff_rows(base / 'Tarifa_estudios de laboratorio.csv')

        veterinary = []
        for name, rows in (
            ('Parametros.csv', params), ('Valores_normalidad.csv', values),
            ('Examenes.csv', exams), ('Paquetes.csv', packages),
        ):
            for number, row in enumerate(rows, 2):
                if is_veterinary_catalog_text(*row.values()):
                    veterinary.append(f'{name}:{number}')
        for name, rows in (
            ('Examenes_Perfil.csv', exam_profile),
            ('Paquetes_Perfil.csv', package_profile),
            ('Tarifa_estudios de laboratorio.csv', tariff),
        ):
            for number, row in enumerate(rows, 3):
                if is_veterinary_catalog_text(*row):
                    veterinary.append(f'{name}:{number}')
        if veterinary:
            raise CommandError('Persisten filas veterinarias: ' + ', '.join(veterinary[:20]))

        self._assert_unique(params, 'Id_parametro', 'Parametros.csv')
        self._assert_unique(exams, 'Id_examen', 'Examenes.csv')
        self._assert_unique(packages, 'Abreviatura', 'Paquetes.csv')

        param_ids = {row.get('Id_parametro', '').strip() for row in params}
        param_keys = {
            value.strip().lower()
            for row in params
            for value in (row.get('Codigo', ''), row.get('Abreviatura', ''))
            if value.strip()
        }
        exam_keys = {
            (row.get('Codigo', '').strip(), row.get('Abreviatura', '').strip())
            for row in exams
        }
        exam_codes = {row.get('Codigo', '').strip() for row in exams}
        package_keys = {row.get('Abreviatura', '').strip() for row in packages}

        orphan_values = [row.get('Id_parametro', '') for row in values
                         if row.get('Id_parametro', '').strip() not in param_ids]
        orphan_exam = [row[:2] for row in exam_profile
                       if row and row[0] and (row[0], row[1]) not in exam_keys]
        orphan_analites = [row[3] for row in exam_profile
                           if len(row) >= 4 and row[3].strip()
                           and row[3].strip().lower() not in param_keys]
        orphan_packages = [row[0] for row in package_profile
                           if row and row[0] and row[0] not in package_keys]
        orphan_package_profiles = [row[3] for row in package_profile
                                  if len(row) >= 4 and row[2].strip().lower() == 'perfil'
                                  and row[3].strip() not in exam_codes]
        errors = []
        if orphan_values:
            errors.append(f'Valores_normalidad sin parámetro: {len(orphan_values)}')
        if orphan_exam:
            errors.append(f'Examenes_Perfil sin examen: {len(orphan_exam)}')
        if orphan_analites:
            errors.append(f'Examenes_Perfil con analito sin catálogo: {len(orphan_analites)}')
        if orphan_packages:
            errors.append(f'Paquetes_Perfil sin paquete: {len(orphan_packages)}')
        if orphan_package_profiles:
            errors.append(f'Paquetes_Perfil con perfil sin catálogo: {len(orphan_package_profiles)}')
        if errors:
            raise CommandError('; '.join(errors))

        duplicate_codes = [key for key, count in Counter(
            row.get('Codigo', '').strip() for row in params if row.get('Codigo', '').strip()
        ).items() if count > 1]
        self.stdout.write(self.style.SUCCESS(
            'Fuentes LIMS válidas: '
            f'{len(params)} analitos, {len(values)} rangos, {len(exams)} perfiles, '
            f'{len(packages)} paquetes, {len(tariff)} tarifas.'
        ))
        if duplicate_codes:
            self.stdout.write(self.style.WARNING(
                f'Advertencia controlada: {len(duplicate_codes)} códigos legacy repetidos; '
                'se resolverán por abreviatura única, nunca por primer registro.'
            ))
        overlaps = self._overlapping_ranges(values)
        if overlaps:
            self.stdout.write(self.style.WARNING(
                f'Validación clínica pendiente: {len(overlaps)} grupos de rangos superpuestos '
                'en Valores_normalidad.csv; no se modificaron automáticamente.'
            ))

    @staticmethod
    def _dict_rows(path):
        with path.open(encoding='utf-8-sig', newline='') as handle:
            return list(csv.DictReader(handle))

    @staticmethod
    def _double_header_rows(path):
        with path.open(encoding='utf-8-sig', newline='') as handle:
            return list(csv.reader(handle))[2:]

    @staticmethod
    def _tariff_rows(path):
        rows = []
        with path.open(encoding='utf-8-sig', newline='') as handle:
            reader = csv.reader(handle)
            for row in reader:
                if row and row[0].strip().lower() == 'tipo':
                    break
            for row in reader:
                if len(row) >= 5 and row[1].strip() and row[4].strip():
                    rows.append(row)
        return rows

    def _assert_unique(self, rows, key, source):
        values = [row.get(key, '').strip() for row in rows if row.get(key, '').strip()]
        duplicated = [value for value, count in Counter(values).items() if count > 1]
        if duplicated:
            raise CommandError(f'{source} tiene {key} duplicados: {", ".join(duplicated[:10])}')

    @staticmethod
    def _overlapping_ranges(rows):
        grouped = {}
        for row in rows:
            try:
                key = (row['Id_parametro'], row['Sexo'], row['Unidad'])
                grouped.setdefault(key, []).append((int(row['Edad_min']), int(row['Edad_max'])))
            except (KeyError, TypeError, ValueError):
                continue
        overlaps = []
        for key, ranges in grouped.items():
            ordered = sorted(ranges)
            for first, second in zip(ordered, ordered[1:]):
                if first[1] >= second[0]:
                    overlaps.append((key, first, second))
        return overlaps
