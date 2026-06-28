import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from core.models import OrdenDeServicio
from iot.models import Kiosco, VerificacionKiosco
from core.decorators import require_api_token
import logging

@csrf_exempt
@require_POST
@require_api_token('PRISLAB_KIOSCO_API_TOKEN')
def api_kiosco_checkin(request, kiosco_id):
    """
    API para que el kiosco envíe los datos de check-in del paciente 
    (QR validado, firma del consentimiento capturada).
    """
    try:
        kiosco = Kiosco.objects.get(id=kiosco_id, activo=True)
        data = json.loads(request.body)
        
        orden_id = data.get('orden_id')
        firma_b64 = data.get('firma_b64')
        
        if not orden_id:
            return JsonResponse({'status': 'error', 'mensaje': 'Orden ID es requerido'}, status=400)
            
        orden = OrdenDeServicio.objects.filter(id=orden_id, empresa=kiosco.empresa).first()
        if not orden:
            return JsonResponse({'status': 'error', 'mensaje': 'Orden no encontrada o no pertenece a la empresa'}, status=404)
            
        # Actualizar la orden como verificada / autorizada por paciente
        # Suponiendo que el modelo OrdenDeServicio tiene un estado o un flag
        orden.estado = 'EN_PROCESO' # o 'VERIFICADA'
        orden.save(update_fields=['estado'])
        
        # Guardar registro en IoT
        VerificacionKiosco.objects.create(
            kiosco=kiosco,
            orden_servicio_id=orden.id,
            estado='EXITOSA',
            detalles='Check-in completado por Kiosco'
        )
        
        return JsonResponse({
            'status': 'success',
            'mensaje': 'Check-in completado exitosamente',
            'orden_id': orden.id
        })
        
    except Kiosco.DoesNotExist:
        return JsonResponse({'status': 'error', 'mensaje': 'Kiosco no existe o está inactivo'}, status=404)
    except Exception as e:
        logging.getLogger(__name__).exception("Error en api_kiosco_checkin")
        return JsonResponse({'status': 'error', 'mensaje': str(e)}, status=500)
