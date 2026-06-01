/**
 * PRIS SENTINEL V4: Web Push Notifications
 * Maneja la suscripción y gestión de notificaciones push nativas
 */

// Utilidad para obtener el CSRF token
function getCsrfToken() {
    const meta = document.querySelector('meta[name="csrf-token"]');
    if (meta) return meta.content;
    
    const cookie = document.cookie.match(/csrftoken=([^;]+)/);
    if (cookie) return cookie[1];
    
    return '';
}

// Convierte una cadena base64 a Uint8Array (para VAPID key)
function urlBase64ToUint8Array(base64String) {
    const padding = '='.repeat((4 - base64String.length % 4) % 4);
    const base64 = (base64String + padding)
        .replace(/\-/g, '+')
        .replace(/_/g, '/');
    
    const rawData = window.atob(base64);
    const outputArray = new Uint8Array(rawData.length);
    
    for (let i = 0; i < rawData.length; ++i) {
        outputArray[i] = rawData.charCodeAt(i);
    }
    return outputArray;
}

// Verifica si el navegador soporta notificaciones push
function isPushSupported() {
    return 'serviceWorker' in navigator && 
           'PushManager' in window && 
           'Notification' in window;
}

// Solicita permiso para mostrar notificaciones
async function requestNotificationPermission() {
    if (!isPushSupported()) {
        throw new Error('Tu navegador no soporta notificaciones push');
    }
    
    const permission = await Notification.requestPermission();
    
    if (permission !== 'granted') {
        throw new Error('Permiso de notificaciones denegado');
    }
    
    return permission;
}

// Obtiene la llave pública VAPID del servidor
async function getVapidPublicKey() {
    const response = await fetch('/api/push/vapid/', {
        credentials: 'same-origin'
    });
    
    if (!response.ok) {
        throw new Error('No se pudo obtener la llave VAPID');
    }
    
    const data = await response.json();
    return data.publicKey;
}

// Suscribe el dispositivo actual a notificaciones push
async function suscribirPush(nombreDispositivo = '') {
    try {
        // 1. Verificar soporte
        if (!isPushSupported()) {
            return {
                success: false,
                error: 'Tu navegador no soporta notificaciones push'
            };
        }
        
        // 2. Solicitar permiso
        await requestNotificationPermission();
        
        // 3. Registrar service worker si aún no está
        let registration;
        try {
            registration = await navigator.serviceWorker.ready;
        } catch (e) {
            registration = await navigator.serviceWorker.register('/static/sw.js', {
                scope: '/'
            });
            await navigator.serviceWorker.ready;
        }
        
        // 4. Obtener llave pública VAPID
        const vapidPublicKey = await getVapidPublicKey();
        const convertedVapidKey = urlBase64ToUint8Array(vapidPublicKey);
        
        // 5. Suscribirse al push manager
        const subscription = await registration.pushManager.subscribe({
            userVisibleOnly: true,
            applicationServerKey: convertedVapidKey
        });
        
        // 6. Enviar suscripción al servidor
        const response = await fetch('/api/push/suscribir/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCsrfToken()
            },
            credentials: 'same-origin',
            body: JSON.stringify({
                endpoint: subscription.endpoint,
                keys: {
                    p256dh: btoa(String.fromCharCode.apply(null, new Uint8Array(subscription.getKey('p256dh')))),
                    auth: btoa(String.fromCharCode.apply(null, new Uint8Array(subscription.getKey('auth'))))
                },
                nombreDispositivo: nombreDispositivo
            })
        });
        
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.message || 'Error al registrar suscripción');
        }
        
        const data = await response.json();
        
        return {
            success: true,
            message: data.message,
            subscription: subscription
        };
        
    } catch (error) {
        console.error('Error al suscribir push:', error);
        return {
            success: false,
            error: error.message
        };
    }
}

// Desuscribe el dispositivo actual de notificaciones push
async function desuscribirPush() {
    try {
        const registration = await navigator.serviceWorker.ready;
        const subscription = await registration.pushManager.getSubscription();
        
        if (!subscription) {
            return {
                success: false,
                error: 'No hay suscripción activa'
            };
        }
        
        // Desuscribirse del push manager
        await subscription.unsubscribe();
        
        // Notificar al servidor
        const response = await fetch('/api/push/desuscribir/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCsrfToken()
            },
            credentials: 'same-origin',
            body: JSON.stringify({
                endpoint: subscription.endpoint
            })
        });
        
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.message || 'Error al desuscribir');
        }
        
        return {
            success: true,
            message: 'Desuscripción exitosa'
        };
        
    } catch (error) {
        console.error('Error al desuscribir push:', error);
        return {
            success: false,
            error: error.message
        };
    }
}

// Verifica el estado actual de la suscripción
async function verificarEstadoSuscripcion() {
    try {
        const registration = await navigator.serviceWorker.ready;
        const subscription = await registration.pushManager.getSubscription();
        
        return {
            suscrito: !!subscription,
            subscription: subscription,
            permisoNotificaciones: Notification.permission
        };
    } catch (error) {
        console.error('Error al verificar estado:', error);
        return {
            suscrito: false,
            subscription: null,
            permisoNotificaciones: Notification.permission,
            error: error.message
        };
    }
}

// Envía una notificación de prueba
async function enviarNotificacionPrueba() {
    try {
        const response = await fetch('/api/push/test/', {
            method: 'POST',
            headers: {
                'X-CSRFToken': getCsrfToken()
            },
            credentials: 'same-origin'
        });
        
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.message || 'Error al enviar notificación de prueba');
        }
        
        const data = await response.json();
        return {
            success: true,
            message: data.message
        };
        
    } catch (error) {
        console.error('Error al enviar notificación de prueba:', error);
        return {
            success: false,
            error: error.message
        };
    }
}

// Detecta el nombre del dispositivo automáticamente
function detectarNombreDispositivo() {
    const ua = navigator.userAgent;
    
    if (/iPhone/.test(ua)) return 'iPhone';
    if (/iPad/.test(ua)) return 'iPad';
    if (/Android/.test(ua)) {
        if (/Mobile/.test(ua)) return 'Android Phone';
        return 'Android Tablet';
    }
    if (/Macintosh/.test(ua)) return 'Mac';
    if (/Windows/.test(ua)) return 'Windows PC';
    if (/Linux/.test(ua)) return 'Linux';
    
    if (/Chrome/.test(ua)) return 'Chrome Desktop';
    if (/Firefox/.test(ua)) return 'Firefox Desktop';
    if (/Safari/.test(ua)) return 'Safari Desktop';
    
    return 'Navegador';
}

// Exportar funciones globalmente
window.PushNotifications = {
    suscribir: suscribirPush,
    desuscribir: desuscribirPush,
    verificarEstado: verificarEstadoSuscripcion,
    enviarPrueba: enviarNotificacionPrueba,
    detectarDispositivo: detectarNombreDispositivo,
    isSupported: isPushSupported
};
