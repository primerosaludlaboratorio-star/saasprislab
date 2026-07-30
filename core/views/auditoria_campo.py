"""
API para registrar auditoría de cambios en campos (REGLA 6).
"""
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
import json
import re

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
        campo_id = str(data.get('campo_id') or '').strip()
        valor_nuevo = data.get('valor_nuevo')
        
        # Esta API solo acompaña la edición de resultados de una orden real.
        # No se aceptan modelo/objeto/valor anterior arbitrarios del cliente.
        match = re.fullmatch(r'resultado_(\d+)(?:_\d+)?', campo_id)
        if not match or valor_nuevo is None:
            return JsonResponse({
                'status': 'error',
                'mensaje': 'Campo de resultado inválido o valor nuevo ausente'
            }, status=400)

        campo_nombre = 'resultado'
        empresa = empresa_efectiva_request(request)
        if not empresa:
            return JsonResponse({'status': 'error', 'mensaje': 'Usuario sin empresa asignada'}, status=403)
        
        # Intentar identificar el modelo desde el campo_id
        # Formato esperado: "resultado_123_0" -> DetalleOrden id=123
        modelo_instancia = None
        try:
            if campo_id.startswith('resultado_'):
                partes = campo_id.split('_')
                if len(partes) >= 2:
                    detalle_id = int(partes[1])
                    modelo_instancia = DetalleOrden.objects.get(id=detalle_id, orden__empresa=empresa)
        except (ValueError, IndexError, DetalleOrden.DoesNotExist):
            modelo_instancia = None

        if not modelo_instancia:
            return JsonResponse({'status': 'error', 'mensaje': 'Resultado no encontrado'}, status=404)

        valor_anterior = getattr(modelo_instancia, 'resultado', '')
        if str(valor_anterior) == str(valor_nuevo):
            return JsonResponse({'status': 'success', 'mensaje': 'Sin cambios'})

        auditar_cambio_campo(
            campo_nombre=campo_nombre,
            valor_anterior=valor_anterior,
            valor_nuevo=str(valor_nuevo),
            modelo_instancia=modelo_instancia,
            request=request,
            modulo='LABORATORIO',
            accion='UPDATE'
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
            'mensaje': 'No fue posible procesar la auditoría.'
        }, status=500)
