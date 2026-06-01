# Plan de Integración V 5.0: "Núcleo Pris-Valle"

## 📋 Resumen Ejecutivo

Este documento define la arquitectura y estrategia de integración para las funcionalidades avanzadas del sistema PRISLAB SaaS, incluyendo IoT, IA y reglas de negocio estrictas.

**Versión:** 5.0  
**Fecha:** 2026-01-20  
**Estado:** Planificación y Arquitectura Base

---

## 🏗️ Arquitectura por Capas

### Capa 1: Hardware IoT y Seguridad Física
- **Módulo de Kiosco** (Auto-Verificación)
- **Botón de Pánico** (Seguridad)
- **Oído Clínico** (IA de Voz)

### Capa 2: Inteligencia Artificial
- **Cotizador IA "Ojo Biónico"** (OCR)
- **Valores de Pánico Inteligentes**

### Capa 3: Reglas de Negocio Estrictas
- **"Triple Llave" de Envío**
- **Corte Ciego**

---

## 📦 Estructura de Módulos Propuesta

```
PRISLAB_SaaS/
├── core/                    # Módulo base (existente)
├── pacientes/              # Módulo pacientes (existente)
├── laboratorio/            # Módulo laboratorio (existente)
├── iot/                    # NUEVO: Hardware IoT y Kiosco
│   ├── models.py
│   ├── views.py
│   ├── consumers.py        # WebSockets (Django Channels)
│   └── templates/iot/
├── seguridad/              # NUEVO: Seguridad física y botón de pánico
│   ├── models.py
│   ├── views.py
│   └── services/
│       └── alertas.py      # WhatsApp/Telegram
├── ia/                     # NUEVO: Módulo de Inteligencia Artificial
│   ├── ocr/
│   │   └── vision.py       # Google Cloud Vision / Tesseract
│   ├── voz/
│   │   └── whisper.py      # OpenAI Whisper
│   └── servicios/
│       └── cotizador.py    # Cotizador IA
└── reglas_negocio/         # NUEVO: Reglas de negocio estrictas
    ├── validadores.py      # Triple Llave, etc.
    └── cortes.py           # Corte Ciego
```

---

## 🎯 Fase 1: Preparación de Arquitectura Base (ACTUAL)

### Objetivo
Preparar los modelos y estructura base para que sean compatibles con las funcionalidades V 5.0.

### Tareas

#### 1.1. Extender Modelos Existentes

**`laboratorio/models.py` - Orden:**
- ✅ `estado_analisis` (ya existe)
- ✅ `fecha_validacion` (ya existe)
- ✅ `usuario_valido` (ya existe)
- ➕ `telefono_verificado` (nuevo - para Triple Llave)
- ➕ `rango_panico_min` y `rango_panico_max` en Estudio (nuevo)

**`pacientes/models.py` - Paciente:**
- ➕ `telefono_verificado` (nuevo - para Triple Llave)
- ➕ `codigo_verificacion_sms` (nuevo)
- ➕ `fecha_verificacion_telefono` (nuevo)

**`core/models.py` - Venta:**
- ➕ `corte_ciego_monto_reportado` (nuevo - para Corte Ciego)
- ➕ `corte_ciego_diferencia` (nuevo)

#### 1.2. Crear Modelos Nuevos

**`seguridad/models.py`:**
- `AlertaPanico` (usuario, fecha, ubicacion, resuelta)
- `ConfiguracionSeguridad` (telefonos_emergencia, activo)

**`iot/models.py`:**
- `Kiosco` (nombre, ip_address, activo, ultima_conexion)
- `VerificacionKiosco` (orden, kiosco, estado, datos_confirmados)

**`ia/models.py`:**
- `CotizacionOCR` (imagen_receta, texto_extraido, estudios_detectados, confianza)
- `TranscripcionVoz` (audio, texto_transcrito, entidades_extraidas)

---

## 🚀 Fase 2: Implementación por Módulos

### Módulo 1: Kiosco (Auto-Verificación)

**Tecnología:** Django Channels (WebSockets) o Polling Simple

**Flujo:**
1. Recepcionista captura datos → Presiona "Enviar a Kiosco"
2. Sistema crea `VerificacionKiosco` con estado `PENDIENTE`
3. Tablet del paciente (polling cada 2s) detecta nueva verificación
4. Muestra modal grande con datos para confirmación
5. Paciente confirma → Estado cambia a `CONFIRMADO`
6. Recepcionista ve confirmación en tiempo real

**Implementación:**
- **Opción A (Simple):** Polling con endpoint `/api/kiosco/pendientes/`
- **Opción B (Avanzado):** WebSockets con Django Channels

**Archivos a crear:**
- `iot/views.py` - Endpoints de kiosco
- `iot/templates/iot/kiosco_verificacion.html` - Vista para tablet
- `laboratorio/templates/laboratorio/recepcion.html` - Botón "Enviar a Kiosco"

---

### Módulo 2: Botón de Pánico

**Tecnología:** Atajo de teclado global + API de WhatsApp/Telegram

**Flujo:**
1. Usuario presiona `Ctrl+Alt+P` (o F12)
2. JavaScript captura evento → AJAX a `/seguridad/panico/`
3. Sistema crea `AlertaPanico` con timestamp y ubicación
4. Servicio de alertas envía mensajes a números configurados
5. Alertas aparecen en dashboard de seguridad

**Implementación:**
- JavaScript global en `base.html`
- Endpoint `/seguridad/panico/` que crea alerta
- Servicio `seguridad/services/alertas.py` con integración WhatsApp/Telegram

**APIs Necesarias:**
- WhatsApp Business API o Twilio
- Telegram Bot API

---

### Módulo 3: Oído Clínico (IA de Voz)

**Tecnología:** OpenAI Whisper API o similar

**Flujo:**
1. Químico presiona "Grabar Entrevista" en pantalla de Toma de Muestras
2. Navegador graba audio (MediaRecorder API)
3. Audio se envía a `/ia/transcribir-voz/`
4. Servicio llama a Whisper API → Obtiene transcripción
5. IA extrae entidades (Ayuno, Alergias, Medicamentos)
6. Campos se llenan automáticamente

**Implementación:**
- `ia/voz/whisper.py` - Cliente de Whisper API
- `ia/servicios/extractor_entidades.py` - Extracción de entidades con LLM
- JavaScript en template de captura para grabación

---

### Módulo 4: Cotizador IA "Ojo Biónico" (OCR)

**Tecnología:** Google Cloud Vision API o Tesseract OCR

**Flujo:**
1. Recepcionista sube foto de receta → `/ia/cotizar-ocr/`
2. OCR extrae texto de la imagen
3. Sistema busca coincidencias en `Estudio` (nombre, código)
4. Arma presupuesto automático
5. Muestra resultados con nivel de confianza

**Implementación:**
- `ia/ocr/vision.py` - Cliente de Google Cloud Vision
- `ia/servicios/cotizador.py` - Lógica de matching y cotización
- Template con preview de imagen y resultados

**Modelo:**
```python
class CotizacionOCR(models.Model):
    imagen_receta = models.ImageField()
    texto_extraido = models.TextField()
    estudios_detectados = models.JSONField()  # [{estudio_id, confianza}]
    total_calculado = models.DecimalField()
    usuario_creador = models.ForeignKey(User)
    fecha = models.DateTimeField(auto_now_add=True)
```

---

### Módulo 5: Valores de Pánico Inteligentes

**Tecnología:** Extensión de modelo `Estudio` existente

**Flujo:**
1. Químico captura resultado
2. Sistema compara con `rango_panico_min` y `rango_panico_max`
3. Si está en pánico → Bloquea impresión/envío
4. Requiere "Doble Validación" (otro químico con contraseña)
5. Se registra auditoría de doble validación

**Implementación:**
- Extender `Estudio` con campos `rango_panico_min` y `rango_panico_max`
- Modificar `Resultado.save()` para detectar pánico
- Agregar campo `requiere_doble_validacion` en `Orden`
- Crear vista de doble validación

---

### Módulo 6: "Triple Llave" de Envío

**Tecnología:** Validador antes de envío de WhatsApp/PDF

**Flujo:**
Antes de enviar resultados por WhatsApp, el sistema verifica:

1. ✅ `Orden.estado_pago == True` (Saldo cero)
2. ✅ `Orden.usuario_valido != None` (Calidad técnica)
3. ✅ `Paciente.telefono_verificado == True` (Seguridad de datos)

Si falta alguna → Bloquea envío y alerta al operador.

**Implementación:**
- Crear `reglas_negocio/validadores.py` con función `validar_triple_llave()`
- Integrar en vista de envío de resultados
- Mostrar mensaje claro de qué falta

**Código Base:**
```python
def validar_triple_llave(orden):
    errores = []
    
    if not orden.estado_pago:
        errores.append("La orden no está pagada completamente")
    
    if not orden.usuario_valido:
        errores.append("La orden no ha sido validada por calidad técnica")
    
    if not orden.paciente.telefono_verificado:
        errores.append("El teléfono del paciente no está verificado")
    
    return len(errores) == 0, errores
```

---

### Módulo 7: Corte Ciego

**Tecnología:** Modificación de vista de Corte de Caja

**Flujo:**
1. Sistema calcula monto esperado en caja
2. En lugar de mostrarlo, muestra input vacío: "¿Cuánto tienes?"
3. Cajero ingresa monto reportado
4. Sistema compara vs. monto real
5. Registra diferencia (sobrante/faltante) como incidencia

**Implementación:**
- Modificar `core/views/farmacia.py` - `corte_caja_dia()`
- Agregar campo `monto_reportado` en modelo `CorteCaja` (si existe)
- Calcular diferencia y guardar en auditoría

---

## 📅 Hoja de Ruta de Implementación

### Fase Actual (Completando Base)
- ✅ Modelos de Pacientes, Laboratorio, Farmacia
- ✅ Recepción, Captura, Validación
- ✅ Sistema de PDFs con QR
- 🔄 **EN PROGRESO:** Preparar arquitectura V 5.0

### Fase 2: Reglas de Negocio (Prioridad Alta)
- **Sprint 1:** Triple Llave de Envío
- **Sprint 2:** Corte Ciego
- **Sprint 3:** Valores de Pánico

### Fase 3: Inteligencia Artificial (Prioridad Media)
- **Sprint 4:** Cotizador OCR
- **Sprint 5:** Oído Clínico (Voz)

### Fase 4: IoT y Seguridad (Prioridad Baja - Requiere Hardware)
- **Sprint 6:** Módulo de Kiosco
- **Sprint 7:** Botón de Pánico

---

## 🔧 Configuración Técnica Requerida

### Dependencias Nuevas
```python
# requirements.txt (agregar)
channels==4.0.0              # WebSockets para Kiosco
channels-redis==4.1.0        # Backend Redis para Channels
google-cloud-vision==3.4.0   # OCR
openai==1.0.0                # Whisper API
twilio==8.10.0               # WhatsApp/Telegram
python-telegram-bot==20.0   # Telegram Bot
```

### Variables de Entorno
```env
# .env
GOOGLE_CLOUD_VISION_API_KEY=...
OPENAI_API_KEY=...
TWILIO_ACCOUNT_SID=...
TWILIO_AUTH_TOKEN=...
TELEGRAM_BOT_TOKEN=...
TELEGRAM_CHAT_ID=...
```

---

## 📝 Notas de Diseño

### Compatibilidad Hacia Atrás
- Todos los nuevos campos deben ser `null=True, blank=True` inicialmente
- Las funcionalidades nuevas deben ser opcionales (feature flags)
- No romper funcionalidad existente

### Seguridad
- Botón de pánico debe ser accesible incluso si el sistema está lento
- Triple Llave debe ser obligatorio (no bypass)
- Valores de pánico requieren doble validación (no se puede omitir)

### Performance
- OCR debe procesarse en background (Celery)
- WebSockets deben usar Redis como backend
- Polling de Kiosco debe ser eficiente (índices en BD)

---

## ✅ Checklist de Preparación

- [x] Documentar arquitectura V 5.0
- [ ] Crear modelos base para nuevas funcionalidades
- [ ] Extender modelos existentes con campos necesarios
- [ ] Crear estructura de carpetas para nuevos módulos
- [ ] Configurar dependencias base
- [ ] Implementar Triple Llave (prioridad)
- [ ] Implementar Corte Ciego (prioridad)
- [ ] Preparar integración OCR (futuro)
- [ ] Preparar integración Voz (futuro)
- [ ] Preparar módulo Kiosco (futuro)
- [ ] Preparar Botón de Pánico (futuro)

---

**Última actualización:** 2026-01-20  
**Próxima revisión:** Después de completar Fase Actual
