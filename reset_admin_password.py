# -*- coding: utf-8 -*-
"""
Script para resetear la contraseña del usuario admin.
"""
import os
import django
import logging

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth import get_user_model

User = get_user_model()

try:
    admin_user = User.objects.get(username='admin')
    password = os.environ.get('DEV_ADMIN_PASSWORD')
    if not password:
        raise RuntimeError('Falta DEV_ADMIN_PASSWORD. Defina una contraseña segura antes de ejecutar este script.')
    admin_user.set_password(password)
    admin_user.save()
    print("[OK] Contraseña reseteada exitosamente para el usuario 'admin'")
    print("Usuario: admin")
    print("Contraseña: [definida por DEV_ADMIN_PASSWORD]")
    print("\nPuedes iniciar sesion en: http://127.0.0.1:8000/login/")
except User.DoesNotExist:
    print("[ERROR] El usuario 'admin' no existe.")
except Exception as e:
    logging.getLogger(__name__).exception("Error inesperado en funcion_desconocida (reset_admin_password.py)")
    print(f"[ERROR] Ocurrio un error: {e}")