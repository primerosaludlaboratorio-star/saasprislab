"""
PRISLAB V5.0 - SCRIPT DE INICIALIZACIÓN IDEMPOTENTE
====================================================
Fecha: 1 de Febrero de 2026
Objetivo: Cargar catálogo de estudios de laboratorio sin duplicar

FILOSOFÍA IDEMPOTENTE:
- Si el estudio YA existe (mismo nombre y categoría): ACTUALIZA precios y datos
- Si el estudio NO existe: LO CREA
- Puede ejecutarse N veces sin riesgo de duplicar datos
"""

import os
import csv
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.db import transaction
from laboratorio.models import CategoriaExamen, Estudio

class Command(BaseCommand):
    help = 'Carga catálogo de estudios de laboratorio de forma idempotente (actualiza si existe, crea si no)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--archivo',
            type=str,
            default='data/estudios_laboratorio.csv',
            help='Ruta al archivo CSV con los estudios'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Simula la carga sin realizar cambios en la base de datos'
        )

    @transaction.atomic
    def handle(self, *args, **options):
        archivo_csv = options['archivo']
        dry_run = options['dry_run']
        
        if dry_run:
            self.stdout.write(self.style.WARNING('🔍 MODO SIMULACIÓN (Dry Run) - No se realizarán cambios'))
        
        # Verificar que el archivo existe
        if not os.path.exists(archivo_csv):
            self.stdout.write(self.style.ERROR(f'❌ Archivo no encontrado: {archivo_csv}'))
            self.stdout.write(self.style.WARNING(f'   Ruta esperada: {os.path.abspath(archivo_csv)}'))
            return
        
        self.stdout.write(self.style.SUCCESS(f'📂 Leyendo archivo: {archivo_csv}'))
        
        # Contadores
        estudios_creados = 0
        estudios_actualizados = 0
        categorias_creadas = 0
        errores = 0
        
        try:
            with open(archivo_csv, 'r', encoding='utf-8-sig') as archivo:
                reader = csv.DictReader(archivo)
                
                # Validar headers requeridos
                headers_requeridos = ['categoria', 'nombre', 'precio_base']
                headers_encontrados = reader.fieldnames
                
                if not all(h in headers_encontrados for h in headers_requeridos):
                    self.stdout.write(self.style.ERROR(
                        f'❌ Headers requeridos: {headers_requeridos}\n'
                        f'   Headers encontrados: {headers_encontrados}'
                    ))
                    return
                
                self.stdout.write(self.style.SUCCESS(f'✓ Headers válidos: {headers_encontrados}'))
                self.stdout.write('')
                
                for i, row in enumerate(reader, start=1):
                    try:
                        # Extraer datos
                        categoria_nombre = row['categoria'].strip()
                        estudio_nombre = row['nombre'].strip()
                        precio_base = Decimal(row['precio_base'].replace(',', '').strip() or '0')
                        
                        # Campos opcionales
                        codigo = row.get('codigo', '').strip() or None
                        valor_minimo = row.get('valor_minimo', '').strip()
                        valor_maximo = row.get('valor_maximo', '').strip()
                        unidades = row.get('unidades', '').strip() or None
                        dias_entrega = row.get('dias_entrega', '').strip() or None
                        muestra_requerida = row.get('muestra_requerida', '').strip() or None
                        keywords = row.get('keywords', '').strip() or None
                        
                        # Validar datos mínimos
                        if not categoria_nombre or not estudio_nombre:
                            self.stdout.write(self.style.WARNING(
                                f'⚠️  Línea {i}: Faltan datos obligatorios (categoría o nombre)'
                            ))
                            errores += 1
                            continue
                        
                        # 1. CREAR O ACTUALIZAR CATEGORÍA (idempotente)
                        categoria, categoria_creada = CategoriaExamen.objects.get_or_create(
                            nombre=categoria_nombre,
                            defaults={'descripcion': f'Categoría de {categoria_nombre}'}
                        )
                        
                        if categoria_creada:
                            categorias_creadas += 1
                            if not dry_run:
                                self.stdout.write(self.style.SUCCESS(
                                    f'  ✓ Categoría creada: {categoria_nombre}'
                                ))
                        
                        # 2. CREAR O ACTUALIZAR ESTUDIO (idempotente)
                        estudio, estudio_creado = Estudio.objects.update_or_create(
                            categoria=categoria,
                            nombre=estudio_nombre,
                            defaults={
                                'codigo': codigo,
                                'precio_base': precio_base,
                                'valor_minimo': Decimal(valor_minimo) if valor_minimo else None,
                                'valor_maximo': Decimal(valor_maximo) if valor_maximo else None,
                                'unidades': unidades,
                                'dias_entrega': dias_entrega,
                                'muestra_requerida': muestra_requerida,
                                'keywords': keywords,
                            }
                        )
                        
                        if estudio_creado:
                            estudios_creados += 1
                            if not dry_run:
                                self.stdout.write(self.style.SUCCESS(
                                    f'  ✓ Estudio creado: {estudio_nombre} (${precio_base})'
                                ))
                        else:
                            estudios_actualizados += 1
                            if not dry_run:
                                self.stdout.write(self.style.WARNING(
                                    f'  ↻ Estudio actualizado: {estudio_nombre} (${precio_base})'
                                ))
                    
                    except Exception as e:
                        errores += 1
                        self.stdout.write(self.style.ERROR(
                            f'❌ Error en línea {i}: {str(e)}'
                        ))
                        continue
        
        except FileNotFoundError:
            self.stdout.write(self.style.ERROR(f'❌ Archivo no encontrado: {archivo_csv}'))
            return
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ Error al procesar archivo: {str(e)}'))
            return
        
        # RESUMEN FINAL
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('=' * 60))
        self.stdout.write(self.style.SUCCESS('  📊 RESUMEN DE CARGA'))
        self.stdout.write(self.style.SUCCESS('=' * 60))
        self.stdout.write(f'  Categorías creadas:    {categorias_creadas}')
        self.stdout.write(f'  Estudios creados:      {estudios_creados}')
        self.stdout.write(f'  Estudios actualizados: {estudios_actualizados}')
        
        if errores > 0:
            self.stdout.write(self.style.ERROR(f'  Errores:               {errores}'))
        else:
            self.stdout.write(self.style.SUCCESS(f'  Errores:               0'))
        
        self.stdout.write(self.style.SUCCESS('=' * 60))
        
        if dry_run:
            self.stdout.write(self.style.WARNING('⚠️  SIMULACIÓN - No se guardaron cambios'))
        else:
            self.stdout.write(self.style.SUCCESS('✅ Carga completada exitosamente'))
        
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('💡 MODO IDEMPOTENTE:'))
        self.stdout.write('   Puedes ejecutar este comando múltiples veces sin riesgo.')
        self.stdout.write('   - Si un estudio existe: Se actualiza con los nuevos datos')
        self.stdout.write('   - Si un estudio no existe: Se crea desde cero')
