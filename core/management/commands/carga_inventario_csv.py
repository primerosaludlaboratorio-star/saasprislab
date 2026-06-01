"""
Carga de Inventario Inicial desde CSV — PRISLAB v5.0
====================================================
Nancy o Janette exportan su inventario actual a CSV/Excel y este
comando lo carga directamente a la base de datos.

Columnas requeridas en el CSV (primera fila = encabezados):
    nombre          — Nombre del medicamento/reactivo/insumo
    codigo          — Código de barras o clave interna (opcional)
    precio_compra   — Costo de adquisición (número, ej: 45.50)
    precio_venta    — Precio al público (número, ej: 89.00)
    stock           — Unidades en existencia (número entero)
    unidad          — Unidad de medida (ej: pieza, caja, frasco, ampolleta)
    categoria       — Categoría (ej: Antibiótico, Analgésico, Reactivo)  [opcional]
    stock_minimo    — Stock mínimo de alerta (número, default: 5)         [opcional]
    requiere_receta — SI/NO (default: NO)                                 [opcional]

Uso:
    # Ver una vista previa de los primeros 10 registros:
    python manage.py carga_inventario_csv --archivo ruta/al/inventario.csv

    # Cargar el inventario real:
    python manage.py carga_inventario_csv --archivo ruta/al/inventario.csv --confirmar

    # Si el separador no es coma sino punto y coma (Excel en español):
    python manage.py carga_inventario_csv --archivo inventario.csv --separador ";" --confirmar

    # Actualizar precios/stock de productos que ya existen (por código):
    python manage.py carga_inventario_csv --archivo inventario.csv --confirmar --actualizar-existentes

Cómo preparar el archivo en Excel:
    1. Abre tu inventario actual en Excel
    2. Asegúrate de que la primera fila tenga los encabezados exactos de arriba
    3. Archivo → Guardar como → CSV UTF-8 (con delimitadores de coma)
    4. Copia el archivo .csv al servidor y ejecuta el comando
"""
import csv
import os
from decimal import Decimal, InvalidOperation

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction


COLUMNAS_REQUERIDAS = {'nombre', 'precio_compra', 'precio_venta', 'stock', 'unidad'}


class Command(BaseCommand):
    help = 'Carga inventario inicial desde un archivo CSV al módulo de Farmacia'

    def add_arguments(self, parser):
        parser.add_argument(
            '--archivo',
            type=str,
            required=True,
            help='Ruta al archivo CSV con el inventario',
        )
        parser.add_argument(
            '--separador',
            type=str,
            default=',',
            help='Separador del CSV (default: coma). Usa ";" para Excel en español.',
        )
        parser.add_argument(
            '--confirmar',
            action='store_true',
            help='Ejecuta la carga real (sin este flag solo muestra vista previa)',
        )
        parser.add_argument(
            '--actualizar-existentes',
            action='store_true',
            help='Si el código ya existe, actualiza precio y stock en lugar de saltar',
        )
        parser.add_argument(
            '--encoding',
            type=str,
            default='utf-8-sig',
            help='Encoding del archivo CSV (default: utf-8-sig, compatible con Excel)',
        )

    def handle(self, *args, **options):
        archivo = options['archivo']
        separador = options['separador']
        confirmar = options['confirmar']
        actualizar = options['actualizar_existentes']
        encoding = options['encoding']

        self.stdout.write(self.style.MIGRATE_HEADING('\n╔═══════════════════════════════════════════╗'))
        self.stdout.write(self.style.MIGRATE_HEADING('║  PRISLAB v5 — CARGA DE INVENTARIO CSV    ║'))
        self.stdout.write(self.style.MIGRATE_HEADING('╚═══════════════════════════════════════════╝\n'))

        # Verificar que el archivo existe
        if not os.path.exists(archivo):
            raise CommandError(f'Archivo no encontrado: {archivo}')

        # Leer y validar el CSV
        try:
            filas = self._leer_csv(archivo, separador, encoding)
        except Exception as e:
            raise CommandError(f'Error al leer el CSV: {e}')

        self.stdout.write(f'  Archivo: {archivo}')
        self.stdout.write(f'  Filas detectadas: {len(filas):,}')

        if not confirmar:
            self.stdout.write(self.style.WARNING('\n  MODO VISTA PREVIA (primeros 10 registros):'))
            for i, fila in enumerate(filas[:10], 1):
                nombre = fila.get('nombre', '?')
                precio = fila.get('precio_venta', '?')
                stock = fila.get('stock', '?')
                unidad = fila.get('unidad', '?')
                self.stdout.write(f'    {i:3d}. {nombre:<35} ${precio:<8} Stock: {stock} {unidad}')
            if len(filas) > 10:
                self.stdout.write(f'    ... y {len(filas) - 10:,} productos más')
            self.stdout.write(self.style.WARNING(
                '\n  Usa --confirmar para cargar todos los productos.\n'
            ))
            return

        # Cargar los productos
        self._cargar_productos(filas, actualizar)

    def _leer_csv(self, archivo, separador, encoding):
        """Lee el CSV y valida encabezados y tipos de datos."""
        filas = []
        errores = []

        with open(archivo, newline='', encoding=encoding) as f:
            reader = csv.DictReader(f, delimiter=separador)

            # Normalizar encabezados (minúsculas, sin espacios)
            if reader.fieldnames:
                reader.fieldnames = [
                    col.strip().lower().replace(' ', '_')
                    for col in reader.fieldnames
                ]

            # Verificar columnas requeridas
            encabezados = set(reader.fieldnames or [])
            faltantes = COLUMNAS_REQUERIDAS - encabezados
            if faltantes:
                raise CommandError(
                    f'Columnas faltantes en el CSV: {", ".join(sorted(faltantes))}\n'
                    f'Columnas encontradas: {", ".join(sorted(encabezados))}'
                )

            for i, fila in enumerate(reader, start=2):  # start=2 porque fila 1 es encabezado
                fila_limpia = {k: (v or '').strip() for k, v in fila.items()}
                error = self._validar_fila(fila_limpia, i)
                if error:
                    errores.append(error)
                else:
                    filas.append(fila_limpia)

        if errores:
            self.stdout.write(self.style.WARNING(f'\n  {len(errores)} filas con errores (se omitirán):'))
            for e in errores[:5]:
                self.stdout.write(f'    {e}')
            if len(errores) > 5:
                self.stdout.write(f'    ... y {len(errores) - 5} errores más')

        return filas

    def _validar_fila(self, fila, numero_fila):
        """Retorna mensaje de error o None si la fila es válida."""
        nombre = fila.get('nombre', '').strip()
        if not nombre:
            return f'Fila {numero_fila}: nombre vacío'

        for campo in ('precio_compra', 'precio_venta', 'stock'):
            valor = fila.get(campo, '').replace(',', '.').replace('$', '').strip()
            try:
                Decimal(valor)
            except (InvalidOperation, ValueError):
                return f'Fila {numero_fila}: {campo} no es un número válido ("{valor}")'

        return None

    def _cargar_productos(self, filas, actualizar):
        """Carga los productos a la base de datos."""
        from core.models import Producto

        creados = 0
        actualizados = 0
        omitidos = 0
        errores = 0

        self.stdout.write(self.style.MIGRATE_LABEL(f'\n  Cargando {len(filas):,} productos...\n'))

        with transaction.atomic():
            for fila in filas:
                try:
                    nombre = fila['nombre'].strip()
                    codigo = fila.get('codigo', '').strip() or None
                    precio_compra = Decimal(fila['precio_compra'].replace(',', '.').replace('$', ''))
                    precio_venta = Decimal(fila['precio_venta'].replace(',', '.').replace('$', ''))
                    stock = int(float(fila['stock'].replace(',', '')))
                    unidad = fila.get('unidad', 'pieza').strip() or 'pieza'
                    stock_minimo = int(float(fila.get('stock_minimo', '5').replace(',', '') or '5'))
                    requiere_receta = fila.get('requiere_receta', 'NO').upper() in ('SI', 'SÍ', 'YES', '1', 'TRUE')
                    categoria_nombre = fila.get('categoria', 'General').strip() or 'General'

                    # Buscar si ya existe (por código si hay, sino por nombre)
                    producto_existente = None
                    if codigo:
                        producto_existente = Producto.objects.filter(codigo=codigo).first()
                    if not producto_existente:
                        producto_existente = Producto.objects.filter(nombre__iexact=nombre).first()

                    if producto_existente and not actualizar:
                        omitidos += 1
                        continue

                    # Obtener o crear categoría si el modelo la usa
                    categoria_obj = self._get_categoria(categoria_nombre)

                    campos = {
                        'nombre': nombre,
                        'precio_compra': precio_compra,
                        'precio_venta': precio_venta,
                        'stock': stock,
                        'unidad': unidad,
                        'stock_minimo': stock_minimo,
                        'requiere_receta': requiere_receta,
                    }
                    if codigo:
                        campos['codigo'] = codigo
                    if categoria_obj:
                        campos['categoria'] = categoria_obj

                    if producto_existente:
                        for attr, val in campos.items():
                            setattr(producto_existente, attr, val)
                        producto_existente.save()
                        actualizados += 1
                    else:
                        Producto.objects.create(**campos)
                        creados += 1

                except Exception as e:
                    errores += 1
                    self.stdout.write(self.style.ERROR(f'  [ERROR] {fila.get("nombre", "?")} — {e}'))

        self.stdout.write(self.style.SUCCESS(f'\n  ✓ Productos creados:     {creados:>5,}'))
        if actualizados:
            self.stdout.write(self.style.SUCCESS(f'  ✓ Productos actualizados: {actualizados:>4,}'))
        if omitidos:
            self.stdout.write(self.style.WARNING(f'  ⚠ Omitidos (ya existen):  {omitidos:>4,}'))
        if errores:
            self.stdout.write(self.style.ERROR(f'  ✗ Errores:                {errores:>4,}'))

        total = creados + actualizados
        self.stdout.write(self.style.SUCCESS(f'\n  Total cargados al sistema: {total:,} productos\n'))

    def _get_categoria(self, nombre):
        """Obtiene o crea la categoría del producto si el modelo la soporta."""
        try:
            from core.models import CategoriaProducto
            obj, _ = CategoriaProducto.objects.get_or_create(nombre=nombre)
            return obj
        except Exception:
            return None
