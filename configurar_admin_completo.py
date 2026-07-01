# -*- coding: utf-8 -*-
"""
Script para asignar empresa y sucursal al usuario admin.
"""
import os
import sys
import django
import logging

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth import get_user_model
from core.models import Empresa, Sucursal

User = get_user_model()

try:
    admin_user = User.objects.get(username='admin')

    eid = os.environ.get("PRISLAB_EMPRESA_ID")
    if eid:
        try:
            empresa = Empresa.objects.get(pk=int(eid))
        except (ValueError, Empresa.DoesNotExist):
            print(f"[ERROR] PRISLAB_EMPRESA_ID={eid!r} inválido.")
            sys.exit(1)
    else:
        empresa = Empresa.objects.filter(nombre__icontains='PRISLAB').first()
    if not empresa:
        print("[ERROR] Sin empresa: defina PRISLAB_EMPRESA_ID o cree una empresa con nombre que contenga PRISLAB.")
        sys.exit(1)
    
    # Obtener la sucursal Matriz
    sucursal = Sucursal.objects.filter(nombre__icontains='Matriz').first()
    if not sucursal and empresa:
        sucursal = Sucursal.objects.filter(empresa=empresa).first()
    
    # Asignar empresa y sucursal
    if empresa:
        admin_user.empresa = empresa
        print(f"[OK] Empresa asignada: {empresa.nombre}")
    
    if sucursal:
        if hasattr(admin_user, 'add_sucursal'):
            admin_user.add_sucursal(sucursal)
        else:
            admin_user.sucursal = sucursal
        print(f"[OK] Sucursal asignada: {sucursal.nombre}")
    
    # Asegurarse de que el rol sea ADMIN
    admin_user.rol = 'ADMIN'
    admin_user.is_staff = True
    admin_user.is_superuser = True
    
    admin_user.save()
    
    print("\n" + "="*60)
    print("[OK] USUARIO ADMIN CONFIGURADO CORRECTAMENTE")
    print("="*60)
    print(f"Usuario: admin")
    print("Contraseña: [definida por DEV_ADMIN_PASSWORD]")
    print(f"Rol: {admin_user.rol}")
    print(f"Empresa: {admin_user.empresa.nombre if admin_user.empresa else 'Sin asignar'}")
    print(f"Sucursal: {admin_user.sucursal.nombre if admin_user.sucursal else 'Sin asignar'}")
    print("\nAcceso: http://127.0.0.1:8000/login/")
    print("="*60)
    
except User.DoesNotExist:
    print("[ERROR] El usuario 'admin' no existe.")
except Exception as e:
    logging.getLogger(__name__).exception("Error inesperado en funcion_desconocida (configurar_admin_completo.py)")
    print(f"[ERROR] Ocurrio un error: {e}")
    import traceback
    traceback.print_exc()