# -*- coding: utf-8 -*-
"""
Script para asignar empresa y sucursal al usuario admin
"""
import os
import django
import logging

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth import get_user_model
from core.models import Empresa, Sucursal

User = get_user_model()

try:
    admin_user = User.objects.get(username='admin')
    empresa = Empresa.objects.get(nombre="PRISLAB S.A. de C.V.")
    sucursal = Sucursal.objects.get(empresa=empresa, nombre="Matriz")
    
    # Asignar empresa y sucursal
    admin_user.empresa = empresa
    admin_user.sucursal = sucursal
    admin_user.rol = 'ADMIN'
    admin_user.save()
    
    print("Usuario admin configurado correctamente:")
    print(f"  - Usuario: admin")
    print("  - Password: [definida por DEV_ADMIN_PASSWORD]")
    print(f"  - Empresa: {empresa.nombre}")
    print(f"  - Sucursal: {sucursal.nombre}")
    print(f"  - Rol: {admin_user.rol}")
    print(f"  - Es superusuario: {admin_user.is_superuser}")
    print("")
    print("Ahora puedes iniciar sesion en: http://127.0.0.1:8000/login/")
    
except User.DoesNotExist:
    print("ERROR: El usuario 'admin' no existe")
except Empresa.DoesNotExist:
    print("ERROR: La empresa 'PRISLAB S.A. de C.V.' no existe")
except Sucursal.DoesNotExist:
    print("ERROR: La sucursal 'Matriz' no existe")
except Exception as e:
    logging.getLogger(__name__).exception("Error inesperado en funcion_desconocida (configurar_admin.py)")
    print(f"ERROR: {e}")