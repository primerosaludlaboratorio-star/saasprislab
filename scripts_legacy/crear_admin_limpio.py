# -*- coding: utf-8 -*-
"""
Script para crear o recrear el usuario admin completamente.
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth import get_user_model
from core.models import Empresa, Sucursal

User = get_user_model()

print("="*70)
print("CONFIGURACION DEL USUARIO ADMIN")
print("="*70)

try:
    # Obtener o crear empresa
    empresa, created = Empresa.objects.get_or_create(
        nombre="PRISLAB S.A. de C.V.",
        defaults={
            'rfc': 'PRS123456789',
            'direccion': 'Av. Principal #123',
            'telefono': '2281234567'
        }
    )
    print(f"\n[1/4] Empresa: {empresa.nombre} {'(creada)' if created else '(existente)'}")
    
    # Obtener o crear sucursal
    sucursal, created = Sucursal.objects.get_or_create(
        empresa=empresa,
        nombre="Matriz",
        defaults={
            'codigo_sucursal': 'SUC-001',
            'direccion': 'Av. Principal #123',
            'telefono': '2281234567',
            'activa': True
        }
    )
    print(f"[2/4] Sucursal: {sucursal.nombre} {'(creada)' if created else '(existente)'}")
    
    # Eliminar usuario admin si existe para recrearlo
    if User.objects.filter(username='admin').exists():
        User.objects.filter(username='admin').delete()
        print("[3/4] Usuario admin anterior eliminado")
    
    # Crear nuevo usuario admin (CICLO 12: desde env)
    admin_user = User.objects.create_user(
        username='admin',
        email='admin@prislab.com',
        password=os.environ.get('DEV_ADMIN_PASSWORD', 'admin123'),
        first_name='Administrador',
        last_name='Sistema',
        empresa=empresa,
        sucursal=sucursal,
        rol='ADMIN',
        is_staff=True,
        is_superuser=True,
        is_active=True
    )
    
    print("[4/4] Usuario admin creado exitosamente")
    
    print("\n" + "="*70)
    print("CREDENCIALES DE ACCESO")
    print("="*70)
    print("URL: http://127.0.0.1:8000/login/")
    print("Usuario: admin")
    print("Contraseña: admin123")
    print("\nEmpresa: " + empresa.nombre)
    print("Sucursal: " + sucursal.nombre)
    print("Rol: ADMIN")
    print("Superusuario: Si")
    print("="*70)
    print("\n[OK] Puedes iniciar sesion ahora!")
    
except Exception as e:
    print(f"\n[ERROR] Ocurrio un error: {e}")
    import traceback
    traceback.print_exc()
