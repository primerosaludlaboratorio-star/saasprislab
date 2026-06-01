import csv
import os
from datetime import datetime
from django.core.management.base import BaseCommand
from django.conf import settings
from core.models import Producto, Lote, Usuario
from core.utils.tenant_strict import add_argument_empresa_id, empresa_desde_management


class Command(BaseCommand):
    help = 'Carga masiva de inventario PRISLAB con rigor sanitario y fiscal'

    def add_arguments(self, parser):
        add_argument_empresa_id(parser, required=True)

    def handle(self, *args, **kwargs):
        try:
            empresa = empresa_desde_management(kwargs)
        except Exception as e:
            self.stdout.write(self.style.ERROR(str(e)))
            return

        archivo = os.path.join(settings.BASE_DIR, 'inventario.csv')

        if not os.path.exists(archivo):
            self.stdout.write(self.style.ERROR(f'No encuentro el archivo "inventario.csv" en {settings.BASE_DIR}'))
            return

        self.stdout.write(self.style.WARNING(f'🚀 Iniciando carga robusta para {empresa.nombre}...'))

        def limpiar_numero(valor):
            if not valor or valor == 'nan': return 0.0
            limpio = str(valor).replace('$', '').replace(',', '').strip()
            try:
                return float(limpio)
            except ValueError:
                return 0.0

        try:
            # Usamos utf-8-sig para manejar el BOM de Excel
            with open(archivo, 'r', encoding='utf-8-sig') as f:
                reader = csv.reader(f)
                # Saltar las 3 líneas de encabezado que tiene tu archivo
                next(reader); next(reader); next(reader)
                
                c_prod = 0
                c_lote = 0

                for row in reader:
                    if not row or len(row) < 30: continue

                    # Mapeo según la estructura real de tu inventario.csv
                    nombre = row[0].strip().upper()
                    sustancia = row[4].strip().upper() if row[4] else "NO ESPECIFICADO"
                    marca = row[6].strip().upper() if row[6] else "GENÉRICO"
                    codigo = row[8].strip()
                    if not codigo or codigo == 'nan': 
                        codigo = row[1].strip() # Usar identificador si no hay barras

                    lote_num = row[15].strip()
                    caducidad_str = row[17].strip()
                    
                    stock = limpiar_numero(row[19])
                    precio = limpiar_numero(row[23])
                    costo = limpiar_numero(row[26])
                    
                    # IVA: Columna 28 (Si dice 16% ponemos 16, si no 0)
                    iva_pct = 16.0 if '16' in row[28] else 0.0
                    es_antibiotico = True if row[31].strip().lower() == 'si' else False

                    # Corrección de Fecha DD/MM/YYYY
                    if not caducidad_str or caducidad_str == 'nan':
                        fecha_cad = datetime.strptime('2030-01-01', '%Y-%m-%d').date()
                    else:
                        try:
                            # Tu archivo viene como 01/06/2027
                            fecha_cad = datetime.strptime(caducidad_str, '%d/%m/%Y').date()
                        except:
                            fecha_cad = datetime.strptime('2030-01-01', '%Y-%m-%d').date()

                    # 1. Crear o Actualizar Producto (Sin duplicar)
                    prod, created = Producto.objects.update_or_create(
                        codigo_barras=codigo,
                        empresa=empresa,
                        defaults={
                            'nombre': nombre,
                            'sustancia_activa': sustancia,
                            'marca_laboratorio': marca,
                            'precio_publico': precio,
                            'iva_porcentaje': iva_pct,
                            'es_antibiotico': es_antibiotico,
                            'linea': row[5].strip().upper() if row[5] else "GENERAL",
                            'forma_farmaceutica': row[7].strip().upper() if row[7] else "UNIDAD"
                        }
                    )
                    if created: c_prod += 1

                    # 2. Crear Lote (Trazabilidad PEPS)
                    if lote_num and lote_num != 'nan':
                        Lote.objects.get_or_create(
                            producto=prod,
                            numero_lote=lote_num,
                            defaults={
                                'fecha_caducidad': fecha_cad,
                                'cantidad': int(stock),
                                'costo_adquisicion': costo
                            }
                        )
                        # Actualizar stock total del producto
                        prod.stock = sum(l.cantidad for l in prod.lotes.all())
                        prod.save()
                        c_lote += 1

            self.stdout.write(self.style.SUCCESS(f'--- CARGA FINALIZADA ---'))
            self.stdout.write(self.style.SUCCESS(f'✔ Productos: {c_prod} nuevos/actualizados'))
            self.stdout.write(self.style.SUCCESS(f'✔ Lotes procesados: {c_lote}'))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ Error grave en proceso: {str(e)}'))