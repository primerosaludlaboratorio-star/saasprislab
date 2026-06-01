# AUDIT_REMASTERED — Farmacia v1.6 & núcleo clínico / LIMS v1.7

**Fecha:** 2026-04-02  
**Ejecutor:** Cursor (lectura de código + `rg`; sin ejecución E2E en esta pasada).  
**Flujo:** READ → THINK → CODE (solo documentación) → LOG.

---

## FASE 1 — Farmacia (v1.6)

### Multi-tenant (`Empresa.objects.first()`)

| Ámbito | Resultado |
| :--- | :--- |
| `farmacia/views/**/*.py` | **0 coincidencias** (`rg Empresa\.objects\.first\(` sobre `farmacia/`). |
| `farmacia/services/*.py` | **0 coincidencias**. |

**Conclusión:** No quedan rastros de `Empresa.objects.first()` bajo `farmacia/` en el workspace actual.

### Integridad `DetalleVentaLote` y `Lote.empresa`

- **`DetalleVentaLote`** (`core/models/ventas.py`): FK a `DetalleVenta` (`related_name=lotes_extraidos`) y a `Lote`; `cantidad_extraida` por fila. Documentación en modelo: una partida puede tener **N** lotes.
- **`ejecutar_venta_pdv`** (`farmacia/services/venta_farmacia_service.py`): tras PEPS multi-lote, crea **un** `DetalleVenta` y luego **un** `DetalleVentaLote` por cada entrada en `lotes_usados_en_item` (bucle `DetalleVentaLote.objects.create(...)`). Coherente con trazabilidad multi-lote.
- **`Lote.empresa`** (`core/models/catalogos.py`): `save()` asigna `empresa_id` desde `Producto.empresa_id` antes de `full_clean()` y `super().save()`. Consulta de lotes en venta filtra `empresa=empresa` junto con `producto`.

**Conclusión:** Diseño y escritura atómica dentro de `transaction.atomic()` alineados con FEFO/PEPS y tenant por lote.

### Servicio de venta — atomicidad y orden FEFO

- Toda la operación envuelta en **`with transaction.atomic():`** desde el inicio de `ejecutar_venta_pdv`.
- Lotes: `select_for_update()`, orden **`order_by('fecha_caducidad', 'fecha_registro')`** (primero caduca antes), exclusión de caducados (`fecha_caducidad__gte=_hoy`).
- Stock: descuento vía **`MovimientoInventario`** (`farmacia.models`), no asignación directa a `lote.cantidad` en la vista de servicio.
- **Nota terminológica:** El código y comentarios dicen “PEPS”; el negocio sanitario suele asociar venta a **FEFO** (primero el que caduca antes). El orden por `fecha_caducidad` ascendente es coherente con FEFO.

---

## FASE 2 — Consistencia `core/` post-catálogo

### Imports rotos hacia `core.models.Estudio` / `Parametro`

**No cumplido a nivel repositorio:** siguen existiendo referencias `from core.models import Estudio` / `Parametro` / `RangoReferencia` / `CategoriaEstudio` / `SeccionLaboratorio` en múltiples módulos (comandos `management`, `core/views/laboratorio.py`, `tarifas.py`, `paquetes.py`, `pris_ia.py`, `ia.py`, `director.py`, `catalogos_maestros.py`, `hl7_receptor.py`, `marketing/views.py`, scripts raíz, etc.).  
`core/models/__init__.py` **ya no exporta** `Estudio` ni `Parametro`; esas importaciones **fallarán** al cargar el módulo correspondiente hasta limpiar o redirigir cada archivo.

**Migración `0052`:** En el workspace auditado, la última migración `core` numerada es **`0051_farmacia_tenant_lote_detalleventalote.py`**; no hay archivo `0052_*.py` en `core/migrations/`. El comentario en `catalogos.py` cita “0052” como referencia de intención; el número real puede diferir al generar `makemigrations`.

### Archivos “huérfanos” o de alto riesgo en `core/` (post-eliminación lógica de catálogo)

No es posible inferir “20 000 líneas” sin métrica histórica; sí se listan **módulos que aún asumen catálogo core** y deben migrarse o borrarse:

| Categoría | Ejemplos (no exhaustivo) |
| :--- | :--- |
| Vistas | `core/views/tarifas.py`, `core/views/paquetes.py`, `core/views/catalogos_maestros.py`, `core/views/ia.py`, `core/views/pris_ia.py`, `core/views/director.py`, tramos de `core/views/laboratorio.py` (`Parametro`, `ConvenioPrecioEstudio`) |
| Comandos | `importar_csv_lab.py`, `simular_flujo_completo.py`, `seed_catalogos.py`, `seed_parametros_lab.py`, `cargar_catalogo_lab.py`, `importar_catalogos_legacy.py`, `diagnostico_total.py`, … |
| Otros | `core/catalog.py`, `core/agent/pris_tools_operativos.py`, `smoke_test.py`, `migracion_ordenes_forense.py` |

**Recomendación:** `rg "from core.models import.*Estudio|Parametro"` y corregir por lotes (LIMS o eliminación).

---

## FASE 3 — Laboratorio y LIMS (v1.7)

### `ResultadoParametro` → solo `lims.Analito`

- Modelo (`core/models/laboratorio.py`): FK **`analito`** → `'lims.Analito'`; `unique_together = ('orden', 'analito')`. **Verificado en código.**

**Huérfanos en BD:** No auditado en runtime (sin `manage.py shell` ni SQL). Cualquier fila sin `analito_id` o con migración incompleta requeriría `inspectdb` / consulta SQL; la ausencia de migración `core` publicada para borrar `parametro_id` impide afirmar estado de producción.

### IDs compuestos (`core/lims_cart.py`)

- Tokens `analito:<id>`, `perfil:<id>`, `paquete:<id>` evitan colisión de PK entre tablas LIMS.
- `resolve_lims_cart_ids`: si llega un entero sin prefijo, prueba en orden **analito → perfil → paquete**; **riesgo residual:** si el mismo entero existe en dos tablas, se resuelve al **primer** match (típicamente analito). El contrato correcto es enviar siempre el string compuesto desde el cliente tras `api_buscar_estudios`.

### Neonatos — `validar_contra_rango`

- Sin default **30 años**: rama explícita `EDAD_DESCONOCIDA` cuando `edad_desconocida` o `(edad is None and edad_dias is None)`.
- Uso de `unidad_edad` **DIAS** vs **ANOS** con rangos en `ValorReferenciaAnalito`.

### ISO — `codigo_rastreo_iso` y seguridad de catálogo

- **Campo:** `lims.models.Analito.codigo_rastreo_iso` existe (`null=True`, `blank=True` en modelo leído). **No** se puede afirmar “presente en todos los registros” sin migración de datos aplicada y query `exclude(codigo_rastreo_iso__isnull=False)` en BD. En el repo **no** hay carpeta `lims/migrations/` versionada en el glob actual; la verificación de backfill es **pendiente de entorno**.
- **RBAC catálogo:** `core/views/laboratorio_config.py` y rutas de estudios/precios en `core/views/catalogos.py` usan `@role_required('DIRECTOR_QC', 'ADMIN')` (además de bypass `staff`/`superuser` del decorador). Las vistas bajo **`lims/views/*.py`** no muestran el mismo decorador en el barrido — acceso típico `login_required`; **brecha documentada** si se exige paridad estricta ISO con solo DIRECTOR_QC/ADMIN en UI `lims`.

---

## Cierre

Este anexo alimenta la actualización de **`DOCS_AUDIT_MAESTRO.md`** (§6.2–§6.5, §9). No sustituye E2E ni revisión del Programador en producción.
