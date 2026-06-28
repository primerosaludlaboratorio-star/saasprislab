"""
Vistas para gestión de paquetes con ordenamiento (REGLA 4).
Catálogo: laboratorio.Estudio (perfiles/paquetes legacy UI). core.Estudio fue retirado en core.0073.
"""
import json

from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.db import transaction

from laboratorio.models import Estudio
import logging


@login_required
@require_http_methods(["POST"])
def api_actualizar_orden_paquete(request, paquete_id):
    """
    API para actualizar el orden de estudios en un paquete.
    REGLA 4: UX de Paquetes (Ordenamiento)
    """
    empresa = getattr(request.user, 'empresa', None)
    
    try:
        paquete = get_object_or_404(Estudio, id=paquete_id, es_perfil=True)
        data = json.loads(request.body)
        orden = data.get('orden', [])
        
        if not orden:
            return JsonResponse({
                'status': 'error',
                'mensaje': 'No se proporcionó orden'
            }, status=400)
        
        # Actualizar orden en descripcion_interna o en una tabla de relación
        # Por ahora, guardar en descripcion_interna como JSON
        with transaction.atomic():
            # Obtener estudios del paquete
            estudios_ordenados = []
            for item in orden:
                estudio_id = item.get('estudio_id')
                orden_num = item.get('orden')
                
                try:
                    estudio = Estudio.objects.get(id=estudio_id)
                    estudios_ordenados.append({
                        'id': estudio.id,
                        'codigo': estudio.codigo,
                        'nombre': estudio.nombre,
                        'orden': orden_num
                    })
                except Estudio.DoesNotExist:
                    continue
            
            # Guardar orden (puede ser en un campo JSON o en una tabla de relación)
            # Por ahora, actualizar descripcion_interna
            paquete.descripcion_interna = json.dumps(estudios_ordenados, ensure_ascii=False)
            paquete.save()
        
        return JsonResponse({
            'status': 'success',
            'mensaje': 'Orden actualizado correctamente'
        })
        
    except Exception as e:
        logging.getLogger(__name__).exception("Error inesperado en api_actualizar_orden_paquete (paquetes.py)")
        return JsonResponse({
            'status': 'error',
            'mensaje': f'Error al actualizar orden: {str(e)}'
        }, status=500)