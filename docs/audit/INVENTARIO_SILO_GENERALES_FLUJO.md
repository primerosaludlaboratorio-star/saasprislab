# Silo insumos generales — flujo canónico vs signal (Fase 1)

**Alcance:** solo módulo `inventario` (sin farmacia / PDV).

## Flujo canónico (principal)

- La entrega de un `ValeRequisicion` aprobado debe hacerse por la vista **`detalle_vale`**, acción **`entregar`** (`inventario/views_generales.py`).
- Ahí se usa **`select_for_update()`** sobre lotes FEFO y se actualizan `cantidad_entregada` / `lote_entregado` en cada línea.

## Signal (fallback)

- `post_save` sobre `ValeRequisicion` con `estado=ENTREGADO` (`inventario/signals.py`).
- Solo actúa si quedan líneas con **`cantidad_entregada=0`** (vale marcado entregado sin pasar por la UI).
- Objetivo: recuperación ante bypass; no debe ejecutarse en el camino feliz si la vista ya surtió las líneas.

## Doble descuento

- Camino feliz: líneas ya surtidas → el signal no entra al bloque FEFO.
- Si el signal corre por líneas pendientes, completa FEFO una sola vez por línea.

## Laboratorio (referencia cruzada)

- Consumo analítico: `SalidaAnaliticaLab` con **`idempotency_key`** determinista `lab_rp{resultado_id}_f{formula_id}_l{lote_id}` y bloqueo de `ResultadoParametro` en la transacción.

## Comandos (Día D inventario)

- `python manage.py auditar_integridad_inventario` — revisa idempotencia, stock negativo, kardex sintético lab, vales ENTREGADO. `--strict` falla también si hay advertencias (kardex/vales). `--exit-code-warnings` → exit 2 solo con advertencias.
- `python manage.py backfill_inventario_idempotency --dry-run` / `--apply` — rellena `idempotency_key` faltante (casos excepcionales tras 0003).
