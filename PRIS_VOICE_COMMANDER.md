# PRIS VOICE COMMANDER - Sistema de Control por Voz
## Arquitectura de Voz de Nivel Militar con IA Contextual

---

## 🎙️ VISIÓN GENERAL

PRIS VOICE COMMANDER convierte la PWA de PRISLAB en un **dispositivo Push-to-Talk inteligente** con:

- 🎤 **Reconocimiento de voz local** (Web Speech API)
- 🧠 **Procesamiento contextual** con Gemini AI
- 🔒 **RBAC estricto** por roles (STAFF vs DIRECTOR)
- 🛡️ **Autenticación biométrica** para comandos críticos
- 📡 **Walkie-Talkie integrado** (comunicación entre usuarios)
- 📊 **Auditoría total** de cada comando

---

## 📋 COMPONENTES IMPLEMENTADOS

### 🎯 BLOQUE 1: INFRAESTRUCTURA DE VOZ

#### 1.1 Botón PTT Flotante (`pris_voice_commander.js`)
```javascript
// Características:
- Botón omnipresente en móvil/desktop
- Haptic feedback (vibración al presionar)
- Web Speech API para transcripción local
- Indicadores visuales (escuchando/procesando)
- Press & Hold en móvil, Click en desktop
```

**Ubicación**: Flotante en esquina inferior derecha
**Estados Visuales**:
- 🟣 **Idle**: Gradiente morado (listo para comando)
- 🔴 **Listening**: Animación pulse roja (escuchando)
- 🟡 **Processing**: Spinner amarillo (procesando con IA)

#### 1.2 Django Channels + WebSockets (`consumers.py`)
```python
# Consumers implementados:
1. VoiceCommandConsumer → Comandos de voz en tiempo real
2. WalkieTalkieConsumer → Audio efímero entre usuarios (intercom)
```

**Configuración**:
- Backend: Redis (channels-redis)
- Fallback: InMemoryChannelLayer (desarrollo)
- URLs WebSocket:
  - `ws://host/ws/voice/commands/` → Comandos
  - `ws://host/ws/voice/walkie/<room>/` → Walkie-Talkie

---

### 🧠 BLOQUE 2: INTELIGENCIA CONTEXTUAL

#### 2.1 Inyección de Contexto Visual (`voice_service.py`)
El sistema NO solo envía audio. Envía:
```json
{
    "transcription": "súrtela",
    "url": "/farmacia/ventas/",
    "context": "Receta #554 pendiente, Paciente: Juan Pérez"
}
```

**Prompt a Gemini** (con contexto inyectado):
```python
"""
Eres PRIS Voice Commander, asistente de voz de un sistema médico.

CONTEXTO DEL USUARIO:
- Rol: FARMACÉUTICO (Nancy)
- Ubicación en el sistema: /farmacia/ventas/
- Pantalla actual: Receta #554 pendiente

COMANDO DEL USUARIO:
"súrtela"

TAREA:
Entender que "súrtela" = surtir la receta #554 visible en pantalla.
"""
```

#### 2.2 Procesamiento con Gemini
```python
# core/services/voice_service.py

procesar_comando_voz(transcripcion, usuario, url_actual, datos_pantalla)
# Retorna:
{
    'intencion': 'surtir_receta',
    'parametros': {'folio': '554'},
    'respuesta': 'Cargando receta #554 en el carrito...',
    'accion': {...},
    'bloqueado': False,
    'requiere_auth': False,
    'tiempo_procesamiento_ms': 850
}
```

#### 2.3 Fallback Offline
Si Gemini no está disponible, análisis basado en palabras clave:
```python
# Palabras clave → Intenciones
"cerrar caja" → cerrar_caja
"nuevo paciente" → nuevo_paciente
"surtir receta 554" → surtir_receta + {'folio': '554'}
```

---

### 🛡️ BLOQUE 3: JERARQUÍA DE MANDO (RBAC)

#### 3.1 Permisos por Rol
```python
# STAFF (Nancy, Brizia, etc.)
PERMITIDOS = [
    'buscar_paciente',
    'ver_stock',
    'consultar_precio',
    'enviar_mensaje',
    'ver_agenda',
    'registrar_venta',
    'surtir_receta',
    'cerrar_caja',
    'nuevo_paciente',
]

BLOQUEADOS = [
    'eliminar',
    'modificar_configuracion',
    'ver_logs',
    'reiniciar_sistema',
    'borrar_datos',
]

# DIRECTOR (Jonathan)
PERMITIDOS = '*'  # Todos los comandos
CRITICOS_REQUIEREN_AUTH = [
    'eliminar',
    'reiniciar_sistema',
    'borrar_datos',
    'modificar_permisos',
    'acceder_logs_sentinel',
]
```

**Verificación**:
```python
permiso = verificar_permiso_comando(usuario, 'eliminar')
# Si STAFF:
#   {'permitido': False, 'motivo': 'Comando no autorizado para nivel STAFF'}
# Si DIRECTOR:
#   {'permitido': True, 'requiere_auth': True, 'motivo': 'Comando crítico...'}
```

#### 3.2 Respuestas Inteligentes de Bloqueo
```javascript
// Usuario STAFF intenta comando bloqueado:
"⚠️ Comando no autorizado para tu nivel de seguridad. Contacta al Director."

// Director ejecuta comando crítico:
"⚠️ Comando crítico. Autenticación biométrica requerida." 
// → Solicita huella/FaceID
```

#### 3.3 Modelo de Auditoría (`VoiceAuditLog`)
```python
# core/models.py - VoiceAuditLog

REGISTRA:
- Usuario y empresa
- Timestamp y URL
- Transcripción del comando
- Intención detectada por IA
- Parámetros extraídos
- Respuesta del sistema
- Estado (EXITOSO / BLOQUEADO / ERROR)
- Nivel de autorización
- Tiempo de procesamiento (ms)
- Si requirió autenticación adicional
```

**Dashboard para Director**:
- `GET /voice/logs/` → Dashboard visual de auditoría
- Estadísticas: Total, bloqueados, críticos
- Top 5 usuarios más activos
- Top 5 intenciones más usadas

---

### ⚡ BLOQUE 4: ACCIONES RÁPIDAS

#### 4.1 Comandos Mapeados
```python
# Comandos → URLs o acciones custom

'cerrar_caja' → /farmacia/cierre-turno/
'nuevo_paciente' → MODAL de registro rápido
'surtir_receta' → Cargar en PDV (AJAX)
'buscar_paciente' → Abrir buscador con término
'ver_stock' → /farmacia/productos/?q=...
```

#### 4.2 Ejecución de Acciones
```javascript
// JavaScript: executeAction()

Si action.url → window.location.href = action.url
Si action.accion === 'cargar_receta_en_pdv':
  → Llamar función cargarRecetaEnPDV(folio)
  → O navegar a /farmacia/pdv/?receta=554
```

---

## 🚀 DEPLOYMENT & SETUP

### Paso 1: Instalar Dependencias

```bash
cd C:\Users\jonil\Desktop\PRISLAB_SaaS

# Activar entorno virtual
.\venv\Scripts\Activate.ps1

# Instalar nuevas dependencias
pip install channels==4.0.0 channels-redis==4.1.0

# Verificar instalación
pip list | Select-String channels
```

### Paso 2: Configurar Redis

#### Opción A: Redis Local (Desarrollo)
```bash
# Windows: Usar Windows Subsystem for Linux (WSL)
wsl
sudo apt update
sudo apt install redis-server
sudo service redis-server start

# O usar Docker
docker run -d -p 6379:6379 redis:alpine
```

#### Opción B: Redis en Cloud (Producción)
```bash
# Google Cloud Memorystore (Redis)
gcloud redis instances create prislab-redis \
  --size=1 \
  --region=us-central1 \
  --redis-version=redis_7_0 \
  --project=prislab-v5-ai

# Obtener IP interna
gcloud redis instances describe prislab-redis \
  --region=us-central1 \
  --format="get(host)"
```

**Configurar en Cloud Run**:
```bash
# Agregar variable de entorno
gcloud run services update prislab-v5 \
  --region=us-central1 \
  --set-env-vars="REDIS_URL=redis://<IP_REDIS>:6379/0" \
  --project=prislab-v5-ai
```

### Paso 3: Generar Migraciones

```bash
python manage.py makemigrations core

# Debe crear algo como:
# core/migrations/0014_voiceauditlog.py
#   - Create model VoiceAuditLog
```

### Paso 4: Aplicar Migraciones

```bash
# Desarrollo local
python manage.py migrate core

# Producción (Cloud Run Job)
gcloud run jobs create apply-voice-migrations \
  --image=gcr.io/prislab-v5-ai/prislab-v5:latest \
  --region=us-central1 \
  --command="python,manage.py,migrate,core" \
  --project=prislab-v5-ai

gcloud run jobs execute apply-voice-migrations \
  --region=us-central1 \
  --project=prislab-v5-ai
```

### Paso 5: Verificar Configuración

```bash
# Verificar que channels está en INSTALLED_APPS
python manage.py check

# Verificar WebSocket routing
python manage.py shell
>>> from config.asgi import application
>>> print(application)
# Debe mostrar ProtocolTypeRouter con http y websocket
```

### Paso 6: Probar Localmente

```bash
# Iniciar servidor ASGI con Daphne (soporta WebSockets)
pip install daphne
daphne config.asgi:application -p 8000

# O con Django dev server (solo HTTP, sin WS)
python manage.py runserver
```

**Abrir en navegador**:
```
http://localhost:8000/
```

**Verificar**:
1. Aparece botón PTT flotante (esquina inferior derecha)
2. Click en botón → Pide permiso de micrófono
3. Hablar comando → Procesa y muestra respuesta
4. Console muestra logs de WebSocket

---

## 🧪 TESTING & PRUEBAS

### Test 1: Botón PTT Básico
```
1. Abrir app en navegador
2. Verificar botón flotante visible
3. Click en botón → Vibra (móvil)
4. Botón cambia a color rojo (escuchando)
5. Hablar: "cerrar caja"
6. Botón cambia a amarillo (procesando)
7. Aparece notificación: "Abriendo cierre de turno..."
8. Navega a /farmacia/cierre-turno/
```

### Test 2: Comando con Contexto
```
1. Ir a /farmacia/ventas/
2. Agregar atributo data-folio="554" a un elemento
3. Click en PTT
4. Hablar: "súrtela" (pronombre ambiguo)
5. IA debe entender: "surtir receta #554"
6. Respuesta: "Cargando receta #554..."
```

### Test 3: RBAC - Bloqueo de Comando
```
1. Login como STAFF (Nancy)
2. Click en PTT
3. Hablar: "eliminar todos los datos"
4. Respuesta: "⚠️ Comando no autorizado para tu nivel..."
5. Verificar en /voice/logs/ que está marcado como BLOQUEADO
```

### Test 4: Comando Crítico con Auth
```
1. Login como DIRECTOR (admin)
2. Click en PTT
3. Hablar: "eliminar paciente 123"
4. Respuesta: "⚠️ Comando crítico. Requiere autenticación..."
5. Aparece prompt de confirmación
6. Confirmar → Ejecuta acción
```

### Test 5: WebSocket Connection
```
1. Abrir DevTools → Network → WS
2. Filtrar por "ws://localhost:8000/ws/voice/commands/"
3. Verificar conexión establecida
4. Mensaje de bienvenida recibido
5. Hablar comando → Ver mensaje enviado por WS
6. Ver respuesta por WS (más rápido que REST)
```

### Test 6: Walkie-Talkie (Futuro)
```
1. Abrir 2 navegadores (Nancy y Brizia)
2. Conectar ambos a ws://host/ws/voice/walkie/farmacia/
3. Nancy presiona PTT y habla
4. Audio de Nancy se reproduce en dispositivo de Brizia
5. Ambos ven notificación "Usuario unido/salió"
```

---

## 📊 ARQUITECTURA TÉCNICA

### Frontend (JavaScript)
```
static/js/pris_voice_commander.js
│
├─ PrisVoiceCommander (clase principal)
│  ├─ Web Speech Recognition (local)
│  ├─ WebSocket Client (tiempo real)
│  ├─ REST API Fallback (HTTP)
│  ├─ Context Extraction (data-* attributes)
│  └─ Action Executor (navegación + custom)
│
└─ static/css/pris_voice_commander.css
   └─ Botón PTT flotante + animaciones
```

### Backend (Django)
```
core/
├─ models.py
│  └─ VoiceAuditLog (auditoría)
│
├─ services/
│  └─ voice_service.py
│     ├─ procesar_comando_voz() → Gemini + RBAC
│     ├─ verificar_permiso_comando() → Filtros por rol
│     └─ registrar_comando_voz() → Guardar en log
│
├─ consumers.py
│  ├─ VoiceCommandConsumer (WS comandos)
│  └─ WalkieTalkieConsumer (WS audio)
│
├─ routing.py
│  └─ websocket_urlpatterns
│
└─ views/
   └─ voice.py
      ├─ procesar_comando_api() → REST fallback
      ├─ historial_comandos() → API de logs
      ├─ dashboard_voice_logs() → Dashboard auditoría
      └─ verificar_webauthn() → Auth biométrica
```

### Infrastructure
```
config/
├─ asgi.py → ProtocolTypeRouter (HTTP + WS)
├─ settings.py
│  ├─ ASGI_APPLICATION
│  └─ CHANNEL_LAYERS (Redis)
└─ urls.py → Rutas API REST
```

---

## 🔒 SEGURIDAD & PRIVACIDAD

### 1. Transcripción Local
- Web Speech API procesa voz **en el dispositivo**
- NO se envía audio crudo al servidor (solo texto)
- Privacidad total: Google/navegador procesa, no PRISLAB

### 2. Auditoría Total
- Cada comando registrado en `VoiceAuditLog`
- Incluye: Usuario, timestamp, intención, respuesta
- Director puede revisar todos los comandos en `/voice/logs/`

### 3. RBAC Estricto
- STAFF: Solo comandos operativos
- DIRECTOR: Todos + críticos con auth
- Comandos bloqueados → Log + notificación

### 4. WebAuthn (Futuro)
- Comandos críticos requieren huella/FaceID
- Actualmente: Prompt de confirmación simple
- Roadmap: Integrar WebAuthn library

---

## 📈 MÉTRICAS & KPIs

### Objetivos Post-Deployment

#### Mes 1
- [ ] 80% del staff usa comandos de voz
- [ ] Comandos más usados: "cerrar caja", "buscar paciente", "surtir receta"
- [ ] <1% de comandos bloqueados por permisos
- [ ] Latencia promedio < 1 segundo (transcripción + IA + respuesta)

#### Mes 3
- [ ] 50% de tareas repetitivas ejecutadas por voz
- [ ] Reducción de 30% en tiempo de cierre de caja
- [ ] 90% de precisión en comprensión de intenciones
- [ ] 0 incidentes de seguridad por comandos maliciosos

### Métricas Técnicas
```sql
-- Comandos más usados
SELECT intencion_detectada, COUNT(*) as total
FROM core_voiceauditlog
GROUP BY intencion_detectada
ORDER BY total DESC
LIMIT 10;

-- Usuarios más activos
SELECT usuario_id, COUNT(*) as total_comandos
FROM core_voiceauditlog
GROUP BY usuario_id
ORDER BY total DESC;

-- Latencia promedio
SELECT AVG(tiempo_procesamiento_ms) as latencia_promedio_ms
FROM core_voiceauditlog
WHERE timestamp > NOW() - INTERVAL '7 days';

-- Tasa de bloqueo
SELECT 
  COUNT(CASE WHEN estado = 'BLOQUEADO' THEN 1 END) * 100.0 / COUNT(*) as tasa_bloqueo_pct
FROM core_voiceauditlog;
```

---

## 🐛 TROUBLESHOOTING

### Error: "Tu navegador no soporta reconocimiento de voz"
**Causa**: Web Speech API no disponible  
**Solución**:
- Desktop: Usar Chrome/Edge (no Firefox)
- Móvil: Usar Chrome Android o Safari iOS 16.4+
- No soportado: Firefox, navegadores antiguos

### Error: "Permiso de micrófono denegado"
**Causa**: Usuario rechazó permiso o navegador bloqueado  
**Solución**:
1. Chrome: icono 🔒 en barra de direcciones → Permisos → Micrófono → Permitir
2. Safari: Configuración → Safari → Permisos → Micrófono

### Error: WebSocket no conecta
**Causa**: Redis no disponible o mal configurado  
**Solución**:
```bash
# Verificar Redis running
redis-cli ping
# Debe retornar: PONG

# Verificar REDIS_URL en settings
python manage.py shell
>>> from django.conf import settings
>>> print(settings.REDIS_URL)

# Usar InMemoryChannelLayer para dev
# (Ya configurado automáticamente si DEBUG=True y no hay REDIS_URL)
```

### Error: IA no procesa comandos
**Causa**: Gemini API key no configurada  
**Solución**:
```bash
# Verificar API key
python manage.py shell
>>> from django.conf import settings
>>> print(settings.GOOGLE_API_KEY)

# Si está vacío, configurar:
# 1. En .env local: GOOGLE_API_KEY=tu-key
# 2. En Cloud Run: Verificar secret gemini-api-key
```

### Error: Comandos siempre bloqueados
**Causa**: RBAC demasiado restrictivo  
**Solución**:
- Verificar grupos del usuario en admin
- Agregar intención a lista PERMITIDOS en `voice_service.py`
- Revisar logs en `/voice/logs/` para ver motivo

---

## 🚀 ROADMAP FUTURO

### v2.0 - Walkie-Talkie Completo
- [ ] Streaming de audio en tiempo real
- [ ] Canales por isla (Farmacia, Consultorio, Lab)
- [ ] Push-to-Talk para Nancy → Brizia directo
- [ ] Historial de mensajes de audio

### v2.1 - Comandos Avanzados
- [ ] "Genera reporte de ventas del mes"
- [ ] "Envía resultado de lab a paciente por WhatsApp"
- [ ] "Programa cita con Dra. Brizia mañana 10am"
- [ ] Multi-step commands ("Busca paciente Juan, luego súrtele receta 554")

### v2.2 - IA Proactiva
- [ ] "Nancy, hay 3 recetas pendientes de surtir"
- [ ] "Briz, tu paciente de las 3pm llegó"
- [ ] "Jonathan, stock crítico en Paracetamol"
- [ ] Alertas de voz automáticas

### v2.3 - Multilenguaje
- [ ] Inglés (turismo médico)
- [ ] Lenguaje de señas (accesibilidad)
- [ ] Dialectos regionales

---

## 📞 SOPORTE & CONTACTO

**Arquitecto Principal**: Cursor AI Agent  
**Cliente**: Jonathan (Director PRISLAB)  
**Versión del Sistema**: PRIS VOICE COMMANDER v1.0  
**Fecha de Implementación**: Febrero 2026

---

## ✅ CHECKLIST PRE-DEPLOYMENT

Antes de desplegar a producción:

- [x] channels y channels-redis en requirements.txt
- [x] ASGI_APPLICATION configurado en settings.py
- [x] CHANNEL_LAYERS con Redis configurado
- [x] Modelo VoiceAuditLog creado
- [x] Migraciones generadas (0014_voiceauditlog.py)
- [ ] Redis disponible (Memorystore o local)
- [ ] REDIS_URL configurada en Cloud Run
- [ ] Migraciones aplicadas en producción
- [ ] CSS y JS incluidos en base.html
- [ ] URLs de voice agregadas en urls.py
- [ ] Permisos de micrófono solicitados en HTTPS

---

**🎉 PRISLAB VOICE COMMANDER - "CONTROL TU CLÍNICA CON TU VOZ" 🎤**
