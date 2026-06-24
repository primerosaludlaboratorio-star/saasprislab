# DOCUMENTO MAESTRO — Claude · Auditoría ejecutora de superficie IA/LLM

**Agente:** Claude (ejecutor + contrapeso) · **Fecha/verificación:** 2026-06-24
**Modo:** ejecución y revalidación sobre código real (app booteada localmente), no lectura ni memoria.
**Par:** Cascada (clasifica la misma superficie). Este documento es para cruzarse con el suyo.

---

## 1. Objetivo
Auditar de forma ejecutora la superficie IA/LLM real de PRISLAB: localizar proveedor real, agente, servicios y endpoints; verificar permisos/tenant/fail-safe **rastreando el código de ejecución** (no asumiendo); aplicar cambios donde haya bug confirmado.

## 2. Alcance
Agente PRIS-JARVIS, servicios IA clínicos, endpoints `ia/`, motor de interpretación y validación IA, y el cableado RBAC del agente. **No** incluye la clasificación canon/archiva (carril de Cascada) ni el flujo PDV (PENDIENTE_VALIDAR aparte).

## 3. Archivos revisados (con evidencia rastreada)
- `core/agent/pris_agent.py` (173) — escudo RBAC `can_execute_tool`, contexto, orquestador.
- `core/agent/pris_tools_operativos.py` (1387) — `TOOLS_OPERATIVOS` (1304) y tools mutadoras.
- `core/views/pris_ia.py` — `_ejecutar_herramienta` (414), `_verificar_rbac` (371), `_TOOL_RBAC` (308), `_SUPERUSER_ONLY_TOOLS` (345).
- `core/services/interpretacion_ia.py` (120), `ia_clinical_governance.py` (17), `validador_ia.py` (287).
- `ia/views.py` (680) — endpoints asistente/síntomas/interacciones/OCR.
- `config/settings.py` (selección de proveedor), `core/utils/gemini_client.py`.

## 4. Evidencia encontrada (verificada, incluye hipótesis descartadas)
- **Proveedor real:** Gemini/Google es el motor de negocio (`gemini` en 47 archivos; `AI_PROVIDER` orden GOOGLE→DEEPSEEK en `settings.py:13`). DeepSeek = fallback. `openai/cohere/ollama/claude` = single-digit (periféricos/legado → para Cascada).
- **RBAC del agente: CORRECTO (verificado).** El entry point real `_ejecutar_herramienta` llama `_verificar_rbac` (pris_ia.py:414) **antes** de ejecutar; `_TOOL_RBAC` (308) gatea cada tool mutadora por rol (p.ej. `gestionar_usuario → [DIRECTOR, ADMIN, Administrador, GERENCIA]` :342; `cobrar_orden`, `cambiar_estado_orden`, etc. con listas correctas). Tools de consulta = `None` (solo login).
- **Tenant scoping: CORRECTO (muestreo).** `tool_consultar_indicadores_kpi` filtra `empresa=` (1129/1141/1151/1159); `_tool_buscar_paciente` filtra `empresa` (489). No se halló fuga en lo muestreado.
- **Fail-safe:** `interpretacion_ia.generar_resumen_bienestar` envuelve todo en try/except → `None` ante error (120). `gemini_client` cae GOOGLE↔DEEPSEEK y falla-cerrado sin key.
- **Hipótesis DESCARTADAS por verificación (transparencia):**
  1. "`api_consultar_asistente` sin auth" → **FALSO**: tiene `@login_required @require_http_methods(["POST"])` (ia/views.py:332-333).
  2. "RBAC del agente roto por `grupos:[]`" → **FALSO**: ese `"grupos"` en `TOOLS_OPERATIVOS` es capa secundaria/muerta; la primaria `_TOOL_RBAC` sí gatea. No es explotable hoy.

## 5. Cambios aplicados
- **`validador_ia.py` (commit local `8df3782`)** — corregido `select_related('parametro')`→`'analito'` y `resultado.parametro`→`resultado.analito` (campo inexistente; FieldError que dejaba **muerta** la validación IA pre-finalización de laboratorio). Verificado por ejecución (la validación corre sin error). *Este es un cambio real en la superficie IA, ya aplicado.*

## 6. Riesgos detectados (verificados, no aplicados aún)
| ID | Riesgo | Evidencia | Clase | Sev |
|----|--------|-----------|-------|-----|
| IA-1 | **Escalada de privilegio en `gestionar_usuario`**: CREAR fija `rol=rol` desde args sin verificar que el rol creado no exceda el del solicitante. Un `GERENCIA` (permitido por `_TOOL_RBAC`) podría crear un `ADMIN`. | pris_tools_operativos.py:1259-1267 + _TOOL_RBAC:342 | permisos | MEDIA |
| IA-2 | **Doble mecanismo RBAC inconsistente (footgun latente)**: `pris_agent.can_execute_tool` lee `required_groups`/`permission`; `TOOLS_OPERATIVOS` declara `grupos` (clave distinta, vacía). Hoy no explota porque el path vivo es `_verificar_rbac`, pero si alguien re-cablea por `PrisAgent`, el gate quedaría abierto. | pris_agent.py:60-69 vs pris_tools_operativos.py:1308-1386 | permisos/code | MEDIA |
| IA-3 | **"Gobernanza clínica" sobrevendida**: `ia_clinical_governance.py` es un helper de 17 líneas (constante `IA_BORRADOR` + defaults `validado=False`), no un motor de gobernanza. El human-in-the-loop real es solo ese default. | ia_clinical_governance.py:1-17 | doc/canon | BAJA |
| IA-4 | **Superficie de prompt-injection** en `interpretacion_ia`: nombre de paciente y analitos se interpolan al prompt. Salida es informativa-only (bajo impacto), pero real. | interpretacion_ia.py:82,89,91-99 | seguridad IA | BAJA |

## 7. Qué quedó cerrado
- Proveedor real identificado (Gemini primario, DeepSeek fallback) — **cerrado**.
- RBAC del agente **verificado como funcional** (no hay hueco explotable) — **cerrado**.
- `validador_ia` FieldError — **corregido y verificado**.

## 8. Qué quedó pendiente
- IA-1 a IA-4 sin aplicar (decisión de taxonomía de roles / refactor → cross-check antes de tocar).
- Tenant scoping del 100% de las ~33 queries del agente (muestreé las críticas; falta barrido completo).
- Endpoints `ia/` OCR/audio (`procesar_receta_ocr`, `transcribir_audio`) no ejecutados en vivo.

## 9. Qué debe revisar el OTRO agente (Cascada)
- Clasificar canon vs archiva de la superficie IA: `ia/` app, `core/agent/*`, `core/services/*ia*`, comandos `auditoria_ia`/`auditoria_gemini_prime`.
- Decidir destino de los proveedores periféricos (`openai/cohere/ollama/claude` single-digit): ¿legado/experimento → archiva?
- **Contraste explícito:** validar mis 2 hipótesis descartadas (api_consultar_asistente con auth; RBAC no roto). Si Cascada encuentra evidencia contraria, marcamos **contradicción** y no se cierra.

## 10. Qué debe integrar Codex al canon oficial
- Promover el fix `validador_ia` (commit `8df3782`) cuando se autorice persistencia.
- Decidir e implementar IA-1 (guard de escalada de rol) e IA-2 (consolidar a un solo mecanismo RBAC; eliminar `grupos` muerto o alinear claves).
- Renombrar/documentar IA-3 para no sobrevender "gobernanza".

---

### Nota de método
Cada afirmación se rastreó hasta `archivo:línea` en el árbol real, con la app booteada localmente. Donde una sospecha no se confirmó, se documentó como **descartada** en vez de reportarla como hallazgo. Reproducible.
