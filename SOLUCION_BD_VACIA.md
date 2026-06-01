## ⚠️ BASE DE DATOS VACÍA - ACCIONES REQUERIDAS

### **SITUACIÓN ACTUAL:**
- ✅ Servidor corriendo en `http://127.0.0.1:8000/`
- ❌ Base de datos sin datos (0 empresas, 0 órdenes)
- ❌ No se puede acceder a `/laboratorio/captura/<id>/` sin órdenes

---

### **SOLUCIÓN: POBLAR LA BASE DE DATOS**

#### **OPCIÓN 1: Crear Superusuario y Datos Mínimos (RECOMENDADO)**

```bash
# 1. Crear superusuario
python manage.py createsuperuser
# Usuario: admin
# Email: admin@prislab.com
# Password: admin123

# 2. Acceder al admin
# URL: http://127.0.0.1:8000/admin/
# Crear manualmente: Empresa, Sucursal, Usuario, Paciente, Orden

# 3. O usar fixtures (si existen)
python manage.py loaddata initial_data.json
```

#### **OPCIÓN 2: Cargar Datos Legacy del LIMS**

```bash
# Si tienes los CSVs del LIMS en datos_legacy/
python manage.py cargar_legacy

# Esto cargará:
# - Secciones de Laboratorio
# - Estudios (98 estudios)
# - Parámetros (cientos)
# - Rangos de Referencia
```

#### **OPCIÓN 3: Script de Datos de Prueba**

Crear un script para poblar datos iniciales:

```python
# crear_datos_prueba.py
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from core.models import Empresa, Sucursal, Usuario, Paciente, OrdenDeServicio, Estudio, DetalleOrden
from django.contrib.auth.hashers import make_password
from datetime import datetime, timedelta

# 1. Crear Empresa
empresa = Empresa.objects.create(
    nombre='PRISLAB S.A. de C.V.',
    nombre_comercial='PRISLAB',
    rfc='PRI180101ABC',
    activa=True
)

# 2. Crear Sucursal
sucursal = Sucursal.objects.create(
    empresa=empresa,
    nombre='Matriz',
    direccion='Av. Principal 123',
    ciudad='Ciudad de México',
    estado='CDMX',
    codigo_postal='01000',
    telefono='5512345678',
    activa=True
)

# 3. Crear Usuario Admin
usuario = Usuario.objects.create(
    username='admin',
    email='admin@prislab.com',
    password=make_password('admin123'),
    empresa=empresa,
    sucursal=sucursal,
    rol='ADMIN',
    is_staff=True,
    is_superuser=True
)

# 4. Crear Paciente de Prueba
paciente = Paciente.objects.create(
    empresa=empresa,
    nombre='Juan',
    apellido_paterno='Pérez',
    apellido_materno='García',
    fecha_nacimiento=datetime(1990, 5, 15).date(),
    sexo='M',
    telefono='5512345678',
    email='juan.perez@email.com'
)

# 5. Crear Estudio de Prueba (si no existe)
estudio, created = Estudio.objects.get_or_create(
    empresa=empresa,
    codigo='QS-001',
    defaults={
        'nombre': 'Química Sanguínea',
        'precio': 350.00,
        'tiempo_entrega_horas': 24
    }
)

# 6. Crear Orden de Prueba
orden = OrdenDeServicio.objects.create(
    empresa=empresa,
    sucursal=sucursal,
    paciente=paciente,
    folio=f'ORD-{datetime.now().strftime("%Y%m%d%H%M%S")}',
    fecha_creacion=datetime.now(),
    estado='PAGADO',
    total=350.00,
    total_pagado=350.00,
    responsable_ingreso=usuario
)

# 7. Crear Detalle de Orden
DetalleOrden.objects.create(
    orden=orden,
    estudio=estudio,
    precio_unitario=350.00,
    cantidad=1,
    subtotal=350.00
)

print("✅ DATOS DE PRUEBA CREADOS")
print(f"   - Empresa: {empresa.nombre}")
print(f"   - Usuario: admin / admin123")
print(f"   - Paciente: {paciente.nombre_completo}")
print(f"   - Orden ID: {orden.id}")
print(f"\n🔗 URL de Captura:")
print(f"   http://127.0.0.1:8000/laboratorio/captura/{orden.id}/")
```

---

### **URLs DISPONIBLES AHORA MISMO:**

1. **Login:**
   ```
   http://127.0.0.1:8000/
   ```

2. **Admin Panel:**
   ```
   http://127.0.0.1:8000/admin/
   ```

3. **Dashboard (necesita login):**
   ```
   http://127.0.0.1:8000/farmacia/dashboard/
   ```

4. **LIMS - Catálogo de Estudios:**
   ```
   http://127.0.0.1:8000/lims/estudios/
   ```

---

### **SIGUIENTE PASO RECOMENDADO:**

1. Ejecutar `python manage.py createsuperuser`
2. Acceder a `/admin/` y crear datos manualmente
3. O ejecutar el script `crear_datos_prueba.py`

---

**Estado:** ✅ Sistema funcionando, esperando datos iniciales
