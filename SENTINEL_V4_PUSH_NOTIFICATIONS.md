# PRIS SENTINEL V4: Web Push Notifications 📱

## Resumen Ejecutivo

PRISLAB V5 ahora cuenta con **notificaciones push nativas** que funcionan como una aplicación móvil real, sin necesidad de WhatsApp, Telegram o servicios externos pagos. El Director Jonathan recibirá alertas instantáneas en su dispositivo cada vez que Sentinel detecte un error crítico.

---

## ✅ Características Implementadas

### 1. PWA (Progressive Web App) Completa
- **Instalable en Móvil**: La aplicación se puede "Agregar a Pantalla de Inicio" y funciona como app nativa
- **Icono Personalizado**: Logo de PRISLAB en la pantalla del dispositivo
- **Modo Standalone**: Se abre sin la barra del navegador (experiencia de app nativa)
- **Funcionamiento Offline**: Cachea recursos estáticos para acceso básico sin conexión

### 2. Notificaciones Push Nativas
- **Sin Servicios Externos**: Usa Web Push API (estándar W3C) directamente desde el navegador
- **Cifrado Seguro**: Autenticación con llaves VAPID (Voluntary Application Server Identification)
- **Compatible con**:
  - ✅ Android (Chrome, Firefox, Edge)
  - ✅ Windows/Mac Desktop (Chrome, Firefox, Edge)
  - ⚠️ iOS/iPad (soporte limitado en Safari 16.4+)

### 3. Integración con PRIS Sentinel
- **Disparo Automático**: Cuando Sentinel captura un error 500, envía notificación push inmediata
- **Información Contextual**:
  - 🚨 Isla afectada (Consultorio, Farmacia, Laboratorio)
  - 🔴 Severidad del error (CRITICA, ALTA, MEDIA, BAJA)
  - 📝 Resumen del análisis de Gemini AI
  - 🔗 Link directo al detalle para abrir con un toque
- **Acciones Rápidas**: Botones "Ver Detalle" y "Cerrar" directamente en la notificación

### 4. Panel de Control en Dashboard del Director
- **Widget Visual**: Card destacado con diseño moderno (gradiente morado)
- **Botones de Gestión**:
  - 🔔 **Activar Notificaciones**: Suscribe el dispositivo actual con un clic
  - 🔕 **Desactivar**: Cancela las notificaciones en el dispositivo
  - 📤 **Prueba**: Envía una notificación de test para verificar funcionamiento
- **Estado en Tiempo Real**: Badge que muestra si el dispositivo está suscrito o no

---

## 🚀 Cómo Usar (Instrucciones para Jonathan)

### Paso 1: Instalar la PWA en tu Móvil (Recomendado)

#### Android (Chrome):
1. Abre `https://prislab-v5-oswjakz55a-uc.a.run.app` en Chrome
2. Aparecerá un banner "Agregar PRISLAB a la pantalla de inicio" → Toca **Agregar**
3. O ve al menú ⋮ → "Agregar a pantalla de inicio"
4. Ahora PRISLAB aparece como app en tu cajón de aplicaciones 🎉

#### iOS/iPad (Safari 16.4+):
1. Abre la URL en Safari
2. Toca el botón "Compartir" 📤
3. Selecciona "Agregar a pantalla de inicio"
4. Toca "Agregar"

### Paso 2: Activar Notificaciones

1. **Inicia sesión** con tu usuario de Director (admin)
2. Ve al **Dashboard de Director**
3. En la parte superior, verás el widget morado de "Notificaciones Móviles Sentinel"
4. Toca el botón **"Activar Notificaciones"**
5. El navegador te pedirá permiso → Toca **"Permitir"**
6. ✅ **Recibirás una notificación de prueba** confirmando que todo funciona

### Paso 3: Configurar Preferencias (Opcional)

Las preferencias se configuran automáticamente para notificar:
- ✅ Todos los errores 500 (CRITICA, ALTA, MEDIA, BAJA)
- ✅ En todas las islas (Consultorio, Farmacia, Laboratorio, Sistema)

Si deseas **solo errores críticos**:
- Ve a la base de datos → Tabla `core_pushsubscription`
- Activa la casilla `notificar_solo_criticos` para tu suscripción

### Paso 4: Probar el Sistema

#### Opción A: Botón de Prueba
1. En el widget de notificaciones, toca **"Prueba"**
2. Deberías recibir una notificación de prueba en 2-3 segundos

#### Opción B: Provocar un Error Real
1. Pide al equipo técnico que inserte temporalmente un error en el código
2. Accede a la página con el error
3. Sentinel lo capturará y **recibirás la notificación automáticamente**

---

## 🔧 Arquitectura Técnica

### Backend (Django)

#### Nuevos Modelos
- **`PushSubscription`** (`core/models.py`):
  - Almacena endpoint, claves p256dh/auth de cada dispositivo
  - Vinculado a usuario (relación `ForeignKey`)
  - Campos: `activa`, `notificar_errores_500`, `notificar_solo_criticos`

#### Servicios
- **`core/push_service.py`**:
  - `enviar_notificacion_push()`: Envía notificación a un dispositivo
  - `notificar_error_sentinel()`: Dispara notificaciones cuando Sentinel detecta error
  - `generar_vapid_keys()`: Genera llaves de autenticación (ejecutar una sola vez)

#### Vistas API (`core/views/push.py`)
- `GET /api/push/vapid/`: Retorna llave pública VAPID para el frontend
- `POST /api/push/suscribir/`: Registra nueva suscripción de dispositivo
- `POST /api/push/desuscribir/`: Desactiva suscripción
- `GET /api/push/estado/`: Estado de suscripciones del usuario
- `POST /api/push/test/`: Envía notificación de prueba (solo admins)

#### Integración con Sentinel
- **`core/middleware/sentinel.py`** (línea ~303):
  - Después de crear incidencia y enriquecer con IA, llama a `notificar_error_sentinel()`
  - Ejecuta en thread asíncrono para no bloquear respuesta HTTP

### Frontend (JavaScript)

#### Service Worker (`static/sw.js`)
- **Listener `push`**: Recibe notificaciones del servidor
- **Listener `notificationclick`**: Abre la URL correspondiente al tocar notificación
- **Caching**: Cache First para estáticos, Network First para páginas dinámicas

#### Módulo Push (`static/js/push_notifications.js`)
- **API Global**: `window.PushNotifications`
  - `suscribir()`: Solicita permisos y registra dispositivo
  - `desuscribir()`: Cancela suscripción
  - `verificarEstado()`: Verifica si el dispositivo está suscrito
  - `enviarPrueba()`: Envía notificación de test
  - `detectarDispositivo()`: Detecta nombre del dispositivo automáticamente

#### UI en Dashboard (`core/templates/core/dashboard_director.html`)
- Widget con gradiente morado en la parte superior
- Botones interactivos con estados dinámicos (suscrito/no suscrito)
- Integración con SweetAlert2 para feedback visual

### Infraestructura

#### Llaves VAPID (Google Secret Manager)
- **`vapid-private-key`**: Llave privada (CONFIDENCIAL) para firmar notificaciones
- **`vapid-public-key`**: Llave pública (pública) para suscripciones del frontend

Agregadas a `cloudbuild.yaml` como secrets en Cloud Run.

#### Variables de Entorno (`config/settings.py`)
```python
VAPID_PRIVATE_KEY = os.environ.get('VAPID_PRIVATE_KEY', '')
VAPID_PUBLIC_KEY = os.environ.get('VAPID_PUBLIC_KEY', '')
VAPID_CLAIMS = {'sub': 'mailto:admin@prislab.com'}
```

#### Dependencias (`requirements.txt`)
```
pywebpush==1.14.0
```

---

## 📊 Flujo de Notificación Completo

```
┌─────────────────────────────────────────────────────────────┐
│ 1. ERROR OCURRE EN PRODUCCIÓN (ej: ZeroDivisionError)      │
└───────────────────────┬─────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────┐
│ 2. SentinelTelemetryMiddleware.process_exception()         │
│    - Captura traceback                                       │
│    - Crea IncidenciaSentinel en DB                          │
│    - Llama a Gemini AI para análisis (async)               │
└───────────────────────┬─────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────┐
│ 3. notificar_error_sentinel(incidencia)                     │
│    - Busca PushSubscription.filter(activa=True)            │
│    - Para cada dispositivo suscrito:                        │
│      • Construye payload JSON con título, cuerpo, URL       │
│      • Envía con pywebpush.webpush()                       │
└───────────────────────┬─────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────┐
│ 4. NAVEGADOR DEL DIRECTOR RECIBE LA NOTIFICACIÓN            │
│    - Service Worker listener 'push' se activa               │
│    - Muestra notificación con showNotification()            │
│    - Aparece banner/vibración en dispositivo                │
└───────────────────────┬─────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────┐
│ 5. USUARIO TOCA LA NOTIFICACIÓN                             │
│    - Service Worker listener 'notificationclick' se activa  │
│    - Abre o enfoca ventana de PRISLAB                       │
│    - Navega a la URL del detalle de la incidencia          │
└─────────────────────────────────────────────────────────────┘
```

---

## 🛡️ Seguridad y Privacidad

### Cifrado End-to-End
- Las notificaciones están cifradas usando las claves p256dh/auth del dispositivo
- Solo el dispositivo suscrito puede descifrar el contenido
- La llave privada VAPID nunca se expone al cliente

### Autenticación
- Solo usuarios autenticados pueden suscribirse
- Las suscripciones están vinculadas a cuentas de usuario
- Las notificaciones solo se envían a administradores (is_superuser=True)

### Permisos del Navegador
- El usuario debe dar permiso explícito para recibir notificaciones
- Puede revocar el permiso en cualquier momento desde la configuración del navegador

---

## 🐛 Troubleshooting

### "Tu navegador no soporta notificaciones push"
**Causa**: Navegador antiguo o iOS < 16.4  
**Solución**: Actualiza el navegador o usa Chrome/Firefox en Android

### "Permiso de notificaciones denegado"
**Causa**: El usuario rechazó el permiso  
**Solución**: 
1. Ve a la configuración del navegador/sitio
2. Encuentra PRISLAB en "Permisos"
3. Cambia "Notificaciones" a "Permitir"
4. Recarga la página y vuelve a suscribirte

### "Error al registrar suscripción"
**Causa**: Llaves VAPID no configuradas o inválidas  
**Solución**:
1. Verifica que los secrets existan en Secret Manager:
   ```bash
   gcloud secrets list --project=prislab-v5-ai | grep vapid
   ```
2. Si faltan, ejecuta `python generar_vapid_keys.py` y vuelve a crearlos

### "No recibo notificaciones"
**Causa**: Service Worker no registrado o suscripción inactiva  
**Verificación**:
1. Abre DevTools → Application → Service Workers
2. Verifica que `/static/sw.js` esté activo
3. Verifica en DB que `core_pushsubscription.activa = True`
4. Prueba con el botón "Prueba" primero

### "La notificación no abre la URL correcta"
**Causa**: Error en el campo `url` del payload  
**Solución**: Verifica `core/push_service.py` línea ~93, debe construir URL correcta

---

## 📈 Próximas Mejoras (Roadmap)

### v4.1: Preferencias Avanzadas
- [ ] UI para configurar preferencias de notificación por isla
- [ ] Horarios de "No Molestar" (ej: no notificar de 10pm a 7am)
- [ ] Sonidos personalizados por severidad

### v4.2: Notificaciones Ricas
- [ ] Imágenes en notificaciones (screenshots del error)
- [ ] Badges numéricos en el icono de la app
- [ ] Acciones inline (ej: "Marcar como Solucionado" sin abrir app)

### v4.3: Multi-Destinatario
- [ ] Enviar notificaciones a múltiples roles (ej: Gerente + Director)
- [ ] Grupos de notificación por isla
- [ ] Escalado automático si no se resuelve en X minutos

---

## 📞 Contacto y Soporte

**Desarrollador**: Cursor AI Agent  
**Proyecto**: PRISLAB V5 - PRIS SENTINEL V4  
**Fecha**: Febrero 2026  
**Versión**: 4.0.0

Para reportar bugs o solicitar features, contacta al equipo técnico de PRISLAB.

---

## 🎉 ¡Felicidades!

PRISLAB ahora tiene notificaciones push de nivel empresarial, sin costos adicionales de servicios externos. El Director Jonathan puede monitorear el sistema desde cualquier lugar, en tiempo real, como si fuera una app nativa.

**¡Bienvenido al futuro de la monitorización clínica!** 🚀📱
