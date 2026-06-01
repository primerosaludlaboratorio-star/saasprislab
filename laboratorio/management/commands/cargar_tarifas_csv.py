"""
Django management command para cargar tarifas desde CSV
Ejecutar: python manage.py cargar_tarifas_csv
"""
from django.core.management.base import BaseCommand
from laboratorio.models import CategoriaExamen, Estudio
from decimal import Decimal
import csv
import os

class Command(BaseCommand):
    help = 'Carga tarifas de laboratorio desde archivo CSV'

    def add_arguments(self, parser):
        parser.add_argument(
            '--archivo',
            type=str,
            default='tarifas.csv',
            help='Archivo CSV con las tarifas (default: tarifas.csv)'
        )

    def handle(self, *args, **options):
        archivo_csv = options['archivo']
        
        self.stdout.write("=" * 80)
        self.stdout.write(self.style.SUCCESS("CARGANDO TARIFAS DE LABORATORIO"))
        self.stdout.write("=" * 80)
        self.stdout.write("")
        
        # Verificar que el archivo existe
        if not os.path.exists(archivo_csv):
            self.stdout.write(self.style.ERROR(f"No se encontro el archivo {archivo_csv}"))
            return
        
        # Contadores
        categorias_creadas = 0
        estudios_creados = 0
        estudios_actualizados = 0
        errores = 0
        
        # Leer el archivo CSV
        with open(archivo_csv, 'r', encoding='utf-8') as file:
            # Saltar las primeras 2 líneas (encabezados no relevantes)
            next(file)
            next(file)
            
            # Leer el CSV
            reader = csv.DictReader(file)
            
            for idx, row in enumerate(reader, start=1):
                try:
                    # Obtener datos del CSV
                    tipo = row.get('Tipo', '').strip()
                    codigo = row.get('Código', '').strip() or row.get('Abreviatura', '').strip()
                    abreviatura = row.get('Abreviatura', '').strip()
                    descripcion = row.get('Descripción', '').strip()
                    importe_str = row.get('Importe', '0').strip()
                    
                    # Validar que tenemos datos mínimos
                    if not tipo or not descripcion:
                        self.stdout.write(f"[WARN] Linea {idx + 2}: Datos incompletos, saltando...")
                        continue
                    
                    # Convertir importe a Decimal
                    try:
                        importe = Decimal(importe_str) if importe_str else Decimal('0')
                    except:
                        importe = Decimal('0')
                        self.stdout.write(f"[WARN] Linea {idx + 2}: Precio invalido '{importe_str}', usando 0")
                    
                    # Crear o obtener la categoría
                    categoria, created = CategoriaExamen.objects.get_or_create(
                        nombre=tipo,
                        defaults={'descripcion': f'Estudios tipo {tipo}'}
                    )
                    
                    if created:
                        categorias_creadas += 1
                        self.stdout.write(self.style.SUCCESS(f"[CATEGORIA] Creada: {tipo}"))
                    
                    # Crear o actualizar el estudio
                    estudio, created = Estudio.objects.update_or_create(
                        codigo=codigo or abreviatura or f"EST{idx}",
                        defaults={
                            'categoria': categoria,
                            'nombre': descripcion[:150],  # Limitar a 150 caracteres
                            'precio_base': importe,
                        }
                    )
                    
                    if created:
                        estudios_creados += 1
                        # Solo mostrar cada 10 estudios para no saturar el output
                        if idx % 10 == 0 or idx <= 20:
                            self.stdout.write(f"[OK] [{idx:03d}] Creado: {codigo[:15]:15s} | ${importe:>8.2f}")
                    else:
                        estudios_actualizados += 1
                        if idx % 10 == 0 or idx <= 20:
                            self.stdout.write(f"[UPDATE] [{idx:03d}] Actualizado: {codigo[:15]:15s} | ${importe:>8.2f}")
                    
                except Exception as e:
                    errores += 1
                    self.stdout.write(self.style.ERROR(f"[ERROR] Linea {idx + 2}: {str(e)[:100]}"))
                    continue
        
        # Resumen final
        self.stdout.write("")
        self.stdout.write("=" * 80)
        self.stdout.write(self.style.SUCCESS("RESUMEN DE IMPORTACION"))
        self.stdout.write("=" * 80)
        self.stdout.write(f"Categorias creadas: {categorias_creadas}")
        self.stdout.write(f"Estudios creados: {estudios_creados}")
        self.stdout.write(f"Estudios actualizados: {estudios_actualizados}")
        self.stdout.write(f"Errores: {errores}")
        self.stdout.write(f"Total procesado: {estudios_creados + estudios_actualizados}")
        self.stdout.write("")
        
        # Verificar en base de datos
        total_estudios = Estudio.objects.count()
        total_categorias = CategoriaExamen.objects.count()
        
        self.stdout.write(f"Total en base de datos:")
        self.stdout.write(f"   - Categorias: {total_categorias}")
        self.stdout.write(f"   - Estudios: {total_estudios}")
        self.stdout.write("")
        
        # Mostrar estadísticas por categoría
        self.stdout.write("Estudios por categoria:")
        for categoria in CategoriaExamen.objects.all():
            count = categoria.estudios.count()
            self.stdout.write(f"   - {categoria.nombre}: {count} estudios")
        
        self.stdout.write("")
        self.stdout.write("=" * 80)
        self.stdout.write(self.style.SUCCESS("IMPORTACION COMPLETADA!"))
        self.stdout.write("=" * 80)
