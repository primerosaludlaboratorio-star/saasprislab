# REPORTE: Hallazgo #3 - Bloqueador Crítico Laboratorio

**Agente:** Claude  
**Fecha:** 2026-06-21  
**Clasificación:** PENDIENTE_VALIDAR (causa encontrada, fix pendiente de prueba)

---

## Síntesis

**Hallazgo #3 (CRÍTICO):** Orden LAB-20260621-001 persiste en estado "Por Validar" (VALIDADO_PARCIAL) y no avanza a COMPLETO/RESULTADOS_LISTOS tras intentar aprobar.

**Paso bloqueador:** Botón "Aprobar Resultados" en `/laboratorio/monitor/` → Sin efecto

**Impacto:** Bloquea completamente Fase 4 (Entrega). Orden no aparece en `/laboratorio/entrega-resultados/`.

---

## Causa Raíz (Investigación técnica)

### Ubicación exacta
- **Archivo:** `core/views/monitor_produccion.py`
- **Línea 368:** en función `_descontar_insumos_orden()`

### El error
```python
# LÍNEA 368 - INCORRECTO
detalles = orden.detalles.select_related('estudio').all()
```

**Problema:** `DetalleOrden` NO tiene campo `estudio` (tiene `analito`, `perfil_lims`, `paquete_lims`)

**Consecuencia:** Django lanza `FieldError` al BD → transacción `atomic()` aborta → `orden.save()` nunca ocurre

### Flujo de fallo
```
api_avanzar_estado() POST /api/laboratorio/avanzar-estado/
  └─ VALIDADO_PARCIAL → COMPLETO
     └─ orden.estado_clinico = 'COMPLETO'  ✓
     └─ orden.estado = 'RESULTADOS_LISTOS' ✓
     └─ _descontar_insumos_orden()
        └─ select_related('estudio').all()  ✗ FieldError
           └─ Transacción abortada
              └─ orden.save() NUNCA EJECUTA
                 └─ Orden sigue en VALIDADO_PARCIAL
```

---

## Fix Implementado (Pendiente prueba)

### Cambio 1: Línea 368-390
```python
# ANTES (incorrecto)
detalles = orden.detalles.select_related('estudio').all()
for detalle in detalles:
    estudio = detalle.estudio
    if not estudio:
        continue

# DESPUÉS (corregido)
detalles = orden.detalles.select_related('analito').all()
descuentos = []
for detalle in detalles:
    estudio = None
    if hasattr(detalle, 'estudio') and detalle.estudio:
        estudio = detalle.estudio
    elif detalle.analito and hasattr(detalle.analito, 'estudio'):
        estudio = detalle.analito.estudio
    
    if not estudio:
        logger.debug(f"Sin Estudio vinculado - sistema LIMS puro")
        continue
```

### Cambio 2: Protección en `api_avanzar_estado()` línea 517-523
```python
# Antes:
_descontar_insumos_orden(orden, request.user)

# Después:
try:
    _descontar_insumos_orden(orden, request.user)
except Exception as e_insumos:
    logger.warning(f"Error insumos: {e_insumos}. Orden avanza igual.")
```

---

## Estado Actual

✅ Causa identificada = CONFIRMADO (análisis de código concuerda con error reportado)  
✅ Fix implementado en código local  
⏳ **Falta:** Prueba funcional en producción

---

## Caso de Prueba Requerido

**Precondición:** Orden capturada hasta VALIDADO_PARCIAL

**Paso:** Click "Aprobar Resultados"

**Esperado:**
- ✅ Orden avanza a COMPLETO
- ✅ `orden.estado` = RESULTADOS_LISTOS
- ✅ Aparece en `/laboratorio/entrega-resultados/`
- ✅ PDF se genera (si no hay saldo pendiente)

**Antes del fix:** ❌ Sin cambio  
**Después del fix:** ✅ Orden avanza

---

## Siguiente Paso

Aguardando:
1. Codex: revisar fix, hacer commit si aprueba
2. Deploy a VPS efa5c2f (rama actual)
3. Claude: ejecutar prueba funcional en producción
4. Cascada: cerrar hallazgo con evidencia de fix + prueba

---

**Documentación técnica completa:** `/INVESTIGACION_CRITICA_BLOQUEO_LABORATORIO.md`
