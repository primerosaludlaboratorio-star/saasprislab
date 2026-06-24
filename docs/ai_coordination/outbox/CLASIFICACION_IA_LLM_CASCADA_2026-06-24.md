# Clasificación Superficie IA/LLM — Cascada — 2026-06-24

Agente: Cascada  
Método: escaneo de importaciones, acoplamiento real al runtime, lectura de archivos fuente  
Base: INVENTARIO_MAESTRO_TOTAL.md + escaneo en vivo del árbol  

---

## 1. Objetivo

Clasificar la superficie IA/LLM real de PRISLAB en 4 categorías por acoplamiento al runtime:
- IA activa de negocio
- IA de soporte / operación
- Tests y comandos de prueba
- Legado / ruido

---

## 2. Alcance — archivos revisados

- `core/utils/gemini_client.py` — leído completo
- `core/views/pris_ia.py` — imports completos escaneados (1590+ líneas)
- `core/views/ai_brain.py` — imports
- `core/views/cerebro.py` — imports
- `ia/views.py` — imports
- `core/agent/pris_agent.py` — referenciado desde `core/middleware/pris_context.py`
- `core/management/commands/supervisor_ia_revisar_ventas.py` — leído
- `core/management/commands/auditoria_ia.py` — leído
- `core/management/commands/generar_auditoria_gemini.py` — leído
- `tools/last_suite_human_summary.json` — leído (evidencia de runner cloud)
- `docs/ai_coordination/ESTADO_TESTS_LLM_Y_CAP5_2026-06-24.md` — leído

---

## 3. Evidencia encontrada — clasificación por acoplamiento real

### CATEGORÍA 1: IA ACTIVA DE NEGOCIO (acoplada a flujos clínicos y transaccionales)

Estos archivos se llaman directamente desde vistas o servicios que operan sobre datos reales de pacientes, ventas u órdenes. Si fallan, el flujo de negocio falla.

| Archivo | Acoplamiento real | Riesgo si falla |
|---------|------------------|-----------------|
| `core/utils/gemini_client.py` | Llamado desde `pris_ia.py`, `ia/views.py`, `core/views/cerebro.py` | Toda la superficie IA frontend cae |
| `core/utils/deepseek_client.py` | Fallback de `gemini_client` — mismo acoplamiento | Fallback inoperativo |
| `core/services/ia_clinical_governance.py` | Llamado desde `pris_ia.py:605` para generar borradores de resultado clínico | Resultados de lab sin borrador IA |
| `core/services/ocr_documental.py` | Llamado desde `pris_ia.py:1056` en flujo de análisis de documentos | OCR desactivado silenciosamente |
| `core/utils/rag_engine.py` (`consultar_cerebro`) | Llamado desde `cerebro.py`, `capacitacion_rag.py`, `pris_ia.py:1493` | Cerebro/RAG cae en esas 3 rutas |
| `core/utils/ia_output_sanitize.py` | Llamado desde `pris_ia.py:1232` antes de devolver respuesta al usuario | Respuestas IA sin sanear |
| `core/utils/ia_resources.py` | Referenciado en superficie IA — clasificar por acoplamiento a flujos clínicos (pendiente verificación profunda) | PENDIENTE_VALIDAR |
| `core/services/validador_ia.py` | Acoplado a flujos clínicos según ground truth de la tarea — **no mover a soporte sin verificar** | PENDIENTE_VALIDAR |

### CATEGORÍA 2: IA DE SOPORTE / OPERACIÓN (acoplada a operaciones internas, no a flujos de paciente)

| Archivo | Función real |
|---------|-------------|
| `core/agent/pris_agent.py` | Importado desde `core/middleware/pris_context.py` — se inyecta en el contexto de request, no en flujo clínico directo |
| `core/agent/pris_tools_operativos.py` | Herramientas del agente: `tool_buscar_o_crear_paciente`, `tool_cambiar_estado_orden`, `tool_registrar_venta_farmacia` — acoplado a operaciones pero mediado por el agente |
| `core/views/pris_ia.py` | Vista principal IA — expone todas las funciones IA al frontend. Es el punto de entrada, no el acoplamiento interno |
| `core/views/ai_brain.py` | Delega a `core/ai_brain.responder` — soporte de conversación |
| `core/views/cerebro.py` | Consulta RAG por pregunta — soporte de conocimiento |
| `core/views/capacitacion_rag.py` | Ingestión y consulta de documentos PDF para capacitación |
| `core/services/ai_medico.py` | Servicio médico IA — profundizar acoplamiento (¿llamado desde consultorio?) — PENDIENTE_VALIDAR |
| `core/services/interpretacion_ia.py` | Interpretación de resultados — probable soporte a lab, no negocio directo — PENDIENTE_VALIDAR |
| `core/services/voice_service.py` | Servicio de voz — soporte a `consultorio/api/procesar_audio.py` |
| `core/utils/ia_cache.py` | Cache de respuestas IA — infraestructura |
| `core/utils/ia_permissions.py` | Control de acceso a funciones IA por empresa/rol |
| `supervisor_ia_revisar_ventas.py` (management command) | Lee ventas del día anterior, detecta anomalías de descuento — **usa lógica de negocio pero no LLM directamente** — soporte operativo |

### CATEGORÍA 3: TESTS Y COMANDOS DE PRUEBA

Separados en dos subcategorías:

**3a — Tests que validan comportamiento IA real (conservar en suite):**

| Archivo | Qué prueba |
|---------|-----------|
| `core/tests/test_ai_provider_views.py` | Endpoints de provider IA |
| `core/tests/test_ai_provider_deepseek.py` | Cliente DeepSeek |
| `core/tests/test_prisci_unified_ai.py` | IA unificada PRISCI |
| `core/tests/test_pris_tools_operativos_security.py` | Seguridad de las tools del agente |
| `core/tests/test_buscar_o_crear_paciente_confirmation.py` | Tool específica del agente |
| `core/tests/test_ia_ethics_p18.py` | Ética IA / restricciones |

Estado: **30 tests LLM no corridos** (ver ESTADO_TESTS_LLM_Y_CAP5_2026-06-24.md) — deuda de verificación, no bug nuevo.

**3b — Comandos de smoke / conexión (no producción):**

| Comando | Clasificación |
|---------|--------------|
| `test_gemini_connection.py` | SMOKE — solo verifica que la API responde |
| `test_gemini_v1.py` | SMOKE — versión anterior del smoke |
| `test_pris_vida.py` | SMOKE — verificación de vida del sistema |
| `auditoria_ia.py` | HERRAMIENTA — audita configuración de IA en el árbol (no runtime) |
| `generar_auditoria_gemini.py` | HERRAMIENTA — genera paquete de auditoría anonimizado para Gemini externo |
| `auditoria_gemini_prime.py` | HERRAMIENTA — variante de auditoría con Gemini |

### CATEGORÍA 4: LEGADO / RUIDO

| Archivo / Grupo | Por qué es legado o ruido |
|----------------|--------------------------|
| `ia/views.py` + `ia/models.py` — app `ia/` completa | La app `ia/` importa desde `gemini_client` pero no tiene management commands ni services propios. Sus vistas (OCR, voz, receta, asistente) duplican funcionalidad ya en `core/views/pris_ia.py`. Probable app legada que no fue eliminada al unificar en `pris_ia.py`. **PENDIENTE_VALIDAR con diff — no cerrar como legado sin verificar si sigue siendo llamada desde URLs activas.** |
| `core/ai_brain.py` (raíz del app, no el view) | Referenciado solo desde `ai_brain.py` view — verificar si es wrapper de `pris_ia` o tiene lógica propia |
| `scripts_legacy/` — referencias a IA | Ningún script legacy llama a IA directamente — ruido documental únicamente |
| MDs de diagnóstico IA (abril 2026) en raíz | `LABORATORIO_INTELIGENTE_MANOS_LIBRES_COMPLETADO_01FEB2026.md`, etc. — histórico, no operativos |

---

## 4. Riesgos reales si alguna IA falla

| Componente | Modo de fallo | Impacto en producción |
|-----------|--------------|----------------------|
| `gemini_client.generate_content` | API key inválida o modelo deprecado | Toda la superficie IA devuelve error — tiene fallback a DeepSeek si está configurado |
| `ia_clinical_governance` | Si falla, borrador de resultado clínico no se genera | Captador de lab no puede usar sugerencia IA — flujo continúa manualmente |
| `ocr_documental` | Fallo silencioso (ver `pris_ia.py:1056`) | OCR no disponible — usuario no ve error claro |
| `rag_engine.consultar_cerebro` | Fallo en 3 puntos de entrada | Cerebro, capacitación RAG y una ruta de pris_ia quedan sin respuesta |
| `pris_agent` + `pris_context middleware` | Si el import falla, el middleware rompe cada request | **CRÍTICO** — afecta todo el sistema, no solo IA |

---

## 5. Qué quedó cerrado

- Clasificación de `gemini_client.py` y `deepseek_client.py` como **capa de infraestructura IA activa** con fallback entre proveedores.
- `test_gemini_connection`, `test_gemini_v1`, `test_pris_vida` clasificados como **smoke de conexión**, no como tests de regresión.
- `generar_auditoria_gemini` y `auditoria_ia` clasificados como **herramientas de soporte**, no como runtime.
- `supervisor_ia_revisar_ventas` clasificado como **soporte operativo** sin dependencia de LLM directo.

---

## 6. Qué quedó pendiente

1. **`core/services/validador_ia.py`** — ground truth dice que está acoplado a flujos clínicos. Necesita lectura directa para confirmar si es categoría 1 o 2.
2. **`core/services/ai_medico.py`** — ¿llamado desde `consultorio/views.py`? No verificado.
3. **`core/services/interpretacion_ia.py`** — ¿acoplado a lab o solo soporte? No verificado.
4. **`ia/views.py` app completa** — ¿sigue siendo llamada desde `config/urls.py`? Si sí, no es legado. Verificar URLs activas.
5. **`core/ai_brain.py`** — ¿wrapper de pris_ia o lógica propia?
6. **30 tests LLM** — deuda de verificación abierta (ver ESTADO_TESTS_LLM_Y_CAP5_2026-06-24.md).
7. **CAP-05** — agente hace 6 rondas LLM en lugar de 3, deuda estructural abierta.

---

## 7. Qué debe revisar Claude

- Verificar desde las **salidas de runner** (`tools/local__ui_omni.json`, `tools/cloud__ui_omni.json`) si las rutas de `ia/views.py` aparecen en el mapa de URLs auditado o no. Si no aparecen, confirma que es legado.
- Verificar si `tools/last_suite_human_summary.json` (`findingsCount: 0`, cloud, `auditoria_ui_20260623_212952`) incluye rutas IA en el scope auditado.
- Buscar evidencia de ejecución real de `ocr_documental` y `ia_clinical_governance` en las salidas de runner.

---

## 8. Qué debe integrar Codex al canon oficial

Solo después de que Claude confirme y el usuario autorice:

1. Mover `ia/` app completa a `LEGADO` en el inventario maestro si Claude confirma que sus URLs no están activas.
2. Agregar nota de riesgo al inventario sobre `pris_agent` en middleware — import crítico que afecta todo el sistema si falla.
3. Separar en el inventario los 6 comandos de smoke/herramienta IA de los comandos operativos.
