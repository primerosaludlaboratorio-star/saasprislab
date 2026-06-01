"""
API para Auditoría Nativa de Campos.
Registra cambios en tiempo real desde el frontend.
"""
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
import json

from core.utils.auditoria_nativa import registrar_cambio_campo


@login_required
@require_http_methods(["POST"])
def api_auditar_campo(request):
    """
    API para registrar cambios en campos críticos desde el frontend.
    
    Payload esperado:
    {
        "modelo": "DetalleOrden",
        "objeto_id": 123,
        "campo_nombre": "resultado",
        "valor_anterior": "100",
        "valor_nuevo": "110",
        "modulo": "LABORATORIO",
        "referencia_id": 456,
        "referencia_tipo": "OrdenDeServicio"
    }
    """
    try:
        data = json.loads(request.body)
        
        modelo = data.get('modelo', '')
        objeto_id = data.get('objeto_id')
        campo_nombre = data.get('campo_nombre', '')
        valor_anterior = data.get('valor_anterior', '')
        valor_nuevo = data.get('valor_nuevo', '')
        modulo = data.get('modulo', 'GENERAL')
        referencia_id = data.get('referencia_id')
        referencia_tipo = data.get('referencia_tipo')
        
        # Validaciones básicas
        if not modelo or not objeto_id or not campo_nombre:
            return JsonResponse({
                'status': 'error',
                'mensaje': 'Faltan campos requeridos'
            }, status=400)
        
        # Registrar cambio
        log = registrar_cambio_campo(
            usuario=request.user,
            modelo=modelo,
            objeto_id=objeto_id,
            campo_nombre=campo_nombre,
            valor_anterior=valor_anterior,
            valor_nuevo=valor_nuevo,
            modulo=modulo,
            empresa=getattr(request.user, 'empresa', None),
            referencia_id=referencia_id,
            referencia_tipo=referencia_tipo,
            request=request
        )
        
        if log:
            return JsonResponse({
                'status': 'success',
                'mensaje': 'Cambio registrado en auditoría',
                'log_id': log.id
            })
        else:
            return JsonResponse({
                'status': 'error',
                'mensaje': 'No se pudo registrar el cambio'
            }, status=500)
            
    except json.JSONDecodeError:
        return JsonResponse({
            'status': 'error',
            'mensaje': 'Error al procesar JSON'
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'mensaje': f'Error inesperado: {str(e)}'
        }, status=500)
