# -*- coding: utf-8 -*-
"""
Script para resetear la contraseña del usuario admin.
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth import get_user_model

User = get_user_model()

try:
    admin_user = User.objects.get(username='admin')
    admin_user.set_password('admin123')
    admin_user.save()
    print("[OK] Contraseña reseteada exitosamente para el usuario 'admin'")
    print("Usuario: admin")
    print("Contraseña: admin123")
    print("\nPuedes iniciar sesion en: http://127.0.0.1:8000/login/")
except User.DoesNotExist:
    print("[ERROR] El usuario 'admin' no existe.")
except Exception as e:
    print(f"[ERROR] Ocurrio un error: {e}")
