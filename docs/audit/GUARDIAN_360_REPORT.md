# Informe de conformidad — GUARDIÁN 360 v5.3

**Versión documento:** 1.0  
**Fecha referencia:** 2026-04-04  
**Base normativa:** `DOCS_AUDIT_MAESTRO.md` §9.2, bloque §9.1 (desviación de esquema controlada).

Este informe consolida el estado de los **9 ángulos** con evidencia **en código y rutas** verificables en el repositorio. La columna **Conformidad** distingue evidencia estática (revisión de código) de prueba en producción (logs Cloud Run, queries en BD operativa).

---

## Resumen ejecutivo

| Ángulo | Tema | Conformidad | Severidad si falla |
| :---: | :--- | :--- | :--- |
| 1 | Paciente / expediente / LFPDPPP | **Condicional** | 🟠 |
| 2 | Laboratorio captura / idempotencia | **Conforme** (código) | 🟠 |
| 3 | Alertas operativas (“Nancy” / stock crítico) | **Condicional** | 🟠 |
| 4 | ISO — metrología en validación | **Conforme** (código) | 🔴 |
| 5 | Marketing / tracking / consentimiento | **Conforme** (código) | 🟠 |
| 6 | IoT / HL7 | **Condicional** | 🟠 |
| 7 | Bienestar / NOM-035 | **Pendiente evidencia** | 🟡 |
| 8 | Infra / migraciones / secretos | **Condicional** (§9.1) | 🟠 |
| 9 | CISO — War Room | **Conforme** (tests) | 🟠 |

**Leyenda:** *Conforme* = regla implementada y localizable en código; *Condicional* = requiere validación en entorno real o datos; *Pendiente* = sin revisión completa en esta iteración.

---

## Ángulo 1 — Paciente / expediente / LFPDPPP

| Campo | Contenido |
| :--- | :--- |
| **Validación UI** | Alta en recepción: checkbox obligatorio privacidad + tratamiento (`recepcion/templates/recepcion/registrar_paciente.html`). |
| **Validación lógica** | Sin `ConsentimientoInformado` con `acepta_privacidad` y `acepta_procesamiento`: **no** se generan enlaces WA masivos, **no** envío masivo por correo con resultados, **no** helper de email con pixel; PIN validación **no** dispara WA; herramienta PRIS IA rechaza con mensaje LFPDPPP. |
| **Validación forense** | Tabla `core_consentimientoinformado`; función `core.utils.lfpdppp_resultados.paciente_autorizado_canal_digital_resultados`. |
| **SLA** | N/A |
| **Severidad** | 🟠 si se omitiera el chequeo en un nuevo canal digital. |

**Evidencia:** `core/utils/lfpdppp_resultados.py`, `core/views/entrega_resultados.py`, `core/views/laboratorio.py` (`api_validar_pin`), `core/utils/marketing_tracking.py`, `core/views/pris_ia.py` (`_tool_notificar_resultados_whatsapp`).

---

## Ángulo 2 — Laboratorio / resultados / concurrencia

| Campo | Contenido |
| :--- | :--- |
| **Validación UI** | Captura industrial envía `equipo_id` en JSON (P2 UI). |
| **Validación lógica** | `api_guardar_resultados`: `select_for_update` sobre orden; si `validar` y orden ya `RESULTADOS_LISTOS`/`ENTREGADO` → **200** con `idempotente: true` (sin duplicar PDF/trazas). |
| **Validación forense** | Logs `api_guardar_resultados validar idempotente orden=…`. |
| **SLA** | Validación < operación clínica aceptable (no cuantificado aquí). |
| **Severidad** | 🟠 |

**Evidencia:** `core/views/laboratorio.py`.

---

## Ángulo 3 — Alertas operativas (stock crítico / “Nancy”)

| Campo | Contenido |
| :--- | :--- |
| **Validación UI** | War Room muestra anomalías de stock; módulo inventario con semáforos en listado de lotes. |
| **Validación lógica** | Cron `cron_check_stock_critico` (`core/views/cron_tasks.py`) recorre silos y puede crear `NotificacionDiscrepancia`; War Room agrega `_detectar_stock_critico`. |
| **Validación forense** | Logs Cloud Run del cron; registros en `NotificacionDiscrepancia`; respuesta JSON del endpoint cron. |
| **SLA** | Depende de programación Scheduler (p. ej. 07:00). |
| **Severidad** | 🟠 |

**Nota:** En documentación operativa se alude a roles de caja / gerencia; la evidencia técnica es el **cron + War Room**, no personas concretas en código.

**Reparación aplicada (2026-04-04):** el cron `cron_check_stock_critico` usa **`cantidad_actual`** y filtros por silo (`ACTIVO` en LAB; `cantidad_actual__gt=0` en consultorio/generales). Lógica centralizada en `inventario/services/critical_stock.py` con tests `inventario.tests.test_critical_stock`.

---

## Ángulo 4 — ISO — Metrología (bloqueo de firma)

| Campo | Contenido |
| :--- | :--- |
| **Validación UI** | Selector de equipo en captura; validación solo si `equipo_id` presente en JSON. |
| **Validación lógica** | `api_guardar_resultados`: con `accion=validar` y `equipo_id` informado, `evaluar_metrologia_equipo(equipo)`; si `nivel != 'ok'` → **JsonResponse 400**, `codigo: METROLOGIA_BLOQUEO`. `evaluar_metrologia_equipo` devuelve `hard` si calibración vencida más de **30** días (`laboratorio/services/metrologia_lab.py`). |
| **Validación forense** | Respuesta HTTP **400** + cuerpo JSON; logs de aplicación en captura. |
| **SLA** | Inmediato (sincrónico en request). |
| **Severidad** | 🔴 si falla el bloqueo. |

**Evidencia:** `core/views/laboratorio.py` (bloque `equipo_id` + metrología), `laboratorio/services/metrologia_lab.py`.

**Condición de prueba en laboratorio:** Enviar `validar` con `equipo_id` de un equipo con `fecha_vencimiento_calibracion` &lt; hoy − 30 días y comprobar **400** y mensaje de calibración vencida.

---

## Ángulo 5 — Marketing / comunicaciones

| Campo | Contenido |
| :--- | :--- |
| **Validación lógica** | Pixel `/marketing/api/track/` con token firmado; envío de email con pixel solo si LFPDPPP autoriza canal digital. |
| **Validación forense** | `marketing/views_tracking.py`; `marketing/tracking_signing.py` (`sign_track_token`). |
| **Severidad** | 🟠 |

---

## Ángulo 6 — IoT / HL7

| Campo | Contenido |
| :--- | :--- |
| **Validación lógica** | Receptor HL7 invoca misma `evaluar_metrologia_equipo` (coherencia con captura manual). **Punto 13 (2026-04-04):** para analitos `NUMERICO`/`CALCULO`, unidad OBX debe coincidir (normalizada) con `lims.Analito.unidades` si el catálogo declara unidad; valor por `Decimal`. Sin match de código → `ResultadoHL7Huerfano` + `NotificacionDiscrepancia` **HL7_MAPEO**. Unidad/valor inválidos → cuarentena + **HL7_CUARENTENA** (sin persistir `ResultadoParametro`). |
| **Evidencia** | `laboratorio/views/hl7_receptor.py`, `laboratorio/services/hl7_handshake.py`, `laboratorio.ResultadoHL7Huerfano`, `laboratorio.tests.test_hl7_handshake`. |
| **Severidad** | 🟠 (🟢 lógica en código; falta evidencia con analizador físico en staging) |

---

## Ángulo 7 — Bienestar / NOM-035

| Campo | Contenido |
| :--- | :--- |
| **Estado** | **Pendiente** de informe detallado en esta revisión (comando `purgar_datos_nom035` y campos en `bienestar` documentados en maestro §auditoría periférica). |

---

## Ángulo 8 — Infra / migraciones / secretos

| Campo | Contenido |
| :--- | :--- |
| **Validación lógica** | §9.1: **no** `core.0065` masivo hasta backup y plan; desviación de esquema **controlada**. **2026-04-04:** migraciones periféricas: `bienestar.0003`, `ia.0003`, `iot.0003`; **HL7:** `laboratorio.0013`, `inventario.0005` (tipos War Room). |
| **Comandos** | `python manage.py check_placeholder_resultados_lims` (`--fail` en CI). `migrate bienestar` → `migrate ia` → `migrate iot` (un app por comando). `migrate laboratorio` / `migrate inventario` para cola HL7. |
| **Severidad** | 🟠 |

---

## Ángulo 9 — CISO (War Room)

| Campo | Contenido |
| :--- | :--- |
| **Validación lógica** | Rol **RECEPCION** → **403** en `/director/war-room/` y API de anomalías; log `war_room acceso denegado (CISO)`. |
| **Evidencia automatizada** | `python manage.py test core.tests.test_guardian_v53` |
| **Severidad** | 🟠 |

**Evidencia:** `core/views/war_room.py`, `core/tests/test_guardian_v53.py`.

---

## Fase 2 Inventario (silos) — estado en esta revisión

| Requisito | Estado |
| :--- | :--- |
| **P2.1** CUARENTENA/VENCIDO no usables en consumo analítico automático | **Conforme:** FEFO en `inventario/signals.py` filtra `estado='ACTIVO'`. |
| **P2.1** Backend salida técnica / manipulación POST | **Reforzado:** rechazo explícito si lote `CUARENTENA`/`VENCIDO` o estado ≠ `ACTIVO` en `inventario/views.py` (`crear_salida_tecnica`). |
| **P2.1** Herramientas IA inventario | **Corregido:** consultas PRIS solo lotes **ACTIVOS**, campo **`cantidad_actual`**. |
| **P2.2** Trazabilidad consumo ↔ `orden_id` | **Conforme:** `SalidaAnaliticaLab` + `idempotency_key` en señal `post_save` `ResultadoParametro` validado. |

---

## Comandos de verificación (Día 1)

```powershell
python manage.py test core.tests.test_guardian_v53
python manage.py check
python manage.py check_placeholder_resultados_lims --fail
```

---

## Firma de revisión

| Rol | Acción |
| :--- | :--- |
| **Cursor / IA** | Generación de informe y parches asociados en repo. |
| **Responsable clínico / calidad** | Aprobar conformidad **en producción** tras ejecutar prueba Ángulo 4 con equipo real vencido y revisar logs del cron Ángulo 3. |

---

*Fin del informe GUARDIÁN 360 v5.3 (v1.0).*
