# 🚀 PLAN MAESTRO: PREPARACIÓN PRE-DESPLIEGUE
## PRISLAB V5 - 26 de Enero de 2026

---

## 🎯 ESTRATEGIA

### FASE 1: YO COMPLETO (Mientras tú obtienes APIs)
**Objetivo:** Dejar el sistema al **98%** sin APIs

### FASE 2: TÚ CONFIGURAS
**Objetivo:** Obtener credenciales de Google Cloud

### FASE 3: INTEGRACIÓN FINAL
**Objetivo:** Conectar APIs e integrar IA

### FASE 4: DESPLIEGUE
**Objetivo:** Migración completa a servidor

### FASE 5: PRUEBAS MASIVAS
**Objetivo:** Validación con personal real

---

## 📋 TRABAJO A REALIZAR (EN ORDEN)

### 🟢 BLOQUE 1: TEMPLATES MARKETING (2-3 horas)
**Backend completo - Solo faltan vistas**

#### Archivos a crear:
1. `marketing/templates/marketing/campañas/lista.html`
   - Lista de campañas activas/inactivas
   - Filtros por estado, fecha, tipo
   - Botón crear nueva campaña
   - Estadísticas (clicks, conversiones, ROI)

2. `marketing/templates/marketing/campañas/crear.html`
   - Formulario completo
   - Selector de segmento de clientes
   - Editor de contenido (mensaje, email)
   - Configuración de canal (email, SMS, WhatsApp)
   - Preview en tiempo real

3. `marketing/templates/marketing/campañas/dashboard.html`
   - Métricas en tiempo real (Chart.js)
   - Campañas activas
   - Tasa de apertura/conversión
   - Calendario de envíos

4. `marketing/templates/marketing/cupones/lista.html`
   - Lista de cupones activos
   - Código, descuento, usos, caducidad
   - Estado (activo/vencido/agotado)

5. `marketing/templates/marketing/cupones/generar.html`
   - Generador de cupones
   - Tipo (porcentaje/monto fijo)
   - Restricciones (monto mínimo, usos, caducidad)
   - Generación masiva de códigos únicos

6. `marketing/templates/marketing/contactos/lista.html`
   - Lista de contactos/leads
   - Filtros por segmento, origen, estado
   - Historial de interacciones

7. `marketing/templates/marketing/contactos/importar.html`
   - Importador CSV/Excel
   - Mapeo de campos
   - Validación en tiempo real
   - Preview antes de importar

**Resultado:** Marketing al 100%

---

### 🟢 BLOQUE 2: TEMPLATES BIENESTAR (2-3 horas)
**Backend completo - Solo faltan vistas**

#### Archivos a crear:
1. `bienestar/templates/bienestar/diario/lista.html`
   - Lista de entradas del diario
   - Filtros por fecha, ánimo, categoría
   - Gráfica de tendencias emocionales (Chart.js)

2. `bienestar/templates/bienestar/diario/nueva_entrada.html`
   - Formulario de entrada diaria
   - Selector de ánimo (emojis)
   - Editor de texto libre
   - Selector de actividades realizadas
   - Nivel de energía, calidad de sueño

3. `bienestar/templates/bienestar/diario/estadisticas.html`
   - Dashboard de bienestar personal
   - Gráficas de ánimo, energía, sueño
   - Patrones detectados
   - Recomendaciones personalizadas

4. `bienestar/templates/bienestar/recursos/lista.html`
   - Biblioteca de recursos (artículos, videos)
   - Categorías (nutrición, ejercicio, salud mental)
   - Buscador y filtros

5. `bienestar/templates/bienestar/recursos/detalle.html`
   - Vista de recurso individual
   - Contenido completo
   - Recursos relacionados
   - Calificación y comentarios

6. `bienestar/templates/bienestar/consultorio/agendar.html`
   - Agendar cita de bienestar
   - Calendario disponibilidad
   - Selector de servicio (nutricional, psicología)
   - Confirmación

**Resultado:** Bienestar al 100%

---

### 🟢 BLOQUE 3: MÓDULO RECEPCIÓN INDEPENDIENTE (4-5 horas)
**Funcionalidad ya existe en core - Separar y mejorar**

#### Archivos a crear:
1. `recepcion/views.py` (~300 líneas)
   - `dashboard_recepcion()` - Panel principal
   - `registrar_paciente()` - Alta de pacientes
   - `buscar_paciente()` - Búsqueda avanzada
   - `agendar_cita()` - Agendar citas
   - `check_in_paciente()` - Registrar llegada
   - `lista_espera()` - Sala de espera en tiempo real
   - `cobrar_consulta()` - Cobro en recepción

2. `recepcion/urls.py` (~50 líneas)
   - Rutas para todas las vistas
   - APIs para búsqueda

3. `recepcion/admin.py` (~80 líneas)
   - Admin para registros de recepción
   - Logs de atención

4. `recepcion/forms.py` (~150 líneas)
   - Form para registrar paciente
   - Form para agendar cita
   - Form para check-in
   - Form para cobro

5. **6 Templates:**
   - `dashboard.html` - Panel principal
   - `registrar_paciente.html` - Alta pacientes
   - `buscar_paciente.html` - Búsqueda
   - `agendar_cita.html` - Agendar
   - `lista_espera.html` - Sala de espera
   - `cobrar_consulta.html` - Cobro

**Resultado:** Recepción 100% independiente

---

### 🟢 BLOQUE 4: MÓDULO ENFERMERÍA INDEPENDIENTE (4-5 horas)
**Funcionalidad ya existe en core - Separar y mejorar**

#### Archivos a crear:
1. `enfermeria/views.py` (~250 líneas)
   - `dashboard_enfermeria()` - Panel principal
   - `lista_pacientes_triage()` - Pacientes pendientes
   - `capturar_signos_vitales()` - Captura de signos
   - `historial_signos_paciente()` - Historial
   - `graficas_tendencias()` - Gráficas Chart.js
   - `alertas_signos_criticos()` - Alertas automáticas

2. `enfermeria/urls.py` (~40 líneas)
   - Rutas para todas las vistas
   - APIs para signos vitales

3. `enfermeria/admin.py` (~60 líneas)
   - Admin para signos vitales
   - Logs de enfermería

4. `enfermeria/forms.py` (~120 líneas)
   - Form para signos vitales (validación)
   - Form con alertas automáticas

5. **6 Templates:**
   - `dashboard.html` - Panel principal
   - `lista_triage.html` - Pacientes pendientes
   - `capturar_signos.html` - Captura signos
   - `historial_signos.html` - Historial
   - `graficas_tendencias.html` - Gráficas
   - `alertas_criticas.html` - Alertas

**Resultado:** Enfermería 100% independiente

---

### 🟡 BLOQUE 5: PREPARAR MÓDULO IA (SIN APIS) (3-4 horas)
**Crear estructura completa - Conectar APIs después**

#### Archivos a crear:
1. `ia/views.py` (~400 líneas)
   - `dashboard_ia()` - Panel principal
   - `procesar_receta_ocr()` - OCR (preparado para Vision API)
   - `transcribir_audio_consulta()` - Speech-to-Text (preparado)
   - `analizar_con_gemini()` - Análisis IA (preparado para Gemini)
   - `asistente_medico()` - Chat médico (preparado para Gemini)
   - `api_procesar_imagen()` - Endpoint AJAX
   - `api_transcribir_audio()` - Endpoint AJAX
   - `api_consultar_asistente()` - Endpoint AJAX

2. `ia/admin.py` (~100 líneas)
   - Admin para CotizacionOCR
   - Admin para TranscripcionVoz
   - Admin para logs de procesamiento
   - Estadísticas de uso

3. `ia/forms.py` (~120 líneas)
   - Form para subir imagen (receta)
   - Form para subir audio
   - Form para consulta al asistente
   - Validaciones

4. `ia/urls.py` (~60 líneas)
   - Rutas para vistas
   - Rutas API

5. **5 Templates:**
   - `dashboard.html` - Panel principal IA
   - `ocr/procesar.html` - Subir receta
   - `ocr/resultados.html` - Resultados OCR
   - `voz/transcripcion.html` - Transcribir audio
   - `asistente/chat.html` - Chat médico

6. **Integración con Pris:**
   - `static/js/pris_ia_connector.js` - Conector IA
   - Endpoints para Pris usar el asistente

**Resultado:** IA al 90% (solo falta conectar APIs)

---

### 🔵 BLOQUE 6: DOCUMENTACIÓN DE DESPLIEGUE (1 hora)

#### Archivos a crear:
1. `GUIA_DESPLIEGUE_CLOUD_RUN_2026.md`
   - Configuración Cloud SQL
   - Configuración Cloud Run
   - Variables de entorno
   - Comandos exactos
   - Troubleshooting

2. `CHECKLIST_PRE_PRODUCCION.md`
   - Validaciones necesarias
   - Migraciones pendientes
   - Archivos estáticos
   - Configuración de seguridad
   - SSL/HTTPS
   - Backup de BD

3. `.env.production.example`
   - Template de variables de entorno
   - Sin valores sensibles
   - Documentado

**Resultado:** Despliegue documentado

---

### 🔵 BLOQUE 7: PROTOCOLO DE PRUEBAS MASIVAS (1 hora)

#### Archivos a crear:
1. `PROTOCOLO_PRUEBAS_MASIVAS.md`
   - Checklist por módulo
   - Roles de prueba (recepción, enfermera, médico, admin)
   - Escenarios de prueba (flujo paciente completo)
   - Formulario de reporte de bugs
   - Matriz de validación

2. `GUIA_USUARIOS_FINALES.md`
   - Manual rápido por rol
   - Capturas de pantalla
   - Flujos principales
   - FAQ

**Resultado:** Pruebas estructuradas

---

## 📊 RESUMEN DE ENTREGABLES

### Al terminar este plan:
- ✅ **Marketing:** 100% (7 templates)
- ✅ **Bienestar:** 100% (6 templates)
- ✅ **Recepción:** 100% independiente
- ✅ **Enfermería:** 100% independiente
- ✅ **IA:** 90% (estructura completa, sin APIs)
- ✅ **Despliegue:** 100% documentado
- ✅ **Pruebas:** 100% protocolo listo

### Sistema total:
- **Antes:** 92%
- **Después de este plan:** 98%
- **Con APIs integradas:** 100% ✨

---

## ⏱️ TIEMPO ESTIMADO TOTAL

| Bloque | Tiempo |
|--------|--------|
| Marketing | 2-3h |
| Bienestar | 2-3h |
| Recepción | 4-5h |
| Enfermería | 4-5h |
| IA (preparación) | 3-4h |
| Documentación | 1h |
| Pruebas | 1h |
| **TOTAL** | **17-24 horas** |

---

## 🎯 FLUJO DE TRABAJO

### AHORA (Mientras tú obtienes APIs):
1. Yo completo Bloques 1-7
2. Sistema al 98%
3. Todo listo para integración

### CUANDO REGRESES (APIs listas):
1. Conectar APIs en `ia/views.py`
2. Integrar Pris con IA
3. Pruebas de IA (1-2h)
4. Sistema al 100%

### DESPLIEGUE:
1. Revisión final
2. Migración a Cloud Run
3. Pruebas en producción
4. Capacitación personal

### PRUEBAS MASIVAS:
1. Personal prueba todo
2. Reporte de bugs
3. Correcciones inmediatas
4. Validación final

---

## ✅ CONFIRMACIÓN

**¿Procedo con los 7 bloques mientras obtienes las APIs?**

**Tiempo:** 17-24 horas de trabajo continuo  
**Resultado:** Sistema al 98% listo para despliegue

Cuando regreses con las APIs, solo faltarán **2-3 horas** para llegar al 100% e iniciar el despliegue.

---

**🚀 INICIANDO IMPLEMENTACIÓN EN 3... 2... 1...**
