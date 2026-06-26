"""
MIGRACIN TOTAL: CEREBRO DE LABORATORIO V5.0
============================================
Carga completa de estructura clnica y financiera desde CSV legacy.

FASE 1: Estructura Clnica (datos_lims/)
- Examenes.csv -> Estudio
- Parametros.csv -> Parametro
- Valores_normalidad.csv -> ValorReferencia
- Paquetes.csv + Paquetes_Perfil.csv -> PerfilLaboratorio

FASE 2: Inyeccin Financiera (tarifas.csv)
- Actualiza precios en Estudio y PerfilLaboratorio

Autor: PRIS AI Team
Fecha: 2026-02-10
"""
import os
import csv
import logging
import re
from decimal import Decimal, InvalidOperation
from datetime import timedelta
import unicodedata
from django.core.management.base import BaseCommand
from django.db import transaction
from django.conf import settings

from laboratorio.models import (
    Estudio,
    Parametro,
    ValorReferencia,
    PerfilLaboratorio,
    CategoriaExamen,
)


def normalize_text(text):
    """Normaliza texto para bsquedas (elimina acentos y convierte a minsculas)"""
    if not text:
        return ""
    # Eliminar acentos
    nfd = unicodedata.normalize('NFD', text)
    without_accents = ''.join(c for c in nfd if unicodedata.category(c) != 'Mn')
    return without_accents.lower().strip()

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Migracin completa de datos clnicos y financieros del laboratorio'

    def __init__(self):
        super().__init__()
        self.base_dir = os.path.join(settings.BASE_DIR, 'datos_lims')
        self.tarifas_path = os.path.join(settings.BASE_DIR, 'tarifas.csv')
        
        # Contadores
        self.estudios_creados = 0
        self.parametros_creados = 0
        self.rangos_creados = 0
        self.paquetes_creados = 0
        self.precios_actualizados = 0
        self.errores = []
        self.precios_huerfanos = []

    def add_arguments(self, parser):
        parser.add_argument(
            '--skip-estudios',
            action='store_true',
            help='Saltar carga de estudios',
        )
        parser.add_argument(
            '--skip-parametros',
            action='store_true',
            help='Saltar carga de parmetros',
        )
        parser.add_argument(
            '--skip-rangos',
            action='store_true',
            help='Saltar carga de rangos de referencia',
        )
        parser.add_argument(
            '--skip-paquetes',
            action='store_true',
            help='Saltar carga de paquetes',
        )
        parser.add_argument(
            '--skip-precios',
            action='store_true',
            help='Saltar actualizacin de precios',
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('=' * 80))
        self.stdout.write(self.style.SUCCESS('MIGRACION TOTAL: CEREBRO DE LABORATORIO V5.0'))
        self.stdout.write(self.style.SUCCESS('=' * 80))
        
        try:
            # FASE 1: ESTRUCTURA CLNICA
            self.stdout.write('\n' + self.style.WARNING('FASE 1: ESTRUCTURA CLINICA'))
            
            if not options['skip_estudios']:
                self.cargar_estudios()
            
            if not options['skip_parametros']:
                self.cargar_parametros()
            
            if not options['skip_rangos']:
                self.cargar_rangos_referencia()
            
            if not options['skip_paquetes']:
                self.cargar_paquetes()
            
            # FASE 2: INYECCIN FINANCIERA
            if not options['skip_precios']:
                self.stdout.write('\n' + self.style.WARNING('FASE 2: INYECCION FINANCIERA'))
                self.cargar_precios()
            
            # FASE 3: REPORTE
            self.mostrar_reporte()
            
        except MigrationError as e:
            self.stdout.write(self.style.ERROR(f'Error de migración: {str(e)}'))
            raise
        except DatabaseError as e:
            self.stdout.write(self.style.ERROR(f'Error de base de datos: {str(e)}'))
            raise
        except django.core.exceptions.ValidationError as e:
            self.stdout.write(self.style.ERROR(f'Error de validación: {str(e)}'))
            raise
        except Exception as e:
            logging.getLogger(__name__).exception("Error inesperado en handle (migrar_lab_completo.py)")
            self.stdout.write(self.style.ERROR(f'Error inesperado: {str(e)}'))
            raise

    # ==========================================================================
    # FASE 1: ESTRUCTURA CLNICA
    # ==========================================================================
    
    def cargar_estudios(self):
        """Carga estudios desde Examenes.csv"""
        self.stdout.write('\n Cargando estudios desde Examenes.csv...')
        archivo = os.path.join(self.base_dir, 'Examenes.csv')
        
        if not os.path.exists(archivo):
            self.stdout.write(self.style.WARNING(f'  Archivo no encontrado: {archivo}'))
            return
        
        categoria_default, _ = CategoriaExamen.objects.get_or_create(
            nombre='General',
            defaults={'descripcion': 'Categora general para estudios sin categora especfica'}
        )
        
        with open(archivo, 'r', encoding='utf-8-sig', errors='replace') as f:
            reader = csv.DictReader(f)
            
            with transaction.atomic():
                for row in reader:
                    try:
                        codigo = row.get('Codigo', '').strip()
                        descripcion = row.get('Descripcion', '').strip()
                        
                        if not codigo or not descripcion:
                            continue
                        
                        # Buscar o crear estudio
                        estudio, created = Estudio.objects.get_or_create(
                            codigo=codigo,
                            defaults={
                                'nombre': descripcion,
                                'categoria': categoria_default,
                                'dias_entrega': row.get('Tiempo_proceso', '').strip() or '1 da',
                                'muestra_requerida': 'Sangre',  # Default
                                'indicaciones': row.get('Indicaciones', '').strip(),
                                'descripcion_interna': row.get('Notas', '').strip(),
                                'es_perfil': False,
                            }
                        )
                        
                        if created:
                            self.estudios_creados += 1
                            if self.estudios_creados % 10 == 0:
                                self.stdout.write(f'    {self.estudios_creados} estudios cargados...')

                    except MigrationError as e:
                        self.errores.append(f'Error en estudio {codigo}: {str(e)}')
                        continue
                    except DatabaseError as e:
                        self.errores.append(f'Error en estudio {codigo}: {str(e)}')
                        continue
                    except django.core.exceptions.ValidationError as e:
                        self.errores.append(f'Error en estudio {codigo}: {str(e)}')
                        continue
                    except Exception as e:
                        logging.getLogger(__name__).exception("Error inesperado en cargar_estudios (migrar_lab_completo.py)")
                        self.errores.append(f'Error en estudio {codigo}: {str(e)}')
                        continue

        self.stdout.write(self.style.SUCCESS(f' {self.estudios_creados} estudios creados'))

    def cargar_parametros(self):
        """Carga parmetros desde Parametros.csv"""
        self.stdout.write('\n Cargando parmetros desde Parametros.csv...')
        archivo = os.path.join(self.base_dir, 'Parametros.csv')
        
        if not os.path.exists(archivo):
            self.stdout.write(self.style.WARNING(f'  Archivo no encontrado: {archivo}'))
            return
        
        with open(archivo, 'r', encoding='utf-8-sig', errors='replace') as f:
            reader = csv.DictReader(f)
            
            with transaction.atomic():
                for row in reader:
                    try:
                        codigo_padre = row.get('Codigo', '').strip()
                        descripcion = row.get('Descripcion', '').strip()
                        unidades = row.get('Unidades', '').strip()
                        
                        if not codigo_padre or not descripcion:
                            continue
                        
                        # Buscar estudio padre
                        estudio = Estudio.objects.filter(codigo=codigo_padre).first()
                        if not estudio:
                            # Si no existe, continuar (puede ser un parmetro hurfano)
                            continue
                        
                        # Crear parmetro
                        parametro, created = Parametro.objects.get_or_create(
                            estudio=estudio,
                            nombre=descripcion,
                            defaults={
                                'unidades': unidades,
                            }
                        )
                        
                        if created:
                            self.parametros_creados += 1
                            if self.parametros_creados % 50 == 0:
                                self.stdout.write(f'    {self.parametros_creados} parmetros cargados...')
                    
                    except MigrationError as e:
    logger.error(f"Error migracion: {e}")
except DatabaseError as e:
    logger.error(f"Error BD: {e}", exc_info=True)
except ValidationError as e:
    logger.error(f"Validacion fallida: {e}")
except MigrationError as e:
    logger.error(f"Error migracion: {e}")
except DatabaseError as e:
    logger.error(f"Error BD: {e}", exc_info=True)
except ValidationError as e:
    logger.error(f"Validacion fallida: {e}")
except Exception as e:
    logger.critical(f"Error desconocido: {e}", exc_info=True)
    logger.critical(f"Error desconocido: {e}", exc_info=True)
                        self.errores.append(f'Error en parmetro {descripcion}: {e}')
                        continue
        
        self.stdout.write(self.style.SUCCESS(f' {self.parametros_creados} parmetros creados'))

    def cargar_rangos_referencia(self):
        """Carga rangos de referencia desde Valores_normalidad.csv"""
        self.stdout.write('\n Cargando rangos de referencia desde Valores_normalidad.csv...')
        archivo = os.path.join(self.base_dir, 'Valores_normalidad.csv')
        
        if not os.path.exists(archivo):
            self.stdout.write(self.style.WARNING(f'  Archivo no encontrado: {archivo}'))
            return
        
        with open(archivo, 'r', encoding='utf-8-sig', errors='replace') as f:
            reader = csv.DictReader(f)
            
            with transaction.atomic():
                for row in reader:
                    try:
                        codigo = row.get('Codigo', '').strip()
                        sexo_raw = row.get('Sexo', '').strip()
                        edad_min_raw = row.get('Edad_min', '').strip()
                        edad_max_raw = row.get('Edad_max', '').strip()
                        ref_min = row.get('Ref_min', '').strip()
                        ref_max = row.get('Ref_max', '').strip()
                        unidad = row.get('Unidad', '').strip()
                        
                        if not codigo or not ref_min or not ref_max:
                            continue
                        
                        # Buscar estudio
                        estudio = Estudio.objects.filter(codigo=codigo).first()
                        if not estudio:
                            continue
                        
                        # Parsear sexo
                        if 'Hombre' in sexo_raw or sexo_raw == 'M' or 'Masculino' in sexo_raw:
                            sexo = 'M'
                        elif 'Mujer' in sexo_raw or sexo_raw == 'F' or 'Femenino' in sexo_raw:
                            sexo = 'F'
                        else:
                            sexo = None  # Ambos
                        
                        # Determinar categora de edad basada en edad_min/max
                        edad_min_dias = self.convertir_edad_a_dias(edad_min_raw, unidad)
                        edad_max_dias = self.convertir_edad_a_dias(edad_max_raw, unidad)
                        
                        # Mapear a categoras del modelo
                        if edad_max_dias <= 30:
                            edad_categoria = 'NEONATO'
                        elif edad_max_dias <= 6570:  # 18 aos
                            edad_categoria = 'INFANTE'
                        elif edad_max_dias <= 23360:  # 64 aos
                            edad_categoria = 'ADULTO'
                        else:
                            edad_categoria = 'ADULTO_MAYOR'
                        
                        # Parsear valores
                        try:
                            valor_min = Decimal(ref_min)
                            valor_max = Decimal(ref_max)
                        except InvalidOperation:
                            continue
                        
                        # Crear rango (el modelo usa 'edad' como CharField, no numrico)
                        rango, created = ValorReferencia.objects.get_or_create(
                            estudio=estudio,
                            sexo=sexo,
                            edad=edad_categoria,
                            defaults={
                                'valor_minimo': valor_min,
                                'valor_maximo': valor_max,
                                'unidades': estudio.unidades or '',
                            }
                        )
                        
                        if created:
                            self.rangos_creados += 1
                            if self.rangos_creados % 50 == 0:
                                self.stdout.write(f'    {self.rangos_creados} rangos cargados...')
                    
                    except MigrationError as e:
    logger.error(f"Error migracion: {e}")
except DatabaseError as e:
    logger.error(f"Error BD: {e}", exc_info=True)
except ValidationError as e:
    logger.error(f"Validacion fallida: {e}")
except MigrationError as e:
    logger.error(f"Error migracion: {e}")
except DatabaseError as e:
    logger.error(f"Error BD: {e}", exc_info=True)
except ValidationError as e:
    logger.error(f"Validacion fallida: {e}")
except Exception as e:
    logger.critical(f"Error desconocido: {e}", exc_info=True)
    logger.critical(f"Error desconocido: {e}", exc_info=True)
                        self.errores.append(f'Error en rango para {codigo}: {e}')
                        continue
        
        self.stdout.write(self.style.SUCCESS(f' {self.rangos_creados} rangos de referencia creados'))

    def cargar_paquetes(self):
        """Carga paquetes desde Paquetes.csv y Paquetes_Perfil.csv"""
        self.stdout.write('\n Cargando paquetes desde Paquetes.csv...')
        archivo_paquetes = os.path.join(self.base_dir, 'Paquetes.csv')
        archivo_perfiles = os.path.join(self.base_dir, 'Paquetes_Perfil.csv')
        
        if not os.path.exists(archivo_paquetes):
            self.stdout.write(self.style.WARNING(f'  Archivo no encontrado: {archivo_paquetes}'))
            return
        
        categoria_default, _ = CategoriaExamen.objects.get_or_create(
            nombre='Paquetes',
            defaults={'descripcion': 'Perfiles y paquetes de estudios'}
        )
        
        # Diccionario para guardar cdigos de paquetes
        paquetes_dict = {}
        
        # PASO 1: Crear paquetes
        with open(archivo_paquetes, 'r', encoding='utf-8-sig', errors='replace') as f:
            reader = csv.DictReader(f)
            
            with transaction.atomic():
                for row in reader:
                    try:
                        codigo = row.get('Abreviatura', '').strip()
                        descripcion = row.get('Descripcion', '').strip()
                        
                        if not codigo or not descripcion:
                            continue
                        
                        perfil, created = PerfilLaboratorio.objects.get_or_create(
                            nombre=descripcion,
                            defaults={
                                'descripcion': row.get('Indicaciones', '').strip(),
                                'precio': Decimal('0.00'),
                                'area_pertenencia': categoria_default,
                                'activo': True,
                            }
                        )
                        
                        paquetes_dict[codigo] = perfil
                        
                        if created:
                            self.paquetes_creados += 1
                    
                    except MigrationError as e:
    logger.error(f"Error migracion: {e}")
except DatabaseError as e:
    logger.error(f"Error BD: {e}", exc_info=True)
except ValidationError as e:
    logger.error(f"Validacion fallida: {e}")
except MigrationError as e:
    logger.error(f"Error migracion: {e}")
except DatabaseError as e:
    logger.error(f"Error BD: {e}", exc_info=True)
except ValidationError as e:
    logger.error(f"Validacion fallida: {e}")
except Exception as e:
    logger.critical(f"Error desconocido: {e}", exc_info=True)
    logger.critical(f"Error desconocido: {e}", exc_info=True)
                        self.errores.append(f'Error en paquete {codigo}: {e}')
                        continue
        
        # PASO 2: Vincular estudios a paquetes
        if os.path.exists(archivo_perfiles):
            self.stdout.write('    Vinculando estudios a paquetes...')
            
            with open(archivo_perfiles, 'r', encoding='utf-8-sig', errors='replace') as f:
                reader = csv.DictReader(f)
                
                # Skip header lines
                try:
                    next(reader)  # Skip first header row
                except StopIteration:
                    pass
                
                with transaction.atomic():
                    for row in reader:
                        try:
                            # Columnas: Abreviatura (paquete), Codigo (estudio)
                            codigo_paquete = row.get('Abreviatura', '').strip()
                            codigo_estudio = row.get('Codigo', '').strip()
                            
                            if not codigo_paquete or not codigo_estudio:
                                continue
                            
                            perfil = paquetes_dict.get(codigo_paquete)
                            if not perfil:
                                continue
                            
                            estudio = Estudio.objects.filter(codigo=codigo_estudio).first()
                            if not estudio:
                                continue
                            
                            perfil.pruebas.add(estudio)
                        
                        except MigrationError as e:
    logger.error(f"Error migracion: {e}")
except DatabaseError as e:
    logger.error(f"Error BD: {e}", exc_info=True)
except ValidationError as e:
    logger.error(f"Validacion fallida: {e}")
except MigrationError as e:
    logger.error(f"Error migracion: {e}")
except DatabaseError as e:
    logger.error(f"Error BD: {e}", exc_info=True)
except ValidationError as e:
    logger.error(f"Validacion fallida: {e}")
except Exception as e:
    logger.critical(f"Error desconocido: {e}", exc_info=True)
    logger.critical(f"Error desconocido: {e}", exc_info=True)
                            self.errores.append(f'Error vinculando {codigo_estudio} a {codigo_paquete}: {e}')
                            continue
        
        self.stdout.write(self.style.SUCCESS(f' {self.paquetes_creados} paquetes creados'))

    # ==========================================================================
    # FASE 2: INYECCIN FINANCIERA
    # ==========================================================================
    
    def cargar_precios(self):
        """Actualiza precios desde tarifas.csv"""
        self.stdout.write('\n Actualizando precios desde tarifas.csv...')
        
        if not os.path.exists(self.tarifas_path):
            self.stdout.write(self.style.WARNING(f'  Archivo no encontrado: {self.tarifas_path}'))
            return
        
        with open(self.tarifas_path, 'r', encoding='utf-8-sig', errors='replace') as f:
            reader = csv.DictReader(f)
            
            # Buscar la fila de encabezados correcta
            for _ in range(3):
                try:
                    next(reader)
                except StopIteration:
                    break
            
            # Reiniciar lectura con encabezados correctos
            f.seek(0)
            lines = f.readlines()
            
            # Encontrar lnea de encabezado
            header_line_idx = 0
            for i, line in enumerate(lines):
                if 'Tipo,Cdigo' in line or 'Tipo,Codigo' in line:
                    header_line_idx = i
                    break
            
            if header_line_idx == 0:
                header_line_idx = 2  # Por defecto, lnea 3
            
            # Leer desde la lnea correcta
            f.seek(0)
            for _ in range(header_line_idx):
                next(f)
            
            reader = csv.DictReader(f)
            
            with transaction.atomic():
                for row in reader:
                    try:
                        tipo = row.get('Tipo', '').strip()
                        codigo = row.get('Cdigo', row.get('Codigo', '')).strip()
                        importe = row.get('Importe', '0').strip()
                        
                        if not tipo or not codigo:
                            continue
                        
                        # Convertir precio
                        try:
                            precio = Decimal(importe.replace(',', ''))
                        except (InvalidOperation, ValueError):
                            precio = Decimal('0.00')
                        
                        if precio <= 0:
                            continue
                        
                        # Actualizar segn tipo
                        if 'paquete' in tipo.lower():
                            # Bsqueda de perfil (normalizada para evitar problemas con acentos)
                            perfil = PerfilLaboratorio.objects.filter(nombre__icontains=codigo).first()
                            
                            # Si no se encuentra por nombre, intentar bsqueda normalizada
                            if not perfil:
                                codigo_norm = normalize_text(codigo)
                                for p in PerfilLaboratorio.objects.all():
                                    if codigo_norm in normalize_text(p.nombre):
                                        perfil = p
                                        break
                            
                            if perfil:
                                perfil.precio = precio
                                perfil.save(update_fields=['precio'])
                                self.precios_actualizados += 1
                            else:
                                self.precios_huerfanos.append(f'Paquete: {codigo} (${precio})')
                        
                        elif 'prueba' in tipo.lower():
                            # Bsqueda de estudio
                            estudio = Estudio.objects.filter(codigo=codigo).first()
                            
                            # Si no se encuentra, intentar bsqueda normalizada
                            if not estudio:
                                codigo_norm = normalize_text(codigo)
                                for e in Estudio.objects.all():
                                    if normalize_text(e.codigo) == codigo_norm or codigo_norm in normalize_text(e.nombre):
                                        estudio = e
                                        break
                            
                            if estudio:
                                estudio.precio_base = precio
                                estudio.save(update_fields=['precio_base'])
                                self.precios_actualizados += 1
                            else:
                                self.precios_huerfanos.append(f'Prueba: {codigo} (${precio})')
                        
                        if self.precios_actualizados % 50 == 0:
                            self.stdout.write(f'    {self.precios_actualizados} precios actualizados...')
                    
                    except MigrationError as e:
    logger.error(f"Error migracion: {e}")
except DatabaseError as e:
    logger.error(f"Error BD: {e}", exc_info=True)
except ValidationError as e:
    logger.error(f"Validacion fallida: {e}")
except MigrationError as e:
    logger.error(f"Error migracion: {e}")
except DatabaseError as e:
    logger.error(f"Error BD: {e}", exc_info=True)
except ValidationError as e:
    logger.error(f"Validacion fallida: {e}")
except Exception as e:
    logger.critical(f"Error desconocido: {e}", exc_info=True)
    logger.critical(f"Error desconocido: {e}", exc_info=True)
                        self.errores.append(f'Error en precio {codigo}: {e}')
                        continue
        
        self.stdout.write(self.style.SUCCESS(f' {self.precios_actualizados} precios actualizados'))
        
        # Guardar hurfanos
        if self.precios_huerfanos:
            orphaned_file = os.path.join(settings.BASE_DIR, 'orphaned_prices.log')
            with open(orphaned_file, 'w', encoding='utf-8') as f:
                f.write('PRECIOS HURFANOS (No se encontr el cdigo en el sistema)\n')
                f.write('=' * 80 + '\n\n')
                for item in self.precios_huerfanos:
                    f.write(item + '\n')
            
            self.stdout.write(self.style.WARNING(f'  {len(self.precios_huerfanos)} precios hurfanos. Ver: orphaned_prices.log'))

    # ==========================================================================
    # UTILIDADES
    # ==========================================================================
    
    def convertir_edad_a_dias(self, edad_str, unidad_str):
        """Convierte edad a das segn la unidad"""
        try:
            edad = int(edad_str)
        except (ValueError, TypeError):
            return 0
        
        if '(dias)' in unidad_str or '(das)' in unidad_str:
            return edad
        elif '(aos)' in unidad_str or '(anos)' in unidad_str:
            return edad * 365
        elif '(meses)' in unidad_str:
            return edad * 30
        else:
            return edad

    def mostrar_reporte(self):
        """Muestra reporte final de la migracin"""
        self.stdout.write('\n' + '=' * 80)
        self.stdout.write(self.style.SUCCESS(' REPORTE FINAL DE MIGRACIN'))
        self.stdout.write('=' * 80)
        
        self.stdout.write(self.style.SUCCESS(f' Estudios Creados: {self.estudios_creados}'))
        self.stdout.write(self.style.SUCCESS(f' Parmetros Creados: {self.parametros_creados}'))
        self.stdout.write(self.style.SUCCESS(f' Rangos de Referencia Creados: {self.rangos_creados}'))
        self.stdout.write(self.style.SUCCESS(f' Paquetes Armados: {self.paquetes_creados}'))
        self.stdout.write(self.style.SUCCESS(f' Precios Actualizados desde Tarifas: {self.precios_actualizados}'))
        
        if self.errores:
            self.stdout.write(self.style.WARNING(f'\n  {len(self.errores)} errores encontrados'))
            errores_file = os.path.join(settings.BASE_DIR, 'errores_migracion.log')
            with open(errores_file, 'w', encoding='utf-8') as f:
                for error in self.errores[:100]:  # Primeros 100
                    f.write(error + '\n')
            self.stdout.write(self.style.WARNING(f'Ver detalles en: errores_migracion.log'))
        
        self.stdout.write('\n' + self.style.SUCCESS(' MIGRACIN COMPLETADA'))
        self.stdout.write('=' * 80 + '\n')