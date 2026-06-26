"""
COMANDO: Carga desde CSV (el más confiable)
Uso: python manage.py cargar_productos_csv <archivo.csv>
"""
import os
import csv
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.db import transaction
from core.models import Producto, Empresa, Sucursal
import logging


class Command(BaseCommand):
    help = 'Carga productos desde CSV'

    def add_arguments(self, parser):
        parser.add_argument('archivo', type=str)
        parser.add_argument('--empresa-id', type=int, default=1)

    def handle(self, *args, **options):
        archivo = options['archivo']
        empresa_id = options['empresa_id']

        try:
            empresa = Empresa.objects.get(id=empresa_id)
            sucursal = Sucursal.objects.filter(empresa=empresa).first()
        except Empresa.DoesNotExist:
            self.stdout.write(self.style.ERROR('[ERROR] Empresa no encontrada'))
            return

        self.stdout.write('=' * 80)
        self.stdout.write(self.style.SUCCESS('CARGA DESDE CSV'))
        self.stdout.write('=' * 80)

        try:
            with open(archivo, 'r', encoding='utf-8-sig', errors='replace') as f:
                reader = csv.DictReader(f)
                
                creados = 0
                actualizados = 0
                
                with transaction.atomic():
                    for row in reader:
                        try:
                            nombre = row.get('Nombre del Producto', '').strip()
                            codigo = (
                                row.get('Código de Barras', '') or
                                row.get('SKU', '') or
                                row.get('Identificador (No Cambiar)', '')
                            ).strip()

                            if not nombre or not codigo:
                                continue

                            marca = row.get('Marca', 'GENERICO').strip()
                            
                            precio_str = row.get('Precio Público', '0').replace(',', '').replace('$', '').strip()
                            precio = Decimal(precio_str) if precio_str else Decimal('0')
                            
                            costo_str = row.get('Costo', '0').replace(',', '').replace('$', '').strip()
                            costo = Decimal(costo_str) if costo_str else Decimal('0')
                            
                            # La columna tiene espacio extra: "Stock Total "
                            stock_str = (row.get('Stock Total ', '') or row.get('Stock Total', '0')).strip()
                            stock = int(float(stock_str)) if stock_str and stock_str != '0' else 0
                            
                            iva_str = row.get('IVA', '16%').replace('%', '').strip()
                            iva = Decimal(iva_str) if iva_str else Decimal('16')
                            
                            receta = row.get('Receta Médica', 'No').lower()
                            es_antibiotico = any(k in receta for k in ['sí', 'si', 'obligatorio'])

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
                                    self.stdout.write(f'  [{creados} productos...]')
                            else:
                                actualizados += 1

                        except Exception as e:  # Aislamiento fila-por-fila: error en una fila no debe abortar toda la carga.
                            logging.getLogger(__name__).exception("Error inesperado en handle (cargar_productos_csv.py)")
                            self.stdout.write(self.style.WARNING(f'  [!] Error: {e}'))
                            continue

                self.stdout.write('\n' + '=' * 80)
                self.stdout.write(f'[OK] Creados: {creados}')
                self.stdout.write(f'[OK] Actualizados: {actualizados}')
                self.stdout.write(self.style.SUCCESS('\n[EXITO] Carga completada'))
                self.stdout.write('=' * 80)

        except Exception as e:  # Integración externa: archivo CSV provisto por usuario (encoding, delimitador o formato inválido).
            logging.getLogger(__name__).exception("Error inesperado en handle (cargar_productos_csv.py)")
            self.stdout.write(self.style.ERROR(f'[ERROR] {e}'))