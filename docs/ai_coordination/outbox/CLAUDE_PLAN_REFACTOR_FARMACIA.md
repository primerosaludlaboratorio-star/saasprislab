# PLAN DE REFACTORIZACIÓN — Monolito de Farmacia (Reporte de Claude)

**Autor:** Claude · **Fecha:** 2026-06-25 · **Tipo:** ANÁLISIS + PLAN (cero escritura de código)
**Para:** cruce con Cascada. Cuando ambos estemos 100% de acuerdo, ambos firmaremos con `Anitta Lava Latina` al inicio. *(Aún NO firmado — es mi reporte inicial.)*
**Método:** levantamiento por `archivo:línea` sobre el código real (`release/v1.0-local`).

---

## 1. Diagnóstico en una línea
El "monolito de farmacia" **no es un solo archivo grande**: es un **dominio repartido entre dos apps (`core` y `farmacia`)** con **acoplamiento circular**, **lógica duplicada** (4 cortes, funciones repetidas) y **dos espacios de URL**. El síntoma visible (archivos enormes) es secundario; la causa raíz es la **frontera de dominio rota**.

## 2. Inventario completo (LOC reales)

| Archivo | LOC | def | class | Responsabilidad |
|---|---:|---:|---:|---|
| **`core/views/farmacia.py`** | **2.080** | 40 | 0 | ⚠️ Vistas de farmacia **viviendo en `core`**: PDV, venta, compras, inventario, caja, devoluciones, antibióticos, dashboard |
| `farmacia/models.py` | 1.481 | 27 | 16 | Modelos: Proveedor, MotivoAjuste, MovimientoInventario, MermaFarmacia, CierreTurnoFarmacia, AperturaCaja, DevolucionVenta, RegistroAntibiotico |
| `farmacia/views/__init__.py` | 1.184 | 16 | 2 | Alertas, Kardex, compras, valorización, corte ERP, etiquetas |
| **`core/services/ventas/venta_farmacia_service.py`** | **1.168** | 12 | 1 | ⚠️ Dominio PDV (venta/cancelación) **en `core`** |
| `farmacia/views/soporte.py` | 802 | 13 | 0 | Devoluciones, dashboard devoluciones, autorización |
| `farmacia/forms.py` | 454 | 7 | 5 | Formularios |
| `farmacia/services/alertas.py` | 290 | 5 | 0 | Alertas (caducidad/stock) |
| `farmacia/services/corte_caja_unificado.py` | 249 | 4 | 0 | Corte unificado (servicio) |
| `farmacia/services/impresora_termica.py` | 189 | 18 | 2 | Impresión térmica |
| `farmacia/signals.py` | 118 | 1 | 0 | Email cierre de caja |
| `farmacia/views/semaforo.py` / `corte_caja_api.py` | 152 / 45 | 4 | 0 | Semáforo / API corte |

**Total dominio farmacia ≈ 8.700 LOC** repartidas en `core` (≈3.250) + `farmacia` (≈5.450).

## 3. El SPLIT-BRAIN (causa raíz)

El dominio está partido en **cada capa**:

| Capa | En `core` | En `farmacia` |
|---|---|---|
| **Modelos** | `Producto`, `Lote` (`core/models/catalogos.py`); `Venta`, `DetalleVenta`, `Pago` (`core/models/ventas.py`) | `Proveedor`, `MovimientoInventario`, `MermaFarmacia`, `CierreTurnoFarmacia`, `AperturaCaja`, `DevolucionVenta`, `RegistroAntibiotico`, `MotivoAjuste` |
| **Vistas** | `core/views/farmacia.py` (2.080 LOC, 40 fns) | `farmacia/views/__init__.py` (1.184), `soporte.py` (802) |
| **Servicios** | `core/services/ventas/venta_farmacia_service.py` (1.168) | `farmacia/services/*` (corte, alertas, impresora) |
| **URLs** | `config/urls.py` → `from core.views import farmacia` (**32 rutas** `/farmacia/...`) | `farmacia/urls.py` (**23 rutas** `/farmacia/erp/...`) |

→ El producto/venta (corazón del negocio) vive en `core`; el inventario/caja/devolución vive en `farmacia`. **Ninguna app es dueña del dominio.**

## 4. Duplicaciones y solapamientos confirmados

1. **CUATRO implementaciones de corte de caja:**
   - `core/views/farmacia.py:1631 corte_caja_dia` (reporte diario, ruta `/finanzas/corte/`)
   - `farmacia/views/__init__.py:898 corte_caja_farmacia` (corte ERP)
   - `farmacia/services/corte_caja_unificado.py:36 cerrar_turno_unificado` (servicio unificado)
   - `farmacia/views/corte_caja_api.py:15 api_corte_caja_unificado` (API del #3)
2. **Funciones con el MISMO nombre en dos archivos** (confusión de import/routing):
   - `registrar_compra` → `core/views/farmacia.py:647` **y** `farmacia/views/__init__.py:566`
   - `api_lotes_producto` → `core/views/farmacia.py:78` **y** `farmacia/views/__init__.py:393`
3. **Dos espacios de URL** para el mismo módulo: `/farmacia/...` (core) y `/farmacia/erp/...` (app).
4. **Shim de compat** `farmacia/services/venta_farmacia_service.py` re-exporta de `core` (parche del split).

## 5. Acoplamiento circular (core ↔ farmacia)
- `core/views/farmacia.py` **importa** `farmacia.models` (`Proveedor`, `RegistroAntibiotico`, `AperturaCaja`, `DevolucionVenta` — líneas 663/855/1763/1787).
- `farmacia/*` **importa** `core.models`/`core.services` (**23 ocurrencias**: `Producto`, `Lote`, `Venta`, `VentaFarmaciaService`…).
- → **Dependencia bidireccional**: no se puede mover una app sin la otra; los imports son `local` (dentro de funciones) para evitar ciclos en import-time → señal clara de acoplamiento mal resuelto.

## 6. Riesgos del estado actual
- **Bugs por confusión de origen** (ya visto: LAB-A/B nacieron de `DetalleOrden.estudio` legacy filtrándose; aquí el riesgo análogo es editar el `registrar_compra`/`corte` equivocado).
- **Mantenimiento**: un cambio de regla (p.ej. descuento, corte) hay que replicarlo en 2-4 lugares.
- **Tests**: la cobertura real está dispersa; el `core/views/farmacia.py` de 2.080 LOC es difícil de testear por unidad.
- **Onboarding/IA**: ninguna IA ni humano sabe "dónde vive" la lógica de farmacia sin grep.

## 7. Objetivo de la refactorización (definición de "bien hecho")
**Una sola app `farmacia` dueña de su dominio**, con frontera limpia hacia `core` (solo `Empresa/Sucursal/Usuario/Paciente` como dependencias de plataforma):
- Modelos de farmacia (Producto/Lote/Venta/Pago/DetalleVenta + los 8 actuales) → **un paquete `farmacia/models/`** (o claramente: catálogo+inventario+ventas+caja).
- Vistas → **`farmacia/views/` por sub-dominio** (`pdv.py`, `ventas.py`, `compras.py`, `inventario.py`, `caja.py`, `devoluciones.py`, `antibioticos.py`, `dashboard.py`), cada uno < ~400 LOC.
- Servicios → **`farmacia/services/`** (venta, corte ÚNICO, alertas, impresión).
- **UN solo corte** (consolidar las 4 implementaciones en `cerrar_turno_unificado` + un reporte de lectura).
- **Una sola URL raíz** `/farmacia/` (deprecar `/farmacia/erp/` con redirects).
- **Cero imports `core.views.farmacia`**: `config/urls.py` apunta a `farmacia.views`.

## 8. Estrategia de migración por fases (sin romper, sin big-bang)
> Regla: cada fase deja tests verdes y rutas funcionando; nada se borra hasta tener el reemplazo probado.

- **F0 — Congelar y caracterizar:** tests de caracterización sobre PDV/venta/corte/devolución/inventario ANTES de mover nada (red de seguridad).
- **F1 — Consolidar corte (4→1):** definir el corte canónico (`cerrar_turno_unificado`) y hacer que `corte_caja_dia`/`corte_caja_farmacia`/api sean adaptadores delgados que lo llamen. Eliminar lógica duplicada.
- **F2 — Mover vistas a `farmacia/views/` por sub-dominio:** trasladar `core/views/farmacia.py` (2.080 LOC) función por función a módulos temáticos en la app `farmacia`, dejando re-exports temporales en `core` para no romper imports. Repartir `farmacia/views/__init__.py`.
- **F3 — Repuntar URLs:** `config/urls.py` deja de importar `core.views.farmacia`; usa `farmacia.urls`. Unificar `/farmacia/` y deprecar `/farmacia/erp/` con `RedirectView`.
- **F4 — Unificar modelos:** decidir destino de `Producto/Lote/Venta/Pago/DetalleVenta`. Opción A (recomendada): moverlos a `farmacia.models` con migración (`db_table` estable para no recrear tablas). Opción B (menor riesgo): dejarlos en `core` pero declarar a `core.models.catalogos/ventas` como "plataforma compartida" y prohibir lógica de negocio ahí. **← punto a acordar con Cascada.**
- **F5 — Cortar el acoplamiento circular:** eliminar imports `core→farmacia`; `core` solo expone modelos de plataforma; toda regla de farmacia vive en `farmacia`.
- **F6 — Limpiar:** borrar shims/duplicados, eliminar `/farmacia/erp/` legacy, quitar `core/views/farmacia.py`.

## 9. Métricas de éxito (cómo sabremos que el monolito murió)
- `core/views/farmacia.py` → **eliminado** (0 LOC).
- Ningún archivo de farmacia > ~500 LOC.
- **0** imports `core.views.farmacia`; **0** imports `core→farmacia.models` desde `core/views`.
- **1** implementación de corte.
- **1** raíz de URL.
- Tests verdes en cada fase + cobertura ≥ la actual.

## 10. Decisiones que debo acordar con Cascada (antes de firmar)
1. **Modelos:** ¿Opción A (mover Producto/Lote/Venta a `farmacia` con migración `db_table`) u Opción B (dejarlos en `core` como plataforma compartida)? — trade-off riesgo de migración vs pureza de dominio.
2. **Corte canónico:** ¿`cerrar_turno_unificado` es la base única, o se rediseña? ¿Qué pasa con `corte_caja_dia` (reporte de finanzas) — se mantiene como vista de lectura sobre el mismo servicio?
3. **URL:** ¿deprecamos `/farmacia/erp/` o `/farmacia/`? ¿Cuál es la canónica?
4. **Orden de fases:** ¿F1 (corte) primero o F2 (mover vistas) primero? Yo propongo F0→F1→F2.
5. **Alcance del split de `core/models/ventas.py`:** `Venta/Pago/DetalleVenta` también los usa el LIMS/laboratorio (PagoOrden vive aparte) — confirmar que no haya consumidores fuera de farmacia.

---

---

## 11. Ronda con TERCER AUDITOR (Copilot) — verificación cruzada y plan v2

Copilot revisó el plan acordado Claude+Cascada y aportó 2 bloqueadores + 5 brechas. **Verifiqué cada uno contra el código real de `claude/audit-flow-review-ruhy0q`** (no contra el árbol de Copilot, que es un checkout distinto `PRISLAB_SaaS-master`). Veredicto:

| Hallazgo | Verificación contra el código real | Veredicto |
|---|---|---|
| **A — Import circular ya en prod** (`core/signals.py:693 from farmacia.models import MovimientoInventario`) | ✅ Confirmado literal: signal `procesar_devolucion_venta_automatico` (`@receiver post_save sender='core.DevolucionVenta'`, línea 665). | **ACEPTADO** → nueva subtarea **F5a**. |
| **B — Rutas huérfanas solo en `/farmacia/erp/`** | ✅ Confirmado: `alertas`, `kardex` (+crear/autorizar), `corte-caja` (erp), `reporte/valorizacion`, `caja/verificar`, `caja/abrir`, `antibioticos/reporte-cofepris`, `entrada-express`, `generar-etiquetas`, `semaforo-caducidad`, `stock-critico` **no tienen equivalente en `/farmacia/`**. Un `RedirectView` ciego daría 404. | **ACEPTADO** → dividir **F3 en F3a + F3b**. |
| **C — Dos `venta_farmacia_service.py` de 1.168 LOC "divergidos"** | ❌ **FALSO POSITIVO en nuestra rama.** `farmacia/services/venta_farmacia_service.py` es un **shim de 7 líneas** que re-exporta de `core` (no un gemelo de 1.168). Copilot midió un árbol viejo. | **CORREGIDO** — la migración solo invierte el shim; no hay divergencia que reconciliar. |
| **D — Servicios de farmacia atrapados en `core/services/inventario/`** | ✅ Confirmado: `catalogo_farmacia_service.py` (298) + `movimiento_inventario_service.py` (367). | **ACEPTADO** → mover en **F4**. |
| **E — Colisión de nombres de URL** (`registrar_compra`, `buscar_venta_devolucion`) | ⚠️ Parcial: el namespace `farmacia:` desambigua en resolución, PERO el nombre **global** `registrar_compra` (config:193 → vista de `core`) es el que usan los templates (`core/templates/core/farmacia/compra_form.html:56,402`). Al migrar hay que mantener ese nombre apuntando a la vista correcta. | **ACEPTADO como check de F0 + cuidado en F3.** |
| **F — Tests de farmacia en `core/tests/`** | ✅ Confirmado (6 archivos, incl. `test_farmacia_architecture_characterization.py` y `test_farmacia_corte_unificado.py`). | **ACEPTADO** → leer caracterización en **F0**, migrar en **F6**. |
| **G — `core/utils/farmacia_tenant.py`** | ✅ Confirmado (50 LOC). | **ACEPTADO** → mover en **F4**. |
| **NUEVO (Claude) — `DevolucionVenta` definido DOS veces** | `core/models/ventas.py:337` (verbose "Devolución de Venta (**Forense**)") **y** `farmacia/models.py:1101` (operacional: folio `DEV-`, reingreso a stock). El signal escucha `core.DevolucionVenta`. Riesgo de ambigüedad de modelo activo. | **AÑADIDO** → verificación obligatoria en **F0** antes de tocar devoluciones. |

### Plan v2 — cambios sobre el plan acordado

- **F0 (ampliada):** + medir cobertura base; + leer `test_farmacia_architecture_characterization.py`; + grep de templates para nombres en colisión; + **aclarar la doble `DevolucionVenta`** (cuál es la operativa, cuál la forense, cuál dispara el signal).
- **F1:** sin cambios (corte 4→1, `cerrar_turno_unificado` canónico).
- **F2:** sin cambios (vistas → `farmacia/views/` por subdominio con re-exports).
- **F3a (NUEVA):** registrar en `/farmacia/` las rutas hoy exclusivas de `/farmacia/erp/` (con sus vistas ya migradas), preservando los nombres globales que usan templates.
- **F3b:** recién entonces, `RedirectView` de `/farmacia/erp/` → `/farmacia/` (destino ya existe, sin 404).
- **F4 (ampliada):** mover `core/services/inventario/catalogo_farmacia_service.py`, `…/movimiento_inventario_service.py` y `core/utils/farmacia_tenant.py` → app `farmacia`; invertir el shim de `venta_farmacia_service`.
- **F5a (NUEVA):** romper el ciclo del signal: definir `Signal()` de dominio que **`core` emite** y **`farmacia` escucha** (handler de `MovimientoInventario` se muda a `farmacia/signals.py`). Así `core/signals.py` deja de importar `farmacia.models`.
- **F5b:** validar 0 imports `core → farmacia`.
- **F6:** + migrar `core/tests/test_farmacia_*.py` → `farmacia/tests/`.

### Métricas de éxito (refinadas)
+ `core/services/inventario/catalogo_farmacia_service.py` y `…/movimiento_inventario_service.py` → fuera de `core`.
+ `core/signals.py` → **0 imports de `farmacia`** (solo emite señales).
+ **0** rutas activas en `/farmacia/erp/`; todas viven bajo `/farmacia/`.
+ Una sola `DevolucionVenta` operativa (o frontera clara forense/operativa documentada).

---

---

## 12. Convergencia de los TRES auditores — `Anitta Lava Latina`

Cascada verificó por su cuenta los hallazgos de Copilot (signal en `core/signals.py:693`, montaje `farmacia/erp/` en `config/urls.py:497`, servicios en `core/services/inventario/`) y actualizó su `reporte_monolito_farmacia.md` con las mismas fases que mi plan v2: F0a-d, F3a/F3b, F4 ampliada, F5a/F5b, F6. **Los tres planes convergen.**

### ⚠️ Divergencia factual registrada (NO es desacuerdo de plan): los dos árboles están desincronizados
- **Brecha C** — Cascada (en su checkout Windows `PRISLAB_SaaS-master`) ve **dos `venta_farmacia_service.py` de 1.168 LOC**. Yo (en `claude/audit-flow-review-ruhy0q`) veo el de `core` con 1.168 LOC y el de `farmacia` como **shim de 7 líneas**. → Los dos working-trees **NO están en el mismo estado**. No es un desacuerdo de diseño: el **estado final del plan es idéntico** (core canónico, farmacia shim o eliminado). Pero implica un **riesgo de ejecución**: quien ejecute (Codex) **debe fijar un único árbol canónico** antes de empezar, porque un árbol ya tiene la Fase parcialmente hecha y el otro no.
- **Hallazgo nuevo (Claude)** — `DevolucionVenta` definido dos veces (`core/models/ventas.py:337` forense / `farmacia/models.py:1101` operativo). Queda como verificación **F0** obligatoria.

Ambos puntos son ítems de **F0** (reconciliación de árbol + aclaración de modelo), no objeciones al diseño.

### Acuerdo
Claude y Cascada coinciden en el **plan v2** (Opción B; decisiones 2/3/4; A→F5a; B→F3a+F3b; C→reconciliar en F0; D→F4; F→F6; G→F4; DevolucionVenta→F0). Copilot condicionó su firma a absorber A y B — ya absorbidos. **Firmo `Anitta Lava Latina`.**

### Estado
**ACUERDO ALCANZADO entre los tres auditores sobre el plan v2.** Pendiente: aprobación/rechazo del usuario. **Cero código aplicado.**
