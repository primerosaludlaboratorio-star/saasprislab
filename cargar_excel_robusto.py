"""
Script Ultra-Robusto: Carga Excel con pandas (ignorando todo error)
"""
import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from core.models import Producto, Empresa, Sucursal
from decimal import Decimal
import pandas as pd

_eid = os.environ.get("PRISLAB_EMPRESA_ID")
if not _eid:
    print("[ERROR] Defina la variable de entorno PRISLAB_EMPRESA_ID (pk de Empresa).")
    sys.exit(1)
try:
    _empresa_ref = Empresa.objects.get(pk=int(_eid))
except (ValueError, Empresa.DoesNotExist):
    print(f"[ERROR] Empresa id={_eid!r} no válida o inexistente.")
    sys.exit(1)

archivo = "Productos-farmacia-2026-02-10-10-31.xlsx"

print("=" * 80)
print("CARGA ROBUSTA CON PANDAS")
print("=" * 80)

try:
    # Pandas es mucho más robusto para Excel problemáticos
    # skiprows=2 porque los headers están en fila 3 (índice 2 en base-0)
    df = pd.read_excel(archivo, sheet_name='Inventario', skiprows=2, engine='openpyxl')
    
    print(f"[OK] Excel leído: {len(df)} filas")
    print(f"[OK] Columnas: {len(df.columns)}")
    print()
    
    print("[COLUMNAS DETECTADAS]:")
    for i, col in enumerate(df.columns[:15], 1):
        print(f"  {i}. {col}")
    print()
    
    empresa = _empresa_ref
    sucursal = Sucursal.objects.filter(empresa=empresa).first()
    
    print("[PROCESANDO...]")
    creados = 0
    actualizados = 0
    errores = 0
    
    for idx, row in df.iterrows():
        try:
            # Extraer datos con pandas (maneja NaN automáticamente)
            nombre = str(row.get('Nombre del Producto', '')).strip()
            codigo = str(row.get('Código de Barras', '')).strip()
            
            # Saltar si no hay datos críticos
            if not nombre or nombre == 'nan' or not codigo or codigo == 'nan':
                continue
            
            marca = str(row.get('Marca', 'GENERICO')).strip()
            if marca == 'nan':
                marca = 'GENERICO'
            
            # Precio
            precio = Decimal('0')
            try:
                precio_raw = row.get('Precio Público')
                if pd.notna(precio_raw):
                    precio = Decimal(str(precio_raw).replace(',', '').replace('$', '').strip())
                    if precio < 0:
                        precio = Decimal('0')
            except:
                pass
            
            # Costo
            costo = Decimal('0')
            try:
                costo_raw = row.get('Costo')
                if pd.notna(costo_raw):
                    costo = Decimal(str(costo_raw).replace(',', '').replace('$', '').strip())
                    if costo < 0:
                        costo = Decimal('0')
            except:
                pass
            
            # Stock
            stock = 0
            try:
                stock_raw = row.get('Stock Total')
                if pd.notna(stock_raw):
                    stock = int(float(stock_raw))
                    if stock < 0:
                        stock = 0
            except:
                pass
            
            # IVA
            iva = Decimal('16')
            try:
                iva_raw = row.get('IVA')
                if pd.notna(iva_raw):
                    iva_str = str(iva_raw).replace('%', '').strip()
                    if iva_str and iva_str != 'nan':
                        iva = Decimal(iva_str)
            except:
                pass
            
            # Receta Médica
            es_antibiotico = False
            try:
                receta_raw = str(row.get('Receta Médica', '')).lower()
                es_antibiotico = 'sí' in receta_raw or 'si' in receta_raw or 'obligatorio' in receta_raw
            except:
                pass
            
            # Crear/Actualizar producto
            producto, created = Producto.objects.update_or_create(
                codigo_barras=codigo,
                defaults={
                    'empresa': empresa,
                    'sucursal': sucursal,
                    'nombre': nombre[:255],
                    'marca_laboratorio': marca[:150],
                    'forma_farmaceutica': 'Pieza',
                    'concentracion': 'N/A',
                    'presentacion': '1',
                    'precio_compra': costo,
                    'precio_publico': precio,
                    'stock': stock,
                    'iva_porcentaje': iva,
                    'clasificacion_sanitaria': 'IV' if es_antibiotico else 'VI',
                    'categoria': 'ANTIBIOTICO' if es_antibiotico else 'GENERICO',
                    'es_antibiotico': es_antibiotico,
                    'es_servicio': False,
                }
            )
            
            if created:
                creados += 1
            else:
                actualizados += 1
            
            if (creados + actualizados) % 100 == 0:
                print(f"  [{creados + actualizados} productos procesados...]")
        
        except Exception as e:
            errores += 1
            if errores <= 10:
                print(f"  [!] Error fila {idx + 4}: {e}")
    
    print()
    print("=" * 80)
    print("[CARGA COMPLETADA]")
    print("=" * 80)
    print(f"Productos NUEVOS: {creados}")
    print(f"Productos ACTUALIZADOS: {actualizados}")
    print(f"Errores: {errores}")
    print(f"Total en BD: {Producto.objects.count()}")
    print("=" * 80)
    
    # Mostrar algunos ejemplos
    print()
    print("[EJEMPLOS DE PRODUCTOS CARGADOS]:")
    for prod in Producto.objects.all()[:10]:
        print(f"  {prod.codigo_barras} | {prod.nombre[:50]} | ${prod.precio_publico} | Stock: {prod.stock}")

except Exception as e:
    print(f"[ERROR CRITICO] {e}")
    import traceback
    traceback.print_exc()
