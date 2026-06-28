"""
PRIS SENTINEL V4: Servicio de Web Push Notifications
Envía notificaciones móviles nativas a dispositivos suscritos sin servicios externos.
"""

import json
import logging
from django.conf import settings
from django.core.cache import cache
from pywebpush import webpush, WebPushException

logger = logging.getLogger('push')


def _push_block_key(subscription):
    return f'push:circuit_breaker:{subscription.pk}'


def _retry_after_seconds(response):
    if not response:
        return 60
    header = None
    try:
        header = response.headers.get('Retry-After')
    except Exception:
        logging.getLogger(__name__).exception("Error inesperado en _retry_after_seconds (push_service.py)")
        header = None
    if not header:
        return 60
    try:
        return max(1, int(header))
    except (TypeError, ValueError):
        return 60


def _push_blocked(subscription):
    return bool(cache.get(_push_block_key(subscription)))


def _block_push(subscription, seconds):
    cache.set(_push_block_key(subscription), True, timeout=max(1, int(seconds)))


def enviar_notificacion_push(subscription, titulo, cuerpo, url='/', datos_extra=None):
    """
    Envía una notificación push a un dispositivo suscrito.
    
    Args:
        subscription: Instancia de PushSubscription
        titulo: Título de la notificación
        cuerpo: Texto del cuerpo
        url: URL a abrir al hacer click
        datos_extra: Dict con datos adicionales (incidenciaId, severidad, isla, etc.)
    
    Returns:
        bool: True si se envió exitosamente, False si falló
    """
    if not subscription.activa:
        logger.warning(f"Push subscription {subscription.id} está inactiva")
        return False

    if _push_blocked(subscription):
        logger.info(f"Push notification omitida por circuit breaker activo para suscripción {subscription.id}")
        return False
    
    # Obtener las llaves VAPID del settings
    vapid_private_key = getattr(settings, 'VAPID_PRIVATE_KEY', None)
    vapid_claims = getattr(settings, 'VAPID_CLAIMS', {})
    
    if not vapid_private_key:
        logger.error("VAPID_PRIVATE_KEY no configurada en settings")
        return False
    
    # Construir el payload de la notificación
    payload_data = {
        'title': titulo,
        'body': cuerpo,
        'icon': '/static/images/icons/icon-192x192.png',
        'badge': '/static/images/icons/icon-72x72.png',
        'url': url,
        'vibrate': [200, 100, 200],
        'tag': 'prislab-notification',
        'requireInteraction': True,
    }
    
    # Agregar datos extra si se proporcionan
    if datos_extra:
        payload_data.update(datos_extra)
    
    payload_json = json.dumps(payload_data)
    
    # Construir subscription_info para pywebpush
    subscription_info = {
        "endpoint": subscription.endpoint,
        "keys": {
            "p256dh": subscription.p256dh,
            "auth": subscription.auth
        }
    }
    
    try:
        # Enviar la notificación push
        webpush(
            subscription_info=subscription_info,
            data=payload_json,
            vapid_private_key=vapid_private_key,
            vapid_claims=vapid_claims
        )
        
        # Actualizar fecha de última notificación
        from django.utils import timezone
        subscription.fecha_ultima_notificacion = timezone.now()
        subscription.save(update_fields=['fecha_ultima_notificacion'])
        
        logger.info(f"Push notification enviada a {subscription.usuario.username} - {subscription.nombre_dispositivo}")
        return True
        
    except WebPushException as e:
        status_code = getattr(getattr(e, 'response', None), 'status_code', None)

        if status_code == 429:
            retry_after = _retry_after_seconds(e.response)
            _block_push(subscription, retry_after)
            logger.warning(f"Push rate-limited en suscripción {subscription.id}; bloqueo por {retry_after}s")
            return False
        
        # Si el endpoint expiró (410 Gone), desactivar la suscripción
        if status_code == 410:
            logger.warning(f"Endpoint expirado, desactivando suscripción {subscription.id}")
            subscription.activa = False
            subscription.save(update_fields=['activa'])
            return False

        logger.error(f"Error al enviar push notification: {e}")
        
        return False
    except Exception as e:
        logger.error(f"Error inesperado al enviar push: {e}", exc_info=True)
        return False


def notificar_error_sentinel(incidencia):
    """
    Envía notificación push al Director cuando Sentinel detecta un error.
    
    Args:
        incidencia: Instancia de IncidenciaSentinel
    """
    from core.models import Usuario, PushSubscription
    
    # Obtener administradores con suscripciones activas
    admins = Usuario.objects.filter(
        is_superuser=True,
        push_subscriptions__activa=True
    ).distinct()
    
    if not admins.exists():
        logger.info("No hay administradores suscritos a push notifications")
        return
    
    # Construir el mensaje
    isla = incidencia.namespace.upper() if incidencia.namespace else 'SISTEMA'
    severidad_emoji = {
        'CRITICA': '🔴',
        'ALTA': '🟠',
        'MEDIA': '🟡',
        'BAJA': '🟢'
    }.get(incidencia.severidad, '⚪')
    
    titulo = f"{severidad_emoji} Error en {isla}"
    
    # Resumen del error (primeras 100 chars del análisis IA o tipo de excepción)
    resumen = incidencia.analisis_ia[:100] if incidencia.analisis_ia else f"{incidencia.tipo_excepcion}"
    if len(incidencia.analisis_ia or '') > 100:
        resumen += '...'
    
    cuerpo = f"{resumen}. Toca para ver detalle."
    
    # URL para abrir el detalle de la incidencia
    url = f'/consultorio/sentinel/{incidencia.id}/'
    
    # Datos extra para la notificación
    datos_extra = {
        'incidenciaId': incidencia.id,
        'severidad': incidencia.severidad,
        'isla': isla,
        'actions': [
            {
                'action': 'open',
                'title': 'Ver Detalle',
            },
            {
                'action': 'close',
                'title': 'Cerrar',
            }
        ]
    }
    
    # Enviar a todos los administradores suscritos
    enviadas = 0
    for admin in admins:
        subscriptions = admin.push_subscriptions.filter(activa=True)
        
        for sub in subscriptions:
            # Verificar preferencias de notificación
            if sub.notificar_solo_criticos and incidencia.severidad not in ['CRITICA', 'ALTA']:
                continue
            
            if enviar_notificacion_push(sub, titulo, cuerpo, url, datos_extra):
                enviadas += 1
    
    logger.info(f"Notificación Sentinel enviada a {enviadas} dispositivos")


def generar_vapid_keys():
    """
    Genera un par de llaves VAPID (Voluntary Application Server Identification).
    Solo se debe ejecutar UNA VEZ durante el setup inicial.
    
    Returns:
        dict: {'private_key': str, 'public_key': str}
    """
    from py_vapid import Vapid01
    from cryptography.hazmat.primitives import serialization
    import base64
    
    vapid = Vapid01()
    vapid.generate_keys()
    
    # Obtener la llave privada en formato PEM
    private_key_pem = vapid.private_pem().decode('utf-8')
    
    # Obtener la llave publica en formato base64url (para el frontend)
    # La llave pública debe estar en formato raw (uncompressed) para Web Push
    public_key_ec = vapid.public_key
    public_key_bytes = public_key_ec.public_bytes(
        encoding=serialization.Encoding.X962,
        format=serialization.PublicFormat.UncompressedPoint
    )
    public_key_b64 = base64.urlsafe_b64encode(public_key_bytes).decode('utf-8').rstrip('=')
    
    return {
        'private_key': private_key_pem,
        'public_key': public_key_b64
    }


def obtener_vapid_public_key():
    """
    Retorna la llave pública VAPID para el frontend.
    
    Returns:
        str: Llave pública VAPID o None si no está configurada
    """
    return getattr(settings, 'VAPID_PUBLIC_KEY', None)