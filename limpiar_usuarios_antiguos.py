"""
LIMPIEZA DE USUARIOS ANTIGUOS
Dejar solo el equipo actual de PRISLAB
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth import get_user_model

User = get_user_model()

print("=" * 80)
print("LIMPIEZA DE USUARIOS ANTIGUOS")
print("=" * 80)
print()

# Usuarios que DEBEN permanecer
usuarios_permitidos = [
    'jonathan',      # CEO/Super Admin
    'nancy',         # IQFB Gerencial
    'gabriela',      # QFB Gerencial
    'janette',       # TLQ
    'tania',         # TLQ
    'deyaneira',     # Auxiliar
    'brizia.nolasco', # Doctora (ya existía)
]

print("[USUARIOS AUTORIZADOS]")
for u in usuarios_permitidos:
    print(f"  [OK] {u}")
print()

# Obtener usuarios a eliminar
usuarios_eliminar = User.objects.exclude(username__in=usuarios_permitidos)

if usuarios_eliminar.count() == 0:
    print("[OK] No hay usuarios antiguos para eliminar")
else:
    print(f"[ELIMINANDO] {usuarios_eliminar.count()} usuarios antiguos:")
    for u in usuarios_eliminar:
        print(f"  [X] {u.username} ({u.get_full_name() or 'Sin nombre'})")
        u.delete()
    print()

print()
print("=" * 80)
print("[EQUIPO FINAL DE PRISLAB]")
print("=" * 80)
print()

usuarios_finales = User.objects.all().order_by('-is_superuser', '-is_staff', 'first_name')
print(f"Total: {usuarios_finales.count()} usuarios")
print()
print(f"{'Usuario':<20} | {'Nombre Completo':<35} | {'Rol':<15} | {'Nivel'}")
print("-" * 95)

for u in usuarios_finales:
    nivel = "[CEO]" if u.is_superuser else "[STAFF]" if u.is_staff else "[USER]"
    nombre = u.get_full_name() or "(sin nombre)"
    rol = u.rol or "N/A"
    print(f"{u.username:<20} | {nombre:<35} | {rol:<15} | {nivel}")

print()
print("=" * 80)
print("[CREDENCIALES]")
print("=" * 80)
print("jonathan   -> Admin2026!     (CEO/Super Admin)")
print("nancy      -> Nancy2026!     (IQFB - Gerencial)")
print("gabriela   -> Gabriela2026!  (QFB - Gerencial)")
print("janette    -> Janette2026!   (TLQ)")
print("tania      -> Tania2026!     (TLQ)")
print("deyaneira  -> Deyaneira2026! (Auxiliar)")
print()
print("[NOTA] brizia.nolasco mantiene su contraseña original")
print("=" * 80)
