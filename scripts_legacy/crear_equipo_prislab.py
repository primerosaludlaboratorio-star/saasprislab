"""
CREACIÓN DEL EQUIPO COMPLETO DE PRISLAB
Sistema creado por Jonathan Alonso Samos Sánchez junto con Cursor y Gemini
Requiere variable de entorno PRISLAB_EMPRESA_ID (pk de Empresa).
"""
import os
import sys
import django
from datetime import datetime

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth import get_user_model
from core.models import Empresa

User = get_user_model()

print("=" * 80)
print("CREACION DEL EQUIPO PRISLAB")
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

# ============================================================================
# 1. SUPER ADMIN - CEO
# ============================================================================
print("[1/6] Verificando CEO/Super Admin...")
jonathan, created = User.objects.update_or_create(
    username='jonathan',
    defaults={
        'first_name': 'Jonathan Alonso',
        'last_name': 'Samos Sánchez',
        'email': 'jonathan@prislab.com',
        'is_staff': True,
        'is_superuser': True,
        'is_active': True,
        'empresa': empresa,
        'rol': 'administrador',
    }
)
if created:
    jonathan.set_password('Admin2026!')
    jonathan.save()
    print(f"  [CREADO] jonathan (CEO/Super Admin)")
else:
    print(f"  [OK] jonathan ya existe (Super Admin)")

# ============================================================================
# 2. NANCY RAMÍREZ CRUZ - IQFB (Gerencial)
# ============================================================================
print("[2/6] Creando Nancy Ramírez Cruz (IQFB - Gerencial)...")
nancy, created = User.objects.update_or_create(
    username='nancy',
    defaults={
        'first_name': 'Nancy',
        'last_name': 'Ramírez Cruz',
        'email': 'nancy@prislab.com',
        'is_staff': True,
        'is_superuser': False,
        'is_active': True,
        'empresa': empresa,
        'rol': 'farmacia',  # Responsable de farmacia, recepción y toma de muestra
    }
)
if created or True:  # Actualizar siempre
    nancy.set_password('Nancy2026!')
    nancy.save()
    print(f"  [OK] nancy - IQFB (Permisos Gerenciales)")
    print(f"       Rol: Farmacia/Recepción/Toma de Muestra")
    print(f"       Fecha Nac: 28-05-1997")

# ============================================================================
# 3. GABRIELA ARAUJO MARTÍNEZ - QFB (Gerencial)
# ============================================================================
print("[3/6] Creando Gabriela Araujo Martínez (QFB - Gerencial)...")
gabriela, created = User.objects.update_or_create(
    username='gabriela',
    defaults={
        'first_name': 'Gabriela',
        'last_name': 'Araujo Martínez',
        'email': 'gabriela@prislab.com',
        'is_staff': True,
        'is_superuser': False,
        'is_active': True,
        'empresa': empresa,
        'rol': 'laboratorio',  # Responsable de proceso
    }
)
if created or True:
    gabriela.set_password('Gabriela2026!')
    gabriela.save()
    print(f"  [OK] gabriela - QFB (Permisos Gerenciales)")
    print(f"       Rol: Laboratorio/Proceso")
    print(f"       Fecha Nac: 16-03-1993")
    print(f"       Nota: Segunda al mando, responsable de proceso")

# ============================================================================
# 4. JANETTE GARCÍA MUÑOZ - TLQ (Técnico)
# ============================================================================
print("[4/6] Creando Janette García Muñoz (TLQ)...")
janette, created = User.objects.update_or_create(
    username='janette',
    defaults={
        'first_name': 'Janette',
        'last_name': 'García Muñoz',
        'email': 'janette@prislab.com',
        'is_staff': False,
        'is_superuser': False,
        'is_active': True,
        'empresa': empresa,
        'rol': 'laboratorio',  # Técnico tomadora
    }
)
if created or True:
    janette.set_password('Janette2026!')
    janette.save()
    print(f"  [OK] janette - TLQ")
    print(f"       Rol: Técnico Tomadora de Confianza")

# ============================================================================
# 5. TANIA MELISSA CASTRO SÁNCHEZ - TLQ (Técnico)
# ============================================================================
print("[5/6] Creando Tania Melissa Castro Sánchez (TLQ)...")
tania, created = User.objects.update_or_create(
    username='tania',
    defaults={
        'first_name': 'Tania Melissa',
        'last_name': 'Castro Sánchez',
        'email': 'tania@prislab.com',
        'is_staff': False,
        'is_superuser': False,
        'is_active': True,
        'empresa': empresa,
        'rol': 'laboratorio',  # Técnico
    }
)
if created or True:
    tania.set_password('Tania2026!')
    tania.save()
    print(f"  [OK] tania - TLQ")
    print(f"       Rol: Técnico de Laboratorio")
    print(f"       Fecha Nac: 06-03-2007")

# ============================================================================
# 6. DEYANEIRA CRUZ ALDÁN - Auxiliar General
# ============================================================================
print("[6/6] Creando Deyaneira Cruz Aldán (Auxiliar General)...")
deyaneira, created = User.objects.update_or_create(
    username='deyaneira',
    defaults={
        'first_name': 'Deyaneira',
        'last_name': 'Cruz Aldán',
        'email': 'deyaneira@prislab.com',
        'is_staff': False,
        'is_superuser': False,
        'is_active': True,
        'empresa': empresa,
        'rol': 'recepcion',  # Solo acceso a bienestar
    }
)
if created or True:
    deyaneira.set_password('Deyaneira2026!')
    deyaneira.save()
    print(f"  [OK] deyaneira - Auxiliar General")
    print(f"       Rol: Limpieza (Solo módulos de Bienestar)")
    print(f"       Nota: Sin funciones administrativas")

# ============================================================================
# VERIFICAR DOCTORA BRIZIA
# ============================================================================
print()
print("[VERIFICACION] Doctora Brizia...")
brizia = User.objects.filter(username='brizia').first()
if brizia:
    print(f"  [OK] brizia ya existe en el sistema")
    print(f"       Nombre: {brizia.get_full_name()}")
    print(f"       Rol: {brizia.rol}")
else:
    print(f"  [AVISO] No se encontró usuario 'brizia'")
    print(f"          Creando con datos básicos...")
    brizia, created = User.objects.update_or_create(
        username='brizia',
        defaults={
            'first_name': 'Brizia',
            'last_name': 'Doctora',
            'email': 'brizia@prislab.com',
            'is_staff': True,
            'is_superuser': False,
            'is_active': True,
            'empresa': empresa,
            'rol': 'medico',
        }
    )
    brizia.set_password('Brizia2026!')
    brizia.save()
    print(f"  [CREADO] brizia (Doctora)")

# ============================================================================
# RESUMEN FINAL
# ============================================================================
print()
print("=" * 80)
print("EQUIPO PRISLAB COMPLETO")
print("=" * 80)
print()

usuarios = User.objects.all().order_by('-is_superuser', '-is_staff', 'first_name')
print(f"Total de usuarios en el sistema: {usuarios.count()}")
print()
print(f"{'Usuario':<15} | {'Nombre Completo':<35} | {'Rol':<15} | {'Permisos'}")
print("-" * 90)

for u in usuarios:
    permisos = "SuperAdmin" if u.is_superuser else "Staff" if u.is_staff else "Usuario"
    nombre = u.get_full_name() or "(sin nombre)"
    rol = u.rol or "N/A"
    print(f"{u.username:<15} | {nombre:<35} | {rol:<15} | {permisos}")

print()
print("=" * 80)
print("[CREDENCIALES TEMPORALES]")
print("=" * 80)
print("jonathan   -> Admin2026!")
print("nancy      -> Nancy2026!")
print("gabriela   -> Gabriela2026!")
print("janette    -> Janette2026!")
print("tania      -> Tania2026!")
print("deyaneira  -> Deyaneira2026!")
print("brizia     -> Brizia2026!")
print()
print("[IMPORTANTE] Cambiar contraseñas en el primer inicio de sesión")
print("=" * 80)
