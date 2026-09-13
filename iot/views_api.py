import json
from django.db import transaction
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from core.models import OrdenDeServicio
from iot.models import Kiosco, VerificacionKiosco
from iot.auth import require_kiosco_token
import logging

@csrf_exempt
@require_POST
@require_kiosco_token
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
            
        # La orden y la verificacion deben confirmarse juntas: un error de
        # persistencia no puede dejar la orden avanzada sin trazabilidad.
        with transaction.atomic():
            orden = OrdenDeServicio.objects.select_for_update().get(
                id=orden.id,
                empresa=kiosco.empresa,
            )
            orden.estado = 'EN_PROCESO'
            orden.save(update_fields=['estado'])
            verificacion = VerificacionKiosco.objects.select_for_update().filter(
                kiosco=kiosco,
                orden=orden,
            ).order_by('-id').first()
            datos_confirmados = {
                'checkin': True,
                'firma_capturada': bool(firma_b64),
            }
            if verificacion is None:
                VerificacionKiosco.objects.create(
                    kiosco=kiosco,
                    orden=orden,
                    estado=VerificacionKiosco.ESTADO_CONFIRMADO,
                    datos_confirmados=datos_confirmados,
                )
            else:
                verificacion.estado = VerificacionKiosco.ESTADO_CONFIRMADO
                verificacion.datos_confirmados = datos_confirmados
                verificacion.fecha_confirmacion = timezone.now()
                verificacion.save(update_fields=[
                    'estado', 'datos_confirmados', 'fecha_confirmacion',
                ])
        
        return JsonResponse({
            'status': 'success',
            'mensaje': 'Check-in completado exitosamente',
            'orden_id': orden.id
        })
        
    except Kiosco.DoesNotExist:
        return JsonResponse({'status': 'error', 'mensaje': 'Kiosco no existe o está inactivo'}, status=404)
    except Exception:
        logging.getLogger(__name__).exception("Error en api_kiosco_checkin")
        return JsonResponse({'status': 'error', 'mensaje': 'Error interno al procesar check-in'}, status=500)
