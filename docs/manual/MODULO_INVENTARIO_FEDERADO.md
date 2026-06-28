# Manual operativo — Inventario federado (PRISLAB v7.5)

**Ámbito:** Silos Laboratorio, Consultorio, Insumos generales; compras; traspasos.  
**Namespace URL:** `inventario` bajo prefijo **`/silo-lab/`** (`config/urls.py` → `include('inventario.urls')`).

**Ubicación canónica:** `docs/manual/` (Directriz v7.5 — Punto 8).

---

## 1. Propósito operativo

Trazabilidad de reactivos e insumos por empresa, FEFO, cuarentena QC (laboratorio), consumo ligado a validación LIMS (`ResultadoParametro` → `SalidaAnaliticaLab` con `orden_id`), y alertas de mínimo hacia War Room.

---

## 2. Guía de usuario (Usuarios)

### Silo laboratorio
- Tablero: `/silo-lab/lab/`
- Catálogo: `/silo-lab/lab/catalogo/`
- Lotes: `/silo-lab/lab/lotes/`
- **Liberación QC (CUARENTENA → ACTIVO):** en el **detalle del lote**, tras recepción y controles ISO 15189 §6.6.2, el personal de calidad marca **`lote_aprobado_qc`**, registra **`aprobado_por`** / **`fecha_aprobacion_qc`** si aplica en flujo, y cambia **`estado`** del lote de **CUARENTENA** a **ACTIVO**. Solo lotes **ACTIVOS** entran en el consumo FEFO automático al validar resultados y en salidas técnicas manuales.
- Salida técnica: `/silo-lab/lab/salidas-tecnicas/nueva/` — solo lotes **ACTIVOS**; backend rechaza **CUARENTENA** / **VENCIDO**
- Consumo por analito: `/silo-lab/lab/consumo/` — define **`ConsumoEstudioReactivo`** (reactivo por analito LIMS). **Excepción de producto:** analitos con **`lims.Analito.es_calculado=True`** **no** disparan descuento FEFO al validar (`inventario/signals.py`); el stock no debe moverse por la mera validación de un resultado calculado (el consumo real corresponde a los analitos de medición directa).

### Consultorio / Generales / Compras / Traspasos
- Ver rutas en `inventario/urls.py` (`consultorio/`, `generales/`, `compras/`, `traspasos/`).

---

## 3. Estados y alertas (laboratorio)

| Estado | Uso |
| :--- | :--- |
| CUARENTENA | No entra en FEFO de validación hasta liberación QC |
| ACTIVO | Único estado consumido en señal analítica (analitos **no** calculados) |
| VENCIDO / BAJA / AGOTADO | No seleccionables para consumo operativo |

Semáforos en `lista_lotes.html` según caducidad y estado.

---

## 4. Mapa técnico (Programador)

- Modelos: `inventario/models.py`
- Señales FEFO: `inventario/signals.py` (excluye **`es_calculado`**)
- **Cron alertas stock:** Cloud Scheduler → job **`prislab-check-stock-critico`** → POST **`/cron/check-stock-critico/`** (`core/views/cron_tasks.py` + `inventario/services/critical_stock.py`). Debe permanecer habilitado en producción (ver **`SOP_DESPLIEGUE_SEGURO.md` §7.1**).
- Tests: `inventario/tests/test_critical_stock.py`, `inventario/tests/test_fefo_analito_calculado.py`

---

## 5. Troubleshooting

| Síntoma | Acción |
| :--- | :--- |
| No descuenta al validar | Revisar `ConsumoEstudioReactivo` y lotes **ACTIVO** |
| War Room sin alertas | Ver ejecución de `cron/check-stock-critico/` y logs |

---

*Sincronizar con cambios en código.*

---

*Fórmulas LIMS (Punto 10): ver docs/manual/APENDICE_FORMULAS_LIMS_v75.md.*
