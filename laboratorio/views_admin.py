"""
Vistas administrativas para el módulo de laboratorio
"""
import csv
import io
import logging
from decimal import Decimal, InvalidOperation

from django.contrib.admin.views.decorators import staff_member_required
from django.db import transaction
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from laboratorio.models import CategoriaExamen, Estudio

logger = logging.getLogger(__name__)

@staff_member_required
@require_POST
def cargar_tarifas_desde_csv(request):
    """
    Endpoint para cargar tarifas desde un archivo CSV subido
    Solo accesible para staff
    """
    if 'archivo' not in request.FILES:
        return JsonResponse({
            'ok': False,
            'mensaje': 'No se proporciono un archivo CSV'
        }, status=400)
    
    archivo = request.FILES['archivo']
    
    # Validar que es un archivo CSV
    if not archivo.name.endswith('.csv'):
        return JsonResponse({
            'ok': False,
            'mensaje': 'El archivo debe ser un CSV'
        }, status=400)
    
    try:
        # Leer el archivo CSV
        contenido = archivo.read().decode('utf-8')
        csv_file = io.StringIO(contenido)
        
        # Saltar las primeras 2 líneas
        next(csv_file)
        next(csv_file)
        
        # Leer el CSV
        reader = csv.DictReader(csv_file)
        
        # Contadores
        categorias_creadas = 0
        estudios_creados = 0
        estudios_actualizados = 0
        errores = []
        
        with transaction.atomic():
            for idx, row in enumerate(reader, start=1):
                try:
                    tipo = row.get('Tipo', '').strip()
                    codigo = row.get('Código', '').strip() or row.get('Abreviatura', '').strip()
                    abreviatura = row.get('Abreviatura', '').strip()
                    descripcion = row.get('Descripción', '').strip()
                    importe_str = row.get('Importe', '0').strip()

                    if not tipo or not descripcion:
                        continue

                    try:
                        importe = Decimal(importe_str) if importe_str else Decimal('0')
                    except (InvalidOperation, ValueError):
                        importe = Decimal('0')

                    categoria, created = CategoriaExamen.objects.get_or_create(
                        nombre=tipo,
                        defaults={'descripcion': f'Estudios tipo {tipo}'}
                    )
                    if created:
                        categorias_creadas += 1

                    estudio, created = Estudio.objects.update_or_create(
                        codigo=codigo or abreviatura or f"EST{idx}",
                        defaults={
                            'categoria': categoria,
                            'nombre': descripcion[:150],
                            'precio_base': importe,
                        }
                    )
                    if created:
                        estudios_creados += 1
                    else:
                        estudios_actualizados += 1

                except Exception as e:
                    logger.warning(f'[CSV Tarifas] Error fila {idx + 2}: {e}')
                    errores.append(f"Linea {idx + 2}: {str(e)}")
        
        # Resumen
        total_estudios = Estudio.objects.count()
        total_categorias = CategoriaExamen.objects.count()
        
        return JsonResponse({
            'ok': True,
            'mensaje': 'Tarifas cargadas exitosamente',
            'resumen': {
                'categorias_creadas': categorias_creadas,
                'estudios_creados': estudios_creados,
                'estudios_actualizados': estudios_actualizados,
                'errores': len(errores),
                'total_estudios': total_estudios,
                'total_categorias': total_categorias,
            },
            'errores_detalle': errores[:10]  # Solo mostrar primeros 10 errores
        })
        
    except Exception as e:
        return JsonResponse({
            'ok': False,
            'mensaje': f'Error al procesar el archivo: {str(e)}'
        }, status=500)


@staff_member_required
def vista_cargar_tarifas(request):
    """
    Vista para mostrar el formulario de carga de tarifas
    """
    from django.shortcuts import render
    return render(request, 'laboratorio/admin/cargar_tarifas.html')
