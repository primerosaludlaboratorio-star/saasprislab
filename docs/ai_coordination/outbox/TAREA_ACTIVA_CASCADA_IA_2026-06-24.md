# Tarea Activa para Cascada - Clasificacion de Superficie IA / LLM

Fecha: 2026-06-24

## Contexto

PRISLAB ya tiene evidencia clara de superficie IA/LLM real en el codigo. La siguiente fase no es reauditar todo el sistema, sino clasificar esa superficie para separar:

- IA activa de negocio
- IA de soporte / operacion
- tests y comandos de prueba
- legado / ruido

## Fuentes canonicas a leer antes de clasificar

- `PROTOCOLO_EJECUCION_PARALELA.md`
- `AI_COORDINATION_STATUS.md`
- `INDICE_CANONICO_TOTAL.md`
- `INVENTARIO_MAESTRO_TOTAL.md`
- `INVENTARIO_REAL_REPO.md`
- `ESTADO_TESTS_LLM_Y_CAP5_2026-06-24.md`
- `docs/ai_coordination/inbox/20260624_IA_GROUND_TRUTH_PRISLAB.md`

## Objetivo

Construir una clasificacion util de la superficie IA/LLM del repo, sin mezclarla con ruido documental ni con el core transaccional.

## Zona prioritaria asignada

Empieza por el nucleo IA real del runtime, no por tests ni por documentos:

### 1) Proveedores y gobernanza IA

- `core/utils/gemini_client.py`
- `core/utils/deepseek_client.py`
- `core/utils/ia_resources.py`
- `core/models/base.py` (BYOK Gemini por empresa)

### 2) Servicios IA acoplados al core

- `core/services/ai_medico.py`
- `core/services/interpretacion_ia.py`
- `core/services/ocr_documental.py`
- `core/services/validador_ia.py`
- `core/services/voice_service.py`
- `core/services/ia_clinical_governance.py`

### 3) Vistas que exponen IA al usuario

- `core/views/pris_ia.py`
- `core/views/ai_brain.py`
- `ia/views.py`
- `core/views/pris_checklist.py`
- `core/views/cerebro.py`

### 4) Superficie de soporte / tooling IA

- `core/agent/pris_agent.py`
- `core/agent/pris_tools_operativos.py`
- `core/utils/rag_engine.py`
- `core/management/commands/auditoria_ia.py`
- `core/management/commands/generar_auditoria_gemini.py`
- `core/management/commands/test_gemini_connection.py`

### 5) Tests y validadores relacionados

Solo despues de clasificar lo de arriba:

- `core/tests/test_ai_provider_views.py`
- `core/tests/test_ai_provider_deepseek.py`
- `core/tests/test_prisci_unified_ai.py`

## Area a clasificar

### IA / LLM activa en runtime

Identificar y separar:

- Gemini
- DeepSeek
- RAG
- OCR documental asistido
- voz / asistente
- validacion IA
- brain / assistant / checklist IA

## Ground truth obligatorio

Antes de clasificar, leer y respetar este hecho:

- `core/services/validador_ia.py` y `core/utils/ia_resources.py` estan acoplados a flujos clinicos y de negocio reales.
- No deben ir automaticamente a "soporte" ni a "legado" solo por ser IA.
- La clasificacion debe decidirse por acoplamiento real, no por nombre de archivo.

### Pruebas y comandos relacionados

Separar:

- tests de proveedor IA
- management commands de auditoria IA
- comandos de conexion / smoke
- harnesses que solo prueban APIs o prompts

### Legado / ruido

Marcar:

- referencias historicas que no operan en runtime
- reportes viejos sobre IA que solo documentan contexto
- scripts obsoletos o placeholders

## Reglas

- No usar memoria.
- No asumir que todo lo que menciona IA es criticidad operacional.
- No mezclar soporte con negocio.
- No reabrir hallazgos cerrados sin diff nuevo.
- Si algo solo aparece en documentación vieja, marcarlo como ruido o legado hasta probar lo contrario.

## Entregable esperado

Un reporte breve con:

1. Lista de superficies IA/LLM activas.
2. Lista de tests/comandos IA.
3. Lista de legacy/ruido.
4. Riesgos reales si alguna IA falla.
5. Recomendacion de que debe quedar canon y que debe archivarse.
