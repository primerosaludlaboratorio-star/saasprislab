# -*- coding: utf-8 -*-
"""
Script para crear superusuario admin y Responsable Sanitario
Fecha: 2026-01-25
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth import get_user_model
from core.models import Empresa, Sucursal
from laboratorio.models import ResponsableSanitario

User = get_user_model()

print("="*70)
print("CREANDO SUPERUSUARIO Y RESPONSABLE SANITARIO")
print("="*70)

# 1. Obtener empresa y sucursal
try:
    empresa = Empresa.objects.get(nombre="PRISLAB S.A. de C.V.")
    sucursal = Sucursal.objects.filter(empresa=empresa).first()
    print(f"\n[OK] Empresa encontrada: {empresa.nombre}")
    print(f"[OK] Sucursal encontrada: {sucursal.nombre}")
except Empresa.DoesNotExist:
    print("\n[ERROR] No se encontro la empresa. Ejecuta crear_datos_prueba_completos.py primero.")
    exit(1)

# 2. Crear o actualizar superusuario
try:
    admin_user = User.objects.get(username='admin')
    print(f"\n[INFO] Usuario 'admin' ya existe. Actualizando...")
    admin_user.set_password(os.environ.get('DEV_ADMIN_PASSWORD', 'admin123'))
    admin_user.is_superuser = True
    admin_user.is_staff = True
    admin_user.is_active = True
    admin_user.empresa = empresa
    admin_user.sucursal = sucursal
    admin_user.rol = 'ADMIN'
    admin_user.save()
    print(f"[OK] Usuario 'admin' actualizado correctamente")
except User.DoesNotExist:
    print(f"\n[INFO] Creando nuevo usuario 'admin'...")
    admin_user = User.objects.create_superuser(
        username='admin',
        email='admin@prislab.com',
        password=os.environ.get('DEV_ADMIN_PASSWORD', 'admin123'),
        first_name='Administrador',
        last_name='Sistema',
        empresa=empresa,
        sucursal=sucursal,
        rol='ADMIN'
    )
    print(f"[OK] Superusuario 'admin' creado correctamente")

# 3. Crear o actualizar Responsable Sanitario
try:
    responsable = ResponsableSanitario.objects.get(usuario=admin_user)
    print(f"\n[INFO] Responsable Sanitario ya existe. Actualizando...")
    responsable.empresa = empresa
    responsable.cedula_profesional = '9439502'
    responsable.universidad_titulo = 'UNIVERSIDAD VERACRUZANA'
    responsable.especialidad = 'Quimico Farmacobiologo'
    responsable.activo = True
    responsable.save()
    print(f"[OK] Responsable Sanitario actualizado")
except ResponsableSanitario.DoesNotExist:
    print(f"\n[INFO] Creando Responsable Sanitario...")
    responsable = ResponsableSanitario.objects.create(
        empresa=empresa,
        usuario=admin_user,
        cedula_profesional='9439502',
        universidad_titulo='UNIVERSIDAD VERACRUZANA',
        especialidad='Quimico Farmacobiologo',
        activo=True
    )
    print(f"[OK] Responsable Sanitario creado correctamente")

print("\n" + "="*70)
print("CONFIGURACION COMPLETADA EXITOSAMENTE")
print("="*70)
print(f"\nCREDENCIALES DE ACCESO:")
print(f"  URL: http://127.0.0.1:8000/login/")
print(f"  Usuario: admin")
print(f"  Password: admin123")
print(f"\nRESPONSABLE SANITARIO:")
print(f"  Nombre: {admin_user.get_full_name()}")
print(f"  Cedula: 9439502")
print(f"  Universidad: UNIVERSIDAD VERACRUZANA")
print("\n" + "="*70)
print("LISTO PARA INICIAR SESION")
print("="*70)
