"""
Management command para cargar inventario de farmacia desde CSV.
Ejecutar: python manage.py cargar_inventario
"""
import csv
import os
from decimal import Decimal
from datetime import datetime
from django.core.management.base import BaseCommand
from django.db import transaction
from core.models import Producto
from core.utils.tenant_strict import add_argument_empresa_id, empresa_desde_management
import logging


class Command(BaseCommand):
    help = 'Carga el inventario de farmacia desde inventario.csv'

    def add_arguments(self, parser):
        parser.add_argument(
            '--archivo',
            type=str,
            default='inventario.csv',
            help='Nombre del archivo CSV a cargar (por defecto: inventario.csv)'
        )

    def handle(self, *args, **options):
        archivo = options['archivo']
        
        # Buscar el archivo en el directorio del proyecto
        if not os.path.exists(archivo):
            # Intentar en la raíz del proyecto
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
            archivo = os.path.join(base_dir, archivo)
        
        if not os.path.exists(archivo):
            self.stdout.write(self.style.ERROR(f'Archivo no encontrado: {archivo}'))
            return
        
        try:
            empresa = empresa_desde_management(options)
        except Exception as e:  # empresa_desde_management puede lanzar CommandError u otro error de config.
            logging.getLogger(__name__).exception("Error inesperado en handle (cargar_inventario.py)")
            self.stdout.write(self.style.ERROR(str(e)))
            return
        
        self.stdout.write(f'Cargando inventario desde: {archivo}')
        self.stdout.write(f'Empresa: {empresa.nombre}')
        self.stdout.write('=' * 60)
        
        creados = 0
        actualizados = 0
        sin_stock = 0
        errores = 0
        
        try:
            with open(archivo, 'r', encoding='utf-8') as f:
                reader = csv.reader(f)
                
                # Saltar las 2 primeras líneas vacías
                try:
                    next(reader)
                    next(reader)
                except StopIteration:
                    pass
                
                # Leer el encabezado
                try:
                    encabezado = next(reader)
                except StopIteration:
                    self.stdout.write(self.style.ERROR('Archivo CSV vacío o mal formado'))
                    return
                
                # Procesar cada línea
                for numero_linea, fila in enumerate(reader, start=4):
                    try:
                        # Validar que la fila tenga datos
                        if not fila or len(fila) < 2:
                            continue
                        
                        # Extraer datos relevantes
                        nombre = fila[0].strip() if len(fila) > 0 and fila[0] else None
                        identificador = fila[1].strip() if len(fila) > 1 and fila[1] else None
                        
                        # Validaciones básicas
                        if not nombre or not identificador:
                            continue
                        
                        # Otros campos opcionales
                        categoria_nombre = fila[5].strip() if len(fila) > 5 and fila[5] else 'GENERICO'
                        marca = fila[6].strip() if len(fila) > 6 and fila[6] else 'GENERICO'
                        codigo_barras = fila[8].strip() if len(fila) > 8 and fila[8] else f'BAR-{identificador}'
                        
                        # Stock (columna 19)
                        try:
                            stock_str = fila[19].strip() if len(fila) > 19 and fila[19] else '0'
                            stock = int(float(stock_str.replace(',', '').replace('$', '').strip()))
                        except (ValueError, IndexError, AttributeError):
                            stock = 0
                        
                        # Saltar productos con stock 0 (lotes vencidos/agotados)
                        if stock <= 0:
                            sin_stock += 1
                            continue
                        
                        # Precios
                        try:
                            precio_publico_str = fila[23].strip() if len(fila) > 23 and fila[23] else '0'
                            precio_publico = Decimal(precio_publico_str.replace(',', '').replace('$', '').strip())
                        except (ValueError, IndexError, AttributeError):
                            precio_publico = Decimal('0')
                        
                        try:
                            costo_str = fila[26].strip() if len(fila) > 26 and fila[26] else '0'
                            costo = Decimal(costo_str.replace(',', '').replace('$', '').strip())
                        except (ValueError, IndexError, AttributeError):
                            costo = Decimal('0')
                        
                        # Receta médica
                        try:
                            requiere_receta_str = fila[31].strip() if len(fila) > 31 and fila[31] else 'No'
                            requiere_receta = requiere_receta_str.upper() == 'SI'
                        except (IndexError, AttributeError):
                            requiere_receta = False
                        
                        # Mapeo de categoría a CATEGORIAS de Producto
                        categoria_map = {
                            'ANTIBIOTICO': 'ANTIBIOTICO',
                            'PATENTE': 'PATENTE',
                            'GENERICO': 'GENERICO',
                            'CURACION': 'CURACION',
                        }
                        categoria = categoria_map.get(categoria_nombre.upper(), 'GENERICO')
                        
                        # Clasificación sanitaria
                        if requiere_receta:
                            clasificacion = 'IV'  # Antibióticos
                        else:
                            clasificacion = 'VI'  # Venta libre
                        
                        # Crear o actualizar producto
                        with transaction.atomic():
                            producto, created = Producto.objects.update_or_create(
                                codigo_barras=codigo_barras,
                                defaults={
                                    'empresa': empresa,
                                    'nombre': nombre[:255],  # Limitar longitud
                                    'marca_laboratorio': marca[:150] if marca else 'GENERICO',
                                    'sustancia_activa': '',  # No disponible en CSV
                                    'forma_farmaceutica': 'Unidad',  # Default
                                    'concentracion': '',  # No disponible
                                    'presentacion': '1',  # Default
                                    'clasificacion_sanitaria': clasificacion,
                                    'categoria': categoria,
                                    'precio_compra': costo,
                                    'precio_publico': precio_publico,
                                    'iva_porcentaje': Decimal('16.00'),  # IVA estándar
                                    'stock': stock,
                                    'es_antibiotico': requiere_receta,
                                    'es_servicio': False,
                                }
                            )
                            
                            if created:
                                creados += 1
                                msg = f"  [+] {nombre[:45]:<45} | Stock: {stock:>4} | ${precio_publico:>7.2f}"
                                self.stdout.write(self.style.SUCCESS(msg))
                            else:
                                actualizados += 1
                                msg = f"  [~] {nombre[:45]:<45} | Stock: {stock:>4} | ${precio_publico:>7.2f}"
                                self.stdout.write(msg)
                    
                    except Exception as e:  # Aislamiento fila-por-fila: error en una fila no debe abortar toda la carga.
                        logging.getLogger(__name__).exception("Error inesperado en handle (cargar_inventario.py)")
                        errores += 1
                        self.stdout.write(self.style.WARNING(
                            f"  [!] Error en linea {numero_linea}: {str(e)}"
                        ))
        
        except Exception as e:  # Integración externa: archivo CSV/texto provisto por usuario (cualquier encoding, formato inválido).
            logging.getLogger(__name__).exception("Error inesperado en handle (cargar_inventario.py)")
            self.stdout.write(self.style.ERROR(f'Error al leer archivo: {str(e)}'))
            import traceback
            self.stdout.write(traceback.format_exc())
            return
        
        # Resumen
        self.stdout.write('=' * 60)
        self.stdout.write(self.style.SUCCESS(f'PROCESO COMPLETADO:'))
        self.stdout.write(f'  + {creados} productos nuevos')
        self.stdout.write(f'  ~ {actualizados} productos actualizados')
        self.stdout.write(f'  - {sin_stock} productos sin stock (omitidos)')
        self.stdout.write(f'  ! {errores} errores')
        total_con_stock = Producto.objects.filter(stock__gt=0).count()
        self.stdout.write(f'  = Total en BD: {total_con_stock} productos con stock')