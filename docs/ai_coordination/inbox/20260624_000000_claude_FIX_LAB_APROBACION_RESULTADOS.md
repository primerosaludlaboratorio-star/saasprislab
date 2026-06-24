# REPORTE: Fix Laboratorio — Desbloqueo de Aprobación de Resultados (Hallazgo #3 real)

**Agente:** Claude
**Fecha:** 2026-06-24
**Tipo:** Cambio de código aplicado (pendiente de decisión de persistencia/deploy)
**Clasificación:** CONFIRMADO (reproducido y verificado por ejecución)
**Para:** Codex (documentar) / Cascada (clasificar) — DECIDIR persistencia

---

## 0. Estado de persistencia (DECISIÓN PENDIENTE DE CODEX/USUARIO)

- Cambios **commiteados localmente**: commit `8df3782` sobre `release/v1.0-local`.
- **NO se hizo push.** La rama designada `claude/audit-flow-review-ruhy0q` en remoto solo
  contiene el README del task (`5ba70c0`, ajeno a `release/v1.0-local`), por lo que escribir
  el fix exige `--force`. No se fuerza sin autorización.
- Codex decide: (a) force-push a la rama designada + PR base `release/v1.0-local`,
  (b) rama nueva basada en `release/v1.0-local`, o (c) re-aplicar el diff en su propio flujo.
- El diff completo está al final de este documento (sección 6).

---

## 1. Problema (auditoría funcional ejecutada)

**URL:** `POST /laboratorio/monitor/api/avanzar-estado/` (botón "Aprobar Resultados" del monitor).
**Paso:** orden **pagada** (saldo $0), `estado_clinico=VALIDADO_PARCIAL`, sin PDF adjunto → avanzar a COMPLETO.
**Esperado:** `estado_clinico=COMPLETO`, `estado=RESULTADOS_LISTOS`, orden entregable.
**Real (antes del fix):** **HTTP 500**; la orden quedaba **atascada en VALIDADO_PARCIAL**; no aparecía en
`/laboratorio/entrega-resultados/` ni en el portal público. Es el síntoma exacto del Hallazgo #3.

**Evidencia del 500 (capturada en ejecución):**
```
{'estado': ['No se puede marcar la orden como lista o entregada si el documento PDF de resultados no está adjunto.']}
```

---

## 2. Causa raíz

| ID | Archivo | Causa |
|----|---------|-------|
| LAB-A (crítico) | `core/views/monitor_produccion.py` | En la transición COMPLETO, `orden.save()` ejecuta `full_clean()`; `OrdenDeServicio.clean()` (`core/models/laboratorio.py:548-560`) exige `archivo_resultado` adjunto para `estado='RESULTADOS_LISTOS'` (salvo saldo pendiente). El PDF se generaba **DESPUÉS** de ese `save()` (orden de operaciones invertido) → el save fallaba → 500 → orden atascada. |
| LAB-B (bajo) | `core/services/validador_ia.py` | `select_related('parametro')` y `resultado.parametro` sobre `ResultadoParametro`, campo inexistente (FK real: `analito`). FieldError silenciado dejaba muerta la validación IA. |
| LAB-C (bajo) | `core/views/monitor_produccion.py` | Toda `ValidationError` de regla de negocio se devolvía como **HTTP 500** con el dict crudo, en vez de un 400 con mensaje claro. |

**Nota:** el "fix H3" previo (canon) solo envolvió el `FieldError` de `_descontar_insumos_orden` en try/except;
la transición seguía rota para órdenes pagadas. Este cambio cierra el bloqueador real.

---

## 3. Solución aplicada

### LAB-A — Reordenar generación del PDF (`monitor_produccion.py`, `api_avanzar_estado`)
Dentro del bloque `if sig_estado == 'COMPLETO'`, nuevo orden:
1. Validación IA (best-effort, try/except).
2. Descuento de insumos (best-effort).
3. **Generar y adjuntar el PDF** (`generar_reporte_pdf` + `guardar_reporte_en_storage`) mientras
   `estado` aún NO es RESULTADOS_LISTOS (así `clean()` no dispara la regla durante el adjunto).
   Si hay saldo pendiente, se omite (el modelo lo permite).
4. Si tras esto no hay PDF adjunto **ni** saldo pendiente → `raise ValidationError(...)`
   (aborta la transición; la orden queda re-aprobable, no en estado roto).
5. Recién entonces `orden.estado = 'RESULTADOS_LISTOS'` → `orden.save()`.

`pdf_url` se inicializa antes del `with transaction.atomic()`. Se elimina el bloque de PDF
posterior al `save()`. El comportamiento queda alineado con `api_validar_pin`, que ya generaba
el PDF antes de marcar la orden (ver test `test_validar_pin_genera_pdf_antes_de_marcar_orden_pagada`).

### LAB-B — Corregir validador IA (`validador_ia.py`)
`select_related('parametro')` → `select_related('analito')`; `resultado.parametro(.nombre)` →
`resultado.analito(.nombre)` (3 referencias).

### LAB-C — Contrato de error 500→400 (`monitor_produccion.py`)
Nuevo `except ValidationError` antes del `except Exception`: responde **HTTP 400** con
`' '.join(ve.messages)`.

---

## 4. Verificación (ejecutada sobre SQLite, harness temporal ya eliminado)

| Caso | Antes | Después |
|------|-------|---------|
| Orden pagada (saldo $0), sin PDF | 500, atascada en VALIDADO_PARCIAL | **200**, `estado_clinico=COMPLETO`, `estado=RESULTADOS_LISTOS`, **PDF adjunto** |
| Orden con saldo pendiente | avanzaba | **200**, RESULTADOS_LISTOS, PDF diferido (correcto) |
| Validador IA | FieldError silenciado | corre sin error |
| Error de regla de negocio | HTTP 500 | HTTP 400 con mensaje |

**Regresión:** `manage.py check` = 0 issues. **12/12** en `core.tests.test_monitor_produccion_workflow`
y `core.tests.test_lab_validation_pdf`. Suites de entrega (`test_entrega_resultados_bitacora`) y
corte (`test_farmacia_corte_unificado`) verdes.

---

## 5. Riesgos / consideraciones para Codex

- La generación del PDF ahora ocurre **dentro** de `transaction.atomic()` con `select_for_update`,
  por lo que el lock se mantiene durante el render (reportlab). Impacto aceptable para una acción
  de aprobación puntual; vigilar latencia si el monitor aprueba en lote.
- Si `generar_reporte_pdf` falla por causa real (no saldo), la orden **no** avanza y se devuelve 400;
  el operador debe reintentar. Esto es intencional (evita orden "lista" sin PDF).
- Falta **validar en VPS** tras desplegar (deploy pendiente, coherente con `AI_COORDINATION_STATUS`).
- Sugerencia: agregar una regresión permanente que cubra `VALIDADO_PARCIAL→COMPLETO` para una orden
  pagada sin PDF previo (hoy `test_monitor_produccion_workflow` cubre el caso sin estudio legacy,
  pero no el adjunto del PDF en esta vista).

---

## 6. Diff completo (commit 8df3782)

```diff
diff --git a/core/services/validador_ia.py b/core/services/validador_ia.py
@@ def validar_resultado_ia(detalle_orden):
         resultados = ResultadoParametro.objects.filter(
             orden=detalle_orden.orden,
-        ).select_related('parametro')
+        ).select_related('analito')

         for resultado in resultados:
             if not resultado.valor:
                 continue

             nombre_param = ''
-            if resultado.parametro:
-                nombre_param = resultado.parametro.nombre or ''
+            if resultado.analito:
+                nombre_param = resultado.analito.nombre or ''

diff --git a/core/views/monitor_produccion.py b/core/views/monitor_produccion.py
@@ imports
 from django.contrib.auth.decorators import login_required
+from django.core.exceptions import ValidationError
 from django.db import transaction
@@ api_avanzar_estado
+        pdf_url = None
         with transaction.atomic():
             ...
             if sig_estado == 'COMPLETO':
-                orden.estado = 'RESULTADOS_LISTOS'
                 # Validacion IA (best-effort)
                 try: alertas_ia = validar_orden_completa(orden)
                 except Exception: pass
                 # Descuento insumos (best-effort)
                 try: _descontar_insumos_orden(orden, request.user)
                 except Exception as e_insumos: logger.warning(...)
+                # PDF: generar y ADJUNTAR antes de marcar RESULTADOS_LISTOS
+                from core.utils.candado_financiero import (
+                    ReportePdfSaldoPendienteError, tiene_saldo_pendiente)
+                saldo_pendiente = tiene_saldo_pendiente(orden)
+                if not saldo_pendiente:
+                    try:
+                        from core.services.motor_reportes_lab import (
+                            generar_reporte_pdf, guardar_reporte_en_storage)
+                        pdf_bytes = generar_reporte_pdf(orden, request=request)
+                        pdf_url = guardar_reporte_en_storage(orden, pdf_bytes)
+                    except ReportePdfSaldoPendienteError:
+                        saldo_pendiente = True
+                    except Exception as e_pdf:
+                        logger.error(f"Error generando PDF para {orden.folio_orden}: {e_pdf}")
+                tiene_pdf = bool(orden.archivo_resultado and getattr(orden.archivo_resultado,'name',None))
+                if not tiene_pdf and not saldo_pendiente:
+                    raise ValidationError('No se pudo generar el PDF de resultados. '
+                        'La orden no se marco como lista; intente aprobar nuevamente.')
+                orden.estado = 'RESULTADOS_LISTOS'
             if sig_estado == 'ENTREGADO':
                 orden.estado = 'ENTREGADO'
             orden.save()
-        # (bloque de PDF posterior al save eliminado)
@@ except handlers
+    except ValidationError as ve:
+        mensajes = getattr(ve, 'messages', None) or [str(ve)]
+        return JsonResponse({'status':'error','mensaje':' '.join(mensajes)}, status=400)
     except Exception as e:
         return JsonResponse({'status':'error','mensaje':str(e)}, status=500)
```

*(Diff resumido; el diff exacto byte-a-byte está en el commit local `8df3782`.)*
