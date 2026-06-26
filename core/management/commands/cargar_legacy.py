"""
Comando Django para carga de datos legacy desde archivos CSV relacionales.

ARQUITECTURA DE ENSAMBLAJE:
1. Parametros.csv → Diccionario en memoria
2. Examenes.csv → Crear Estudios
3. Examenes_Perfil.csv → Vincular Estudios con Parametros
4. Valores_normalidad.csv → Rangos de referencia

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
    help = 'Carga datos legacy desde archivos CSV relacionales'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dir',
            type=str,
            default='datos_lims',
            help='Directorio con archivos CSV legacy'
        )

    def handle(self, *args, **options):
        raise CommandError(
            "DEPRECATED: Este comando opera sobre el catálogo legacy. "
            "Usa 'importar_catalogo_lims' para LIMS v7.5."
        )
        self.stdout.write('=' * 80)
        self.stdout.write('   MOTOR DE INGESTA LEGACY - LIMS V5')
        self.stdout.write('=' * 80)
        
        dir_legacy = options['dir']
        
        # Validar directorio
        if not os.path.exists(dir_legacy):
            self.stdout.write(self.style.ERROR(f'\n[ERROR] Directorio no encontrado: {dir_legacy}'))
            return
        
        # Archivos requeridos
        archivos = {
            'parametros': os.path.join(dir_legacy, 'Parametros.csv'),
            'examenes': os.path.join(dir_legacy, 'Examenes.csv'),
            'perfil': os.path.join(dir_legacy, 'Examenes_Perfil.csv'),
            'rangos': os.path.join(dir_legacy, 'Valores_normalidad.csv')
        }
        
        # Validar existencia
        for nombre, ruta in archivos.items():
            if not os.path.exists(ruta):
                self.stdout.write(self.style.WARNING(f'[AVISO] {nombre} no encontrado: {ruta}'))
        
        stats = {
            'secciones': 0,
            'estudios': 0,
            'parametros': 0,
            'rangos': 0,
            'errores': 0
        }
        
        try:
            with transaction.atomic():
                # FASE 1: Cargar definiciones de parámetros en memoria
                self.stdout.write('\n>> FASE 1: Cargando diccionario de parametros...')
                dict_parametros = self.cargar_dict_parametros(archivos['parametros'])
                self.stdout.write(f'   [OK] {len(dict_parametros)} definiciones en memoria')
                
                # FASE 2: Crear estudios
                self.stdout.write('\n>> FASE 2: Creando estudios...')
                dict_estudios = self.cargar_estudios(archivos['examenes'], stats)
                self.stdout.write(f'   [OK] {stats["estudios"]} estudios creados')
                
                # FASE 3: Ensamblar (Vincular estudios con parámetros)
                self.stdout.write('\n>> FASE 3: Ensamblando estudios + parametros...')
                self.ensamblar_perfil(archivos['perfil'], dict_estudios, dict_parametros, stats)
                self.stdout.write(f'   [OK] {stats["parametros"]} parametros vinculados')
                
                # FASE 4: Cargar rangos de referencia
                if os.path.exists(archivos['rangos']):
                    self.stdout.write('\n>> FASE 4: Cargando rangos de referencia...')
                    self.cargar_rangos(archivos['rangos'], stats)
                    self.stdout.write(f'   [OK] {stats["rangos"]} rangos creados')
            
            # Resumen final
            self.stdout.write(self.style.SUCCESS('\n' + '=' * 80))
            self.stdout.write(self.style.SUCCESS('   SISTEMA RECONSTRUIDO DESDE LEGACY'))
            self.stdout.write(self.style.SUCCESS('=' * 80))
            self.stdout.write(f'\n>> ESTADISTICAS FINALES:')
            self.stdout.write(f'   - Secciones: {stats["secciones"]}')
            self.stdout.write(f'   - Estudios: {stats["estudios"]}')
            self.stdout.write(f'   - Parametros inyectados: {stats["parametros"]}')
            self.stdout.write(f'   - Rangos: {stats["rangos"]}')
            if stats['errores'] > 0:
                self.stdout.write(f'   - Errores: {stats["errores"]}')
            self.stdout.write(self.style.SUCCESS('\n>> Sistema LIMS V5 listo para operacion\n'))
        
        except Exception as e:
            logging.getLogger(__name__).exception("Error inesperado en handle (cargar_legacy.py)")
            self.stdout.write(self.style.ERROR(f'\n[ERROR] CRITICO: {e}'))
            import traceback
            traceback.print_exc()

    def cargar_dict_parametros(self, archivo):
        """
        PASO A: Carga Parametros.csv en diccionario en memoria.
        Key: Codigo
        Value: {Nombre, Unidad, Depto, Metodo, etc}
        """
        if not os.path.exists(archivo):
            return {}
        
        dict_parametros = {}
        encodings = ['utf-8', 'latin-1', 'cp1252']
        
        for enc in encodings:
            try:
                with open(archivo, 'r', encoding=enc) as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        codigo = row.get('Codigo', row.get('codigo', '')).strip()
                        if codigo:
                            dict_parametros[codigo] = {
                                'nombre': row.get('Nombre', row.get('nombre', row.get('Descripcion', ''))).strip(),
                                'unidad': row.get('Unidad', row.get('unidad', '')).strip(),
                                'depto': row.get('Depto', row.get('depto', row.get('Seccion', ''))).strip(),
                                'metodo': row.get('Metodo', row.get('metodo', row.get('Metodologia', ''))).strip(),
                            }
                break
            except:
                continue
        
        return dict_parametros

    def cargar_estudios(self, archivo, stats):
        """
        PASO B: Lee Examenes.csv y crea objetos Estudio.
        Retorna diccionario {Codigo: Estudio} para acceso rápido.
        """
        if not os.path.exists(archivo):
            return {}
        
        dict_estudios = {}
        encodings = ['utf-8', 'latin-1', 'cp1252']
        
        for enc in encodings:
            try:
                with open(archivo, 'r', encoding=enc) as f:
                    reader = csv.DictReader(f)
                    
                    for i, row in enumerate(reader, start=2):
                        try:
                            codigo = row.get('Codigo', row.get('codigo', '')).strip()
                            nombre = row.get('Descripcion', row.get('descripcion', row.get('Nombre', ''))).strip()
                            precio_str = row.get('Costo', row.get('costo', row.get('Precio', '0'))).strip()
                            depto = row.get('Depto', row.get('depto', row.get('Seccion', ''))).strip().upper()
                            
                            if not codigo or not nombre:
                                continue
                            
                            # Crear/obtener sección
                            seccion = None
                            if depto:
                                seccion, created = SeccionLaboratorio.objects.get_or_create(
                                    nombre=depto,
                                    defaults={'activo': True, 'orden': stats['secciones']}
                                )
                                if created:
                                    stats['secciones'] += 1
                            
                            # Parsear precio
                            try:
                                precio = Decimal(precio_str.replace('$', '').replace(',', '').strip() or '0')
                            except:
                                precio = Decimal('0.00')
                            
                            # Crear estudio
                            estudio, created = Estudio.objects.get_or_create(
                                codigo=codigo,
                                defaults={
                                    'nombre': nombre,
                                    'seccion': seccion,
                                    'precio': precio,
                                    'activo': True,
                                    'dias_entrega': 1
                                }
                            )
                            
                            if created:
                                stats['estudios'] += 1
                                dict_estudios[codigo] = estudio
                                self.stdout.write(f'      [+] {codigo} - {nombre}')
                            else:
                                dict_estudios[codigo] = estudio
                        
                        except Exception as e:
                            logging.getLogger(__name__).exception("Error inesperado en cargar_estudios (cargar_legacy.py)")
                            self.stdout.write(f'   [ERROR] Fila {i}: {e}')
                            stats['errores'] += 1
                
                break
            except:
                continue
        
        return dict_estudios

    def ensamblar_perfil(self, archivo, dict_estudios, dict_parametros, stats):
        """
        PASO C: Lee Examenes_Perfil.csv y vincula Estudios con Parametros.
        Columna 0 (o 'Examen'): Codigo del Estudio Padre
        Columna 3 (o 'Codigo'): Codigo del Parametro Hijo
        """
        if not os.path.exists(archivo):
            return
        
        encodings = ['utf-8', 'latin-1', 'cp1252']
        
        for enc in encodings:
            try:
                with open(archivo, 'r', encoding=enc) as f:
                    reader = csv.reader(f)
                    headers = next(reader, None)  # Primera fila (headers agrupados)
                    headers2 = next(reader, None)  # Segunda fila (headers reales)
                    
                    # Usar segunda fila como headers reales
                    idx_examen = 0  # "Codigo" del examen
                    idx_codigo_param = 3  # "Codigo" del parámetro
                    
                    for i, row in enumerate(reader, start=3):  # Empezar en fila 3 (después de 2 headers)
                        try:
                            if len(row) <= max(idx_examen, idx_codigo_param):
                                continue
                            
                            codigo_estudio = row[idx_examen].strip()
                            codigo_parametro = row[idx_codigo_param].strip()
                            
                            if not codigo_estudio or not codigo_parametro:
                                continue
                            
                            # Buscar estudio
                            estudio = dict_estudios.get(codigo_estudio)
                            if not estudio:
                                self.stdout.write(f'   [AVISO] Estudio no encontrado: {codigo_estudio}')
                                continue
                            
                            # Buscar definición de parámetro
                            def_parametro = dict_parametros.get(codigo_parametro)
                            if not def_parametro:
                                # Si no está en el diccionario, usar el código como nombre
                                def_parametro = {
                                    'nombre': codigo_parametro,
                                    'unidad': '',
                                    'depto': '',
                                    'metodo': ''
                                }
                            
                            # Crear parámetro vinculado
                            parametro, created = Parametro.objects.get_or_create(
                                estudio=estudio,
                                nombre=def_parametro['nombre'],
                                defaults={
                                    'unidad': def_parametro['unidad'],
                                    'tipo_dato': 'NUMERICO' if def_parametro['unidad'] else 'TEXTO',
                                    'orden_impresion': stats['parametros'],
                                    'activo': True,
                                    'metodologia': def_parametro['metodo']
                                }
                            )
                            
                            if created:
                                stats['parametros'] += 1
                                if stats['parametros'] <= 20:  # Mostrar solo primeros 20
                                    self.stdout.write(f'      [+] {estudio.codigo} > {def_parametro["nombre"]}')
                        
                        except Exception as e:
                            logging.getLogger(__name__).exception("Error inesperado en ensamblar_perfil (cargar_legacy.py)")
                            stats['errores'] += 1
                
                break
            except:
                continue

    def cargar_rangos(self, archivo, stats):
        """
        PASO D: Lee Valores_normalidad.csv y crea RangoReferencia.
        Busca parámetros por código o nombre.
        """
        if not os.path.exists(archivo):
            return
        
        encodings = ['utf-8', 'latin-1', 'cp1252']
        
        for enc in encodings:
            try:
                with open(archivo, 'r', encoding=enc) as f:
                    reader = csv.DictReader(f)
                    
                    for i, row in enumerate(reader, start=2):
                        try:
                            # Buscar parámetro
                            codigo_param = row.get('Codigo', row.get('codigo', '')).strip()
                            nombre_param = row.get('Parametro', row.get('parametro', row.get('Nombre', ''))).strip()
                            
                            if not codigo_param and not nombre_param:
                                continue
                            
                            # Buscar parámetro en BD
                            parametro = None
                            if codigo_param:
                                parametro = Parametro.objects.filter(nombre__icontains=codigo_param).first()
                            if not parametro and nombre_param:
                                parametro = Parametro.objects.filter(nombre__iexact=nombre_param).first()
                            
                            if not parametro:
                                continue
                            
                            # Parsear sexo
                            sexo_str = row.get('Sexo', row.get('sexo', 'I')).strip().upper()
                            sexo = 'M' if sexo_str in ['M', 'H', 'MASCULINO'] else ('F' if sexo_str in ['F', 'FEMENINO'] else 'I')
                            
                            # Parsear edad
                            edad_str = row.get('Edad', row.get('edad', row.get('Rango Edad', ''))).strip()
                            edad_min, edad_max = self.parse_edad(edad_str)
                            
                            # Parsear valores
                            valor_min = self.parse_decimal(row.get('Valor Minimo', row.get('valor_minimo', row.get('Min', ''))))
                            valor_max = self.parse_decimal(row.get('Valor Maximo', row.get('valor_maximo', row.get('Max', ''))))
                            panico_min = self.parse_decimal(row.get('Panico Minimo', row.get('panico_minimo', row.get('Critico Min', ''))))
                            panico_max = self.parse_decimal(row.get('Panico Maximo', row.get('panico_maximo', row.get('Critico Max', ''))))
                            
                            # Crear rango
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
                                stats['rangos'] += 1
                        
                        except Exception as e:
                            logging.getLogger(__name__).exception("Error inesperado en cargar_rangos (cargar_legacy.py)")
                            stats['errores'] += 1
                
                break
            except:
                continue

    def parse_decimal(self, valor_str):
        try:
            if not valor_str or str(valor_str).strip() == '':
                return None
            valor_clean = str(valor_str).replace(',', '.').strip()
            return Decimal(valor_clean)
        except:
            return None

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