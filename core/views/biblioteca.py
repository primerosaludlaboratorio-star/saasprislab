"""
Vista de Biblioteca de Liderazgo para el Director.
"""
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.utils import timezone
import json

from core.models import LibroLiderazgo


@login_required
def biblioteca_liderazgo(request):
    """Vista principal de la Biblioteca de Liderazgo (galería de tarjetas)."""
    empresa = getattr(request.user, 'empresa', None)
    
    if not empresa:
        from django.contrib import messages
        messages.error(request, 'Usuario no tiene empresa asignada.')
        from django.shortcuts import redirect
        return redirect('home')
    
    libros = LibroLiderazgo.objects.filter(empresa=empresa).order_by('-fecha_agregado')
    
    # Contar por estado
    por_leer = libros.filter(estado_lectura='POR_LEER').count()
    leyendo = libros.filter(estado_lectura='LEYENDO').count()
    terminados = libros.filter(estado_lectura='TERMINADO').count()
    
    return render(request, 'core/biblioteca_liderazgo.html', {
        'empresa': empresa,
        'libros': libros,
        'por_leer': por_leer,
        'leyendo': leyendo,
        'terminados': terminados,
        'total': libros.count()
    })


@login_required
@require_http_methods(["POST"])
def api_cambiar_estado_libro(request, libro_id):
    """
    API para cambiar el estado de lectura de un libro.
    Body JSON: { estado_lectura: 'POR_LEER'|'LEYENDO'|'TERMINADO' }
    """
    empresa = getattr(request.user, 'empresa', None)
    
    if not empresa:
        return JsonResponse({'status': 'error', 'mensaje': 'Usuario no tiene empresa asignada'}, status=400)
    
    try:
        libro = get_object_or_404(LibroLiderazgo, id=libro_id, empresa=empresa)
        data = json.loads(request.body)
        nuevo_estado = data.get('estado_lectura', libro.estado_lectura)
        
        if nuevo_estado not in [e[0] for e in LibroLiderazgo.ESTADO_LECTURA_CHOICES]:
            return JsonResponse({'status': 'error', 'mensaje': 'Estado inválido'}, status=400)
        
        libro.estado_lectura = nuevo_estado
        
        # Actualizar fechas según el estado
        ahora = timezone.now()
        if nuevo_estado == 'LEYENDO' and not libro.fecha_inicio_lectura:
            libro.fecha_inicio_lectura = ahora
        elif nuevo_estado == 'TERMINADO':
            if not libro.fecha_inicio_lectura:
                libro.fecha_inicio_lectura = ahora
            libro.fecha_fin_lectura = ahora
        elif nuevo_estado == 'POR_LEER':
            # Si vuelve a "Por Leer", limpiar fechas
            libro.fecha_inicio_lectura = None
            libro.fecha_fin_lectura = None
        
        libro.save()
        
        return JsonResponse({
            'status': 'success',
            'mensaje': f'Libro marcado como {libro.get_estado_lectura_display()}',
            'libro_id': libro.id,
            'estado_lectura': libro.estado_lectura
        })
        
    except LibroLiderazgo.DoesNotExist:
        return JsonResponse({'status': 'error', 'mensaje': 'Libro no encontrado'}, status=404)
    except Exception as e:
        return JsonResponse({'status': 'error', 'mensaje': str(e)}, status=500)


@login_required
def agregar_libro(request):
    """API para agregar un nuevo libro a la biblioteca."""
    empresa = getattr(request.user, 'empresa', None)
    
    if not empresa:
        return JsonResponse({'status': 'error', 'mensaje': 'Usuario no tiene empresa asignada'}, status=400)
    
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'mensaje': 'Método no permitido'}, status=405)
    
    try:
        titulo = request.POST.get('titulo', '').strip()
        autor = request.POST.get('autor', '').strip()
        portada_url = request.POST.get('portada_url', '').strip()
        resumen_ejecutivo = request.POST.get('resumen_ejecutivo', '').strip()
        aplicacion_practica = request.POST.get('aplicacion_practica', '').strip()
        estado_lectura = request.POST.get('estado_lectura', 'POR_LEER')
        
        if not titulo or not autor or not resumen_ejecutivo:
            return JsonResponse({'status': 'error', 'mensaje': 'Título, autor y resumen ejecutivo son obligatorios'}, status=400)
        
        libro = LibroLiderazgo.objects.create(
            empresa=empresa,
            titulo=titulo,
            autor=autor,
            portada_url=portada_url if portada_url else None,
            resumen_ejecutivo=resumen_ejecutivo,
            aplicacion_practica=aplicacion_practica,
            estado_lectura=estado_lectura
        )
        
        return JsonResponse({
            'status': 'success',
            'mensaje': f'Libro "{titulo}" agregado correctamente',
            'libro_id': libro.id
        })
        
    except Exception as e:
        import logging
        logger = logging.getLogger('core')
        logger.error(f"Error al agregar libro: {str(e)}", exc_info=True)
        return JsonResponse({'status': 'error', 'mensaje': str(e)}, status=500)
