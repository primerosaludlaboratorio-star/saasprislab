"""
MIGRACIÓN MAESTRA PRISLAB GOLD
=============================
Estructura Clínica + Precios Reales + Paquetes
Versión Final Optimizada

Autor: PRIS AI + Jonathan
Fecha: 2026-02-10
"""
import os
import csv
import unicodedata
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.db import transaction

from laboratorio.models import (
    Estudio,
    Parametro,
    ValorReferencia,
    PerfilLaboratorio,
    CategoriaExamen,
)
import logging


def clean_float(value):
    """Limpia y convierte valores a float"""
    try:
        return float(str(value).replace(',', '').strip())
    except:
        return 0.0


def normalize_text(text):
    """Normaliza texto (elimina acentos)"""
    if not text:
        return ""
    nfd = unicodedata.normalize('NFD', text)
    return ''.join(c for c in nfd if unicodedata.category(c) != 'Mn').lower().strip()


class Command(BaseCommand):
    help = 'Migración MAESTRA: Estructura Clínica + Precios Reales + Paquetes'

    def handle(self, *args, **kwargs):
        base_path = 'datos_lims'
        self.stdout.write(self.style.SUCCESS('=' * 80))
        self.stdout.write(self.style.SUCCESS('INICIANDO MIGRACION PRISLAB GOLD...'))
        self.stdout.write(self.style.SUCCESS('=' * 80))

        # Crear categoría default
        cat_default, _ = CategoriaExamen.objects.get_or_create(
            nombre='General',
            defaults={'descripcion': 'Categoría general'}
        )

        # --- FASE 1: ESTUDIOS (EXAMENES) ---
        self.stdout.write('\n>> Cargando Estudios...')
        try:
            with open(os.path.join(base_path, 'Examenes.csv'), encoding='utf-8') as f:
                reader = csv.DictReader(f)
                count = 0
                for row in reader:
                    codigo = row['Codigo'].strip()
                    nombre = row['Descripcion'].strip()
                    # Buscar primero por codigo, luego por (categoria, nombre)
                    est = Estudio.objects.filter(codigo=codigo).first()
                    if not est:
                        est = Estudio.objects.filter(
                            categoria=cat_default, nombre=nombre
                        ).first()
                    if not est:
                        try:
                            est = Estudio.objects.create(
                                codigo=codigo,
                                nombre=nombre,
                                categoria=cat_default,
                                dias_entrega=row.get('Tiempo_proceso', '') or '1 dia',
                                precio_base=Decimal('0.00'),
                            )
                            count += 1
                        except (DatabaseError, IntegrityError, ValidationError):
                            # Si aun falla, actualizar el existente por nombre
                            est = Estudio.objects.filter(nombre=nombre).first()
                            if est and not est.codigo:
                                est.codigo = codigo
                                est.save(update_fields=['codigo'])
                    else:
                        # Asegurar que tenga codigo correcto
                        if est.codigo != codigo:
                            est.codigo = codigo
                            est.save(update_fields=['codigo'])
                self.stdout.write(self.style.SUCCESS(f'[OK] {count} Estudios nuevos creados. Total: {Estudio.objects.count()}'))
        except MigrationError as e:
    logger.error(f"Error migracion: {e}")
except DatabaseError as e:
    logger.error(f"Error BD: {e}", exc_info=True)
except IntegrityError as e:
    logger.error(f"Error integridad: {e}", exc_info=True)
except MigrationError as e:
    logger.error(f"Error migracion: {e}")
except DatabaseError as e:
    logger.error(f"Error BD: {e}", exc_info=True)
except IntegrityError as e:
    logger.error(f"Error integridad: {e}", exc_info=True)
except Exception as e:
    logger.critical(f"Error desconocido: {e}", exc_info=True)
    logger.critical(f"Error desconocido: {e}", exc_info=True)
            self.stdout.write(self.style.ERROR(f'[ERROR] Error Estudios: {e}'))

        # --- FASE 2: PARÁMETROS (ELEMENTOS) ---
        self.stdout.write('\n>> Cargando Parámetros...')
        try:
            with open(os.path.join(base_path, 'Parametros.csv'), encoding='utf-8') as f:
                reader = csv.DictReader(f)
                count = 0
                for row in reader:
                    try:
                        # Buscar estudio padre por código
                        padre = Estudio.objects.filter(codigo=row['Codigo']).first()
                        
                        if padre:
                            _, created = Parametro.objects.get_or_create(
                                estudio=padre,
                                nombre=row['Descripcion'],
                                defaults={'unidades': row.get('Unidades', '') or ''}
                            )
                            if created:
                                count += 1
                    except (DatabaseError, IntegrityError, ValidationError):
                        pass
                self.stdout.write(self.style.SUCCESS(f'[OK] {count} Parametros nuevos vinculados.'))
        except MigrationError as e:
            self.stdout.write(self.style.ERROR(f'Error de migración: {str(e)}'))
            raise
        except DatabaseError as e:
            self.stdout.write(self.style.ERROR(f'Error de base de datos: {str(e)}'))
            raise
        except IntegrityError as e:
            self.stdout.write(self.style.ERROR(f'Error de integridad: {str(e)}'))
            raise
        except Exception as e:
            logging.getLogger(__name__).exception("Error inesperado en handle (migrar_lab_master.py)")
            self.stdout.write(self.style.ERROR(f'Error inesperado: {str(e)}'))
            raise

        # --- FASE 3: PAQUETES ---
        self.stdout.write('\n>> Armando Paquetes...')
        try:
            paquetes_dict = {}
            
            # Crear paquetes
            with open(os.path.join(base_path, 'Paquetes.csv'), encoding='utf-8') as f:
                # Limpiar trailing commas de cada linea
                clean_lines = [line.rstrip().rstrip(',') + '\n' for line in f.readlines()]
                reader = csv.DictReader(clean_lines)
                for row in reader:
                    paq, _ = PerfilLaboratorio.objects.get_or_create(
                        nombre=row['Descripcion'],
                        defaults={
                            'descripcion': row.get('Indicaciones', ''),
                            'precio': Decimal('0.00'),
                            'area_pertenencia': cat_default,
                        }
                    )
                    abreviatura = row.get('Abreviatura', '').strip()
                    if abreviatura:
                        paquetes_dict[abreviatura] = paq
            
            # Vincular contenido (skip super-header en linea 1, usar linea 2 como headers)
            with open(os.path.join(base_path, 'Paquetes_Perfil.csv'), encoding='utf-8') as f:
                lines = f.readlines()
                # Linea 0 es super-header ("Paquete,Paquete,Estudios del paquete...")
                # Linea 1 es header real ("Abreviatura,Descripcion,Tipo,Codigo,Descripcion")
                # Linea 2+ son datos reales
                if len(lines) > 2 and "Paquete,Paquete" in lines[0]:
                    clean_data = [lines[1].strip().rstrip(',') + '\n']
                    for line in lines[2:]:
                        clean_data.append(line.strip().rstrip(',') + '\n')
                else:
                    clean_data = [l.strip().rstrip(',') + '\n' for l in lines]
                reader = csv.DictReader(clean_data)
                
                links = 0
                for row in reader:
                    try:
                        # Columnas: Abreviatura (paquete), Codigo (estudio)
                        paq_abbr = row.get('Abreviatura', '').strip()
                        item_codigo = row.get('Codigo', '').strip()
                        
                        paquete = paquetes_dict.get(paq_abbr)
                        estudio = Estudio.objects.filter(codigo=item_codigo).first()
                        
                        if paquete and estudio:
                            paquete.pruebas.add(estudio)
                            links += 1
                    except (DatabaseError, IntegrityError, ValidationError):
                        pass
                
                self.stdout.write(self.style.SUCCESS(f'[OK] {links} Estudios vinculados a Paquetes.'))
        except MigrationError as e:
            self.stdout.write(self.style.ERROR(f'Error de migración: {str(e)}'))
            raise
        except DatabaseError as e:
            self.stdout.write(self.style.ERROR(f'Error de base de datos: {str(e)}'))
            raise
        except IntegrityError as e:
            self.stdout.write(self.style.ERROR(f'Error de integridad: {str(e)}'))
            raise
        except Exception as e:
            logging.getLogger(__name__).exception("Error inesperado en handle (migrar_lab_master.py)")
            self.stdout.write(self.style.ERROR(f'Error inesperado: {str(e)}'))
            raise

        # --- FASE 4: PRECIOS REALES (LA FIFA) ---
        self.stdout.write('\n>> Inyectando PRECIOS REALES (tarifas.csv)...')
        try:
            with open('tarifas.csv', encoding='utf-8-sig', errors='replace') as f:
                lines = f.readlines()
                # Buscar header real
                start = next((i for i, l in enumerate(lines) if "Tipo,Código" in l or "Tipo,Codigo" in l), 2)
                reader = csv.DictReader(lines[start:])
                
                updated = 0
                for row in reader:
                    # Limpiar datos
                    row = {k.strip(): v.strip() for k, v in row.items() if k}
                    codigo = (row.get('Código') or row.get('Codigo', '')).strip()
                    precio = clean_float(row.get('Importe', '0'))
                    tipo = row.get('Tipo', '').strip()

                    if codigo and precio > 0:
                        if 'Prueba' in tipo or 'prueba' in tipo.lower():
                            # Buscar estudio exacto
                            ests = Estudio.objects.filter(codigo__iexact=codigo)
                            
                            # Si no encuentra, buscar normalizado
                            if not ests.exists():
                                codigo_norm = normalize_text(codigo)
                                for e in Estudio.objects.all():
                                    if normalize_text(e.codigo) == codigo_norm:
                                        ests = [e]
                                        break
                            
                            for e in ests:
                                e.precio_base = Decimal(str(precio))
                                e.save(update_fields=['precio_base'])
                                updated += 1
                                
                        elif 'Paquete' in tipo or 'paquete' in tipo.lower():
                            # Buscar paquete por nombre
                            descripcion = row.get('Descripción', row.get('Descripcion', '')).strip()
                            
                            paqs = PerfilLaboratorio.objects.filter(nombre__icontains=codigo)
                            if not paqs.exists() and descripcion:
                                paqs = PerfilLaboratorio.objects.filter(nombre__icontains=descripcion)
                            
                            for p in paqs:
                                p.precio = Decimal(str(precio))
                                p.save(update_fields=['precio'])
                                updated += 1
                
                self.stdout.write(self.style.SUCCESS(f'[$$$] {updated} Precios actualizados.'))
        except MigrationError as e:
            self.stdout.write(self.style.ERROR(f'Error de migración: {str(e)}'))
            raise
        except DatabaseError as e:
            self.stdout.write(self.style.ERROR(f'Error de base de datos: {str(e)}'))
            raise
        except IntegrityError as e:
            self.stdout.write(self.style.ERROR(f'Error de integridad: {str(e)}'))
            raise
        except Exception as e:
            logging.getLogger(__name__).exception("Error inesperado en handle (migrar_lab_master.py)")
            self.stdout.write(self.style.ERROR(f'Error inesperado: {str(e)}'))
            raise

        # --- FASE 5: RANGOS DE REFERENCIA ---
        self.stdout.write('\n>> Configurando Inteligencia Clínica...')
        try:
            with open(os.path.join(base_path, 'Valores_normalidad.csv'), encoding='latin-1') as f:
                reader = csv.DictReader(f)
                created = 0
                for row in reader:
                    try:
                        codigo = row.get('Codigo', '').strip()
                        if not codigo:
                            continue
                        
                        # Convertir edad a categoría
                        factor = 365 if 'año' in row.get('Unidad', '').lower() else 1
                        edad_min_dias = int(float(row.get('Edad_min', 0))) * factor
                        edad_max_dias = int(float(row.get('Edad_max', 0))) * factor
                        
                        # Mapear a categorías
                        if edad_max_dias <= 30:
                            edad_categoria = 'NEONATO'
                        elif edad_max_dias <= 6570:  # 18 años
                            edad_categoria = 'INFANTE'
                        elif edad_max_dias <= 23360:  # 64 años
                            edad_categoria = 'ADULTO'
                        else:
                            edad_categoria = 'ADULTO_MAYOR'
                        
                        # Parsear sexo
                        sexo_raw = row.get('Sexo', '').strip()
                        if 'M' in sexo_raw or 'Hombre' in sexo_raw:
                            sexo = 'M'
                        elif 'F' in sexo_raw or 'Mujer' in sexo_raw:
                            sexo = 'F'
                        else:
                            sexo = None
                        
                        # Buscar estudio
                        estudio = Estudio.objects.filter(codigo=codigo).first()
                        if not estudio:
                            continue
                        
                        # Crear rango
                        ref_min = row.get('Ref_min', '').strip()
                        ref_max = row.get('Ref_max', '').strip()
                        
                        if ref_min and ref_max:
                            _, created_val = ValorReferencia.objects.get_or_create(
                                estudio=estudio,
                                sexo=sexo,
                                edad=edad_categoria,
                                defaults={
                                    'valor_minimo': Decimal(ref_min),
                                    'valor_maximo': Decimal(ref_max),
                                    'unidades': estudio.unidades or '',
                                }
                            )
                            if created_val:
                                created += 1
                    except (DatabaseError, IntegrityError, ValidationError, ValueError):
                        pass
                
                self.stdout.write(self.style.SUCCESS(f'[OK] {created} Reglas clinicas nuevas creadas.'))
        except MigrationError as e:
            self.stdout.write(self.style.ERROR(f'Error de migración: {str(e)}'))
            raise
        except DatabaseError as e:
            self.stdout.write(self.style.ERROR(f'Error de base de datos: {str(e)}'))
            raise
        except IntegrityError as e:
            self.stdout.write(self.style.ERROR(f'Error de integridad: {str(e)}'))
            raise
        except Exception as e:
            logging.getLogger(__name__).exception("Error inesperado en handle (migrar_lab_master.py)")
            self.stdout.write(self.style.ERROR(f'Error inesperado: {str(e)}'))
            raise

        # --- REPORTE FINAL ---
        self.stdout.write('\n' + '=' * 80)
        self.stdout.write(self.style.SUCCESS('MIGRACION PRISLAB GOLD COMPLETADA'))
        self.stdout.write('=' * 80)
        
        total_estudios = Estudio.objects.count()
        total_parametros = Parametro.objects.count()
        total_paquetes = PerfilLaboratorio.objects.count()
        total_rangos = ValorReferencia.objects.count()
        
        self.stdout.write(f'\n[TOTALES ACUMULADOS]:')
        self.stdout.write(f'   Estudios: {total_estudios}')
        self.stdout.write(f'   Parametros: {total_parametros}')
        self.stdout.write(f'   Paquetes: {total_paquetes}')
        self.stdout.write(f'   Rangos Referencia: {total_rangos}')
        
        self.stdout.write(self.style.SUCCESS('\n[EXITO] LISTO PARA OPERAR'))
        self.stdout.write('=' * 80 + '\n')