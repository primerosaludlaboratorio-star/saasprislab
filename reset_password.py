#!/usr/bin/env python
"""
Script para resetear contraseña de cualquier usuario de Django
Uso: python reset_password.py [username] [nueva_password]
"""
import os
import sys
import django

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from core.models import Usuario

def resetear_password(username, password):
    """Resetea la contraseña de un usuario"""
    try:
        usuario = Usuario.objects.get(username=username)
        usuario.set_password(password)
        usuario.is_active = True
        usuario.save()
        print(f"[OK] Contrasena reseteada para '{username}'")
        print(f"     Usuario: {username}")
        print(f"     Nueva contrasena: {password}")
        return True
    except Usuario.DoesNotExist:
        print(f"[ERROR] Usuario '{username}' no encontrado")
        print("\nUsuarios disponibles:")
        for u in Usuario.objects.all():
            print(f"  - {u.username} (staff: {u.is_staff}, superuser: {u.is_superuser})")
        return False

if __name__ == '__main__':
    if len(sys.argv) >= 3:
        username = sys.argv[1]
        password = sys.argv[2]
        resetear_password(username, password)
    else:
        print("Uso: python reset_password.py [username] [nueva_password]")
        print("\nEjemplo: python reset_password.py admin mi_password_seguro")
