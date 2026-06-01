"""
CARGA DE PRODUCTOS FARMACIA DESDE CSV
======================================
Lee el CSV exportado del sistema POS y carga productos + lotes.

Formato esperado (columnas CSV):
  Nombre del Producto, Identificador, Es un Servicio, Se Vende,
  Descripción, Categoría, Marca, Unidad de Venta, Código de Barras,
  SKU, ..., Usa Lotes, Lote, Fabricación del Lote, Caducidad del Lote,
  Utiliza Stock, Stock Total, Stock Mínimo, ..., Precio Público,
  Precio PERSONAL, ..., Costo, Impuestos, IVA, ..., Receta Médica, ...

Nota: Un mismo producto puede aparecer en MÚLTIPLES filas (una por lote).
      El comando consolida stock total y crea los lotes individuales.

Uso:
  python manage.py cargar_productos_farmacia --empresa-id=<pk> [ruta/al/archivo.csv]
"""
import csv
import os
from datetime import datetime, date
from decimal import Decimal, InvalidOperation
from collections import defaultdict

from django.core.management.base import BaseCommand
from django.db import transaction
from django.conf import settings

from core.models import Producto, Lote, Sucursal


class Command(BaseCommand):
    help = 'Carga productos de farmacia y lotes desde CSV del sistema POS'

    def add_arguments(self, parser):
        from core.utils.tenant_strict import add_argument_empresa_id

        add_argument_empresa_id(parser, required=True)
        parser.add_argument(
            'archivo',
            nargs='?',
            default=None,
            type=str,
            help='Ruta al archivo CSV (auto-detecta si no se proporciona)'
        )

    def handle(self, *args, **options):
        archivo = options['archivo'] or self._auto_detectar_csv()

        if not archivo:
            self.stdout.write(self.style.WARNING(
                '[SKIP] No se encontró CSV de productos de farmacia. '
                'Coloca un archivo como Productos-farmacia-*.csv en la raíz.'
            ))
            return

        if not os.path.exists(archivo):
            self.stdout.write(self.style.ERROR(f'[ERROR] Archivo no encontrado: {archivo}'))
            return

        from core.utils.tenant_strict import empresa_desde_management

        try:
            empresa = empresa_desde_management(options)
        except Exception as e:
            self.stdout.write(self.style.ERROR(str(e)))
            return

        sucursal = Sucursal.objects.filter(empresa=empresa).first()

        self.stdout.write('=' * 80)
        self.stdout.write(self.style.SUCCESS('CARGA DE PRODUCTOS FARMACIA (CSV)'))
        self.stdout.write(f'Archivo: {archivo}')
        self.stdout.write(f'Empresa: {empresa.nombre}')
        self.stdout.write('=' * 80)

        # Leer y parsear CSV
        filas = self._leer_csv(archivo)
        if not filas:
            self.stdout.write(self.style.ERROR('[ERROR] CSV vacío o formato incorrecto.'))
            return

        self.stdout.write(f'[OK] {len(filas)} filas leídas del CSV')

        # Agrupar por producto (código de barras o identificador)
        productos_agrupados = self._agrupar_por_producto(filas)
        self.stdout.write(f'[OK] {len(productos_agrupados)} productos únicos detectados')

        # Cargar en BD
        creados, actualizados, lotes_creados, errores = self._cargar_en_bd(
            productos_agrupados, empresa, sucursal
        )

        # Reporte final
        self.stdout.write('')
        self.stdout.write('=' * 80)
        self.stdout.write(self.style.SUCCESS('CARGA COMPLETADA'))
        self.stdout.write(f'  Productos creados:      {creados}')
        self.stdout.write(f'  Productos actualizados:  {actualizados}')
        self.stdout.write(f'  Lotes creados:           {lotes_creados}')
        if errores:
            self.stdout.write(self.style.WARNING(f'  Errores:                 {len(errores)}'))
            for e in errores[:10]:
                self.stdout.write(f'    - {e}')
        self.stdout.write('=' * 80)

    def _auto_detectar_csv(self):
        """Busca automáticamente un CSV de productos en la raíz del proyecto."""
        base = settings.BASE_DIR
        candidatos = [
            'Productos-farmacia-2026-02-10-10-31.csv',
            'inventario.csv',
        ]
        # Buscar por nombre conocido
        for nombre in candidatos:
            ruta = os.path.join(base, nombre)
            if os.path.exists(ruta):
                return ruta
        # Buscar por patrón
        for f in os.listdir(base):
            if f.lower().startswith('productos') and f.endswith('.csv'):
                return os.path.join(base, f)
        return None

    def _leer_csv(self, archivo):
        """Lee CSV con manejo de encoding y líneas vacías."""
        filas = []
        for encoding in ['utf-8-sig', 'utf-8', 'latin-1', 'cp1252']:
            try:
                with open(archivo, 'r', encoding=encoding) as f:
                    lineas = f.readlines()

                # Encontrar la línea de encabezado
                header_idx = None
                for i, linea in enumerate(lineas):
                    if 'Nombre del Producto' in linea:
                        header_idx = i
                        break

                if header_idx is None:
                    self.stdout.write(f'  [DEBUG] Header no encontrado con encoding {encoding}')
                    continue

                contenido = ''.join(lineas[header_idx:])
                reader = csv.DictReader(contenido.splitlines())
                for row in reader:
                    nombre = (row.get('Nombre del Producto') or '').strip()
                    if nombre:
                        filas.append(row)

                if filas:
                    self.stdout.write(f'  [OK] CSV leído con encoding: {encoding}')
                    break
            except UnicodeDecodeError:
                continue
            except Exception as e:
                self.stdout.write(f'  [DEBUG] Error con encoding {encoding}: {e}')
                continue
        return filas

    def _agrupar_por_producto(self, filas):
        """
        Agrupa filas por producto único (código de barras o identificador).
        Un producto puede tener múltiples filas (una por lote).
        """
        grupos = defaultdict(lambda: {'info': None, 'lotes': [], 'stock_total': 0})

        for fila in filas:
            codigo = (fila.get('Código de Barras') or '').strip()
            identificador = (fila.get('Identificador (No Cambiar)') or '').strip()
            clave = codigo or identificador

            if not clave:
                continue

            # Guardar info del producto (primera aparición)
            if grupos[clave]['info'] is None:
                grupos[clave]['info'] = fila

            # Acumular stock
            stock_str = self._limpiar_numero(fila.get('Stock Total ', '0'))
            try:
                stock = int(float(stock_str))
            except (ValueError, TypeError):
                stock = 0
            grupos[clave]['stock_total'] += max(stock, 0)

            # Guardar datos del lote si existe
            lote_num = (fila.get('Lote') or '').strip()
            caducidad = (fila.get('Caducidad del Lote') or '').strip()
            if lote_num:
                grupos[clave]['lotes'].append({
                    'numero': lote_num,
                    'caducidad': caducidad,
                    'stock': max(stock, 0),
                })

        return grupos

    def _cargar_en_bd(self, productos_agrupados, empresa, sucursal):
        """Carga productos y lotes en la BD."""
        creados = 0
        actualizados = 0
        lotes_creados = 0
        errores = []

        with transaction.atomic():
            for clave, data in productos_agrupados.items():
                try:
                    info = data['info']
                    nombre = (info.get('Nombre del Producto') or '').strip()
                    if not nombre:
                        continue

                    codigo_barras = (info.get('Código de Barras') or '').strip()
                    identificador = (info.get('Identificador (No Cambiar)') or '').strip()

                    # Si no hay código de barras, usar identificador como código
                    if not codigo_barras:
                        codigo_barras = identificador or f'SIN-CB-{hash(nombre) % 100000:05d}'

                    marca = (info.get('Marca') or 'GENÉRICO').strip()
                    categoria_raw = (info.get('Categoría') or '').strip()
                    descripcion = (info.get('Descripción') or '').strip()

                    precio_publico = self._parse_precio(info.get('Precio Público', '0'))
                    costo = self._parse_precio(info.get('Costo', '0'))

                    es_servicio = (info.get('Es un Servicio') or 'No').strip().lower() in ('si', 'sí', 'yes', '1')
                    es_receta = (info.get('Receta Médica') or 'No').strip().lower() in ('si', 'sí', 'yes', '1', 'obligatorio')

                    categoria = self._mapear_categoria(categoria_raw)
                    clasificacion = 'IV' if es_receta else 'VI'

                    stock_total = data['stock_total']

                    # Stock mínimo
                    stock_min_str = self._limpiar_numero(info.get('Stock Mínimo ', '0'))
                    try:
                        stock_minimo = int(float(stock_min_str))
                    except (ValueError, TypeError):
                        stock_minimo = 0

                    # Crear o actualizar producto
                    producto, created = Producto.objects.update_or_create(
                        codigo_barras=codigo_barras,
                        defaults={
                            'empresa': empresa,
                            'sucursal': sucursal,
                            'nombre': nombre[:255],
                            'sustancia_activa': descripcion[:255] if descripcion else '',
                            'marca_laboratorio': marca[:150],
                            'forma_farmaceutica': 'Unidad',
                            'concentracion': 'N/A',
                            'presentacion': '1',
                            'precio_compra': costo,
                            'precio_publico': precio_publico,
                            'stock': stock_total,
                            'iva_porcentaje': Decimal('0.00'),
                            'clasificacion_sanitaria': clasificacion,
                            'categoria': categoria,
                            'es_antibiotico': es_receta,
                            'es_servicio': es_servicio,
                        }
                    )

                    if created:
                        creados += 1
                    else:
                        actualizados += 1

                    # Crear lotes
                    for lote_data in data['lotes']:
                        fecha_cad = self._parse_fecha(lote_data['caducidad'])
                        if not fecha_cad or fecha_cad < date.today():
                            continue  # Saltar lotes sin caducidad o ya caducados

                        _, lote_created = Lote.objects.get_or_create(
                            producto=producto,
                            numero_lote=lote_data['numero'],
                            defaults={
                                'fecha_caducidad': fecha_cad,
                                'fecha_fabricacion': None,
                                'cantidad': lote_data['stock'],
                                'costo_adquisicion': costo if costo > 0 else Decimal('0.01'),
                            }
                        )
                        if lote_created:
                            lotes_creados += 1

                    if creados % 100 == 0 and creados > 0:
                        self.stdout.write(f'  [{creados} productos creados...]')

                except Exception as e:
                    errores.append(f'{clave}: {e}')

        return creados, actualizados, lotes_creados, errores

    def _parse_precio(self, valor):
        """Parsea precios con formato $ 225.00 o 225.00"""
        try:
            if not valor:
                return Decimal('0.00')
            limpio = str(valor).replace('$', '').replace(',', '').strip()
            return Decimal(limpio)
        except (InvalidOperation, ValueError):
            return Decimal('0.00')

    def _limpiar_numero(self, valor):
        """Limpia un valor numérico."""
        if not valor:
            return '0'
        return str(valor).replace(',', '').replace('$', '').strip()

    def _parse_fecha(self, fecha_str):
        """Parsea fecha en formato DD/MM/YYYY."""
        if not fecha_str:
            return None
        for fmt in ('%d/%m/%Y', '%Y-%m-%d', '%m/%d/%Y', '%d-%m-%Y'):
            try:
                return datetime.strptime(fecha_str.strip(), fmt).date()
            except ValueError:
                continue
        return None

    def _mapear_categoria(self, categoria_raw):
        """Mapea categoría del CSV a opciones del modelo."""
        if not categoria_raw:
            return 'GENERICO'
        cat = str(categoria_raw).lower()
        if 'antibi' in cat:
            return 'ANTIBIOTICO'
        elif 'patente' in cat or 'marca' in cat:
            return 'PATENTE'
        elif 'curacion' in cat or 'material' in cat:
            return 'CURACION'
        elif 'medicamento' in cat:
            return 'GENERICO'
        elif 'generico' in cat or 'genérico' in cat:
            return 'GENERICO'
        return 'OTRO'
