#!/usr/bin/env python3
"""Configura usuarios superadmin para empresas PRISLAB y Demo."""
import os
import sys

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import django
django.setup()

from django.contrib.auth import get_user_model
from core.models import Empresa, Sucursal

Usuario = get_user_model()


def _password_env() -> str:
    password = os.environ.get('PRISLAB_SUPERUSER_PASSWORD') or os.environ.get('DEV_ADMIN_PASSWORD')
    if not password:
        raise RuntimeError(
            'Falta PRISLAB_SUPERUSER_PASSWORD (o DEV_ADMIN_PASSWORD). Defina una contraseña segura antes de ejecutar este script.'
        )
    return password

print("=" * 60)
print("CONFIGURANDO ACCESOS SUPER ADMINISTRADOR")
print("=" * 60)

# 1. Crear/verificar Empresa PRISLAB
empresa_prislab, created = Empresa.objects.get_or_create(
    nombre='PRISLAB',
    defaults={'rfc': 'PRI123456789'}
)
print(f"[OK] Empresa PRISLAB: {'creada' if created else 'ya existe'} (ID: {empresa_prislab.id})")

# 2. Crear/verificar Sucursal principal PRISLAB
sucursal_prislab, created = Sucursal.objects.get_or_create(
    empresa=empresa_prislab,
    nombre='Sucursal Principal',
    defaults={
        'codigo_sucursal': 'PRI001',
        'direccion': 'Av. Principal 123, Ciudad de Mexico',
        'telefono': '5555555555'
    }
)
print(f"[OK] Sucursal PRISLAB: {'creada' if created else 'ya existe'} (ID: {sucursal_prislab.id})")

# 3. Crear/verificar Empresa Demo
empresa_demo, created = Empresa.objects.get_or_create(
    nombre='Clinica Demo',
    defaults={'rfc': 'DEMO123456789'}
)
print(f"[OK] Empresa Demo: {'creada' if created else 'ya existe'} (ID: {empresa_demo.id})")

# 4. Crear/verificar Sucursal Demo
sucursal_demo, created = Sucursal.objects.get_or_create(
    empresa=empresa_demo,
    nombre='Sucursal Demo Principal',
    defaults={
        'codigo_sucursal': 'DEM001',
        'direccion': 'Calle Demo 456',
        'telefono': '5551234567'
    }
)
print(f"[OK] Sucursal Demo: {'creada' if created else 'ya existe'} (ID: {sucursal_demo.id})")

# 5. Crear usuario Super Admin PRISLAB
admin_prislab, created = Usuario.objects.get_or_create(
    username='admin_prislab',
    defaults={
        'email': 'admin@prislab.com',
        'first_name': 'Super',
        'last_name': 'Admin PRISLAB',
        'is_staff': True,
        'is_superuser': True,
        'empresa': empresa_prislab,
        'sucursal': sucursal_prislab,
        'rol': 'ADMIN'
    }
)
if created:
    admin_prislab.set_password(_password_env())
    admin_prislab.save()
    print(f"[OK] Usuario admin_prislab CREADO")
else:
    print(f"[OK] Usuario admin_prislab ya existe")

# 6. Crear usuario Super Admin Demo
admin_demo, created = Usuario.objects.get_or_create(
    username='admin_demo',
    defaults={
        'email': 'admin@demo.com',
        'first_name': 'Super',
        'last_name': 'Admin Demo',
        'is_staff': True,
        'is_superuser': True,
        'empresa': empresa_demo,
        'sucursal': sucursal_demo,
        'rol': 'ADMIN'
    }
)
if created:
    admin_demo.set_password(_password_env())
    admin_demo.save()
    print(f"[OK] Usuario admin_demo CREADO")
else:
    print(f"[OK] Usuario admin_demo ya existe")

# 7. Verificar usuario admin general (si existe, actualizar empresa)
admin_general = Usuario.objects.filter(username='admin').first()
if admin_general and not admin_general.empresa:
    admin_general.empresa = empresa_prislab
    admin_general.sucursal_default = sucursal_prislab
    admin_general.save()
    print(f"[OK] Usuario 'admin' actualizado con empresa PRISLAB")

print("\n" + "=" * 60)
print("DATOS DE ACCESO - SUPER ADMINISTRADORES")
print("=" * 60)
print(f"""
EMPRESA: PRISLAB
----------------
URL:      http://127.0.0.1:8000/
Usuario:  admin_prislab
Password: [definida por PRISLAB_SUPERUSER_PRISLAB_PASSWORD o PRISLAB_SUPERUSER_PASSWORD]
Empresa:  {empresa_prislab.nombre}
Sucursal: {sucursal_prislab.nombre}
Rol:      SUPER ADMINISTRADOR

EMPRESA: CLINICA DEMO
---------------------
URL:      http://127.0.0.1:8000/
Usuario:  admin_demo
Password: [definida por PRISLAB_SUPERUSER_DEMO_PASSWORD o PRISLAB_SUPERUSER_PASSWORD]
Empresa:  {empresa_demo.nombre}
Sucursal: {sucursal_demo.nombre}
Rol:      SUPER ADMINISTRADOR

ADMIN GENERAL (legacy)
----------------------
Usuario:  admin
Password: [definida por DEV_ADMIN_PASSWORD]
Empresa:  {empresa_prislab.nombre if admin_general else 'N/A'}
""")
print("=" * 60)
