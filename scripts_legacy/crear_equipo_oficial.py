"""
CREAR EQUIPO OFICIAL EN PRODUCCIÓN
Script para ejecutar en el servidor de producción
Requiere PRISLAB_EMPRESA_ID (pk de Empresa).
"""
import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth import get_user_model
from core.models import Empresa

User = get_user_model()

print("=" * 80)
print("CREACION DEL EQUIPO PRISLAB EN PRODUCCION")
print("=" * 80)
print()

_eid = os.environ.get("PRISLAB_EMPRESA_ID")
if not _eid:
    print("[ERROR] Defina PRISLAB_EMPRESA_ID (pk de Empresa).")
    sys.exit(1)
try:
    empresa = Empresa.objects.get(pk=int(_eid))
except (ValueError, Empresa.DoesNotExist):
    print(f"[ERROR] Empresa id={_eid!r} no válida.")
    sys.exit(1)

print(f"Empresa: {empresa.nombre}")
print()

# ============================================================================
# EQUIPO PRISLAB
# ============================================================================

usuarios_crear = [
    {
        'username': 'jonathan',
        'first_name': 'Jonathan Alonso',
        'last_name': 'Samos Sánchez',
        'email': 'jonathan@prislab.com',
        'password': 'Admin2026!',
        'is_staff': True,
        'is_superuser': True,
        'rol': 'administrador',
    },
    {
        'username': 'nancy',
        'first_name': 'Nancy',
        'last_name': 'Ramírez Cruz',
        'email': 'nancy@prislab.com',
        'password': 'Nancy2026!',
        'is_staff': True,
        'is_superuser': False,
        'rol': 'farmacia',
    },
    {
        'username': 'gabriela',
        'first_name': 'Gabriela',
        'last_name': 'Araujo Martínez',
        'email': 'gabriela@prislab.com',
        'password': 'Gabriela2026!',
        'is_staff': True,
        'is_superuser': False,
        'rol': 'laboratorio',
    },
    {
        'username': 'janette',
        'first_name': 'Janette',
        'last_name': 'García Muñoz',
        'email': 'janette@prislab.com',
        'password': 'Janette2026!',
        'is_staff': False,
        'is_superuser': False,
        'rol': 'laboratorio',
    },
    {
        'username': 'tania',
        'first_name': 'Tania Melissa',
        'last_name': 'Castro Sánchez',
        'email': 'tania@prislab.com',
        'password': 'Tania2026!',
        'is_staff': False,
        'is_superuser': False,
        'rol': 'laboratorio',
    },
    {
        'username': 'deyaneira',
        'first_name': 'Deyaneira',
        'last_name': 'Cruz Aldán',
        'email': 'deyaneira@prislab.com',
        'password': 'Deyaneira2026!',
        'is_staff': False,
        'is_superuser': False,
        'rol': 'recepcion',
    },
    {
        'username': 'brizia.nolasco',
        'first_name': 'Brizia Itzel',
        'last_name': 'Nolasco Polito',
        'email': 'brizia@prislab.com',
        'password': 'Brizia2026!',
        'is_staff': True,
        'is_superuser': False,
        'rol': 'medico',
    },
]

print("[CREANDO USUARIOS]")
creados = 0
actualizados = 0

for data in usuarios_crear:
    username = data.pop('username')
    password = data.pop('password')
    
    user, created = User.objects.update_or_create(
        username=username,
        defaults={**data, 'empresa': empresa, 'is_active': True}
    )
    
    user.set_password(password)
    user.save()
    
    if created:
        creados += 1
        print(f"  [CREADO] {username}")
    else:
        actualizados += 1
        print(f"  [ACTUALIZADO] {username}")

print()
print("=" * 80)
print(f"[RESUMEN]")
print(f"  Creados: {creados}")
print(f"  Actualizados: {actualizados}")
print(f"  Total en sistema: {User.objects.filter(is_active=True).count()}")
print("=" * 80)
