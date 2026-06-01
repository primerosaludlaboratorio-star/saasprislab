"""
import_estudios_excel.py — PRISLAB v5.2
════════════════════════════════════════════════════════════════════
Carga o actualiza el catálogo de estudios de laboratorio desde un
archivo Excel (.xlsx) o CSV.

Columnas esperadas (insensible a mayúsculas/acentos):
  Nombre / NOMBRE / nombre
  Codigo / CODIGO / codigo
  Abreviatura
  Precio / Precio Publico / Precio Venta
  Muestra / Muestra Requerida
  Tubo / Color Tubo
  Seccion / Sección
  Indicaciones
  Dias Entrega
  Es Perfil       (1/0/Sí/No)
  Activo          (1/0/Sí/No, default True)

Uso:
    python manage.py import_estudios_excel --file tarifas.xlsx
    python manage.py import_estudios_excel --file estudios.csv
    python manage.py import_estudios_excel --file tarifas.xlsx --dry-run
    python manage.py import_estudios_excel --file tarifas.xlsx --limpiar
════════════════════════════════════════════════════════════════════
"""
import os
import re
from decimal import Decimal, InvalidOperation

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction


# ── Normalización de nombres de columna ───────────────────────────────────────

def _normalizar(texto: str) -> str:
    """Convierte 'Precio Público' → 'precio_publico' para comparación."""
    texto = texto.strip().lower()
    texto = re.sub(r'[áàä]', 'a', texto)
    texto = re.sub(r'[éèë]', 'e', texto)
    texto = re.sub(r'[íìï]', 'i', texto)
    texto = re.sub(r'[óòö]', 'o', texto)
    texto = re.sub(r'[úùü]', 'u', texto)
    texto = re.sub(r'[^a-z0-9]', '_', texto)
    texto = re.sub(r'_+', '_', texto).strip('_')
    return texto


ALIAS_COLUMNAS = {
    'nombre':       ['nombre', 'name', 'estudio', 'descripcion', 'descripcion_estudio'],
    'codigo':       ['codigo', 'code', 'clave', 'cve'],
    'abreviatura':  ['abreviatura', 'abrev', 'abbreviation', 'sigla'],
    'precio':       ['precio', 'precio_publico', 'precio_venta', 'venta', 'precio_lista', 'price', 'tarifa'],
    'muestra':      ['muestra', 'muestra_requerida', 'tipo_muestra', 'sample'],
    'tubo':         ['tubo', 'tubo_color', 'color_tubo', 'color'],
    'seccion':      ['seccion', 'seccion_lab', 'area', 'department'],
    'indicaciones': ['indicaciones', 'instrucciones', 'preparacion', 'notes'],
    'dias_entrega': ['dias_entrega', 'dias', 'days', 'tiempo_entrega'],
    'es_perfil':    ['es_perfil', 'perfil', 'paquete', 'is_profile', 'package'],
    'activo':       ['activo', 'active', 'habilitado', 'enabled'],
}

TUBO_COLORES = {
    'rojo': 'ROJO', 'red': 'ROJO', 'suero': 'ROJO',
    'morado': 'MORADO', 'purple': 'MORADO', 'edta': 'MORADO', 'lila': 'MORADO',
    'azul': 'AZUL', 'blue': 'AZUL', 'citrato': 'AZUL',
    'verde': 'VERDE', 'green': 'VERDE', 'heparina': 'VERDE',
    'gris': 'GRIS', 'gray': 'GRIS', 'grey': 'GRIS', 'fluoruro': 'GRIS',
    'amarillo': 'AMARILLO', 'yellow': 'AMARILLO', 'gel': 'AMARILLO',
    'negro': 'NEGRO', 'black': 'NEGRO', 'esr': 'NEGRO',
}


def _clean(val) -> str:
    if val is None:
        return ''
    s = str(val).strip()
    return '' if s.lower() in ('nan', 'none', '#n/a', 'n/a', '') else s


def _bool_val(val) -> bool:
    v = _clean(val).lower()
    return v in ('1', 'si', 'sí', 'yes', 'true', 'x', 'activo', 'active')


def _precio(val) -> Decimal:
    v = _clean(val).replace(',', '').replace('$', '').replace(' ', '')
    try:
        return Decimal(v)
    except (InvalidOperation, ValueError):
        return Decimal('0.00')


def _detectar_columna(headers_norm: dict, campo: str):
    """Retorna el índice de la columna que coincide con los alias del campo."""
    for alias in ALIAS_COLUMNAS.get(campo, []):
        if alias in headers_norm:
            return headers_norm[alias]
    return None


def _leer_excel(ruta: str) -> tuple[list, list]:
    """Retorna (headers, filas) desde xlsx o csv."""
    ext = os.path.splitext(ruta)[1].lower()
    if ext in ('.xlsx', '.xls', '.xlsm'):
        try:
            import openpyxl
        except ImportError:
            raise CommandError(
                'openpyxl no está instalado. Ejecuta: pip install openpyxl'
            )
        wb = openpyxl.load_workbook(ruta, read_only=True, data_only=True)
        ws = wb.active
        filas = [[cell.value for cell in row] for row in ws.iter_rows()]
        wb.close()
        if not filas:
            return [], []
        return filas[0], filas[1:]

    elif ext == '.csv':
        import csv
        encodings = ['utf-8', 'latin-1', 'cp1252']
        for enc in encodings:
            try:
                with open(ruta, newline='', encoding=enc) as f:
                    reader = list(csv.reader(f))
                    if reader:
                        return reader[0], reader[1:]
            except UnicodeDecodeError:
                continue
        raise CommandError(f'No se pudo leer {ruta} con ningún encoding conocido.')

    else:
        raise CommandError(f'Formato no soportado: {ext}. Use .xlsx o .csv')


class Command(BaseCommand):
    help = 'Importa o actualiza el catálogo de estudios desde un archivo Excel o CSV.'

    def add_arguments(self, parser):
        parser.add_argument('--file', '--archivo', dest='file', required=True,
                            help='Ruta al archivo .xlsx o .csv')
        parser.add_argument('--dry-run', action='store_true',
                            help='Solo muestra qué se haría, sin guardar nada')
        parser.add_argument('--limpiar', action='store_true',
                            help='Desactiva estudios no presentes en el archivo antes de cargar')
        parser.add_argument('--sheet', default=None,
                            help='Nombre de la hoja a leer (solo xlsx, default: primera hoja)')

    def handle(self, *args, **options):
        raise CommandError(
            "DEPRECATED: Este comando opera sobre el catálogo legacy. "
            "Usa 'importar_catalogo_lims' para LIMS v7.5."
        )
        from core.models import Estudio, SeccionLaboratorio

        ruta = options['file']
        if not os.path.isabs(ruta):
            from django.conf import settings
            ruta = os.path.join(settings.BASE_DIR, ruta)

        if not os.path.isfile(ruta):
            raise CommandError(f'Archivo no encontrado: {ruta}')

        self.stdout.write(f'\nLeyendo: {ruta}')
        headers_raw, filas = _leer_excel(ruta)

        if not headers_raw:
            raise CommandError('El archivo está vacío o no tiene encabezados.')

        # Normalizar headers → { nombre_normalizado: indice }
        headers_norm = {
            _normalizar(str(h or '')): idx
            for idx, h in enumerate(headers_raw)
            if h is not None
        }
        self.stdout.write(f'Columnas detectadas: {list(headers_norm.keys())}')

        # Detectar índices de columnas
        col = {campo: _detectar_columna(headers_norm, campo) for campo in ALIAS_COLUMNAS}

        if col['nombre'] is None:
            raise CommandError(
                'No se encontró la columna "Nombre". '
                f'Columnas disponibles: {list(headers_norm.keys())}'
            )

        self.stdout.write(f'Mapeo de columnas: {col}')

        dry_run = options['dry_run']
        if dry_run:
            self.stdout.write(self.style.WARNING('MODO DRY-RUN: no se guardará nada.'))

        creados = 0
        actualizados = 0
        omitidos = 0
        errores = []
        codigos_procesados = set()

        secciones_cache = {}

        def get_seccion(nombre_sec: str):
            if not nombre_sec:
                return None
            if nombre_sec not in secciones_cache:
                sec, _ = SeccionLaboratorio.objects.get_or_create(
                    nombre__iexact=nombre_sec,
                    defaults={'nombre': nombre_sec}
                )
                secciones_cache[nombre_sec] = sec
            return secciones_cache[nombre_sec]

        def get_cell(fila, campo):
            idx = col.get(campo)
            if idx is None or idx >= len(fila):
                return None
            return fila[idx]

        with transaction.atomic():
            for i, fila in enumerate(filas, start=2):
                if all(_clean(c) == '' for c in fila):
                    continue  # fila vacía

                nombre = _clean(get_cell(fila, 'nombre'))
                if not nombre:
                    omitidos += 1
                    continue

                codigo = _clean(get_cell(fila, 'codigo')) or None
                abreviatura = _clean(get_cell(fila, 'abreviatura')) or None
                precio = _precio(get_cell(fila, 'precio'))
                muestra = _clean(get_cell(fila, 'muestra')) or 'Suero'
                indicaciones = _clean(get_cell(fila, 'indicaciones')) or 'Ayuno 8 hrs'
                nombre_seccion = _clean(get_cell(fila, 'seccion'))

                tubo_raw = _clean(get_cell(fila, 'tubo')).lower()
                tubo = TUBO_COLORES.get(tubo_raw, None)

                dias_raw = _clean(get_cell(fila, 'dias_entrega'))
                try:
                    dias = int(float(dias_raw)) if dias_raw else 1
                except (ValueError, TypeError):
                    dias = 1

                es_perfil_raw = get_cell(fila, 'es_perfil')
                es_perfil = _bool_val(es_perfil_raw) if es_perfil_raw is not None else False

                activo_raw = get_cell(fila, 'activo')
                activo = _bool_val(activo_raw) if activo_raw is not None else True

                # Buscar estudio existente por código o nombre
                estudio = None
                if codigo:
                    estudio = Estudio.objects.filter(codigo__iexact=codigo).first()
                    codigos_procesados.add(codigo.upper())
                if estudio is None:
                    estudio = Estudio.objects.filter(nombre__iexact=nombre).first()
                    if codigo:
                        codigos_procesados.add(codigo.upper())

                seccion = None
                if not dry_run and nombre_seccion:
                    try:
                        seccion = get_seccion(nombre_seccion)
                    except Exception as e:
                        errores.append(f'Fila {i} - sección "{nombre_seccion}": {e}')

                defaults = {
                    'nombre': nombre,
                    'precio': precio,
                    'muestra_requerida': muestra,
                    'indicaciones': indicaciones,
                    'dias_entrega': dias,
                    'es_perfil': es_perfil,
                    'activo': activo,
                }
                if abreviatura:
                    defaults['abreviatura'] = abreviatura
                if tubo:
                    defaults['tubo_color'] = tubo
                if seccion:
                    defaults['seccion'] = seccion

                if dry_run:
                    accion = 'CREAR' if not estudio else 'ACTUALIZAR'
                    self.stdout.write(f'  [{accion}] {nombre} | Precio: ${precio} | Código: {codigo or "auto"}')
                    if not estudio:
                        creados += 1
                    else:
                        actualizados += 1
                    continue

                try:
                    if estudio is None:
                        if not codigo:
                            # Generar código automático
                            prefix = (abreviatura or nombre[:6]).upper().replace(' ', '')
                            existing = Estudio.objects.filter(
                                codigo__startswith=prefix
                            ).count()
                            codigo = f'{prefix}-{existing+1:03d}'
                        Estudio.objects.create(codigo=codigo, **defaults)
                        creados += 1
                    else:
                        for k, v in defaults.items():
                            setattr(estudio, k, v)
                        if codigo:
                            estudio.codigo = codigo
                        estudio.save()
                        actualizados += 1
                except Exception as e:
                    errores.append(f'Fila {i} ({nombre}): {e}')
                    omitidos += 1

            if options['limpiar'] and not dry_run:
                # Desactivar estudios no presentes en el archivo
                desactivados = Estudio.objects.filter(activo=True).exclude(
                    codigo__in=codigos_procesados
                ).update(activo=False)
                self.stdout.write(self.style.WARNING(
                    f'Desactivados {desactivados} estudios no presentes en el archivo.'
                ))

            if dry_run:
                transaction.set_rollback(True)

        # Reporte final
        self.stdout.write('')
        self.stdout.write('=' * 60)
        self.stdout.write(f'IMPORTACION COMPLETADA — {os.path.basename(ruta)}')
        self.stdout.write('=' * 60)
        self.stdout.write(self.style.SUCCESS(f'  Creados:     {creados}'))
        self.stdout.write(self.style.SUCCESS(f'  Actualizados:{actualizados}'))
        if omitidos:
            self.stdout.write(self.style.WARNING(f'  Omitidos:    {omitidos}'))
        if errores:
            self.stdout.write(self.style.ERROR(f'  Errores:     {len(errores)}'))
            for err in errores[:10]:
                self.stdout.write(self.style.ERROR(f'    - {err}'))
        self.stdout.write('')
        total_activos = Estudio.objects.filter(activo=True).count()
        self.stdout.write(f'Total estudios activos en DB: {total_activos}')
        self.stdout.write('=' * 60)
