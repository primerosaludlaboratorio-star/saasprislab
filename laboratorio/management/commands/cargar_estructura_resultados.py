import csv
import os
from decimal import Decimal, InvalidOperation

from django.conf import settings
from django.core.management.base import BaseCommand

from laboratorio.models import Estudio, Parametro, CategoriaExamen


class Command(BaseCommand):
    """
    Carga la estructura de resultados (parámetros) a partir de un CSV
    tipo 'Resultados (1).xlsx - Reporte.csv'.

    - Detecta filas de ESTUDIO padre (solo descripción, sin unidades / refs)
    - Detecta filas de PARÁMETRO hijo (con unidades y/o rangos)
    - Crea Parametro(nombre, unidades, valor_ref_min, valor_ref_max) ligado al Estudio
    """

    help = "Carga la estructura de parámetros de laboratorio en el modelo Parametro."

    def add_arguments(self, parser):
        parser.add_argument(
            '--archivo',
            type=str,
            default='Resultados (1).xlsx - Reporte.csv',
            help='Nombre del archivo CSV en la raíz del proyecto.',
        )

    def handle(self, *args, **options):
        """
        Busca automáticamente un archivo que comience con 'Resultados' y termine en '.csv'
        en la carpeta BASE_DIR. Usa el primero que encuentre.
        """
        base_dir = settings.BASE_DIR
        candidato = None
        for nombre in os.listdir(base_dir):
            if nombre.lower().startswith('resultados') and nombre.lower().endswith('.csv'):
                candidato = nombre
                break

        if not candidato:
            self.stdout.write(self.style.ERROR('[ERROR] No se encontró ningún archivo "Resultados*.csv" en la carpeta raíz.'))
            return

        ruta = os.path.join(base_dir, candidato)
        self.stdout.write(self.style.WARNING(f'[INFO] Archivo encontrado: {candidato}'))
        self.stdout.write(self.style.WARNING(f'[INFO] Leyendo estructura desde: {ruta}'))

        # Algunos archivos exportados desde Excel pueden venir en ANSI/Latin-1,
        # por eso usamos latin-1 para evitar errores de decodificación.
        with open(ruta, 'r', encoding='latin-1', newline='') as f:
            reader = csv.reader(f)

            encabezados = None
            # Buscar fila de encabezados que contenga 'Descripción'
            for row in reader:
                if not row:
                    continue
                lower = [c.strip().lower() for c in row]
                if 'descripción' in lower or 'descripcion' in lower:
                    encabezados = [c.strip() for c in row]
                    break

            if not encabezados:
                self.stdout.write(self.style.ERROR('[ERROR] No se encontró fila de encabezados con "Descripción".'))
                return

            # Normalizar índices de columnas
            def idx(nombre):
                """
                Busca el índice de una columna por nombre, siendo tolerante a tildes
                y problemas de codificación (Descripci�n vs Descripción).
                """
                nombre = nombre.lower()
                for i, col in enumerate(encabezados):
                    c = col.lower()
                    # Coincidencia directa
                    if nombre in c:
                        return i
                    # Coincidencia por prefijo genérico (ej. 'descr' para descripción)
                    if nombre.startswith('descr') and c.startswith('descr'):
                        return i
                return None

            idx_desc = idx('descripción') or idx('descripcion')
            idx_unid = idx('unidad')
            idx_ref_min = idx('ref. min')
            idx_ref_max = idx('ref. max')

            if idx_desc is None:
                self.stdout.write(self.style.ERROR('[ERROR] No se pudo localizar la columna "Descripción".'))
                return

            self.stdout.write(self.style.WARNING(
                f'[INFO] Mapeo columnas -> desc={idx_desc}, unidades={idx_unid}, '
                f'ref_min={idx_ref_min}, ref_max={idx_ref_max}'
            ))

            estudio_actual = None
            creados = 0
            actualizados = 0

            for row in reader:
                if not row or len(row) <= idx_desc:
                    continue

                desc = (row[idx_desc] or '').strip()
                if not desc:
                    continue

                unidades = (row[idx_unid].strip() if idx_unid is not None and len(row) > idx_unid else '') if row else ''
                ref_min_raw = (row[idx_ref_min].strip() if idx_ref_min is not None and len(row) > idx_ref_min else '') if row else ''
                ref_max_raw = (row[idx_ref_max].strip() if idx_ref_max is not None and len(row) > idx_ref_max else '') if row else ''

                tiene_unidades = bool(unidades)
                tiene_refs = bool(ref_min_raw or ref_max_raw)

                # 1) Estudio padre: descripción con unidades y refs vacíos
                if desc and not tiene_unidades and not tiene_refs:
                    # Intentar encontrar el estudio por nombre; si no, crearlo en categoría genérica
                    estudio = Estudio.objects.filter(nombre__iexact=desc).first()
                    if not estudio:
                        categoria, _ = CategoriaExamen.objects.get_or_create(nombre='ESTUDIOS AUTOMATICOS')
                        estudio = Estudio.objects.create(
                            nombre=desc,
                            categoria=categoria,
                            precio_base=Decimal('0.00'),
                        )
                        self.stdout.write(f'[CREADO ESTUDIO] {estudio.nombre}')
                    else:
                        self.stdout.write(f'[USADO ESTUDIO] {estudio.nombre}')

                    estudio_actual = estudio
                    continue

                # 2) Parámetro hijo: requiere tener estudio_actual y algo en unidades o referencias
                if not estudio_actual:
                    # No hay contexto de estudio, saltar
                    self.stdout.write(f'[SKIP] Parámetro sin estudio padre: {desc}')
                    continue

                if not (tiene_unidades or tiene_refs):
                    # Línea informativa sin datos de parámetro
                    continue

                # Intentar convertir rangos a Decimal si son numéricos
                ref_min = None
                ref_max = None

                def to_decimal(texto):
                    if not texto:
                        return None
                    try:
                        limpio = texto.replace(',', '').replace('<', '').replace('>', '').strip()
                        if not limpio:
                            return None
                        return Decimal(limpio)
                    except (InvalidOperation, ValueError):
                        return None

                ref_min = to_decimal(ref_min_raw)
                ref_max = to_decimal(ref_max_raw)

                # Detectar si el rango es claramente texto (NEGATIVO, REACTIVO, etc.)
                rango_textual = False
                if (ref_min is None and ref_min_raw) or (ref_max is None and ref_max_raw):
                    rango_textual = True

                if rango_textual:
                    self.stdout.write(f'[INFO] Rango textual para parámetro "{desc}" (estudio {estudio_actual.nombre})')

                # Crear o actualizar parámetro por nombre dentro del mismo estudio
                defaults = {
                    'unidades': unidades or None,
                    'valor_ref_min': ref_min,
                    'valor_ref_max': ref_max,
                }
                param, creado = Parametro.objects.update_or_create(
                    estudio=estudio_actual,
                    nombre=desc,
                    defaults=defaults,
                )
                if creado:
                    creados += 1
                else:
                    actualizados += 1

            self.stdout.write(self.style.SUCCESS(
                f'[EXITO] Parámetros creados: {creados}, actualizados: {actualizados}'
            ))

