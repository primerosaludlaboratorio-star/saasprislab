"""
Vistas para Microbiología y Antibiogramas (REGLA 3).
Flujo: Bacteria -> Grupo de Antibióticos -> Sensibilidad (S/I/R)
"""
import json

from django.shortcuts import get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.db import transaction

from core.models import DetalleOrden
import logging


def _resolver_modelos_microbiologia():
    """
    Importa los modelos de microbiología de forma diferida.

    El módulo histórico quedó cableado a modelos que no existen en esta rama.
    En lugar de romper import de vistas o devolver 500 críptico, respondemos
    explícitamente que el bloque sigue pendiente de implementación real.
    """
    try:
        from core.models.microbiologia import Bacteria, GrupoAntibiotico, ResultadoAntibiograma
        return Bacteria, GrupoAntibiotico, ResultadoAntibiograma
    except Exception:
        logging.getLogger(__name__).exception("Error inesperado en _resolver_modelos_microbiologia (microbiologia.py)")
        return None


@login_required
@require_http_methods(["POST"])
def api_inyectar_antibiogramas(request, detalle_id):
    """
    API para inyectar automáticamente las filas de antibióticos cuando se reporta una bacteria.
    REGLA 3: Flujo de Microbiología
    """
    empresa = getattr(request.user, 'empresa', None)
    modelos = _resolver_modelos_microbiologia()
    if not modelos:
        return JsonResponse({
            'status': 'error',
            'mensaje': 'El módulo de microbiología aún no está implementado completamente en esta versión.'
        }, status=503)
    Bacteria, GrupoAntibiotico, ResultadoAntibiograma = modelos
    
    try:
        detalle = get_object_or_404(DetalleOrden, id=detalle_id, orden__empresa=empresa)
        data = json.loads(request.body)
        bacteria_id = data.get('bacteria_id')
        
        if not bacteria_id:
            return JsonResponse({
                'status': 'error',
                'mensaje': 'Debe especificar una bacteria'
            }, status=400)
        
        bacteria = get_object_or_404(Bacteria, id=bacteria_id, empresa=empresa)
        
        # Obtener grupos de antibióticos para esta bacteria
        grupos = GrupoAntibiotico.objects.filter(
            bacteria=bacteria,
            activo=True
        ).prefetch_related('antibioticos').order_by('orden')
        
        antibioticos_data = []
        
        with transaction.atomic():
            for grupo in grupos:
                antibioticos = grupo.antibioticos.filter(activo=True).order_by('orden')
                
                for antibiotico in antibioticos:
                    # Crear o obtener resultado de antibiograma
                    resultado, creado = ResultadoAntibiograma.objects.get_or_create(
                        detalle_orden=detalle,
                        bacteria=bacteria,
                        antibiotico=antibiotico,
                        defaults={
                            'sensibilidad': '',
                            'usuario_registro': request.user
                        }
                    )
                    
                    antibioticos_data.append({
                        'id': resultado.id,
                        'antibiotico_id': antibiotico.id,
                        'nombre': antibiotico.nombre,
                        'grupo': grupo.nombre,
                        'concentracion': antibiotico.concentracion or '',
                        'sensibilidad': resultado.sensibilidad or '',
                        'diametro_inhibicion': str(resultado.diametro_inhibicion) if resultado.diametro_inhibicion else '',
                        'cim': str(resultado.cim) if resultado.cim else '',
                        'creado': creado
                    })
        
        return JsonResponse({
            'status': 'success',
            'mensaje': f'Se inyectaron {len(antibioticos_data)} antibióticos para {bacteria.nombre}',
            'bacteria': {
                'id': bacteria.id,
                'nombre': bacteria.nombre
            },
            'antibioticos': antibioticos_data
        })
        
    except Exception as e:
        logging.getLogger(__name__).exception("Error inesperado en api_inyectar_antibiogramas (microbiologia.py)")
        return JsonResponse({
            'status': 'error',
            'mensaje': f'Error al inyectar antibióticos: {str(e)}'
        }, status=500)


@login_required
@require_http_methods(["POST"])
def api_guardar_sensibilidad(request, resultado_id):
    """
    API para guardar la sensibilidad (S/I/R) de un antibiótico.
    """
    empresa = getattr(request.user, 'empresa', None)
    modelos = _resolver_modelos_microbiologia()
    if not modelos:
        return JsonResponse({
            'status': 'error',
            'mensaje': 'El módulo de microbiología aún no está implementado completamente en esta versión.'
        }, status=503)
    _, _, ResultadoAntibiograma = modelos
    
    try:
        resultado = get_object_or_404(
            ResultadoAntibiograma,
            id=resultado_id,
            detalle_orden__orden__empresa=empresa
        )
        
        data = json.loads(request.body)
        sensibilidad = data.get('sensibilidad', '').upper()
        diametro_inhibicion = data.get('diametro_inhibicion')
        cim = data.get('cim')
        
        if sensibilidad not in ['S', 'I', 'R', '']:
            return JsonResponse({
                'status': 'error',
                'mensaje': 'Sensibilidad inválida. Debe ser S, I o R'
            }, status=400)
        
        resultado.sensibilidad = sensibilidad
        if diametro_inhibicion:
            resultado.diametro_inhibicion = float(diametro_inhibicion)
        if cim:
            resultado.cim = float(cim)
        resultado.save()
        
        return JsonResponse({
            'status': 'success',
            'mensaje': 'Sensibilidad guardada correctamente'
        })
        
    except Exception as e:
        logging.getLogger(__name__).exception("Error inesperado en api_guardar_sensibilidad (microbiologia.py)")
        return JsonResponse({
            'status': 'error',
            'mensaje': f'Error al guardar: {str(e)}'
        }, status=500)