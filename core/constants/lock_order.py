"""
ORDEN UNIVERSAL DE BLOQUEOS EN PRISLAB v1.14 — Bankguard
========================================================

REGLA ORO: Todos los bloqueos DEBEN respetar este orden.
Violar esto = Deadlock en producción.

ORDEN DETERMINISTA (de padre a hijo):
--------------------------------------
1. Empresa
2. Sucursal  
3. Venta / OrdenDeServicio / Receta
4. MovimientoCaja / MovimientoInventario / Pago / PagoOrden
5. DetalleVenta / DetalleOrden / ResultadoParametro

EJEMPLOS CORRECTOS:
-------------------
✅ select_for_update(Empresa) → Sucursal → Venta → MovimientoCaja
✅ select_for_update(OrdenDeServicio) → PagoOrden
✅ select_for_update(Venta) → MovimientoCaja → DetalleVenta
✅ select_for_update(Producto) → MovimientoInventario

EJEMPLOS INCORRECTOS (DEADLOCK):
--------------------------------
❌ select_for_update(MovimientoCaja) → Venta (INVERTIDO)
❌ select_for_update(PagoOrden) → OrdenDeServicio (INVERTIDO)
❌ select_for_update(DetalleVenta) → Venta (INVERTIDO)

IMPLEMENTACIÓN EN CÓDIGO:
-------------------------

# CORRECTO: Orden padre → hijo
with transaction.atomic():
    venta = Venta.objects.select_for_update().get(pk=venta_id)
    mov = MovimientoCaja.objects.select_for_update().get_or_create(
        idempotency_key=key,
        defaults={...}
    )

# INCORRECTO: Orden hijo → padre (¡DEADLOCK!)
with transaction.atomic():
    mov = MovimientoCaja.objects.select_for_update().get(pk=mov_id)  # ❌ Hijo primero
    venta = Venta.objects.select_for_update().get(pk=mov.venta_id)   # ❌ Padre después

CUMPLIMIENTO:
-------------
- Code Review: Verificar orden en cada transacción con select_for_update()
- Test: pytest tests/test_lock_order.py (detecta ciclos)
- CI/CD: Bloquear merge si hay violación del orden

MIGRACIONES:
------------
Al agregar nuevos modelos, actualizar este archivo y LOCK_ORDER.

Autor: Windsurf Cascade
Versión: 1.14-Bankguard
Fecha: 2026-04-03
"""

# Diccionario de orden para validación programática
LOCK_ORDER = {
    'Empresa': 1,
    'Sucursal': 2,
    'Venta': 3,
    'OrdenDeServicio': 3,
    'Receta': 3,
    'MovimientoCaja': 4,
    'MovimientoInventario': 4,
    'Pago': 4,
    'PagoOrden': 4,
    'DetalleVenta': 5,
    'DetalleOrden': 5,
    'ResultadoParametro': 5,
}

def validate_lock_order(models_locked):
    """
    Valida que el orden de bloqueos sea correcto.
    
    Args:
        models_locked: Lista de tuplas (nombre_modelo, timestamp_lock)
    
    Raises:
        RuntimeError: Si el orden viola LOCK_ORDER
    
    Ejemplo:
        validate_lock_order([
            ('Venta', 1),
            ('MovimientoCaja', 2),
        ])  # OK
        
        validate_lock_order([
            ('MovimientoCaja', 1),
            ('Venta', 2),
        ])  # RuntimeError
    """
    for i in range(len(models_locked) - 1):
        current_model, current_time = models_locked[i]
        next_model, next_time = models_locked[i + 1]
        
        current_rank = LOCK_ORDER.get(current_model, 99)
        next_rank = LOCK_ORDER.get(next_model, 99)
        
        if next_rank < current_rank:
            raise RuntimeError(
                f"VIOLACIÓN ORDEN DE LOCKS: {current_model} (rango {current_rank}) "
                f"bloqueado ANTES que {next_model} (rango {next_rank}). "
                f"Orden correcto: padre → hijo. Revisar core/constants/lock_order.py"
            )
    return True


if __name__ == "__main__":
    # Test básico
    print("Validando orden de locks...")
    
    # Caso correcto
    validate_lock_order([
        ('Empresa', 1),
        ('Sucursal', 2),
        ('Venta', 3),
        ('MovimientoCaja', 4),
    ])
    print("✅ Caso correcto: Empresa → Sucursal → Venta → MovimientoCaja")
    
    # Caso incorrecto (debe fallar)
    try:
        validate_lock_order([
            ('MovimientoCaja', 1),
            ('Venta', 2),
        ])
        print("❌ Error: Debería haber fallado")
    except RuntimeError as e:
        print(f"✅ Caso incorrecto detectado: {e}")
    
    print("\nDocumentación completa en docstring.")
