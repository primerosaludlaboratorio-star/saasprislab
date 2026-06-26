"""
SCRIPT: Creación Rápida de Usuarios para PRISLAB
Ejecutar: PRISLAB_EMPRESA_ID=<pk> python crear_usuarios.py
"""
import os
import sys
import django
import logging

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.conf import settings
from django.contrib.auth import get_user_model
from core.models import Empresa

User = get_user_model()


def _validar_ejecucion():
    if not settings.DEBUG and os.environ.get('PRISLAB_ALLOW_LEGACY_SCRIPTS', '').lower() != 'true':
        raise SystemExit('BLOQUEADO: defina PRISLAB_ALLOW_LEGACY_SCRIPTS=true o use un management command.')

def crear_usuarios():
    """
    Crea usuarios para el sistema PRISLAB.
    Modifica esta función con los datos reales de tus usuarios.
    """
    _validar_ejecucion()
    eid = os.environ.get("PRISLAB_EMPRESA_ID")
    if not eid:
        print("[ERROR] Defina PRISLAB_EMPRESA_ID (pk de Empresa).")
        return
    try:
        empresa = Empresa.objects.get(pk=int(eid))
    except (ValueError, Empresa.DoesNotExist):
        print(f"[ERROR] Empresa id={eid!r} no válida.")
        return
    
    print("=" * 80)
    print("CREACION DE USUARIOS - PRISLAB GOLD")
    print("=" * 80)
    print(f"Empresa: {empresa.nombre if empresa else 'Sin empresa'}\n")
    
    # LISTA DE USUARIOS A CREAR
    usuarios = [
        {
            'username': 'nancy',
            'email': 'nancy@prislab.com',
            'first_name': 'Nancy',
            'last_name': 'Pérez',
            'password': 'nancy2026',  # CAMBIAR EN PRODUCCIÓN
            'is_staff': True,  # Acceso al admin
            'is_superuser': False,  # No es super admin
        },
        {
            'username': 'drjuan',
            'email': 'drjuan@prislab.com',
            'first_name': 'Juan',
            'last_name': 'García',
            'password': 'medico2026',  # CAMBIAR EN PRODUCCIÓN
            'is_staff': True,
            'is_superuser': False,
        },
        {
            'username': 'enfermera',
            'email': 'enfermera@prislab.com',
            'first_name': 'María',
            'last_name': 'López',
            'password': 'enf2026',  # CAMBIAR EN PRODUCCIÓN
            'is_staff': False,
            'is_superuser': False,
        },
        {
            'username': 'recepcion',
            'email': 'recepcion@prislab.com',
            'first_name': 'Ana',
            'last_name': 'Martínez',
            'password': 'rec2026',  # CAMBIAR EN PRODUCCIÓN
            'is_staff': False,
            'is_superuser': False,
        },
        {
            'username': 'laboratorio',
            'email': 'lab@prislab.com',
            'first_name': 'Carlos',
            'last_name': 'Rodríguez',
            'password': 'lab2026',  # CAMBIAR EN PRODUCCIÓN
            'is_staff': True,
            'is_superuser': False,
        },
    ]
    
    creados = 0
    existentes = 0
    
    for datos in usuarios:
        username = datos['username']
        
        # Verificar si ya existe
        if User.objects.filter(username=username).exists():
            print(f"[EXISTE] Usuario '{username}' ya está registrado")
            existentes += 1
            continue
        
        try:
            # Crear usuario
            user = User.objects.create_user(
                username=datos['username'],
                email=datos['email'],
                password=datos['password'],
                first_name=datos['first_name'],
                last_name=datos['last_name'],
            )
            
            # Configurar permisos
            user.is_staff = datos.get('is_staff', False)
            user.is_superuser = datos.get('is_superuser', False)
            
            # Asignar empresa si existe el campo
            if empresa and hasattr(user, 'empresa'):
                user.empresa = empresa
            
            user.save()
            
            print(f"[OK] Usuario '{username}' creado exitosamente")
            print(f"     Email: {datos['email']}")
            print(f"     Contraseña: {datos['password']}")
            print(f"     Rol: {'Admin' if user.is_staff else 'Usuario'}")
            print()
            
            creados += 1
            
        except Exception as e:
            logging.getLogger(__name__).exception("Error inesperado en crear_usuarios (crear_usuarios.py)")
            print(f"[ERROR] No se pudo crear '{username}': {e}")
            print()
    
    # Resumen
    print("=" * 80)
    print("RESUMEN")
    print("=" * 80)
    print(f"Usuarios creados: {creados}")
    print(f"Usuarios existentes (no modificados): {existentes}")
    print(f"Total en sistema: {User.objects.count()}")
    print()
    print("[EXITO] Proceso completado")
    print("=" * 80)
    print()
    print("CREDENCIALES DE ACCESO:")
    print("=" * 80)
    for datos in usuarios:
        if User.objects.filter(username=datos['username']).exists():
            print(f"Usuario: {datos['username']}")
            print(f"Contraseña: {datos['password']}")
            print(f"URL: http://127.0.0.1:8000/admin/")
            print("-" * 80)

if __name__ == '__main__':
    crear_usuarios()