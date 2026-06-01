# 📦 GUÍA: CARGA DE INVENTARIO Y USUARIOS

## 🎯 PASO 1: PREPARAR EL ARCHIVO EXCEL

### Formato Recomendado del Excel

Tu archivo Excel debe tener las siguientes columnas (pueden estar en cualquier orden):

| Columna | Requerido | Ejemplos de nombres válidos |
|---------|-----------|----------------------------|
| Código/Clave | ✅ SÍ | Codigo, Clave, SKU, Código de Barras |
| Nombre | ✅ SÍ | Nombre, Producto, Descripción |
| Laboratorio | ⚠️ Opcional | Laboratorio, Marca, Fabricante |
| Sustancia Activa | ⚠️ Opcional | Sustancia, Genérico, Activo |
| Precio Compra | ⚠️ Opcional | Compra, Costo, Adquisición |
| Precio Venta | ⚠️ Opcional | Venta, Publico, Precio |
| Stock | ⚠️ Opcional | Stock, Existencia, Inventario, Cantidad |

### Ejemplo de Excel válido:

```
| Codigo | Nombre                    | Laboratorio | Precio_Compra | Precio_Venta | Stock |
|--------|---------------------------|-------------|---------------|--------------|-------|
| 7501   | Paracetamol 500mg Tab     | BAYER       | 2.50          | 5.00         | 100   |
| 7502   | Amoxicilina 500mg Cap     | PFIZER      | 15.00         | 30.00        | 50    |
| 7503   | Ibuprofeno 400mg Tab      | GENERICO    | 1.80          | 3.50         | 200   |
```

---

## 🚀 PASO 2: CARGAR EL INVENTARIO

### Opción A: Con detección automática de columnas (Recomendado)

```bash
# 1. Activar entorno virtual
venv\Scripts\activate

# 2. Copiar tu archivo Excel a la carpeta del proyecto
# Ejemplo: inventario_farmacia.xlsx

# 3. Ejecutar el comando
python manage.py cargar_inventario_excel inventario_farmacia.xlsx --skip-header
```

### Opción B: Si el Excel NO tiene encabezados

```bash
python manage.py cargar_inventario_excel inventario_farmacia.xlsx
```

### Opción C: Especificar empresa diferente

```bash
python manage.py cargar_inventario_excel inventario_farmacia.xlsx --skip-header --empresa-id 2
```

---

## 👥 PASO 3: CREAR USUARIOS

### 1. Editar el archivo de usuarios (OPCIONAL)

Si quieres personalizar los usuarios, edita: `crear_usuarios.py`

Busca la sección `usuarios = [...]` y modifica:

```python
{
    'username': 'nancy',
    'email': 'nancy@prislab.com',
    'first_name': 'Nancy',
    'last_name': 'Pérez',
    'password': 'nancy2026',  # ⚠️ CAMBIAR EN PRODUCCIÓN
    'is_staff': True,
    'is_superuser': False,
},
```

### 2. Ejecutar el script

```bash
python crear_usuarios.py
```

### 3. Resultado esperado

```
================================================================================
CREACION DE USUARIOS - PRISLAB GOLD
================================================================================
Empresa: PRISLAB

[OK] Usuario 'nancy' creado exitosamente
     Email: nancy@prislab.com
     Contraseña: nancy2026
     Rol: Admin

[OK] Usuario 'drjuan' creado exitosamente
     Email: drjuan@prislab.com
     Contraseña: medico2026
     Rol: Admin

...

================================================================================
RESUMEN
================================================================================
Usuarios creados: 5
Usuarios existentes (no modificados): 0
Total en sistema: 6

[EXITO] Proceso completado
```

---

## 🔍 PASO 4: VERIFICAR LA CARGA

### Opción A: Desde el Admin de Django

1. Iniciar servidor: `python manage.py runserver`
2. Ir a: http://127.0.0.1:8000/admin/
3. Login con tus credenciales de admin
4. Ver sección "Productos y Servicios"

### Opción B: Desde la consola

```bash
python manage.py shell -c "from core.models import Producto; print(f'Productos cargados: {Producto.objects.count()}')"
```

---

## ⚠️ SOLUCIÓN DE PROBLEMAS

### Error: "ModuleNotFoundError: No module named 'openpyxl'"

**Solución:**
```bash
pip install openpyxl
```

### Error: "Archivo no encontrado"

**Solución:**
- Verifica que el archivo esté en la carpeta del proyecto
- Usa la ruta completa: `python manage.py cargar_inventario_excel "C:\Users\jonil\Desktop\inventario.xlsx"`

### Error: "Duplicate entry for key 'codigo_barras'"

**Solución:**
- Algunos productos ya existen en la base de datos
- El script los actualizará automáticamente
- Si quieres empezar de cero, vacía la tabla primero:

```bash
python manage.py shell -c "from core.models import Producto; Producto.objects.all().delete()"
```

### Productos no se detectan correctamente

**Solución:**
1. Verifica que tu Excel tenga encabezados en la primera fila
2. Usa `--skip-header` si tiene encabezados
3. Si no tiene encabezados, NO uses `--skip-header`

---

## 📊 FORMATOS DE DATOS ACEPTADOS

### Precios

✅ Válidos:
- `15.50`
- `15,50`
- `$15.50`
- `$15,50`

❌ Inválidos:
- `15.50 MXN` (se quitará automáticamente)
- Vacío (se pondrá en 0)

### Códigos de Barras

✅ Válidos:
- Números: `7501234567890`
- Alfanuméricos: `ABC-12345`
- Con guiones: `75-012-345`

❌ Inválidos:
- Duplicados (se actualizará el existente)
- Vacíos (se saltará la fila)

---

## 📝 PLANTILLA DE EXCEL

Si necesitas una plantilla, aquí está el formato mínimo:

**Archivo: plantilla_inventario.xlsx**

| Codigo | Nombre | Laboratorio | Precio_Compra | Precio_Venta | Stock |
|--------|--------|-------------|---------------|--------------|-------|
| 001    | Producto 1 | Lab A | 10.00 | 20.00 | 100 |
| 002    | Producto 2 | Lab B | 15.00 | 30.00 | 50 |

Puedes descargar esta plantilla o crear la tuya con estos encabezados.

---

## 🎯 ¿NECESITAS AYUDA?

Si tienes problemas con la carga:

1. Comparte las primeras 5 filas de tu Excel
2. Indica qué columnas tiene
3. Copia el mensaje de error completo

---

**¡Listo! Tu inventario estará cargado en minutos** 🚀
