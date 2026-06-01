"""
Comando de Management: Carga Masiva del Catálogo Maestro de Pruebas

Este comando importa el archivo catalogo_maestro_de_pruebas.csv que contiene
163 parámetros individuales de laboratorio, siendo la ÚNICA FUENTE DE VERDAD.

Estructura CSV:
- codigo_unico: ID primario (ej. PRU-001)
- nombre: Descripción completa
- abreviatura: Nombre corto para reportes
- unidades: Unidades de medida
- valor_bajo / valor_alto: Rangos para activar Alerta Neón
- area: Clasificación operativa (Hematología, Química, etc.)
- estudio: Clasificación para agrupación (Citometría, Química de 32, etc.)
"""

import csv
import os
from decimal import Decimal, InvalidOperation
from django.core.management.base import BaseCommand
from django.conf import settings
from django.db import transaction
from laboratorio.models import CategoriaExamen, Estudio
from core.models import Empresa


class Command(BaseCommand):
    help = 'Carga masiva del catálogo maestro de pruebas desde catalogo_maestro_de_pruebas.csv'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Forzar actualización de estudios existentes',
        )

    def handle(self, *args, **options):
        force = options.get('force', False)
        
        archivo = os.path.join(settings.BASE_DIR, 'catalogo_maestro_de_pruebas.csv')
        
        if not os.path.exists(archivo):
            self.stdout.write(self.style.ERROR(f'[ERROR] No se encuentra el archivo "catalogo_maestro_de_pruebas.csv" en {settings.BASE_DIR}'))
            return
        
        # Obtener empresa Prislab
        try:
            empresa_prislab = Empresa.objects.get(nombre='PRISLAB')
        except Empresa.DoesNotExist:
            self.stdout.write(self.style.ERROR('[ERROR] La empresa PRISLAB no existe. Ejecuta primero: python manage.py inicializar_pris_valle'))
            return
        
        self.stdout.write(self.style.SUCCESS(f'\n[INICIO] Cargando Catálogo Maestro de Pruebas para {empresa_prislab.nombre}...\n'))
        
        # Estadísticas
        categorias_creadas = 0
        estudios_creados = 0
        estudios_actualizados = 0
        errores = 0
        
        try:
            with transaction.atomic():
                # Leer CSV con encoding UTF-8-sig para manejar BOM
                with open(archivo, 'r', encoding='utf-8-sig') as f:
                    reader = csv.DictReader(f)
                    
                    for idx, row in enumerate(reader, start=2):  # start=2 porque la fila 1 es el encabezado
                        try:
                            # Limpiar datos del CSV
                            codigo_unico = row['Código Único'].strip()
                            nombre = row['Nombre de la Prueba'].strip()
                            abreviatura = row['Abreviatura'].strip() if row['Abreviatura'] else ''
                            unidades = row['Unidades'].strip() if row['Unidades'] else ''
                            valor_bajo_str = row['Valor Bajo (Ref)'].strip() if row['Valor Bajo (Ref)'] else None
                            valor_alto_str = row['Valor Alto (Ref)'].strip() if row['Valor Alto (Ref)'] else None
                            area = row['Área de Laboratorio'].strip()
                            estudio_grupo = row['Estudio (Grupo)'].strip()
                            
                            # Validar campos obligatorios (filtrar filas vacías silenciosamente)
                            if not codigo_unico or not nombre or not area:
                                continue  # Fila vacía, omitir silenciosamente
                            
                            # ============================================================
                            # PASO 1: Crear/Obtener Categoría (Área)
                            # ============================================================
                            categoria, cat_created = CategoriaExamen.objects.get_or_create(
                                nombre=area,
                                defaults={
                                    'descripcion': f'Categoría de {area}'
                                }
                            )
                            if cat_created:
                                categorias_creadas += 1
                                self.stdout.write(self.style.SUCCESS(f'  [OK] Categoría creada: {categoria.nombre}'))
                            
                            # ============================================================
                            # PASO 2: Procesar Valores de Referencia
                            # ============================================================
                            # Manejar valores numéricos vs texto (ej: "NEGATIVO", "Amarillo")
                            valor_minimo = None
                            valor_maximo = None
                            rango_panico_min = None
                            rango_panico_max = None
                            es_texto = False
                            
                            if valor_bajo_str and valor_alto_str:
                                # Intentar convertir a decimal
                                try:
                                    valor_minimo = Decimal(str(valor_bajo_str).replace(',', '.'))
                                    valor_maximo = Decimal(str(valor_alto_str).replace(',', '.'))
                                    # Los valores del CSV son para Alerta Neón (rango_panico)
                                    rango_panico_min = valor_minimo
                                    rango_panico_max = valor_maximo
                                except (InvalidOperation, ValueError):
                                    # Es texto (ej: "NEGATIVO", "Amarillo")
                                    es_texto = True
                                    # Para valores de texto, no hay rango numérico
                                    # Estos se manejarán en la captura de resultados
                            
                            # ============================================================
                            # PASO 3: Crear/Actualizar Estudio Individual
                            # ============================================================
                            # Intentar buscar por código primero, luego por nombre+categoría
                            try:
                                estudio = Estudio.objects.get(codigo=codigo_unico)
                                est_created = False
                            except Estudio.DoesNotExist:
                                # Intentar buscar por nombre y categoría (unique_together)
                                try:
                                    estudio = Estudio.objects.get(categoria=categoria, nombre=nombre)
                                    est_created = False
                                    # Actualizar código si no tenía
                                    if not estudio.codigo:
                                        estudio.codigo = codigo_unico
                                except Estudio.DoesNotExist:
                                    # Crear nuevo estudio
                                    estudio = Estudio(
                                        codigo=codigo_unico,
                                        categoria=categoria,
                                        nombre=nombre,
                                        unidades=unidades if unidades and unidades != '-' else '',
                                        valor_minimo=valor_minimo,
                                        valor_maximo=valor_maximo,
                                        rango_panico_min=rango_panico_min,
                                        rango_panico_max=rango_panico_max,
                                        precio_base=Decimal('0.00'),
                                        descripcion_interna=f'Código: {codigo_unico} | Abreviatura: {abreviatura} | Estudio Grupo: {estudio_grupo}',
                                    )
                                    estudio.save()
                                    est_created = True
                            
                            if est_created:
                                estudios_creados += 1
                                self.stdout.write(self.style.SUCCESS(f'  [OK] Estudio creado: {codigo_unico} - {nombre}'))
                            else:
                                # Actualizar si está en modo force o si faltan datos
                                if force or not estudio.codigo or not estudio.rango_panico_min:
                                    if not estudio.codigo:
                                        estudio.codigo = codigo_unico
                                    estudio.categoria = categoria
                                    if estudio.nombre != nombre:
                                        estudio.nombre = nombre
                                    estudio.unidades = unidades if unidades and unidades != '-' else ''
                                    if valor_minimo is not None:
                                        estudio.valor_minimo = valor_minimo
                                    if valor_maximo is not None:
                                        estudio.valor_maximo = valor_maximo
                                    if rango_panico_min is not None:
                                        estudio.rango_panico_min = rango_panico_min
                                    if rango_panico_max is not None:
                                        estudio.rango_panico_max = rango_panico_max
                                    if not estudio.descripcion_interna:
                                        estudio.descripcion_interna = f'Código: {codigo_unico} | Abreviatura: {abreviatura} | Estudio Grupo: {estudio_grupo}'
                                    estudio.save()
                                    estudios_actualizados += 1
                                    if force:
                                        self.stdout.write(self.style.WARNING(f'  [ACTUALIZADO] Estudio: {codigo_unico} - {nombre}'))
                            
                        except Exception as e:
                            self.stdout.write(self.style.ERROR(f'  [ERROR] Fila {idx}: {str(e)}'))
                            errores += 1
                            continue
                
                # ============================================================
                # RESUMEN FINAL
                # ============================================================
                total_estudios = Estudio.objects.filter(categoria__nombre__in=['Hematología', 'Química Clínica', 'Especiales', 'Serología', 'Uroanálisis']).count()
                
                self.stdout.write(self.style.SUCCESS('\n' + '='*60))
                self.stdout.write(self.style.SUCCESS('[COMPLETADO] CARGA MASIVA FINALIZADA'))
                self.stdout.write(self.style.SUCCESS('='*60))
                self.stdout.write(f'\nResumen:')
                self.stdout.write(f'   - Categorias creadas: {categorias_creadas}')
                self.stdout.write(f'   - Estudios nuevos: {estudios_creados}')
                self.stdout.write(f'   - Estudios actualizados: {estudios_actualizados}')
                self.stdout.write(f'   - Errores: {errores}')
                self.stdout.write(f'   - Total de estudios en catálogo: {total_estudios}')
                self.stdout.write(self.style.SUCCESS(f'\n[EXITO] Catálogo Maestro de Pruebas cargado exitosamente!\n'))
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'\n[ERROR] Error durante la carga: {str(e)}'))
            self.stdout.write(self.style.ERROR('   La transaccion ha sido revertida.'))
            raise
