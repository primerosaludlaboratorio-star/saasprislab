"""
Catálogos Maestros (Métodos y Muestras)
REGLA: Estandarizar formularios usando modales asíncronos.
Herencia: Si se edita un Método en el catálogo maestro, ofrecer actualización opcional en todos los estudios vinculados.
"""
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.db import transaction
from django.db.models import Count

from core.models import Empresa
from laboratorio.models import Estudio as EstudioLab
from core.utils.estandares_industriales import auditar_cambio_campo


@login_required
def gestionar_metodos(request):
    """
    Vista principal para gestión de métodos (catálogo maestro).
    REGLA: Modales asíncronos para ediciones rápidas.
    """
    empresa = getattr(request.user, 'empresa', None)
    
    # Obtener métodos únicos de los estudios
    metodos = EstudioLab.objects.filter(
        metodo__isnull=False
    ).exclude(metodo='').values('metodo').annotate(
        num_estudios=Count('id')
    ).order_by('metodo')
    
    return render(request, 'core/catalogos_maestros/metodos.html', {
        'empresa': empresa,
        'metodos': metodos
    })


@login_required
@require_http_methods(["GET"])
def api_obtener_metodo(request, metodo_id=None):
    """
    API para obtener datos de un método (para modal de edición).
    """
    empresa = getattr(request.user, 'empresa', None)
    
    if metodo_id:
        # Obtener método específico (si existe modelo Método)
        # Por ahora, obtener desde estudios
        estudios = EstudioLab.objects.filter(
            metodo__isnull=False
        ).exclude(metodo='').distinct('metodo')
        
        metodo_nombre = request.GET.get('nombre', '')
        if metodo_nombre:
            estudios_con_metodo = EstudioLab.objects.filter(
                metodo=metodo_nombre
            )
            
            return JsonResponse({
                'status': 'success',
                'metodo': {
                    'nombre': metodo_nombre,
                    'num_estudios': estudios_con_metodo.count(),
                    'estudios': [
                        {
                            'id': e.id,
                            'codigo': e.codigo,
                            'nombre': e.nombre
                        }
                        for e in estudios_con_metodo[:20]
                    ]
                }
            })
    
    return JsonResponse({
        'status': 'error',
        'mensaje': 'Método no especificado'
    }, status=400)


@login_required
@require_http_methods(["POST"])
def api_actualizar_metodo(request):
    """
    API para actualizar un método en el catálogo maestro.
    REGLA: Herencia - Ofrecer actualización opcional en todos los estudios vinculados.
    """
    empresa = getattr(request.user, 'empresa', None)
    
    try:
        data = json.loads(request.body)
        metodo_anterior = data.get('metodo_anterior', '').strip()
        metodo_nuevo = data.get('metodo_nuevo', '').strip()
        actualizar_estudios = data.get('actualizar_estudios', False)  # Herencia
        
        if not metodo_anterior or not metodo_nuevo:
            return JsonResponse({
                'status': 'error',
                'mensaje': 'Debe especificar método anterior y nuevo'
            }, status=400)
        
        # Buscar estudios con el método anterior
        estudios_afectados = EstudioLab.objects.filter(metodo=metodo_anterior)
        num_estudios = estudios_afectados.count()
        
        with transaction.atomic():
            if actualizar_estudios:
                # Actualizar todos los estudios vinculados (herencia)
                estudios_actualizados = estudios_afectados.update(metodo=metodo_nuevo)
                
                # Registrar auditoría para cada estudio actualizado
                for estudio in estudios_afectados:
                    auditar_cambio_campo(
                        campo_nombre='metodo',
                        valor_anterior=metodo_anterior,
                        valor_nuevo=metodo_nuevo,
                        modelo_instancia=estudio,
                        request=request,
                        modulo='LABORATORIO',
                        accion='UPDATE'
                    )
                
                mensaje = f'Método actualizado en {estudios_actualizados} estudios'
            else:
                # Solo actualizar el catálogo maestro (sin tocar estudios)
                mensaje = f'Método actualizado en catálogo maestro ({num_estudios} estudios afectados, no actualizados)'
        
        return JsonResponse({
            'status': 'success',
            'mensaje': mensaje,
            'num_estudios_afectados': num_estudios,
            'actualizados': estudios_actualizados if actualizar_estudios else 0
        })
        
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'mensaje': f'Error al actualizar método: {str(e)}'
        }, status=500)


@login_required
def gestionar_muestras(request):
    """
    Vista principal para gestión de muestras (catálogo maestro).
    REGLA: Modales asíncronos para ediciones rápidas.
    """
    empresa = getattr(request.user, 'empresa', None)
    
    # Obtener muestras únicas de los estudios
    muestras = EstudioLab.objects.filter(
        muestra_requerida__isnull=False
    ).exclude(muestra_requerida='').values('muestra_requerida').annotate(
        num_estudios=Count('id')
    ).order_by('muestra_requerida')
    
    return render(request, 'core/catalogos_maestros/muestras.html', {
        'empresa': empresa,
        'muestras': muestras
    })


@login_required
@require_http_methods(["POST"])
def api_actualizar_muestra(request):
    """
    API para actualizar una muestra en el catálogo maestro.
    REGLA: Herencia - Ofrecer actualización opcional en todos los estudios vinculados.
    """
    empresa = getattr(request.user, 'empresa', None)
    
    try:
        data = json.loads(request.body)
        muestra_anterior = data.get('muestra_anterior', '').strip()
        muestra_nueva = data.get('muestra_nueva', '').strip()
        actualizar_estudios = data.get('actualizar_estudios', False)  # Herencia
        
        if not muestra_anterior or not muestra_nueva:
            return JsonResponse({
                'status': 'error',
                'mensaje': 'Debe especificar muestra anterior y nueva'
            }, status=400)
        
        # Buscar estudios con la muestra anterior
        estudios_afectados = EstudioLab.objects.filter(muestra_requerida=muestra_anterior)
        num_estudios = estudios_afectados.count()
        
        with transaction.atomic():
            if actualizar_estudios:
                # Actualizar todos los estudios vinculados (herencia)
                estudios_actualizados = estudios_afectados.update(muestra_requerida=muestra_nueva)
                
                # Registrar auditoría
                for estudio in estudios_afectados:
                    auditar_cambio_campo(
                        campo_nombre='muestra_requerida',
                        valor_anterior=muestra_anterior,
                        valor_nuevo=muestra_nueva,
                        modelo_instancia=estudio,
                        request=request,
                        modulo='LABORATORIO',
                        accion='UPDATE'
                    )
                
                mensaje = f'Muestra actualizada en {estudios_actualizados} estudios'
            else:
                mensaje = f'Muestra actualizada en catálogo maestro ({num_estudios} estudios afectados, no actualizados)'
        
        return JsonResponse({
            'status': 'success',
            'mensaje': mensaje,
            'num_estudios_afectados': num_estudios,
            'actualizados': estudios_actualizados if actualizar_estudios else 0
        })
        
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'mensaje': f'Error al actualizar muestra: {str(e)}'
        }, status=500)
