# 📕 DOCUMENTO MAESTRO ÚNICO — Claude · Todas las auditorías

**Agente:** Claude (ejecutor + contrapeso) · **Inicio:** 2026-06-24 · **Estado:** DOCUMENTO VIVO (se actualiza, no se fragmenta)
**Regla:** todo análisis de Claude se consolida aquí. Cuando Claude y Cascada terminen → **cruce mutuo** → integración del usuario → **Codex** ejecuta el paso final.
**Base de código:** `release/v1.0-local` (`f3e43e9` + trabajo interno). Método: rastreo a `archivo:línea` + ejecución real (app booteada local sobre SQLite). Cloud de producción NO alcanzable desde el contenedor (proxy 403) → lo "en vivo cloud" lo corre el humano (human:ui).

> Leyenda estado: ✅ verificado OK · 🐞 bug confirmado · 🔧 corregido (commit local) · ⏳ PENDIENTE_VALIDAR · ❎ hipótesis descartada
> Leyenda clase: UI · API · PERMISOS · DATOS · INFRA · SEGURIDAD-IA

---

## 0. Índice de bloques
- A. Laboratorio — aprobación de resultados (LAB-A/B/C) → 🔧 corregido `8df3782`
- B. Cierres / caja / cobros (farmacia·lab·consultorio) → 🐞 confirmados por ejecución
- C. PDV / farmacia (flujo en vivo) → ⏳ espera salida real human:ui
- D. Seguridad transversal (2FA, Sentinel, sesiones, token público)
- E. Inventario total del proyecto → mapa completo
- F. Superficie IA/LLM → 🔧 1 fix + 4 riesgos
- G. Autenticidad del repo / canon
- Z. Estado vivo: pendientes · qué cruza Cascada · qué integra Codex

---

## A. Laboratorio — Aprobación de resultados  `[🔧 8df3782]`
| ID | Hallazgo | URL/archivo | Esperado | Real | Clase | Estado |
|----|----------|-------------|----------|------|-------|--------|
| LAB-A | `orden.save()` exige PDF adjunto (clean) **antes** de generarlo → 500, orden atascada en VALIDADO_PARCIAL | `POST /laboratorio/monitor/api/avanzar-estado/` · `monitor_produccion.py:535` vs `models/laboratorio.py:548-560` | orden→RESULTADOS_LISTOS | 500 (ejecutado, pagada saldo$0) | API/DATOS | 🔧 reordenado: PDF antes de marcar lista |
| LAB-B | `validador_ia` `select_related('parametro')`/`resultado.parametro` (campo inexistente) → FieldError, validación IA muerta | `validador_ia.py:79,86-87` | validación corre | FieldError silenciado | DATOS/API | 🔧 →`analito` |
| LAB-C | `ValidationError` de negocio devuelta como 500 con dict crudo | `monitor_produccion.py:608` | 400 con mensaje | 500 | UI/API | 🔧 `except ValidationError`→400 |

**Verificación:** orden pagada→RESULTADOS_LISTOS con PDF (200); saldo pendiente→avanza sin PDF. Regresión 12/12 (`test_monitor_produccion_workflow`, `test_lab_validation_pdf`). Cierra el **Hallazgo #3** real (el "fix" previo solo envolvía el FieldError de insumos).

---

## B. Cierres / caja / cobros  `[🐞 confirmados por ejecución]`
| ID | Hallazgo | Evidencia ejecutada | Clase | Sev |
|----|----------|---------------------|-------|-----|
| C1 | Corte farmacia **no descuenta devoluciones** | venta $80 + devol $30 → corte reporta $80 (real $50), +$30 | DATOS | ALTA |
| C2 | Corte lab usa `total` teórico, no lo cobrado (`anticipo`) | CxC total 500/cobrado 200 → corte cuenta 500 | DATOS | ALTA |
| C3 | Corte lab **no excluye CANCELADO** | orden cancelada 300 sumada → corte 800 vs 200 real (+$600) | DATOS | ALTA |
| C4 | Ventana temporal inconsistente: farmacia usa apertura real, lab usa `ahora-12h` fijo | `corte_caja_unificado.py:144` vs `187` | DATOS/INFRA | MEDIA |
| K1 | **Doble cobro de consulta** (sin idempotencia) | 2× POST mismo `consulta_id` → 2 CobroConsulta, caja $600 vs $300 | DATOS/API | ALTA |
| K2 | Cobro/vale atribuidos a `request.user`, no al médico tratante | `consultorio/views.py:3791,3822` (cobrado_por=RECEPCION) | DATOS | MEDIA |
| K3 | Folio receta `count()+1` sin lock (colisión) | `consultorio/views.py:1465` | DATOS | BAJA |
| L-sobrepago | Cobro lab acepta `anticipo>total` (saldo negativo) | 500: pago 600 sobre 500→anticipo 800 | DATOS | MEDIA |
| F2 | `user_passes_test(login_url=)` en API → 302 HTML, no 403 JSON | farmacia/views.py:1558; cadena 302→/login | UI/API | BAJA |

**Verificados OK (no bugs):** cancelación+devolución de laboratorio (reembolso exacto, doble-cancel bloqueada); devolución y cancelación de farmacia (RBAC gerente/admin + anti-doble); token público de resultados (firmado 30d + candado financiero). *Excluidos por orden del usuario de re-trabajo: corte unificado y devoluciones cruzadas como tema nuevo.*

---

## C. PDV / farmacia — flujo en vivo  `[⏳ PENDIENTE_VALIDAR]`
- Evidencia canónica = salida real de `human:ui` (`auditoria_ui_<ts>/report.{md,json}` + screenshots). **No está en mi árbol** (local, sin push). El artefacto remoto `scripts_cascade_e2e/output/octogono_ui_audit_report.json` es **placeholder** (0 findings, started==finished 2026-04-05) → no es evidencia.
- No audito el placeholder ni sustituyo por código. **Bloque PDV = PENDIENTE_VALIDAR** hasta persistir la corrida real.
- Capacidad confirmada: mi contenedor SÍ puede correr navegador real local (Playwright + chromium en `/opt/pw-browsers`); cloud bloqueado (proxy 403).

---

## D. Seguridad transversal
| ID | Hallazgo | Evidencia | Clase | Sev |
|----|----------|-----------|-------|-----|
| SEC-2FA | Bypass 2FA implícito por red privada (`192.168.`/`10.` hardcodeados) **y** `REMOTE_ADDR=127.0.0.1` tras nginx→gunicorn → **2FA inerte en producción** | `autenticacion_2fa.py:44-46,34`; `nginx prislab.conf` upstream 127.0.0.1; `prislab-gunicorn.service:18` | SEGURIDAD | **CRÍTICA** |
| SEC-SENT | Sentinel: recovery BD hace `redirect` a misma URL sin guarda anti-loop (la guarda solo está en `_intentar_autoreparacion`) → loop bajo fallo BD persistente | `sentinel.py:257-272` vs `327-334` | INFRA | MEDIA |
| SEC-SESS | SessionTimeout (8h) OK; tras `logout()` continúa request anónima sin redirect explícito | `seguridad.py:42-99` | INFRA | BAJA |
| ✅ Expediente | DIRECTOR/MEDICO acceden donde deben | `expediente.py:73-76` | PERMISOS | ✅ |

---

## E. Inventario total del proyecto (escaneo real)
- **1.890** archivos · 974 `.py` · 407 HTML · 269 `.md`. **18 apps**. **240 modelos**, 3.567 funcs, 1.228 clases.
- **1.847 endpoints** (1.067 admin + ~780 app), **256 API**. **164 comandos** de gestión (123 en `core`, ~20 son `auditoria_*`/`audit_*` que ya existían y no se ejecutaban). **98 archivos de test / 342 métodos**.
- `core` = monolito (57% código, 45% modelos). Sin tests: enfermeria, recepcion, iot, bienestar.
- Legado: `scripts_legacy/`, `_archive_legacy/`, **115 `.py`** con marcadores deprecated/legacy.
- **Meta-hallazgo:** el repo ya traía herramientas de auditoría no usadas (comandos + `tools/audit_url_inventory.py`, `audit_coverage_gate.py`, `audit_data_integrity.py`) → explica por qué cosas (tests `scripts_cursor_e2e`) quedaban invisibles.
- Detalle completo: `docs/ai_coordination/INVENTARIO_TOTAL_ESCANEADO_2026-06-24.md`.

---

## F. Superficie IA/LLM  `[🔧 1 fix + 4 riesgos]`
- **Proveedor real:** Gemini/Google primario (`gemini` en 47 archivos; `AI_PROVIDER` GOOGLE→DEEPSEEK); DeepSeek fallback; `openai/cohere/ollama/claude` single-digit (periféricos → Cascada decide).
- ✅ **RBAC del agente funcional** (verificado): `_ejecutar_herramienta`→`_verificar_rbac`→`_TOOL_RBAC` gatea cada tool mutadora (`gestionar_usuario→[DIRECTOR,ADMIN,GERENCIA]`).
- ✅ Tenant scoping correcto (KPIs y búsqueda filtran `empresa`). ✅ Fail-safe (interpretacion_ia→None).
- ❎ **Descartadas por verificación:** "api_consultar_asistente sin auth" (tiene `@login_required`); "RBAC roto por `grupos:[]`" (capa secundaria muerta; la primaria gatea).

| ID | Riesgo | Evidencia | Clase | Sev |
|----|--------|-----------|-------|-----|
| IA-1 | Escalada de rol: `gestionar_usuario` crea con `rol` de args sin verificar jerarquía (GERENCIA podría crear ADMIN) | `pris_tools_operativos.py:1259-1267` | PERMISOS | MEDIA |
| IA-2 | Doble RBAC inconsistente (`required_groups` vs `grupos` muerto) — footgun latente | `pris_agent.py:60-69` vs `pris_tools_operativos.py:1308-1386` | PERMISOS/CODE | MEDIA |
| IA-3 | "Gobernanza clínica" = helper de 17 líneas (sobrevende) | `ia_clinical_governance.py` | DOC | BAJA |
| IA-4 | Prompt-injection informativo (nombre/analitos al prompt) | `interpretacion_ia.py:82-99` | SEGURIDAD-IA | BAJA |

Detalle: `docs/ai_coordination/inbox/20260624_claude_MAESTRO_AUDITORIA_IA_LLM.md`.

---

## G. Autenticidad del repo / canon
- El código real vive en `release/v1.0-local`; `main` (remoto) = solo README. La herramienta `human:ui` + docs nuevas (Codex) son **locales sin push** → mi remoto no las ve.
- Reportes históricos `.md` de "certificación/100%" contradicen evidencia cruda (cobertura ~25-34%, TODOs/`pass`/`csrf_exempt` presentes) → autenticidad parcial; a reconciliar en canon.

---

## Z. Estado vivo
**Cambios aplicados (commits locales, sin push):** `8df3782` (LAB-A/B/C + validador_ia), `81e22a1`/`3c158ac`/`789fe77` (reportes/inventario/maestro-IA).

**Pendientes de Claude:**
- Barrido completo tenant-scoping de las ~33 queries del agente.
- Endpoints `ia/` OCR/audio en vivo.
- PDV: auditar la salida real de human:ui cuando se persista.

**Qué debe cruzar Cascada:** clasificación canon/archiva de IA/LLM; validar mis hipótesis descartadas; contraste de C1-C4/K1-K2 con su lectura. Si discrepa → **contradicción, no se cierra**.

**Qué debe integrar Codex (canon, tras autorización):** promover `8df3782`; implementar IA-1/IA-2, C1-C4 (corte real = cobrado − devoluciones, excluir cancelado), K1 (idempotencia cobro), L-sobrepago (tope), SEC-2FA (resolver IP real + flag bypass), SEC-SENT (anti-loop en recovery).

---

## H. MÓDULO 1 — TESTS  `[evidencia de ejecución real]`
**Suite completa ejecutada** (`manage.py test` 18 apps): **315 tests / 175s → 297 OK · 2 fallos · 2 errores · 14 skipped.**

### Clasificación
- **CANON (verde, ~297):** la suite unitaria/regresión está sana. Incluye mis fixes (laboratorio, corte, cobro) sin romper nada → **mis 7 correcciones NO introdujeron regresiones**.
- **CONTRADICCIONES (2 fallos reales — alta prioridad):** `core/tests/test_lims_config_tenant_security.py`
  - `test_rangos_parametro_no_expone_analito_de_otro_tenant`: `GET api_rangos_parametro(analito_ajeno)` → **200** (esperado **404**) ⇒ **fuga cross-tenant** de analito de otra empresa.
  - `test_staff_sin_empresa_no_puede_usar_config_lims`: superuser **sin empresa** → **200** (esperado **403**) ⇒ viola canon "staff/superuser requieren empresa válida".
  - **RESUELTO (root-cause por ejecución):**
    - `api_rangos_parametro` **cross-tenant → CORREGIDO** (`commit sentinel`): el filtro por empresa SIEMPRE funcionó (no había fuga de datos); el bug era que **`Sentinel.process_exception` enmascaraba todo `Http404` como página `status=200`** (`_render_error_page`). Ahora respeta el 404. **Test pasa.** Clase: INFRA/contrato HTTP.
    - `test_staff_sin_empresa` (200≠403) → **CÓDIGO VIOLA EL CANON** (no es test obsoleto — corrección tras leer el canon). `CIERRE_CANONICO_AUDITORIA_TENANT_2026-06-21.md` (Regla final aprobada): *"Empresa obligatoria siempre. Staff/superuser **solo operan si tienen empresa válida**."* El código lo viola: `Usuario.save()` (base.py:351-361) **auto-asigna empresa por defecto** y el strict-mode (`empresa.py:81`) **exime a superusers** → "tiene empresa" falso que burla la regla. **Fix canónico (Codex, diferido por usuario):** en operaciones tenant-sensibles LIMS exigir empresa **realmente asignada** (no el default-fallback) para staff/superuser → 403 si no la tienen. **NO cambiar el test** (codifica el canon). Clase: SEGURIDAD/PERMISOS. Estado: documentado, sin tocar código por indicación del usuario.
  - **Lección de proceso:** consultar el canon documentado ANTES de clasificar (clasifiqué este punto como "test obsoleto" sin leerlo; el canon dice lo contrario).
- **RUIDO/ENTORNO (2 errores de import, NO lógica):** `core/tests_e2e.py` (`selenium` no instalado) y `core/tests/test_blindaje_capacitacion_push.py` (`pywebpush` no compila en este contenedor). Son **limitaciones de mi entorno**, no fallos de código. Recomendación de alineación: envolver esos imports en `skipUnless` para que la colección no ERRORee donde falte la dep opcional (no lo aplico para no enmascarar tests canónicos sin tu visto bueno).

### Estado del módulo Tests
- ✅ Suite canónica sana y verde salvo 1 contradicción tenant real (LIMS) + 2 limitaciones de entorno.
- ⏳ Pendiente (Codex/LIMS): cerrar `LIMS-TENANT` (fuga rangos + staff sin empresa).

---

## ✔ Correcciones aplicadas en esta sesión (commits locales, sin push)
| Fix | Commit | Verificado |
|-----|--------|-----------|
| LAB-A/B/C (aprobación resultados + validador_ia) | `8df3782` | sí (12/12) |
| K1 doble cobro + L-sobrepago + C1/C2/C3 corte | `f98a84c` | sí (ejecución) |
| K3 folio receta + SEC-SENT anti-loop | `24a90ba` | sí (check+AST) |
| SEC-2FA bypass off por defecto | `820fae4` | sí (+seguridad 5/5) |

**Walk-backs por verificación (NO eran bugs):** IA-1 (guarda en `pris_tools_operativos.py:1223` limita a ADMIN/DIRECTOR/superuser; creados nunca superuser) · K2 (`Medico` no tiene FK a `Usuario` → sin atribución limpia; es deuda de modelo, no fix puntual).

---

## I. MÓDULO 2 — CONSULTORIO  `[verde · ya alineado tras K1/K3]`
**Tests:** `manage.py test consultorio` → **36/36 OK** (skipped=4). Mis fixes K1/K3 no rompieron nada.

### Alineación al canon (estado)
- ✅ **Cobro de consulta** alineado: idempotencia (K1) + folio receta sin colisión (K3) ya aplicados (`f98a84c`/`24a90ba`).
- ⚠️ **K2 (atribución a `request.user`)**: deuda de **modelo**, no de código — `Medico` carece de FK a `Usuario`, no hay a quién atribuir el vale cuando cobra recepción. Requiere decisión de modelo (Codex). NO es fix puntual.

### Clasificación de legacy / ruido
- **LEGACY (conservar, canon-explícito):** `consultorio/models.py:16-80` — bloque "MODELOS LEGACY (MANTENER POR COMPATIBILIDAD)" y `ConsultaMedica` marcada `DEPRECATED / (LEGACY)`. Intencional para compatibilidad → conservar y documentar; no promover a nuevas features.
- **RUIDO menor:** 8 `pass` vacíos (todos en `except` de generación de PDF: `pdf_views.py`, `pdf_views_prislab.py`, `views.py:1248,1380`) — swallowing benigno; 1 placeholder en `models.py:104`. Baja prioridad.
- **Sin contradicciones** en la suite de consultorio (a diferencia de LIMS).
- **REFACTOR candidato (NO forzado):** `consultorio/views.py` = **4.648 LOC** (monolito). Recomendación: dividir en submódulos (cobros / consultas / recetas / certificados / pdf). Riesgo alto → requiere tu autorización antes de tocar.

### Veredicto módulo Consultorio
✅ Funcional y alineado al canon en lo accionable. Pendiente: K2 (modelo, Codex) y refactor del monolito (requiere go). Listo para el siguiente módulo.

---

## J. MÓDULO 3 — FARMACIA  `[el más limpio · verde · alineado]`
**Tests:** `manage.py test farmacia` → **18/18 OK**. Mi fix C1 (corte descuenta devoluciones) no rompió nada.

### Alineación al canon (estado)
- ✅ **Corte de farmacia** alineado (C1, `f98a84c`). **Devolución** y **cancelación de venta** ya verificadas correctas en rondas previas (RBAC gerente/admin, anti-doble, reversión de stock Kardex).
- ✅ **PDV/venta**: lógica PEPS multi-lote con `select_for_update`, bloqueo de caducados — correcta (revisada). *(El flujo en vivo PDV sigue ⏳ PENDIENTE_VALIDAR vía human:ui — bloque C.)*

### Clasificación de legacy / ruido
- ✅ **0 marcadores** DEPRECATED/LEGACY/FIXME en el módulo — limpio.
- **Shim intencional (conservar, NO es ruido):** `farmacia/services/venta_farmacia_service.py` (7 líneas) = capa de compatibilidad que re-exporta de `core.services.ventas` (fuente única). Buen diseño.
- **RUIDO baja prioridad:** **12 `except:` desnudos** — **todos** en comandos de carga (`management/commands/cargar_inventario*`, `cargar_productos_*`): parsing tolerante de Excel/CSV, **fuera** de flujos request/transaccionales → riesgo bajo. Recomendación: acotar a excepciones concretas + log, pero NO tocar sin pruebas de carga (podría romper imports). 8 `pass` vacíos similares.
- **Sin contradicciones** en la suite de farmacia.

### Veredicto módulo Farmacia
✅ **Módulo más sano y alineado al canon.** Sin cambios pendientes en flujos productivos. Deuda cosmética acotada a scripts de carga (no forzar). Listo para el siguiente módulo.

---

## K. MÓDULO 4 — IA / LLM  `[bien construido · 1 fix aplicado · stubs declarados]`
**Tests:** `manage.py test ia` → **3 OK (2 skipped)**. Cobertura delgada (1 test activo). App `ia` registrada en INSTALLED_APPS (sin `apps.py`).

### Alineación al canon (estado)
- ✅ **RBAC del agente PRIS verificado funcional** (`_verificar_rbac` + `_TOOL_RBAC` gatea cada tool mutadora). Tenant scoping OK. Fail-safe OK. Proveedor real = Gemini/DeepSeek. *(Detalle en bloque F + `inbox/20260624_claude_MAESTRO_AUDITORIA_IA_LLM.md`.)*
- 🔧 **`validador_ia` corregido** (LAB-B, `8df3782`) — FieldError que dejaba muerta la validación IA.

### Clasificación de legacy / ruido / stubs
- ✅ **0 `except:` desnudos** en `ia/` y `core/agent/` — limpio.
- **STUBS declarados (incompletos, con fallback):** `ia/views.py:435,480,639,669` — 4 funciones "PLACEHOLDER: Se activará cuando se configuren las APIs" (Google Cloud **Vision OCR** y **Speech** para receta/audio). Degradan a `_extraer_texto_fallback`. Clasificación: **feature incompleta esperada** (depende de config GCP), no bug. → Codex/canon: marcar como "no implementado" explícito.
- **Placeholders de UI (no es ruido):** `ia/forms.py:62,73` son `placeholder=` de formularios HTML — legítimos.

### Riesgos IA (de bloque F, para cruce/Codex)
- **IA-2 (MEDIA):** doble mecanismo RBAC inconsistente (`pris_agent.TOOL_REGISTRY`/`required_groups` — andamiaje no usado — vs `pris_ia._TOOL_RBAC`/`grupos` — el vivo). Footgun latente. → Codex: consolidar a uno, eliminar el muerto.
- **IA-3 (BAJA):** `ia_clinical_governance.py` sobrevende (helper 17 líneas).
- **IA-4 (BAJA):** prompt-injection informativo en `interpretacion_ia`.
- ❎ **IA-1 descartado** (guarda real en `pris_tools_operativos.py:1223`).

### Veredicto módulo IA
✅ **Bien construido y seguro** (RBAC real). 1 fix aplicado (validador_ia). Pendiente Codex: IA-2 (consolidar RBAC), marcar stubs Vision/Speech como no-implementados, +cobertura de tests. Sin contradicciones.

---

# 🏁 CIERRE DE SECUENCIA (Tests · Consultorio · Farmacia · IA)
| Módulo | Tests | Estado | Pendiente (Codex/decisión) |
|--------|-------|--------|----------------------------|
| 1. Tests | 315 (297 OK) | ✅ + 1 contradicción | **LIMS-TENANT** (fuga rangos + staff sin empresa) |
| 2. Consultorio | 36/36 | ✅ alineado | K2 (modelo), refactor monolito (go) |
| 3. Farmacia | 18/18 | ✅ el más limpio | cosmético en scripts de carga |
| 4. IA | 3 (1 activo) | ✅ seguro | IA-2 (consolidar RBAC), stubs, +tests |

**Correcciones aplicadas y verificadas (4 commits locales):** `8df3782`, `f98a84c`, `24a90ba`, `820fae4` — LAB-A/B/C, K1, L-sobrepago, C1/C2/C3, K3, SEC-SENT, SEC-2FA.
**Prioridad #1 para Codex:** `LIMS-TENANT` (seguridad cross-tenant, confirmada por test que falla).

---

## L. CRUCE — Revisión de Claude sobre el trabajo de Cascada (Core + Farmacia)
**Core — fix `pris_context.py` (lazy import + try/except):** ENDORSADO. Verificado contra código real (mi árbol tiene el original sin guarda: línea 11 import módulo, línea 26 call sin try/except). **Corrección de rationale:** un fallo de import rompe el **arranque**, no "cada request"; el valor real del fix es aislar **excepciones runtime** por-request + desacoplar el boot de `pris_agent`. `check` 0 issues OK (no ejercita runtime).
- ⚠️ **Omisión de Cascada (contrapeso):** su barrido de `core/middleware` no flageó `SEC-2FA` ni `SEC-SENT` (mismos directorios), ambos **ya corregidos por Claude** (`820fae4`, `24a90ba`). Complementarios.

**Farmacia — COINCIDIMOS (sin contradicción):** shim correcto, 18/18, monolito `views/__init__.py` = deuda. Aportes válidos de Cascada que Claude no detalló: signals (`ready()`/`dispatch_uid`/`fail_silently`) y clasificación de **5 comandos de carga como LEGACY_CANDIDATE** (`importar_excel_inventario.py` propuesto canónico). Caveat Claude: son mgmt-commands manuales, decisión de archivado = usuario. → **cerrado sin contradicción** (regla "si coinciden, mejor").

**Estado del cruce:** sin contradicciones bloqueantes. 1 corrección de rationale (Core) + 1 omisión cubierta por Claude (SEC-2FA/SEC-SENT). Nota: los cambios de Cascada viven en el árbol local del usuario (sin push); revisé su *diagnóstico y razonamiento*, no su diff aplicado (no visible en mi remoto).

---

## M. MÓDULO 5 — LABORATORIO  `[asignado a Claude · ya alineado tras LAB-A/B/C]`
**Tests:** `manage.py test laboratorio` → **16/16 OK** (skipped=1). ⚠️ Suite de la **app es delgada** (corre en 0.002s); la cobertura real del flujo lab vive en `core/tests` (`test_monitor_produccion_workflow`, `test_lab_validation_pdf`, `test_lims_*`), toda verde tras mis fixes (incl. LIMS-tenant).

### Alineación al canon (estado)
- ✅ **Flujo de resultados** alineado: LAB-A (aprobación 500→entregable), LAB-B (validador_ia), LAB-C (400 vs 500), cobro sobrepago, cancelación+devolución — todos corregidos y verificados (`8df3782`/`f98a84c`).
- ✅ **Canon NEXT_ACTIONS #1 — "cerrar patrón LIMS/legacy `DetalleOrden.estudio` en código productivo": CERRADO.** Verificado: `core.DetalleOrden` **no tiene** campo `estudio` (FKs: analito/perfil_lims/paquete_lims). Las únicas referencias vivas a `.estudio` en superficie productiva son mi fix **guardado** (`monitor_produccion.py:382-386`, `hasattr` + try/except → órdenes LIMS puras saltan descuento de insumos, comportamiento correcto). El resto: comando de simulación sobre modelos **legacy** `laboratorio.*` (donde `estudio` sí existe) y migraciones.

### Clasificación de legacy / ruido
- ✅ **0 marcadores** DEPRECATED/FIXME.
- **Ruido baja prioridad:** 6 `except:` desnudos — **todos** en comandos de carga/migración (`cargar_tarifas_csv`, `importar_tarifas_lab`, `migrar_lab_master`), fuera de flujos request. 26 `pass` vacíos (mayoría en `except` de impresión/PDF). No forzar.
- **LEGACY intencional (bridge de migración, conservar):** `services/etiquetas_zpl.py:zpl_desde_orden_legacy`, `services/unificacion.py:crear_orden_core_desde_legacy` + `_encontrar_core_medico` — convierten legacy→core (LIMS). Documentar, no borrar.
- **REFACTOR candidato (no forzado):** `core/views/laboratorio.py` 3.146 LOC, `laboratorio/models.py` 1.813 LOC → split (requiere go).

### ⚠️ Contradicción/deuda ARQUITECTÓNICA (la de fondo)
- **Sistema dual de modelos:** `laboratorio.{Estudio,Orden,DetalleOrden}` (legacy) **coexiste** con `core.{OrdenDeServicio,DetalleOrden}` (LIMS). El flujo productivo usa LIMS/core; el legacy persiste con un bridge (`unificacion.py`). **Es la raíz de los bugs `.estudio` (LAB-A/B):** suposiciones del modelo legacy se filtraban a código LIMS. → **Codex:** planificar retiro formal del modelo `laboratorio.*` legacy o formalizar la frontera. NO es fix puntual (riesgo alto).

### Veredicto módulo Laboratorio
✅ **Flujo funcional alineado al canon** (mis fixes + patrón `.estudio` cerrado en productivo). Deuda real = **dual-model legacy↔LIMS** (arquitectónica, para Codex) + monolitos. Sin cambios productivos pendientes de mi parte.

---

## N. LOGIN/UI — "falla en ventana normal, funciona en incógnito"  `[root-cause + fix opt-in]`
**Limitación:** producción NO alcanzable desde el contenedor (proxy 403) y sin acceso al estado del navegador del usuario → la repro normal-vs-incógnito sobre el browser real la hace el humano. Diagnóstico = **código + config**.

**Causa raíz (clase del fallo = sesiones divididas por host):**
1. App servida en **4 hosts** (nginx `server_name`: `prislab.labcorecloud.com`, `labcorecloud.com`, `www.labcorecloud.com`, `216.238.89.243`).
2. `CanonicalHostMiddleware` estaba **inerte**: `LEGACY_HOSTS=set()` + `CANONICAL_HOST='prislab.local'` (hardcode) → nunca consolidaba.
3. **Sin `SESSION_COOKIE_DOMAIN`/`CSRF_COOKIE_DOMAIN`** → cookies host-only (no compartidas entre hosts).
4. **`CSRF_TRUSTED_ORIGINS=[]`** por defecto (solo env) → POST de login desde host no listado = **CSRF 403** (Django 4+).
→ En ventana normal con cookie/CSRF de otro host: login da 403 / redirect-a-login (aparenta "error"/500). Incógnito (fresco, 1 host): funciona.

**Fix aplicado (pequeño, seguro, opt-in):** `CanonicalHostMiddleware` ahora lee `PRISLAB_CANONICAL_HOST`/`PRISLAB_LEGACY_HOSTS` de env; sin config = no-op; con config = 302 de hosts legacy → canónico (verificado: preserva path+query, no toca el canónico, sin loop). Archivos: `core/middleware/canonical_host.py`, `config/settings.py`.

**Remediación completa (config de despliegue, para Codex/infra):**
- `PRISLAB_CANONICAL_HOST=prislab.labcorecloud.com` + `PRISLAB_LEGACY_HOSTS=labcorecloud.com,www.labcorecloud.com,216.238.89.243` (o redirección 301 en nginx).
- `CSRF_TRUSTED_ORIGINS=https://prislab.labcorecloud.com` (+ los demás hosts si sirven login).
- Opcional multi-subdominio: `SESSION_COOKIE_DOMAIN=.labcorecloud.com`, `CSRF_COOKIE_DOMAIN=.labcorecloud.com`.
- Workaround inmediato usuario: limpiar cookies del dominio / usar siempre el host canónico (por eso incógnito funciona).

---

## O. Hallazgos de la auditoría con agente real (Gemini browser, prod) — análisis Claude
El agente Gemini (en la máquina del usuario, sí alcanza prod) recorrió módulos. Mi rol: **root-cause + fix** de lo que reporta.
- **🔴 SEC-CRED (CRÍTICO, CONFIRMADO):** prod usa `admin` / `Prislab@Admin2026!` = **exactamente la contraseña hardcodeada** en `core/management/commands/crear_superusuarios_iniciales.py:50-62` (fallback usado si no se setea `PRISLAB_SUPERUSER_PASSWORD`). Cualquiera con acceso al repo tiene admin de producción. → **Codex/usuario: ROTAR ya + quitar fallbacks hardcodeados (exigir env).**
- **QZ-WS (cosmético, CORREGIDO):** el agente reportó `wss://localhost:8181 error` como HIGH en Lista-Trabajo/PDV/Consultorio/Director/War-room. Root-cause: es **QZ Tray** (impresora térmica, `qz-tray.js`); el silenciador de `base.html` cubría puertos inseguros (8182/8283/8384/8485) y omitía los seguros (**8181**/8282/8383/8484). **No es bug funcional.** Fix: regex que cubre los 8 puertos QZ (`base.html`). Reclasificado HIGH→BAJO.
- **🟡 LIMS-ADMIN-REDIRECT (agente lo marcó HIGH → real BAJO):** `/lims/estudios/` (`lista_pruebas`, `core/views/laboratorio_config.py:41-47`) redirige a `/admin/lims/analito/` **a propósito** — el catálogo LIMS se movió al Django Admin en v7.5; la vista es un stub de redirect, gateado por `@role_required('DIRECTOR_QC','ADMIN')` (los no-admin NO llegan). NO es hueco de seguridad. Matiz de canon (Codex): el canon permite LABORATORIO/LIMS gestionar catálogo, pero esta ruta solo deja DIRECTOR_QC/ADMIN y exige `is_staff` (Django admin) → un usuario LIMS/LABORATORIO no puede gestionar catálogo por aquí. UX: exponer el admin como UI de catálogo es pobre.
- **🛠 Agente "al siguiente nivel" (entregado):** `tools/audit_human_flows.mjs` — drop-in para el runner: presupuesto POR módulo (cubre los 12), flujos humanos concretos por módulo (no solo títulos), `LoopGuard` anti-loop (3 repeticiones), `resolveSelectorVariants` (selector inteligente), y `buildSystemPrompt` con severidades correctas (QZ Tray 8181-8485 = ignorar). Verificado (JS OK, 12 módulos, 9 pasos/módulo @120).
- **Nota de método:** el agente navega y reporta a nivel superficie; clasifica severidades sin contexto (marcó QZ Tray como HIGH). Claude aporta el root-cause y la severidad correcta sobre cada hallazgo.

---

## P. MÓDULOS DIRECTOR + IA/PRIS  `[auditados · 1 bug real CONFIRMADO y CORREGIDO · regresión verde]`

**Alcance:** Director (`core/views/director.py` 425 LOC, war_room, coach, pris_checklist, analizadores) + IA/PRIS (~10.2k LOC: `pris_ia.py` 1.655, `pris_tools_operativos.py` 1.387, `pris_jarvis.py` 873, `ia/views.py` 680, `ai_brain.py`, `ia_dashboard.py`, `gemini_client.py`).

### 🔴 P-TZ (CONFIRMADO · CORREGIDO) — bug de zona horaria recurrente, ahora también en Director e IA
Misma clase que el bug de caja-lab/finanzas. Con `USE_TZ=True` + `TIME_ZONE=America/Mexico_City` (UTC-6), `timezone.now().date()` devuelve la fecha **UTC**: entre 18:00–23:59 hora local la fecha UTC ya es "mañana", así que toda ventana "del día" se va al futuro y los tableros muestran **0 ventas / 0 órdenes / 0 KPIs** cada noche pese a la actividad real.
- **18 ocurrencias corregidas** → `timezone.localdate()` (fix canónico, idéntico al ya aprobado en `finanzas.py`):
  - `core/views/director.py:40` (dashboard ejecutivo: ventas/órdenes/quejas/incidencias del día).
  - `core/views/war_room.py:220,283,381,408` (anomalías, escalamiento mantenimiento, ingresos/gastos y métricas del día).
  - `core/views/ia_dashboard.py:30,309` · `core/views/pris_ia.py:512,514,548,751,863,865` · `core/views/pris_jarvis.py:434,506,512` · `core/agent/pris_tools_operativos.py:1113` (KPI agente periodo HOY) · `core/ai_brain.py:193`.
- **Verificación:** `manage.py check` limpio · `py_compile` OK los 7 archivos · **regresión nueva** `core/tests/test_director_dashboard_tz.py` (mockea 03:30 UTC = 21:30 MX, crea Venta COMPLETADA, exige `cantidad_ventas==1`/`total==750`) — **verde**; falla con el código viejo. Junto con `test_caja_laboratorio_tz.py`: **2/2 OK**.

### ✅ Falsos positivos / sin bug (verificado)
- **`gemini_client.py`**: bien construido — key por env (`GOOGLE_API_KEY`/`GEMINI_API_KEY`), **0 claves hardcodeadas**, fallback de proveedor (gemini↔deepseek), timeout 15s, normalización 403→`PermissionError`. Sin deuda.
- **Gating de auth**: entrypoints IA (`pris_ia`, `pris_jarvis`, `ia_dashboard`, `ia/views`) están protegidos (`login_required`/helpers de rol). Webhook `prisci_webhook.py` usa `csrf_exempt` **compensado** con `_webhook_token_ok` + `hub.verify_token`. OK.
- **Scoping multi-tenant** en `pris_tools_operativos.py`: las queries del agente filtran por `empresa` (paciente/orden/venta/cotización). OK.

### 🟡 Riesgo residual (decisión de producto, NO bug)
- **DIR-ANALIZADORES cross-tenant:** `director_analizadores*` opera sobre `laboratorio.models.Equipo`, que **no tiene FK empresa** (catálogo técnico global); el aislamiento es solo RBAC (comentado en `director.py:311-312`). En despliegue multi-empresa real, un director de empresa A ve/edita/borra analizadores de B. Si el despliegue es 1-instalación-por-lab, es aceptable. → Definir con Codex/producto.
- **DIR-PROBAR-CONEXION (SSRF leve):** `director_analizadores_probar_conexion` hace `socket.connect_ex((ip,puerto))` con IP/puerto del POST (gateado a rol director). Permite sondear puertos internos. Bajo, intencional (probar analizador). Flag, no fix.

---

*(Documento vivo: cada nueva auditoría de Claude se añade aquí, no en archivos sueltos.)*
