"""
PRIS SENTINEL V4: Vistas para Web Push Notifications
"""

import json
import logging
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from core.models import PushSubscription
from core.push_service import obtener_vapid_public_key, enviar_notificacion_push

logger = logging.getLogger('push')


def _json_no_store(payload, status=200):
    response = JsonResponse(payload, status=status)
    response['Cache-Control'] = 'no-store, private, must-revalidate'
    response['Pragma'] = 'no-cache'
    response['Expires'] = '0'
    return response


@login_required
@require_http_methods(["GET"])
def obtener_vapid_key(request):
    """
    API: Retorna la llave pública VAPID para que el frontend pueda suscribirse.
    """
    public_key = obtener_vapid_public_key()
    
    if not public_key:
        return _json_no_store({
            'status': 'error',
            'message': 'Llaves VAPID no configuradas en el servidor'
        }, status=500)
    
    return _json_no_store({
        'status': 'success',
        'publicKey': public_key
    })


@login_required
@require_http_methods(["POST"])
def suscribir_push(request):
    """
    API: Registra una nueva suscripción de push notification para el usuario actual.
    
    Payload esperado (JSON):
    {
        "endpoint": "https://...",
        "keys": {
            "p256dh": "...",
            "auth": "..."
        },
        "nombreDispositivo": "iPhone de Jonathan" (opcional)
    }
    """
    try:
        data = json.loads(request.body)
        
        endpoint = data.get('endpoint')
        keys = data.get('keys', {})
        p256dh = keys.get('p256dh')
        auth = keys.get('auth')
        nombre_dispositivo = data.get('nombreDispositivo', '')
        
        if not all([endpoint, p256dh, auth]):
            return _json_no_store({
                'status': 'error',
                'message': 'Faltan datos de suscripción (endpoint, keys.p256dh, keys.auth)'
            }, status=400)
        
        # Obtener o crear la suscripción
        subscription, created = PushSubscription.objects.update_or_create(
            endpoint=endpoint,
            defaults={
                'usuario': request.user,
                'p256dh': p256dh,
                'auth': auth,
                'user_agent': request.META.get('HTTP_USER_AGENT', '')[:500],
                'nombre_dispositivo': nombre_dispositivo[:100],
                'activa': True,
            }
        )
        
        # Enviar notificación de prueba
        enviar_notificacion_push(
            subscription,
            titulo='✅ PRISLAB - Suscripción Exitosa',
            cuerpo='Las notificaciones push están activas. Recibirás alertas de errores críticos.',
            url='/',
        )
        
        action = 'creada' if created else 'actualizada'
        logger.info(f"Push subscription {action} para {request.user.username}")
        
        return _json_no_store({
            'status': 'success',
            'message': f'Suscripción {action} exitosamente',
            'subscriptionId': subscription.id
        })
        
    except json.JSONDecodeError:
        return _json_no_store({
            'status': 'error',
            'message': 'JSON inválido'
        }, status=400)
    except Exception as e:
        logger.error(f"Error al suscribir push: {e}", exc_info=True)
        return _json_no_store({
            'status': 'error',
            'message': f'Error del servidor: {type(e).__name__}'
        }, status=500)


@login_required
@require_http_methods(["POST"])
def desuscribir_push(request):
    """
    API: Desactiva la suscripción de push notification del dispositivo actual.
    
    Payload esperado (JSON):
    {
        "endpoint": "https://..."
    }
    """
    try:
        data = json.loads(request.body)
        endpoint = data.get('endpoint')
        
        if not endpoint:
            return _json_no_store({
                'status': 'error',
                'message': 'Falta el endpoint de la suscripción'
            }, status=400)
        
        # Buscar y desactivar la suscripción
        try:
            subscription = PushSubscription.objects.get(
                endpoint=endpoint,
                usuario=request.user
            )
            subscription.activa = False
            subscription.save(update_fields=['activa'])
            
            logger.info(f"Push subscription desactivada para {request.user.username}")
            
            return _json_no_store({
                'status': 'success',
                'message': 'Suscripción desactivada exitosamente'
            })
        except PushSubscription.DoesNotExist:
            return _json_no_store({
                'status': 'error',
                'message': 'Suscripción no encontrada'
            }, status=404)
        
    except json.JSONDecodeError:
        return _json_no_store({
            'status': 'error',
            'message': 'JSON inválido'
        }, status=400)
    except Exception as e:
        logger.error(f"Error al desuscribir push: {e}", exc_info=True)
        return _json_no_store({
            'status': 'error',
            'message': f'Error del servidor: {type(e).__name__}'
        }, status=500)


@login_required
@require_http_methods(["GET"])
def estado_suscripciones(request):
    """
    API: Retorna el estado de las suscripciones del usuario actual.
    """
    subscriptions = PushSubscription.objects.filter(
        usuario=request.user,
        activa=True
    ).values('id', 'nombre_dispositivo', 'fecha_creacion', 'fecha_ultima_notificacion')
    
    return _json_no_store({
        'status': 'success',
        'subscriptions': list(subscriptions),
        'total': subscriptions.count()
    })


@login_required
@require_http_methods(["POST"])
def test_notificacion(request):
    """
    API: Envía una notificación de prueba a todos los dispositivos del usuario.
    Solo para administradores.
    """
    if not request.user.is_superuser:
        return _json_no_store({
            'status': 'error',
            'message': 'Requiere permisos de administrador'
        }, status=403)
    
    subscriptions = PushSubscription.objects.filter(
        usuario=request.user,
        activa=True
    )
    
    if not subscriptions.exists():
        return _json_no_store({
            'status': 'error',
            'message': 'No hay dispositivos suscritos'
        }, status=404)
    
    enviadas = 0
    for sub in subscriptions:
        if enviar_notificacion_push(
            sub,
            titulo='🧪 PRISLAB - Prueba de Notificación',
            cuerpo='Esta es una notificación de prueba del sistema Sentinel V4.',
            url='/consultorio/sentinel/',
            datos_extra={'test': True}
        ):
            enviadas += 1
    
    return _json_no_store({
        'status': 'success',
        'message': f'Notificación enviada a {enviadas} de {subscriptions.count()} dispositivos'
    })
