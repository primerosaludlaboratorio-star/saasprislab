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
  - **Causa raíz:** `lims/views/tenant_lims.py:empresa_lims` + resolución de `empresa_actual` por `EmpresaIdentityMiddleware` para superusers. **NO parcheado** (root-cause de tenant requiere traza completa; un fix a medias es peligroso). → **Codex/LIMS**, prioridad alta. Clase: SEGURIDAD/PERMISOS.
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

*(Documento vivo: cada nueva auditoría de Claude se añade aquí, no en archivos sueltos.)*
