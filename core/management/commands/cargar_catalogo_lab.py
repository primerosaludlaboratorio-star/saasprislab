"""
Comando Django para carga masiva del catálogo de laboratorio desde archivos CSV.

Uso:
    python manage.py cargar_catalogo_lab
    python manage.py cargar_catalogo_lab --parametros ruta/parametros.csv --rangos ruta/rangos.csv
    python manage.py cargar_catalogo_lab --limpiar  # Limpia BD antes de cargar

Autor: PRISLAB Engineering Team
Fecha: 2026-01-25
"""
import csv
import re
from decimal import Decimal
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
import os
import logging


class Command(BaseCommand):
    help = 'Carga masiva del catalogo de laboratorio desde CSVs'

    def add_arguments(self, parser):
        parser.add_argument(
            '--parametros',
            type=str,
            default='data/Parametros.csv',
            help='Ruta al archivo Parametros.csv'
        )
        parser.add_argument(
            '--rangos',
            type=str,
            default='data/Valores_normalidad.csv',
            help='Ruta al archivo Valores_normalidad.csv'
        )
        parser.add_argument(
            '--limpiar',
            action='store_true',
            help='Limpia la BD antes de cargar (CUIDADO)'
        )
        parser.add_argument(
            '--encoding',
            type=str,
            default='utf-8',
            help='Encoding del CSV (utf-8, latin-1, cp1252)'
        )

    def handle(self, *args, **options):
        raise CommandError(
            "DEPRECATED: Este comando opera sobre el catálogo legacy. "
            "Usa 'importar_catalogo_lims' para LIMS v7.5."
        )
        self.stdout.write('=' * 80)
        self.stdout.write('   CARGA MASIVA DE INTELIGENCIA LIMS')
        self.stdout.write('=' * 80)
        
        # Configuracion
        archivo_parametros = options['parametros']
        archivo_rangos = options['rangos']
        encoding = options['encoding']
        limpiar = options['limpiar']
        
        # Validar archivos
        if not os.path.exists(archivo_parametros):
            self.stdout.write(self.style.ERROR(f'\n[ERROR] Archivo no encontrado: {archivo_parametros}'))
            self.stdout.write('[TIP] Coloca el archivo en la carpeta data/ del proyecto')
            return
        
        if not os.path.exists(archivo_rangos):
            self.stdout.write(f'\n[AVISO] Archivo de rangos no encontrado: {archivo_rangos}')
            self.stdout.write('   Se cargaran solo los parametros sin rangos')
            archivo_rangos = None
        
        # Limpieza (opcional)
        if limpiar:
            self.stdout.write('\n[AVISO] LIMPIANDO BASE DE DATOS...')
            try:
                with transaction.atomic():
                    count_rangos = RangoReferencia.objects.all().delete()[0]
                    count_parametros = Parametro.objects.all().delete()[0]
                    count_estudios = Estudio.objects.all().delete()[0]
                    count_secciones = SeccionLaboratorio.objects.all().delete()[0]
                    
                    self.stdout.write(self.style.SUCCESS(f'   [OK] Eliminados: {count_rangos} rangos, {count_parametros} parametros'))
            except Exception as e:
                logging.getLogger(__name__).exception("Error inesperado en handle (cargar_catalogo_lab.py)")
                self.stdout.write(self.style.ERROR(f'   [ERROR] Error limpiando: {e}'))
                return
        
        # Estadisticas
        stats = {
            'secciones_creadas': 0,
            'estudios_creados': 0,
            'parametros_creados': 0,
            'rangos_creados': 0,
            'errores': 0
        }
        
        try:
            # FASE 1: Cargar Parametros
            self.stdout.write('\n>> FASE 1: Cargando Parametros...')
            with transaction.atomic():
                stats = self.cargar_parametros(archivo_parametros, encoding, stats)
            
            # FASE 2: Cargar Rangos
            if archivo_rangos:
                self.stdout.write('\n>> FASE 2: Cargando Rangos...')
                with transaction.atomic():
                    stats = self.cargar_rangos(archivo_rangos, encoding, stats)
            
            # Resumen
            self.stdout.write(self.style.SUCCESS('\n' + '=' * 80))
            self.stdout.write(self.style.SUCCESS('   CARGA COMPLETADA'))
            self.stdout.write(self.style.SUCCESS('=' * 80))
            self.stdout.write(f'\n>> ESTADISTICAS:')
            self.stdout.write(f'   - Secciones: {stats["secciones_creadas"]}')
            self.stdout.write(f'   - Estudios: {stats["estudios_creados"]}')
            self.stdout.write(f'   - Parametros: {stats["parametros_creados"]}')
            self.stdout.write(f'   - Rangos: {stats["rangos_creados"]}')
            if stats['errores'] > 0:
                self.stdout.write(f'   - Errores: {stats["errores"]}')
            
            self.stdout.write(self.style.SUCCESS(f'\n>> Sistema LIMS listo\n'))
        
        except Exception as e:
            logging.getLogger(__name__).exception("Error inesperado en handle (cargar_catalogo_lab.py)")
            self.stdout.write(self.style.ERROR(f'\n[ERROR] CRITICO: {e}'))
            import traceback
            traceback.print_exc()

    def cargar_parametros(self, archivo, encoding, stats):
        self.stdout.write(f'   Leyendo: {archivo}')
        
        # Leer CSV
        csv_data = None
        encodings = [encoding, 'utf-8', 'latin-1', 'cp1252']
        
        for enc in encodings:
            try:
                with open(archivo, 'r', encoding=enc) as f:
                    csv_data = list(csv.DictReader(f))
                    self.stdout.write(self.style.SUCCESS(f'   [OK] Archivo leido ({enc})'))
                    self.stdout.write(f'   Total filas: {len(csv_data)}')
                    break
            except:
                continue
        
        if not csv_data:
            self.stdout.write(self.style.ERROR('   [ERROR] No se pudo leer'))
            return stats
        
        if not csv_data:
            return stats
        
        headers = list(csv_data[0].keys())
        self.stdout.write(f'   Columnas: {", ".join(headers)}')
        
        col_map = self.detectar_columnas(headers)
        
        seccion_actual = None
        estudio_actual = None
        orden = 0
        
        for i, row in enumerate(csv_data, start=2):
            try:
                row_clean = {k: str(v).strip() if v else '' for k, v in row.items()}
                
                # SECCION
                nombre_seccion = row_clean.get(col_map.get('seccion', ''), '').upper()
                if nombre_seccion and nombre_seccion != seccion_actual:
                    seccion, created = SeccionLaboratorio.objects.get_or_create(
                        nombre=nombre_seccion,
                        defaults={'activo': True, 'orden': stats['secciones_creadas']}
                    )
                    if created:
                        stats['secciones_creadas'] += 1
                        self.stdout.write(self.style.SUCCESS(f'   [+] Seccion: {nombre_seccion}'))
                    seccion_actual = nombre_seccion
                else:
                    seccion = SeccionLaboratorio.objects.filter(nombre=seccion_actual).first()
                
                # ESTUDIO
                nombre_estudio = row_clean.get(col_map.get('estudio', ''), '').strip()
                if not nombre_estudio:
                    continue
                
                codigo_estudio = self.generar_codigo(nombre_estudio, seccion)
                precio = self.parse_precio(row_clean.get(col_map.get('precio', ''), '0'))
                metodologia = row_clean.get(col_map.get('metodologia', ''), '')
                
                estudio, created = Estudio.objects.get_or_create(
                    codigo=codigo_estudio,
                    defaults={
                        'nombre': nombre_estudio,
                        'seccion': seccion,
                        'precio': precio,
                        'metodologia': metodologia or '',
                        'activo': True,
                        'dias_entrega': 1
                    }
                )
                
                if created:
                    stats['estudios_creados'] += 1
                    self.stdout.write(f'      [+] {codigo_estudio} - {nombre_estudio}')
                    orden = 0
                
                estudio_actual = estudio
                
                # PARAMETRO
                nombre_parametro = row_clean.get(col_map.get('parametro', ''), '').strip()
                if not nombre_parametro:
                    continue
                
                unidad = row_clean.get(col_map.get('unidad', ''), '').strip()
                tipo_dato = self.detectar_tipo_dato(unidad, nombre_parametro)
                
                parametro, created = Parametro.objects.get_or_create(
                    estudio=estudio,
                    nombre=nombre_parametro,
                    defaults={
                        'unidad': unidad,
                        'tipo_dato': tipo_dato,
                        'orden_impresion': orden,
                        'activo': True,
                        'metodologia': metodologia or ''
                    }
                )
                
                if created:
                    stats['parametros_creados'] += 1
                    orden += 1
                    self.stdout.write(f'         - {nombre_parametro} ({unidad})')
            
            except Exception as e:
                logging.getLogger(__name__).exception("Error inesperado en cargar_parametros (cargar_catalogo_lab.py)")
                self.stdout.write(self.style.ERROR(f'   [ERROR] Fila {i}: {e}'))
                stats['errores'] += 1
        
        return stats

    def cargar_rangos(self, archivo, encoding, stats):
        self.stdout.write(f'   Leyendo: {archivo}')
        
        csv_data = None
        encodings = [encoding, 'utf-8', 'latin-1', 'cp1252']
        
        for enc in encodings:
            try:
                with open(archivo, 'r', encoding=enc) as f:
                    csv_data = list(csv.DictReader(f))
                    self.stdout.write(self.style.SUCCESS(f'   [OK] Leido ({enc})'))
                    break
            except:
                continue
        
        if not csv_data:
            return stats
        
        self.stdout.write(f'   Filas: {len(csv_data)}')
        
        headers = list(csv_data[0].keys())
        col_map = self.detectar_columnas_rangos(headers)
        
        for i, row in enumerate(csv_data, start=2):
            try:
                row_clean = {k: str(v).strip() if v else '' for k, v in row.items()}
                
                nombre_parametro = row_clean.get(col_map.get('parametro', ''), '').strip()
                if not nombre_parametro:
                    continue
                
                parametro = Parametro.objects.filter(
                    nombre__iexact=nombre_parametro
                ).first()
                
                if not parametro:
                    self.stdout.write(f'   [AVISO] Parametro "{nombre_parametro}" no encontrado')
                    stats['errores'] += 1
                    continue
                
                sexo_str = row_clean.get(col_map.get('sexo', ''), 'I').upper()
                sexo = self.parse_sexo(sexo_str)
                
                edad_str = row_clean.get(col_map.get('edad', ''), '')
                edad_min, edad_max = self.parse_edad(edad_str)
                
                valor_min = self.parse_decimal(row_clean.get(col_map.get('valor_min', ''), ''))
                valor_max = self.parse_decimal(row_clean.get(col_map.get('valor_max', ''), ''))
                panico_min = self.parse_decimal(row_clean.get(col_map.get('panico_min', ''), ''))
                panico_max = self.parse_decimal(row_clean.get(col_map.get('panico_max', ''), ''))
                
                rango, created = RangoReferencia.objects.get_or_create(
                    parametro=parametro,
                    sexo=sexo,
                    edad_minima=edad_min,
                    edad_maxima=edad_max,
                    defaults={
                        'valor_minimo': valor_min,
                        'valor_maximo': valor_max,
                        'panico_minimo': panico_min,
                        'panico_maximo': panico_max,
                        'activo': True
                    }
                )
                
                if created:
                    stats['rangos_creados'] += 1
                    self.stdout.write(f'      [+] {parametro.nombre} | {sexo} {edad_min or 0}-{edad_max or "inf"}')
            
            except Exception as e:
                logging.getLogger(__name__).exception("Error inesperado en cargar_rangos (cargar_catalogo_lab.py)")
                self.stdout.write(self.style.ERROR(f'   [ERROR] Fila {i}: {e}'))
                stats['errores'] += 1
        
        return stats

    def detectar_columnas(self, headers):
        col_map = {}
        for header in headers:
            h = header.lower().strip()
            if any(x in h for x in ['seccion', 'area', 'departamento']):
                col_map['seccion'] = header
            elif any(x in h for x in ['estudio', 'prueba', 'test']):
                col_map['estudio'] = header
            elif any(x in h for x in ['parametro', 'analito']):
                col_map['parametro'] = header
            elif any(x in h for x in ['unidad']):
                col_map['unidad'] = header
            elif any(x in h for x in ['metodo', 'metodologia']):
                col_map['metodologia'] = header
            elif any(x in h for x in ['precio', 'costo']):
                col_map['precio'] = header
        return col_map

    def detectar_columnas_rangos(self, headers):
        col_map = {}
        for header in headers:
            h = header.lower().strip()
            if any(x in h for x in ['parametro', 'analito']):
                col_map['parametro'] = header
            elif 'sexo' in h:
                col_map['sexo'] = header
            elif 'edad' in h:
                col_map['edad'] = header
            elif any(x in h for x in ['min', 'minimo']) and 'panico' not in h:
                col_map['valor_min'] = header
            elif any(x in h for x in ['max', 'maximo']) and 'panico' not in h:
                col_map['valor_max'] = header
            elif 'panico' in h and any(x in h for x in ['min', 'bajo']):
                col_map['panico_min'] = header
            elif 'panico' in h and any(x in h for x in ['max', 'alto']):
                col_map['panico_max'] = header
        return col_map

    def generar_codigo(self, nombre, seccion):
        palabras = nombre.upper().split()
        if len(palabras) >= 2:
            codigo = ''.join([p[0] for p in palabras[:3]])
        else:
            codigo = nombre[:3].upper()
        
        codigo_base = codigo
        contador = 1
        while Estudio.objects.filter(codigo=codigo).exists():
            codigo = f"{codigo_base}{contador:02d}"
            contador += 1
        
        return codigo

    def parse_precio(self, precio_str):
        try:
            precio_clean = precio_str.replace('$', '').replace(',', '').replace(' ', '').strip()
            if not precio_clean:
                return Decimal('0.00')
            return Decimal(precio_clean)
        except:
            return Decimal('0.00')

    def parse_decimal(self, valor_str):
        try:
            if not valor_str or valor_str.strip() == '':
                return None
            valor_clean = valor_str.replace(',', '.').strip()
            return Decimal(valor_clean)
        except:
            return None

    def parse_sexo(self, sexo_str):
        s = sexo_str.upper().strip()
        if s in ['M', 'MASCULINO', 'HOMBRE', 'H']:
            return 'M'
        elif s in ['F', 'FEMENINO', 'MUJER']:
            return 'F'
        else:
            return 'I'

    def parse_edad(self, edad_str):
        if not edad_str or edad_str.strip() == '':
            return (None, None)
        
        edad_str = edad_str.strip().lower()
        numeros = re.findall(r'\d+', edad_str)
        
        if not numeros:
            return (None, None)
        
        if 'dia' in edad_str or 'day' in edad_str:
            edad_min = int(numeros[0]) / 365 if numeros else 0
            edad_max = int(numeros[1]) / 365 if len(numeros) > 1 else edad_min
            return (int(edad_min), int(edad_max) if edad_max > 0 else None)
        elif 'mes' in edad_str or 'month' in edad_str:
            edad_min = int(numeros[0]) / 12 if numeros else 0
            edad_max = int(numeros[1]) / 12 if len(numeros) > 1 else edad_min
            return (int(edad_min), int(edad_max) if edad_max > 1 else 1)
        else:
            edad_min = int(numeros[0]) if numeros else None
            edad_max = int(numeros[1]) if len(numeros) > 1 else edad_min
            if '+' in edad_str:
                edad_max = None
            return (edad_min, edad_max)

    def detectar_tipo_dato(self, unidad, nombre):
        if not unidad:
            nombre_lower = nombre.lower()
            if any(x in nombre_lower for x in ['positivo', 'negativo']):
                return 'POSITIVO_NEGATIVO'
            elif any(x in nombre_lower for x in ['tipo', 'grupo']):
                return 'TEXTO_PREDEFINIDO'
            else:
                return 'TEXTO'
        else:
            return 'NUMERICO'