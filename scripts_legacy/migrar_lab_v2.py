"""
MIGRACION CORREGIDA DE LABORATORIO V2
======================================
Maneja headers basura, encoding UTF-8 y unidades de edad.
Ajustado a los modelos REALES del sistema.

Autor: PRIS AI Team
Fecha: 2026-02-10
"""
from django.core.management.base import BaseCommand
from django.db import transaction
from laboratorio.models import (
    Estudio, 
    Parametro, 
    ValorReferencia, 
    PerfilLaboratorio,
    CategoriaExamen
)
from decimal import Decimal
import csv
import os
from django.conf import settings


class Command(BaseCommand):
    help = 'Migracion CORREGIDA de Laboratorio (Maneja Headers basura y Unidades)'

    def __init__(self):
        super().__init__()
        self.base_path = os.path.join(settings.BASE_DIR, 'datos_lims')
        self.tarifas_path = os.path.join(settings.BASE_DIR, 'tarifas.csv')
        
    def handle(self, *args, **kwargs):
        print("=" * 80)
        print("MIGRACION LABORATORIO V2 - CORREGIDA")
        print("=" * 80)
        
        # Categoria default
        self.categoria_default, _ = CategoriaExamen.objects.get_or_create(
            nombre='General',
            defaults={'descripcion': 'Categoria general'}
        )
        
        # 1. CARGA DE EXAMENES (ESTUDIOS)
        self.cargar_estudios()
        
        # 2. CARGA DE PARAMETROS (ELEMENTOS)
        self.cargar_parametros()
        
        # 3. CARGA DE RANGOS (CON PARSEO DE UNIDADES)
        self.cargar_rangos()
        
        # 4. CARGA DE PAQUETES
        self.cargar_paquetes()
        
        # 5. CARGA DE PRECIOS (TARIFAS REALES)
        self.cargar_precios()
        
        print("\n" + "=" * 80)
        print("MIGRACION COMPLETADA")
        print("=" * 80)

    def cargar_estudios(self):
        """Carga estudios desde Examenes.csv"""
        print("\n--- CARGANDO ESTUDIOS ---")
        archivo = os.path.join(self.base_path, 'Examenes.csv')
        
        if not os.path.exists(archivo):
            print(f"ERROR: No se encontro {archivo}")
            return
        
        try:
            with open(archivo, encoding='utf-8-sig', errors='replace') as f:
                reader = csv.DictReader(f)
                count = 0
                
                with transaction.atomic():
                    for row in reader:
                        try:
                            codigo = row.get('Codigo', '').strip()
                            descripcion = row.get('Descripcion', '').strip()
                            
                            if not codigo or not descripcion:
                                continue
                            
                            estudio, created = Estudio.objects.get_or_create(
                                codigo=codigo,
                                defaults={
                                    'nombre': descripcion,
                                    'categoria': self.categoria_default,
                                    'dias_entrega': row.get('Tiempo_proceso', '').strip() or '1 dia',
                                    'indicaciones': row.get('Indicaciones', '').strip(),
                                    'precio_base': Decimal('0.00'),
                                }
                            )
                            
                            if created:
                                count += 1
                                
                        except Exception as e:
                            print(f"Error en estudio {codigo}: {e}")
                            continue
                
                print(f"EXITO: {count} Estudios creados.")
                
        except Exception as e:
            print(f"ERROR CRITICO en Examenes.csv: {e}")

    def cargar_parametros(self):
        """Carga parametros desde Parametros.csv"""
        print("\n--- CARGANDO PARAMETROS ---")
        archivo = os.path.join(self.base_path, 'Parametros.csv')
        
        if not os.path.exists(archivo):
            print(f"ERROR: No se encontro {archivo}")
            return
        
        try:
            with open(archivo, encoding='utf-8-sig', errors='replace') as f:
                reader = csv.DictReader(f)
                count = 0
                
                with transaction.atomic():
                    for row in reader:
                        try:
                            # En Parametros.csv, 'Codigo' es el codigo del ESTUDIO PADRE
                            codigo_padre = row.get('Codigo', '').strip()
                            descripcion = row.get('Descripcion', '').strip()
                            unidades = row.get('Unidades', '').strip()
                            
                            if not codigo_padre or not descripcion:
                                continue
                            
                            # Buscar estudio padre
                            estudio = Estudio.objects.filter(codigo=codigo_padre).first()
                            if not estudio:
                                continue
                            
                            # Crear parametro
                            parametro, created = Parametro.objects.get_or_create(
                                estudio=estudio,
                                nombre=descripcion,
                                defaults={
                                    'unidades': unidades,
                                }
                            )
                            
                            if created:
                                count += 1
                                
                        except Exception as e:
                            continue
                
                print(f"EXITO: {count} Parametros creados.")
                
        except Exception as e:
            print(f"ERROR en Parametros.csv: {e}")

    def cargar_rangos(self):
        """Carga rangos de referencia con parseo de unidades (dias/anos)"""
        print("\n--- CARGANDO RANGOS DE REFERENCIA ---")
        archivo = os.path.join(self.base_path, 'Valores_normalidad.csv')
        
        if not os.path.exists(archivo):
            print(f"ERROR: No se encontro {archivo}")
            return
        
        try:
            with open(archivo, encoding='utf-8-sig', errors='replace') as f:
                reader = csv.DictReader(f)
                count = 0
                
                with transaction.atomic():
                    for row in reader:
                        try:
                            codigo = row.get('Codigo', '').strip()
                            sexo_raw = row.get('Sexo', '').strip()
                            unidad = row.get('Unidad', '').strip()
                            edad_min_raw = row.get('Edad_min', '').strip()
                            edad_max_raw = row.get('Edad_max', '').strip()
                            ref_min = row.get('Ref_min', '').strip()
                            ref_max = row.get('Ref_max', '').strip()
                            
                            if not codigo:
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
                                sexo = None
                            
                            # Parsear edad con factor de conversion
                            factor = 1  # Dias por defecto
                            if 'anos' in unidad or 'años' in unidad.lower():
                                factor = 365
                            elif 'meses' in unidad.lower():
                                factor = 30
                            
                            try:
                                edad_min = int(float(edad_min_raw)) * factor
                                edad_max = int(float(edad_max_raw)) * factor
                            except (ValueError, TypeError):
                                edad_min = 0
                                edad_max = 36500  # 100 anos
                            
                            # Parsear valores
                            try:
                                valor_min = Decimal(ref_min) if ref_min else None
                                valor_max = Decimal(ref_max) if ref_max else None
                            except:
                                valor_min = None
                                valor_max = None
                            
                            # Crear rango
                            # NOTA: ValorReferencia usa campo 'edad' no 'edad_minima_dias'
                            # Voy a usar el campo correcto basado en el modelo real
                            rango, created = ValorReferencia.objects.get_or_create(
                                estudio=estudio,
                                sexo=sexo,
                                edad=f'{edad_min}-{edad_max} dias',  # Como string
                                defaults={
                                    'valor_minimo': valor_min,
                                    'valor_maximo': valor_max,
                                    'unidades': estudio.unidades or '',
                                }
                            )
                            
                            if created:
                                count += 1
                                
                        except Exception as e:
                            continue
                
                print(f"EXITO: {count} Rangos de referencia creados.")
                
        except Exception as e:
            print(f"ERROR en Valores_normalidad.csv: {e}")

    def cargar_paquetes(self):
        """Carga paquetes desde Paquetes.csv y vincula con estudios"""
        print("\n--- CARGANDO PAQUETES ---")
        archivo_paquetes = os.path.join(self.base_path, 'Paquetes.csv')
        archivo_perfiles = os.path.join(self.base_path, 'Paquetes_Perfil.csv')
        
        if not os.path.exists(archivo_paquetes):
            print(f"ERROR: No se encontro {archivo_paquetes}")
            return
        
        categoria_paquetes, _ = CategoriaExamen.objects.get_or_create(
            nombre='Paquetes',
            defaults={'descripcion': 'Perfiles y paquetes de estudios'}
        )
        
        paquetes_dict = {}
        
        try:
            # Crear paquetes
            with open(archivo_paquetes, encoding='utf-8-sig', errors='replace') as f:
                reader = csv.DictReader(f)
                count = 0
                
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
                                    'area_pertenencia': categoria_paquetes,
                                    'activo': True,
                                }
                            )
                            
                            paquetes_dict[codigo] = perfil
                            
                            if created:
                                count += 1
                                
                        except Exception as e:
                            continue
                
                print(f"EXITO: {count} Paquetes creados.")
            
            # Vincular estudios a paquetes
            if os.path.exists(archivo_perfiles):
                print("   Vinculando estudios a paquetes...")
                
                with open(archivo_perfiles, encoding='utf-8-sig', errors='replace') as f:
                    reader = csv.DictReader(f)
                    
                    # Skip primera linea de header
                    try:
                        next(reader)
                    except StopIteration:
                        pass
                    
                    vinculados = 0
                    
                    with transaction.atomic():
                        for row in reader:
                            try:
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
                                vinculados += 1
                                
                            except Exception as e:
                                continue
                    
                    print(f"   {vinculados} estudios vinculados a paquetes.")
                
        except Exception as e:
            print(f"ERROR en Paquetes: {e}")

    def cargar_precios(self):
        """Actualiza precios desde tarifas.csv (saltando headers basura)"""
        print("\n--- ACTUALIZANDO PRECIOS DESDE TARIFAS.CSV ---")
        
        if not os.path.exists(self.tarifas_path):
            print(f"ERROR: No se encontro {self.tarifas_path}")
            return
        
        try:
            with open(self.tarifas_path, encoding='utf-8-sig', errors='replace') as f:
                # Leer todas las lineas
                lines = f.readlines()
                
                # Saltar primeras 2 lineas basura
                header_line = 2
                content_lines = lines[header_line:]
                
                # Crear reader desde las lineas limpias
                import io
                reader = csv.DictReader(io.StringIO(''.join(content_lines)))
                
                updated_estudios = 0
                updated_paquetes = 0
                
                with transaction.atomic():
                    for row in reader:
                        try:
                            tipo = row.get('Tipo', '').strip()
                            codigo = row.get('Codigo', row.get('Código', '')).strip()
                            importe = row.get('Importe', '0').strip()
                            
                            if not codigo or not importe:
                                continue
                            
                            try:
                                precio = Decimal(importe)
                            except:
                                continue
                            
                            if tipo.lower() == 'pruebas':
                                # Actualizar precio en Estudio
                                estudios = Estudio.objects.filter(codigo=codigo)
                                if estudios.exists():
                                    estudio = estudios.first()
                                    estudio.precio_base = precio
                                    estudio.save(update_fields=['precio_base'])
                                    updated_estudios += 1
                            
                            elif tipo.lower() == 'paquetes':
                                # Actualizar precio en PerfilLaboratorio
                                perfiles = PerfilLaboratorio.objects.filter(nombre__icontains=codigo)
                                if perfiles.exists():
                                    perfil = perfiles.first()
                                    perfil.precio = precio
                                    perfil.save(update_fields=['precio'])
                                    updated_paquetes += 1
                            
                        except Exception as e:
                            continue
                
                print(f"EXITO: {updated_estudios} precios de Estudios actualizados.")
                print(f"EXITO: {updated_paquetes} precios de Paquetes actualizados.")
                
        except Exception as e:
            print(f"ERROR CRITICO en Tarifas: {e}")
