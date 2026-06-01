# ANÁLISIS FARMACIA DEEP DIVE — Cierre de Integridad v1.13

**Fecha:** 2026-04-03  
**Versión:** v1.13 (CIERRE DE INTEGRIDAD FARMACIA)  
**Autor:** Windsurf Cascade (bajo directriz "Borrón y Cuenta Nueva" v7.5)  
**Módulo:** Farmacia (app `farmacia` + señales `core.signals` + modelo `core.Venta`)  
**Estado:** ✅ Quirúrgico completado — 4 refuerzos de integridad aplicados

---

## 1. RESUMEN EJECUTIVO

Este documento consolida el **ANÁLISIS INTEGRAL DE FARMACIA** con las **correcciones quirúrgicas v1.13** aplicadas para garantizar integridad transaccional, concurrencia segura y validaciones matemáticas robustas.

### Cambios aplicados (CIERRE INTEGRIDAD v1.13)

| # | Problema | Solución | Archivo modificado |
|---|----------|----------|-------------------|
| 1 | **Doble descuento de inventario** — La signal usaba flag en memoria (`_inventario_descontado`) que no persistía entre transacciones | Campo persistente `Venta.inventario_descontado` + `select_for_update()` en signal | `core/models/ventas.py`, `core/signals.py` |
| 2 | **División por cero en CPP** — Si `stock_resultante` era 0, el cálculo del Costo Promedio Ponderado podría fallar | Validación explícita antes de dividir; `ValidationError` con contexto | `farmacia/models.py` |
| 3 | **Race condition en cancelaciones** — Dos cancelaciones simultáneas podían reponer el mismo stock dos veces | `select_for_update()` al recuperar movimientos originales | `core/views/farmacia.py` |
| 4 | **Cierre de caja sobre apertura cerrada** — Se podía crear un cierre sobre una caja ya cerrada | Validación en `CierreTurnoFarmacia.clean()` | `farmacia/models.py` |

---

## 2. ARQUITECTURA DE 5 PILARES (Resumen del análisis original)

```
FARMACIA
├─ Pillar 1: CATÁLOGOS (Proveedores, MotivosAjuste)
├─ Pillar 2: KARDEX FORENSE (MovimientoInventario — única fuente de verdad)
├─ Pillar 3: OPERACIONES (PDV, Ventas, Devoluciones)
├─ Pillar 4: CONTROL (Mermas, Apertura/Cierre de Caja)
└─ Pillar 5: FINANCIERO (Corte de Caja, Reportes)
```

### 2.1 Modelos principales y sus responsabilidades

| Modelo | Líneas (aprox) | Responsabilidad |
|--------|----------------|-----------------|
| `Proveedor` | 21-126 | Catálogo de proveedores con validación RFC mexicano (`^[A-ZÑ&]{3,4}\d{6}[A-Z0-9]{3}$`) |
| `MotivoAjuste` | 131-180 | Catálogo cerrado de motivos para ajustes (elimina texto libre) |
| `MovimientoInventario` | 185-534 | **KARDEX FORENSE** — registro inmutable de cada movimiento; calcula CPP; actualiza stock |
| `MermaFarmacia` | 539-726 | Bajas auditadas que generan `SALIDA_MERMA` automáticamente en Kardex |
| `CierreTurnoFarmacia` | 731-971 | Corte de caja ciego — Nancy declara, sistema compara |
| `AperturaCaja` | 976-1079 | Fondo inicial de caja para cálculo correcto del cierre |
| `DevolucionVenta` | 1084-1308 | Reingreso a stock o envío a mermas, con trazabilidad completa |
| `RegistroAntibiotico` | 1313-1460 | Compliance NOM-072-SSA1-2012 (COFEPRIS) |

---

## 3. DETALLE DE CORRECCIONES v1.13

### 3.1 Idempotencia en Descuento de Inventario (Tarea 1)

**Problema original:**
```python
# CÓDIGO ANTIGUO (vulnerable)
if hasattr(instance, '_inventario_descontado') and instance._inventario_descontado:
    return  # Flag en memoria — no persiste si la signal se dispara 2x
```

**Solución aplicada:**
```python
# NUEVO (v1.13) — Campo persistente + bloqueo
# 1. Agregar campo a modelo Venta
inventario_descontado = models.BooleanField(
    default=False,
    verbose_name="Inventario Descontado",
    help_text="True si el Kardex ya descontó el stock..."
)

# 2. Signal actualizada
with transaction.atomic():
    venta_bloqueada = Venta.objects.select_for_update().get(pk=instance.pk)
    if venta_bloqueada.inventario_descontado:
        return  # Idempotencia garantizada por BD
    # ... descuento de inventario ...
    venta_bloqueada.inventario_descontado = True
    venta_bloqueada.save(update_fields=['inventario_descontado'])
```

**Archivos:**
- `core/migrations/0054_venta_inventario_descontado_v113.py`
- `core/models/ventas.py` (campo agregado)
- `core/signals.py` (signal actualizada)

---

### 3.2 Seguridad Matemática en CPP (Tarea 2)

**Fórmula del Costo Promedio Ponderado:**

$$CPP_{nuevo} = \frac{(Stock_{ant} \cdot CPP_{ant}) + (Cant_{nueva} \cdot Costo_{unit})}{Stock_{nuevo}}$$

**Problema:** Si `stock_nuevo = 0`, división por cero.

**Solución aplicada:**
```python
# VALIDACIÓN MATEMÁTICA v1.13
if self.stock_resultante <= 0:
    raise ValidationError(
        f"No se puede calcular CPP: stock resultante es {self.stock_resultante}. "
        f"Stock anterior: {self.stock_anterior}, Cantidad entrada: {self.cantidad}."
    )
self.costo_promedio_nuevo = valor_total / self.stock_resultante
```

**Archivo:** `farmacia/models.py` (líneas 501-509 aprox)

---

### 3.3 Concurrencia en Cancelaciones (Tarea 3)

**Problema:** Dos peticiones simultáneas de cancelación podrían:
1. Leer movimientos originales sin bloquear
2. Crear duplicados de `ENTRADA_DEVOLUCION`
3. Reponer stock dos veces

**Solución aplicada:**
```python
# En cancelar_venta() — core/views/farmacia.py
with _dbt.atomic():
    # Bloquear venta y verificar estado dentro de la transacción
    venta_bloqueada = Venta.objects.select_for_update().get(pk=venta.pk)
    if venta_bloqueada.estado == 'CANCELADA':
        return JsonResponse({'status': 'error', 'mensaje': 'La venta ya está cancelada'})
    
    # Bloquear movimientos originales
    movimientos_originales = MovimientoInventario.objects.select_for_update().filter(
        venta=venta_bloqueada,
        tipo_movimiento='SALIDA_VENTA',
    )
    # ... crear reversión ...
```

---

### 3.4 Validación de Cierre de Caja (Tarea 4)

**Problema:** Se podía crear un `CierreTurnoFarmacia` vinculado a una `AperturaCaja` ya cerrada.

**Solución aplicada:**
```python
# En CierreTurnoFarmacia.clean() — farmacia/models.py
def clean(self):
    # ... validaciones existentes ...
    
    # VALIDACIÓN INTEGRIDAD v1.13
    if self.apertura_caja and not self.apertura_caja.activa:
        raise ValidationError(
            "No se puede cerrar una caja que no está activa o ya fue cerrada. "
            f"Apertura {self.apertura_caja.folio} ya está cerrada."
        )
```

---

## 4. FLUJOS DE NEGOCIO CRÍTICOS (Resumen)

### 4.1 Flujo de Venta con Idempotencia v1.13

```
1. Cliente compra → Cajera procesa venta
2. Venta guardada con estado='COMPLETADA'
3. Signal post_save dispara descontar_inventario_al_completar_venta
   └─ transaction.atomic()
      ├─ select_for_update() sobre Venta
      ├─ IF venta.inventario_descontado == True: RETURN (idempotencia)
      ├─ Para cada detalle:
      │  ├─ select_for_update() sobre Lote
      │  └─ Descontar cantidad
      ├─ Guardar Venta con inventario_descontado=True
      └─ COMMIT
4. ✅ Stock descontado exactamente una vez
```

### 4.2 Flujo de Cancelación con Concurrencia Segura

```
1. Gerente solicita cancelación de venta #123
2. Vista cancelar_venta inicia transacción
   └─ transaction.atomic()
      ├─ select_for_update() sobre Venta #123
      ├─ IF ya cancelada: rechazar
      ├─ select_for_update() sobre Movimientos SALIDA_VENTA
      ├─ Crear movimientos ENTRADA_DEVOLUCION (reversión)
      └─ COMMIT
3. Segunda petición simultánea:
   └─ Espera por bloqueo → Al obtenerlo, venta ya cancelada → rechaza
4. ✅ Stock revertido exactamente una vez
```

---

## 5. ÍNDICES Y PERFORMANCE

Los índices clave para soportar estas operaciones:

```python
# MovimientoInventario (farmacia/models.py)
indexes = [
    models.Index(fields=['empresa', '-fecha_movimiento']),
    models.Index(fields=['venta']),  # Crítico para cancelaciones
    models.Index(fields=['producto', '-fecha_movimiento']),
    models.Index(fields=['lote', '-fecha_movimiento']),
]

# Venta (core/models/ventas.py)
indexes = [
    models.Index(fields=['fecha']),
    models.Index(fields=['empresa', 'fecha']),
    models.Index(fields=['empresa', 'estado', 'fecha']),
    # Nota: inventario_descontado no requiere índice (booleano de baja selectividad)
]
```

---

## 6. CHECKLIST DE INTEGRIDAD v1.13

```yaml
☑️ IDEMPOTENCIA DESCUENTO INVENTARIO
  ☑️ Campo inventario_descontado en modelo Venta
  ☑️ Migración 0054 creada
  ☑️ Signal usa select_for_update() sobre Venta
  ☑️ Signal usa select_for_update() sobre Lotes
  ☑️ Flag persistente en BD (no memoria)

☑️ SEGURIDAD MATEMÁTICA CPP
  ☑️ Validación stock_resultante <= 0 antes de dividir
  ☑️ ValidationError con mensaje descriptivo
  ☑️ Fórmula CPP documentada

☑️ CONCURRENCIA CANCELACIONES
  ☑️ select_for_update() sobre Venta en cancelar_venta
  ☑️ select_for_update() sobre MovimientoInventario originales
  ☑️ Verificación estado dentro de transacción
  ☑️ Mensaje de error si ya cancelada

☑️ VALIDACIÓN CIERRE DE CAJA
  ☑️ CierreTurnoFarmacia.clean() verifica apertura_caja.activa
  ☑️ ValidationError con folio de apertura
  ☑️ Previene cierre sobre caja ya cerrada

☑️ DOCUMENTACIÓN
  ☑️ Este archivo ANALISIS_FARMACIA_DEEP_DIVE.md
  ☑️ DOCS_AUDIT_MAESTRO.md actualizado a v1.13
  ☑️ Entrada en §9 del maestro
```

---

## 7. RIESGOS RESIDUALES POST-v1.13

| Riesgo | Severidad | Mitigación | Estado |
|--------|-----------|------------|--------|
| Signal se dispara antes del COMMIT de la transacción padre | Baja | Idempotencia por campo persistente | ✅ Mitigado |
| Deadlock por select_for_update() múltiple | Baja | Orden consistente: Venta → Lotes | ✅ Aceptado |
| Stock negativo por race condition externa | Media | Validación en MovimientoInventario.save() | ✅ Mitigado |
| Cálculo incorrecto de diferencias en cierre | Baja | Fórmula ajustada con fondo inicial | ✅ Verificado |

---

## 8. REFERENCIAS CRUZADAS

- `DOCS_AUDIT_MAESTRO.md` — Bitácora maestra v1.13
- `core/migrations/0054_venta_inventario_descontado_v113.py`
- `VEREDICTO_LIMS_CASCADE.md` — Análisis paralelo de Laboratorio

---

**Fin del documento — CIERRE DE INTEGRIDAD FARMACIA v1.13**
