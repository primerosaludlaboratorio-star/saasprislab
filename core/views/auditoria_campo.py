"""
API para registrar auditoría de cambios en campos (REGLA 6).
"""
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
import json

from core.utils.estandares_industriales import auditar_cambio_campo
from core.models import DetalleOrden, OrdenDeServicio
from core.utils.empresa_request import empresa_efectiva_request
import logging


@login_required
@require_http_methods(["POST"])
def api_auditoria_campo(request):
    """
    API para registrar auditoría de cambios en campos.
    REGLA 6: Auditoría Nativa
    """
    try:
        data = json.loads(request.body)
        campo_id = data.get('campo_id')
        campo_nombre = data.get('campo_nombre')
        valor_anterior = data.get('valor_anterior')
        valor_nuevo = data.get('valor_nuevo')
        
        if not campo_id or not campo_nombre:
            return JsonResponse({
                'status': 'error',
                'mensaje': 'Faltan datos requeridos'
            }, status=400)
        
        # Intentar identificar el modelo desde el campo_id
        # Formato esperado: "resultado_123_0" -> DetalleOrden id=123
        modelo_instancia = None
        try:
            if campo_id.startswith('resultado_'):
                partes = campo_id.split('_')
                if len(partes) >= 2:
                    detalle_id = int(partes[1])
                    empresa = empresa_efectiva_request(request)
                    modelo_instancia = DetalleOrden.objects.get(id=detalle_id, orden__empresa=empresa)
        except (ValueError, IndexError, DetalleOrden.DoesNotExist):
            pass

        # Si no se pudo identificar, crear un log genérico
        if modelo_instancia:
            auditar_cambio_campo(
                campo_nombre=campo_nombre,
                valor_anterior=valor_anterior,
                valor_nuevo=valor_nuevo,
                modelo_instancia=modelo_instancia,
                request=request,
                modulo='LABORATORIO',
                accion='UPDATE'
            )
        else:
            # Registrar en TrazabilidadOperacion directamente
            from core.utils.trazabilidad import registrar_trazabilidad
            registrar_trazabilidad(
                tipo_operacion='CAMPO_MODIFICADO',
                modulo='LABORATORIO',
                referencia_id=None,
                referencia_tipo='Campo',
                accion='UPDATE',
                descripcion=f'Campo {campo_nombre} modificado: {valor_anterior} → {valor_nuevo}',
                usuario=request.user,
                empresa=getattr(request.user, 'empresa', None),
                datos_anteriores={campo_nombre: valor_anterior},
                datos_nuevos={campo_nombre: valor_nuevo},
                request=request,
            )
        
        return JsonResponse({
            'status': 'success',
            'mensaje': 'Auditoría registrada correctamente'
        })
        
    except json.JSONDecodeError:
        return JsonResponse({
            'status': 'error',
            'mensaje': 'Error al procesar JSON'
        }, status=400)
    except Exception as e:
        logging.getLogger(__name__).exception("Error inesperado en api_auditoria_campo (auditoria_campo.py)")
        return JsonResponse({
            'status': 'error',
            'mensaje': f'Error inesperado: {str(e)}'
        }, status=500)