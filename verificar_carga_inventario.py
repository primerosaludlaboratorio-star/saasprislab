"""
Verificación del inventario cargado
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from core.models import Producto

print("=" * 80)
print("VERIFICACIÓN DE INVENTARIO CARGADO")
print("=" * 80)
print()

total = Producto.objects.count()
print(f"[OK] Total de productos en sistema: {total}")
print()

print("[EJEMPLOS DE PRODUCTOS CARGADOS]")
print("=" * 80)
print(f"{'Codigo':<15} | {'Nombre':<45} | {'Precio':>10} | {'Stock':>6}")
print("-" * 80)

for p in Producto.objects.all()[:15]:
    nombre = p.nombre[:45] if len(p.nombre) > 45 else p.nombre
    precio = f"${p.precio_publico}"
    print(f"{p.codigo_barras:<15} | {nombre:<45} | {precio:>10} | {p.stock:>6}")

print("=" * 80)
print()

# Estadisticas adicionales
con_stock = Producto.objects.filter(stock__gt=0).count()
sin_stock = Producto.objects.filter(stock=0).count()
antibioticos = Producto.objects.filter(es_antibiotico=True).count()

print("[ESTADISTICAS]")
print(f"  - Productos con stock: {con_stock}")
print(f"  - Productos sin stock: {sin_stock}")
print(f"  - Antibioticos: {antibioticos}")
print()

# Rango de precios
if total > 0:
    from decimal import Decimal
    precios = Producto.objects.exclude(precio_publico=Decimal('0'))
    if precios.exists():
        min_precio = precios.order_by('precio_publico').first()
        max_precio = precios.order_by('-precio_publico').first()
        print("[RANGO DE PRECIOS]")
        print(f"  - Mas economico: ${min_precio.precio_publico} ({min_precio.nombre[:30]}...)")
        print(f"  - Mas costoso: ${max_precio.precio_publico} ({max_precio.nombre[:30]}...)")

print()
print("=" * 80)
print("[EXITO] INVENTARIO LISTO PARA OPERAR")
print("=" * 80)
