"""
Script para cargar tarifas de laboratorio desde CSV
Ejecutar: python manage.py shell < cargar_tarifas.py
"""
import os
import django
import csv
import logging

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from laboratorio.models import CategoriaExamen, Estudio
from decimal import Decimal

def cargar_tarifas():
    """
    Carga las tarifas desde el archivo tarifas.csv
    """
    archivo_csv = 'tarifas.csv'
    
    print("=" * 80)
    print("CARGANDO TARIFAS DE LABORATORIO")
    print("=" * 80)
    print()
    
    # Verificar que el archivo existe
    if not os.path.exists(archivo_csv):
        print(f"[ERROR] No se encontro el archivo {archivo_csv}")
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
                    print(f"[WARN] Linea {idx + 2}: Datos incompletos, saltando...")
                    continue
                
                # Convertir importe a Decimal
                try:
                    importe = Decimal(importe_str) if importe_str else Decimal('0')
                except:
                    importe = Decimal('0')
                    print(f"[WARN] Linea {idx + 2}: Precio invalido '{importe_str}', usando 0")
                
                # Crear o obtener la categoría
                categoria, created = CategoriaExamen.objects.get_or_create(
                    nombre=tipo,
                    defaults={'descripcion': f'Estudios tipo {tipo}'}
                )
                
                if created:
                    categorias_creadas += 1
                    print(f"[CATEGORIA] Creada: {tipo}")
                
                # Crear o actualizar el estudio
                estudio, created = Estudio.objects.update_or_create(
                    codigo=codigo or abreviatura or f"EST{idx}",
                    defaults={
                        'categoria': categoria,
                        'nombre': descripcion,
                        'precio_base': importe,
                    }
                )
                
                if created:
                    estudios_creados += 1
                    print(f"[OK] [{idx:03d}] Creado: {codigo[:15]:15s} | {descripcion[:50]:50s} | ${importe:>8.2f}")
                else:
                    estudios_actualizados += 1
                    print(f"[UPDATE] [{idx:03d}] Actualizado: {codigo[:15]:15s} | {descripcion[:50]:50s} | ${importe:>8.2f}")
                
            except Exception as e:
                logging.getLogger(__name__).exception("Error inesperado en cargar_tarifas (cargar_tarifas.py)")
                errores += 1
                print(f"[ERROR] Linea {idx + 2}: Error al procesar - {str(e)}")
                continue
    
    # Resumen final
    print()
    print("=" * 80)
    print("RESUMEN DE IMPORTACION")
    print("=" * 80)
    print(f"Categorias creadas: {categorias_creadas}")
    print(f"Estudios creados: {estudios_creados}")
    print(f"Estudios actualizados: {estudios_actualizados}")
    print(f"Errores: {errores}")
    print(f"Total procesado: {estudios_creados + estudios_actualizados}")
    print()
    
    # Verificar en base de datos
    total_estudios = Estudio.objects.count()
    total_categorias = CategoriaExamen.objects.count()
    
    print(f"Total en base de datos:")
    print(f"   - Categorias: {total_categorias}")
    print(f"   - Estudios: {total_estudios}")
    print()
    
    # Mostrar estadísticas por categoría
    print("Estudios por categoria:")
    for categoria in CategoriaExamen.objects.all():
        count = categoria.estudios.count()
        print(f"   - {categoria.nombre}: {count} estudios")
    
    print()
    print("=" * 80)
    print("IMPORTACION COMPLETADA!")
    print("=" * 80)

if __name__ == '__main__':
    cargar_tarifas()