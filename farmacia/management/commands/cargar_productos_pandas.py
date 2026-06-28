"""
COMANDO ALTERNATIVO: Carga con Pandas (más robusto)
Para archivos Excel con problemas de formato

Uso: python manage.py cargar_productos_pandas <archivo.xlsx>
"""
import os
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.db import transaction
from core.models import Producto, Empresa, Sucursal
import pandas as pd
import logging


class Command(BaseCommand):
    help = 'Carga productos usando pandas (más robusto para archivos con problemas)'

    def add_arguments(self, parser):
        parser.add_argument('archivo', type=str, help='Ruta al archivo Excel')
        parser.add_argument('--empresa-id', type=int, default=1, help='ID empresa')

    def handle(self, *args, **options):
        archivo = options['archivo']
        empresa_id = options['empresa_id']

        if not os.path.exists(archivo):
            self.stdout.write(self.style.ERROR(f'[ERROR] Archivo no encontrado: {archivo}'))
            return

        try:
            empresa = Empresa.objects.get(id=empresa_id)
        except Empresa.DoesNotExist:
            self.stdout.write(self.style.ERROR(f'[ERROR] Empresa ID {empresa_id} no existe'))
            return

        sucursal = Sucursal.objects.filter(empresa=empresa).first()

        self.stdout.write('=' * 80)
        self.stdout.write(self.style.SUCCESS('CARGA DE PRODUCTOS CON PANDAS'))
        self.stdout.write('=' * 80)
        self.stdout.write(f'Archivo: {archivo}')
        self.stdout.write(f'Empresa: {empresa.nombre}')
        self.stdout.write('')

        # Leer Excel con pandas (más robusto)
        try:
            self.stdout.write('[...] Leyendo Excel con pandas...')
            df = pd.read_excel(archivo, engine='openpyxl')
            self.stdout.write(f'[OK] {len(df)} filas leídas')
            self.stdout.write(f'[OK] Columnas detectadas: {len(df.columns)}')
        except Exception as e:  # Integración externa: archivo Excel provisto por usuario (pandas/openpyxl, cualquier formato inválido).
            logging.getLogger(__name__).exception("Error inesperado en handle (cargar_productos_pandas.py)")
            self.stdout.write(self.style.ERROR(f'[ERROR] No se pudo leer: {e}'))
            return

        # Mapear columnas
        col_map = {}
        for col in df.columns:
            col_str = str(col).strip()
            if 'Nombre del Producto' in col_str:
                col_map['nombre'] = col
            elif 'Código de Barras' in col_str:
                col_map['codigo'] = col
            elif 'SKU' in col_str and 'codigo' not in col_map:
                col_map['codigo'] = col
            elif 'Identificador' in col_str and 'codigo' not in col_map:
                col_map['codigo'] = col
            elif 'Marca' in col_str:
                col_map['marca'] = col
            elif 'Precio Público' in col_str:
                col_map['precio'] = col
            elif 'Costo' in col_str:
                col_map['costo'] = col
            elif 'Stock Total' in col_str:
                col_map['stock'] = col
            elif 'IVA' in col_str:
                col_map['iva'] = col
            elif 'Receta Médica' in col_str:
                col_map['receta'] = col
            elif 'Categoría' in col_str:
                col_map['categoria'] = col
            elif 'Descripción' in col_str:
                col_map['descripcion'] = col

        self.stdout.write('\n[COLUMNAS MAPEADAS]:')
        for k, v in col_map.items():
            self.stdout.write(f'  {k}: {v}')

        if 'nombre' not in col_map or 'codigo' not in col_map:
            self.stdout.write(self.style.ERROR('[ERROR] No se encontraron columnas requeridas'))
            return

        # Procesar filas
        self.stdout.write('\n[PROCESANDO...]')
        creados = 0
        actualizados = 0
        errores = []

        with transaction.atomic():
            for idx, row in df.iterrows():
                try:
                    nombre = str(row[col_map['nombre']]) if pd.notna(row[col_map['nombre']]) else None
                    codigo = str(row[col_map['codigo']]) if pd.notna(row[col_map['codigo']]) else None

                    if not nombre or not codigo or nombre == 'nan' or codigo == 'nan':
                        continue

                    # Datos opcionales
                    marca = str(row[col_map.get('marca', col_map['nombre'])]) if col_map.get('marca') and pd.notna(row.get(col_map.get('marca'))) else 'GENERICO'
                    
                    precio = Decimal('0.00')
                    if col_map.get('precio'):
                        try:
                            val = row[col_map['precio']]
                            if pd.notna(val):
                                precio = Decimal(str(val).replace(',', '').replace('$', '').strip())
                        except (ValueError, TypeError, ArithmeticError):
                            pass

                    costo = Decimal('0.00')
                    if col_map.get('costo'):
                        try:
                            val = row[col_map['costo']]
                            if pd.notna(val):
                                costo = Decimal(str(val).replace(',', '').replace('$', '').strip())
                        except (ValueError, TypeError, ArithmeticError):
                            pass

                    stock = 0
                    if col_map.get('stock'):
                        try:
                            val = row[col_map['stock']]
                            if pd.notna(val):
                                stock = int(float(val))
                        except (ValueError, TypeError):
                            pass

                    iva = Decimal('16.00')
                    if col_map.get('iva'):
                        try:
                            val = str(row[col_map['iva']])
                            if pd.notna(val) and val != 'nan':
                                iva = Decimal(val.replace('%', '').strip())
                        except (ValueError, TypeError, ArithmeticError):
                            pass

                    es_antibiotico = False
                    if col_map.get('receta'):
                        val = str(row[col_map['receta']]).lower()
                        es_antibiotico = any(k in val for k in ['sí', 'si', 'yes', 'obligatorio'])

                    # Crear producto
                    producto, created = Producto.objects.update_or_create(
                        codigo_barras=codigo,
                        defaults={
                            'empresa': empresa,
                            'sucursal': sucursal,
                            'nombre': nombre[:255],
                            'marca_laboratorio': marca[:150],
                            'forma_farmaceutica': 'Pieza',
                            'concentracion': 'N/A',
                            'presentacion': '1',
                            'precio_compra': costo,
                            'precio_publico': precio,
                            'stock': stock,
                            'iva_porcentaje': iva,
                            'clasificacion_sanitaria': 'IV' if es_antibiotico else 'VI',
                            'categoria': 'ANTIBIOTICO' if es_antibiotico else 'GENERICO',
                            'es_antibiotico': es_antibiotico,
                            'es_servicio': False,
                        }
                    )

                    if created:
                        creados += 1
                        if creados % 50 == 0:
                            self.stdout.write(f'  [{creados} creados...]')
                    else:
                        actualizados += 1

                except Exception as e:  # Aislamiento fila-por-fila: error en una fila no debe abortar toda la carga.
                    logging.getLogger(__name__).exception("Error inesperado en handle (cargar_productos_pandas.py)")
                    errores.append(f'Fila {idx}: {e}')
                    if len(errores) <= 5:
                        self.stdout.write(self.style.WARNING(f'  [!] Error fila {idx}: {e}'))

        # Reporte
        self.stdout.write('\n' + '=' * 80)
        self.stdout.write(self.style.SUCCESS('CARGA COMPLETADA'))
        self.stdout.write('=' * 80)
        self.stdout.write(f'[OK] Productos creados: {creados}')
        self.stdout.write(f'[OK] Productos actualizados: {actualizados}')
        if errores:
            self.stdout.write(self.style.WARNING(f'[!] Errores: {len(errores)}'))
        self.stdout.write('\n[EXITO] Inventario cargado')
        self.stdout.write('=' * 80)