import csv
import os
import re
from decimal import Decimal, InvalidOperation
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from core.utils.tenant_strict import add_argument_empresa_id, empresa_desde_management
import logging


class Command(BaseCommand):
    help = 'Importa catálogo de estudios clínicos desde archivo CSV'

    def add_arguments(self, parser):
        add_argument_empresa_id(parser, required=True)
        parser.add_argument(
            '--archivo',
            type=str,
            help='Nombre del archivo CSV (buscará en la raíz del proyecto)',
            default='Tarifa_Detalle_20260114_064905.xlsx - Reporte.csv'
        )

    def handle(self, *args, **options):
        raise CommandError(
            "DEPRECATED: Este comando opera sobre el catálogo legacy. "
            "Usa 'importar_catalogo_lims' para LIMS v7.5."
        )
        archivo_nombre = options['archivo']
        archivo_path = os.path.join(settings.BASE_DIR, archivo_nombre)
        
        # Si no existe con ese nombre exacto, buscar cualquier CSV que contenga "Tarifa" o "Reporte"
        if not os.path.exists(archivo_path):
            self.stdout.write(self.style.WARNING(f'No se encontró "{archivo_nombre}", buscando archivos CSV...'))
            archivos_csv = [f for f in os.listdir(settings.BASE_DIR) if f.endswith('.csv')]
            if archivos_csv:
                # Buscar uno que contenga "Tarifa" o "Reporte"
                for f in archivos_csv:
                    if 'tarifa' in f.lower() or 'reporte' in f.lower():
                        archivo_path = os.path.join(settings.BASE_DIR, f)
                        self.stdout.write(self.style.SUCCESS(f'Archivo encontrado: {f}'))
                        break
                else:
                    # Si no encuentra uno específico, usar el primero
                    archivo_path = os.path.join(settings.BASE_DIR, archivos_csv[0])
                    self.stdout.write(self.style.SUCCESS(f'Usando archivo: {archivos_csv[0]}'))
            else:
                self.stdout.write(self.style.ERROR(f'No se encontró ningún archivo CSV en {settings.BASE_DIR}'))
                return
        
        if not os.path.exists(archivo_path):
            self.stdout.write(self.style.ERROR(f'No se encontró el archivo: {archivo_path}'))
            return

        try:
            empresa = empresa_desde_management(options)
        except Exception as e:
            logging.getLogger(__name__).exception("Error inesperado en handle (importar_csv_lab.py)")
            self.stdout.write(self.style.ERROR(str(e)))
            return

        self.stdout.write(self.style.WARNING(f'🚀 Iniciando importación desde: {os.path.basename(archivo_path)}'))

        def limpiar_precio(valor):
            """Convierte un string de precio a Decimal, quitando comas y símbolos."""
            if not valor or str(valor).strip() == '' or str(valor).lower() == 'nan':
                return Decimal('0.00')
            # Quitar comas, espacios, símbolos de moneda
            limpio = str(valor).replace('$', '').replace(',', '').replace(' ', '').strip()
            try:
                return Decimal(limpio)
            except (InvalidOperation, ValueError):
                return Decimal('0.00')

        def extraer_dias(valor):
            """Extrae el número de días de un string como '2 días' o '1 día'."""
            if not valor or str(valor).strip() == '':
                return 0
            # Buscar el primer número en el string
            match = re.search(r'\d+', str(valor))
            if match:
                return int(match.group())
            return 0

        def encontrar_header(reader):
            """Busca la línea que contiene el header correcto."""
            for i, row in enumerate(reader):
                if row and len(row) > 0:
                    # Buscar la línea que empieza con "Tipo" o contiene "Tipo,Código"
                    primera_col = str(row[0]).strip() if row[0] else ''
                    if primera_col.lower() in ['tipo', 'tipo,código', 'tipo,codigo']:
                        return row, i
            return None, None

        try:
            # Intentar diferentes encodings
            encodings = ['utf-8-sig', 'utf-8', 'latin-1', 'cp1252']
            reader_obj = None
            encoding_usado = None
            
            for enc in encodings:
                try:
                    f = open(archivo_path, 'r', encoding=enc)
                    reader_obj = csv.reader(f)
                    encoding_usado = enc
                    break
                except UnicodeDecodeError:
                    continue
            
            if reader_obj is None:
                self.stdout.write(self.style.ERROR('No se pudo leer el archivo con ningún encoding'))
                return

            # Buscar el header
            header_row, header_line = encontrar_header(reader_obj)
            
            if header_row is None:
                self.stdout.write(self.style.ERROR('No se encontró la línea de encabezado (Tipo, Código, ...)'))
                return

            # Crear diccionario de índices de columnas
            header_lower = [str(col).strip().lower() for col in header_row]
            indices = {}
            for i, col in enumerate(header_lower):
                if 'tipo' in col:
                    indices['tipo'] = i
                elif 'código' in col or 'codigo' in col:
                    indices['codigo'] = i
                elif 'abreviatura' in col:
                    indices['abreviatura'] = i
                elif 'descripción' in col or 'descripcion' in col:
                    indices['descripcion'] = i
                elif 'importe' in col or 'precio' in col:
                    indices['precio'] = i
                elif 'tiempo' in col and 'proceso' in col:
                    indices['tiempo'] = i
                elif 'indicaciones' in col:
                    indices['indicaciones'] = i
                elif 'muestra' in col:
                    indices['muestra'] = i
                elif 'incluidos' in col or 'estudios' in col:
                    indices['estudios_incluidos'] = i

            self.stdout.write(self.style.SUCCESS(f'Header encontrado en línea {header_line + 1}'))
            self.stdout.write(f'Columnas detectadas: {indices}')

            # Obtener o crear categorías
            cat_paquetes, _ = CategoriaEstudio.objects.get_or_create(nombre='PAQUETES')
            cat_general, _ = CategoriaEstudio.objects.get_or_create(nombre='GENERAL')

            contador_creados = 0
            contador_actualizados = 0
            contador_errores = 0

            # Leer las filas de datos
            for row_num, row in enumerate(reader_obj, start=header_line + 2):
                if not row or len(row) < max(indices.values(), default=0) + 1:
                    continue

                try:
                    # Extraer datos según los índices
                    tipo = str(row[indices.get('tipo', 0)]).strip() if indices.get('tipo') is not None else ''
                    codigo = str(row[indices.get('codigo', 1)]).strip() if indices.get('codigo') is not None else ''
                    
                    if not codigo or codigo.lower() in ['', 'nan', 'none']:
                        continue

                    descripcion = str(row[indices.get('descripcion', 2)]).strip() if indices.get('descripcion') is not None else ''
                    abreviatura = str(row[indices.get('abreviatura', -1)]).strip() if indices.get('abreviatura') is not None and indices.get('abreviatura') < len(row) else ''
                    
                    precio_str = str(row[indices.get('precio', 3)]).strip() if indices.get('precio') is not None else '0'
                    precio = limpiar_precio(precio_str)
                    
                    tiempo_str = str(row[indices.get('tiempo', 4)]).strip() if indices.get('tiempo') is not None else '0'
                    dias_entrega = extraer_dias(tiempo_str)
                    
                    indicaciones = str(row[indices.get('indicaciones', 5)]).strip() if indices.get('indicaciones') is not None and indices.get('indicaciones') < len(row) else ''
                    muestra = str(row[indices.get('muestra', 6)]).strip() if indices.get('muestra') is not None and indices.get('muestra') < len(row) else 'Suero'
                    estudios_incluidos = str(row[indices.get('estudios_incluidos', 7)]).strip() if indices.get('estudios_incluidos') is not None and indices.get('estudios_incluidos') < len(row) else ''

                    # Determinar si es perfil
                    es_perfil = tipo.lower() in ['paquetes', 'paquete', 'perfil', 'perfiles']
                    
                    # Asignar categoría
                    if es_perfil:
                        categoria = cat_paquetes
                    else:
                        categoria = cat_general

                    # Actualizar o crear estudio
                    estudio, creado = Estudio.objects.update_or_create(
                        codigo=codigo,
                        defaults={
                            'nombre': descripcion[:200] if descripcion else f'Estudio {codigo}',
                            'abreviatura': abreviatura[:50] if abreviatura else None,
                            'precio': precio,
                            'categoria': categoria,
                            'dias_entrega': dias_entrega,
                            'muestra_requerida': muestra[:100] if muestra else 'Suero',
                            'indicaciones': indicaciones if indicaciones else 'Ayuno 8 hrs',
                            'descripcion_interna': estudios_incluidos if estudios_incluidos else '',
                            'es_perfil': es_perfil,
                            'activo': True
                        }
                    )

                    if creado:
                        contador_creados += 1
                        self.stdout.write(self.style.SUCCESS(f'✓ Creado: {codigo} - {descripcion[:50]}'))
                    else:
                        contador_actualizados += 1
                        self.stdout.write(self.style.WARNING(f'↻ Actualizado: {codigo} - {descripcion[:50]} (Precio: ${precio})'))

                except Exception as e:
                    logging.getLogger(__name__).exception("Error inesperado en encontrar_header (importar_csv_lab.py)")
                    contador_errores += 1
                    self.stdout.write(self.style.ERROR(f'✗ Error en línea {row_num}: {str(e)}'))
                    continue

            f.close()

            # Resumen
            self.stdout.write(self.style.SUCCESS('\n' + '='*50))
            self.stdout.write(self.style.SUCCESS(f'✅ IMPORTACIÓN COMPLETADA'))
            self.stdout.write(self.style.SUCCESS(f'   Creados: {contador_creados}'))
            self.stdout.write(self.style.SUCCESS(f'   Actualizados: {contador_actualizados}'))
            self.stdout.write(self.style.SUCCESS(f'   Errores: {contador_errores}'))
            self.stdout.write(self.style.SUCCESS(f'   Total procesados: {contador_creados + contador_actualizados}'))
            self.stdout.write(self.style.SUCCESS('='*50))

        except Exception as e:
            logging.getLogger(__name__).exception("Error inesperado en encontrar_header (importar_csv_lab.py)")
            self.stdout.write(self.style.ERROR(f'Error fatal: {str(e)}'))
            import traceback
            self.stdout.write(self.style.ERROR(traceback.format_exc()))