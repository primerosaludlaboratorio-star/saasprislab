#!/usr/bin/env python
"""
Script para crear o resetear un superusuario de Django
"""
import os
import sys
import django

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from core.models import Usuario

def crear_o_resetear_admin():
    """Crea o resetea el usuario admin. Use DEV_ADMIN_PASSWORD en .env para producción."""
    username = 'admin'
    password = os.environ.get('DEV_ADMIN_PASSWORD')
    if not password:
        raise RuntimeError(
            'Falta DEV_ADMIN_PASSWORD. Defina una contraseña segura antes de ejecutar este script.'
        )
    
    try:
        # Intentar obtener el usuario existente
        usuario = Usuario.objects.get(username=username)
        print(f"Usuario '{username}' encontrado. Reseteando contraseña...")
        usuario.set_password(password)
        usuario.is_staff = True
        usuario.is_superuser = True
        usuario.is_active = True
        usuario.save()
        print(f"[OK] Contrasena reseteada para '{username}'")
    except Usuario.DoesNotExist:
        # Crear nuevo usuario
        print(f"Creando nuevo usuario '{username}'...")
        usuario = Usuario.objects.create_user(
            username=username,
            password=password,
            email='admin@prislab.com',
            is_staff=True,
            is_superuser=True,
            is_active=True
        )
        print(f"[OK] Usuario '{username}' creado exitosamente")
    
    print("\n=== CREDENCIALES DE ACCESO ===")
    print(f"   Usuario: {username}")
    print("   Contrasena: [definida por DEV_ADMIN_PASSWORD]")
    print("\n[IMPORTANTE] Cambia esta contrasena despues del primer login por seguridad.")

if __name__ == '__main__':
    crear_o_resetear_admin()
