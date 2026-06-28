"""
DESACTIVAR USUARIOS ANTIGUOS (más seguro que eliminar)
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth import get_user_model

User = get_user_model()

print("=" * 80)
print("DESACTIVAR USUARIOS ANTIGUOS")
print("=" * 80)
print()

# Usuarios que DEBEN estar activos
usuarios_activos = [
    'jonathan',      # CEO/Super Admin
    'nancy',         # IQFB Gerencial
    'gabriela',      # QFB Gerencial
    'janette',       # TLQ
    'tania',         # TLQ
    'deyaneira',     # Auxiliar
    'brizia.nolasco', # Doctora
]

print("[EQUIPO ACTIVO]")
for u in usuarios_activos:
    print(f"  [OK] {u}")
print()

# Desactivar usuarios antiguos
usuarios_antiguos = User.objects.exclude(username__in=usuarios_activos)

if usuarios_antiguos.count() == 0:
    print("[OK] No hay usuarios antiguos")
else:
    print(f"[DESACTIVANDO] {usuarios_antiguos.count()} usuarios antiguos:")
    for u in usuarios_antiguos:
        u.is_active = False
        u.save()
        print(f"  [DESACTIVADO] {u.username} ({u.get_full_name() or 'Sin nombre'})")
    print()

# Activar usuarios del equipo
print("[ACTIVANDO] Equipo oficial:")
for username in usuarios_activos:
    try:
        u = User.objects.get(username=username)
        u.is_active = True
        u.save()
        print(f"  [ACTIVADO] {username}")
    except User.DoesNotExist:
        print(f"  [AVISO] {username} no existe")

print()
print("=" * 80)
print("[EQUIPO PRISLAB - USUARIOS ACTIVOS]")
print("=" * 80)
print()

usuarios_finales = User.objects.filter(is_active=True).order_by('-is_superuser', '-is_staff', 'first_name')
print(f"Total activos: {usuarios_finales.count()}")
print()
print(f"{'Usuario':<20} | {'Nombre Completo':<35} | {'Rol':<15} | {'Nivel'}")
print("-" * 95)

for u in usuarios_finales:
    nivel = "[CEO]" if u.is_superuser else "[STAFF]" if u.is_staff else "[USER]"
    nombre = u.get_full_name() or "(sin nombre)"
    rol = (u.rol or "N/A").upper()
    print(f"{u.username:<20} | {nombre:<35} | {rol:<15} | {nivel}")

print()
print("=" * 80)
print("[CREDENCIALES DEL EQUIPO]")
print("=" * 80)
print()
print("SUPER ADMIN:")
print("  jonathan   -> Admin2026!")
print()
print("STAFF/GERENCIAL:")
print("  nancy      -> Nancy2026!")
print("  gabriela   -> Gabriela2026!")
print()
print("TECNICOS:")
print("  janette    -> Janette2026!")
print("  tania      -> Tania2026!")
print()
print("AUXILIAR:")
print("  deyaneira  -> Deyaneira2026!")
print()
print("MEDICO:")
print("  brizia.nolasco (contrasena original)")
print()
print("[NOTA] Cambiar contrasenas en el primer inicio de sesion")
print("=" * 80)
