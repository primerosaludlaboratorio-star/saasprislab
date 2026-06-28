#!/usr/bin/env python
"""
PRISLAB V5 — Script de Provisión COMPLETA en Producción
============================================================
Crea/actualiza TODOS los usuarios del equipo PRISLAB:
  1. Admin (Director Jonathan Alonso) — Superusuario
  2. Dra. Brizia Nolasco — Médico Cirujano General
  3. Jonathan — CEO/Super Admin
  4. Nancy Ramírez Cruz — IQFB (Farmacia/Recepción)
  5. Gabriela Araujo Martínez — QFB (Laboratorio/Proceso)
  6. Janette García Muñoz — TLQ (Técnico Tomadora)
  7. Tania Melissa Castro Sánchez — TLQ (Técnico)
  8. Deyaneira Cruz Aldán — Auxiliar General

Se ejecuta automáticamente en cada despliegue (idempotente).

CICLO 12: Contraseñas desde variables de entorno.
- PRISLAB_INIT_PASSWORD: si está definida, se usa para TODOS los usuarios creados.
- Si no está definida, se usan valores por defecto solo para desarrollo (cambiar en producción).
"""
import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth import get_user_model

User = get_user_model()


def crear_o_actualizar_usuario(username, password, email, **extra_fields):
    """Crea o actualiza un usuario de forma idempotente."""
    is_superuser = extra_fields.pop('is_superuser', False)
    is_staff = extra_fields.pop('is_staff', False)

    if User.objects.filter(username=username).exists():
        user = User.objects.get(username=username)
        # Solo cambiar contrasena si es diferente (evita invalidar sesiones en cada deploy)
        if not user.check_password(password):
            user.set_password(password)
        user.email = email
        user.is_superuser = is_superuser
        user.is_staff = is_staff
        user.is_active = True
        for key, value in extra_fields.items():
            setattr(user, key, value)
        user.save()
        print(f"  [OK] Usuario '{username}' actualizado")
        return user
    else:
        if is_superuser:
            user = User.objects.create_superuser(
                username=username, email=email, password=password
            )
        else:
            user = User.objects.create_user(
                username=username, email=email, password=password
            )
            user.is_staff = is_staff
        user.is_active = True
        for key, value in extra_fields.items():
            setattr(user, key, value)
        user.save()
        print(f"  [OK] Usuario '{username}' creado")
        return user


def asignar_empresa(user, empresa_nombre="PRISLAB S.A. de C.V."):
    """Asigna la empresa al usuario si no tiene una (PRISLAB_EMPRESA_ID o nombre exacto)."""
    from core.models import Empresa
    if user.empresa:
        return user.empresa
    eid = os.environ.get("PRISLAB_EMPRESA_ID")
    if eid:
        try:
            empresa = Empresa.objects.get(pk=int(eid))
        except (ValueError, Empresa.DoesNotExist):
            print(f"  [ERROR] PRISLAB_EMPRESA_ID={eid!r} inválido")
            sys.exit(1)
    else:
        empresa = Empresa.objects.filter(nombre=empresa_nombre).first()
        if not empresa:
            print(
                f"  [ERROR] No existe empresa {empresa_nombre!r}. "
                "Defina PRISLAB_EMPRESA_ID o cree la empresa en admin."
            )
            sys.exit(1)
    user.empresa = empresa
    user.save()
    print(f"  [OK] Empresa asignada a '{user.username}'")
    return user.empresa


def crear_perfil_medico(nombre_completo, cedula, especialidad, empresa=None):
    """Crea el perfil Medico si no existe."""
    from core.models import Medico, Empresa
    if empresa is None:
        eid = os.environ.get("PRISLAB_EMPRESA_ID")
        if not eid:
            print("  [ERROR] crear_perfil_medico: pase empresa= o PRISLAB_EMPRESA_ID")
            sys.exit(1)
        try:
            empresa = Empresa.objects.get(pk=int(eid))
        except (ValueError, Empresa.DoesNotExist):
            print(f"  [ERROR] PRISLAB_EMPRESA_ID={eid!r} inválido")
            sys.exit(1)
    medico, created = Medico.objects.get_or_create(
        cedula_profesional=cedula,
        defaults={
            'nombre_completo': nombre_completo,
            'especialidad': especialidad,
            'empresa': empresa,
            'activo': True,
        }
    )
    if not created:
        medico.nombre_completo = nombre_completo
        medico.especialidad = especialidad
        if empresa and not medico.empresa:
            medico.empresa = empresa
        medico.activo = True
        medico.save()
    status = "creado" if created else "actualizado"
    print(f"  [OK] Perfil Médico '{nombre_completo}' (cédula {cedula}) {status}")
    return medico


def vincular_firma_digital(user, cedula, imagen_path='firmas/firma_brizia_processed.png'):
    """Vincula la firma digital al usuario y cédula."""
    from core.models import FirmaDigital
    firma, created = FirmaDigital.objects.get_or_create(
        medico=user,
        cedula_profesional=cedula,
        defaults={
            'imagen_firma': imagen_path,
            'activa': True,
        }
    )
    if not created:
        firma.imagen_firma = imagen_path
        firma.activa = True
        firma.save()
    # También actualizar cualquier firma existente con esa imagen
    FirmaDigital.objects.filter(imagen_firma=imagen_path).exclude(medico=user).update(
        medico=user, cedula_profesional=cedula
    )
    status = "creada" if created else "actualizada"
    print(f"  [OK] Firma Digital (cédula {cedula}) {status}")


# ==============================================================================
# EJECUCIÓN PRINCIPAL
# ==============================================================================
print("")
print("=" * 70)
print("  PRISLAB V5 -- Provision COMPLETA de Usuarios")
print("=" * 70)

# Contraseña única de despliegue (evitar hardcoded en repo)
_init_pass = os.environ.get('PRISLAB_INIT_PASSWORD', 'PrislabV5_2026')

# ── 1. ADMIN (Director) ─────────────────────────────────────────────────────
print("\n[1/8] Administrador del Sistema:")
admin_user = crear_o_actualizar_usuario(
    username='admin',
    password=os.environ.get('PRISLAB_INIT_ADMIN_PASSWORD', _init_pass),
    email='admin@prislab.com',
    first_name='Administrador',
    last_name='Sistema',
    is_superuser=True,
    is_staff=True,
    rol='ADMIN',
    puede_usar_ia=True,
    nivel_ia='IA_MASTER',
)
empresa = asignar_empresa(admin_user)

# ── 2. DRA. BRIZIA NOLASCO (Médico Cirujano General) ────────────────────────
print("\n[2/8] Dra. Brizia Itzel Nolasco Polito:")
brizia_user = crear_o_actualizar_usuario(
    username='brizia.nolasco',
    password=os.environ.get('PRISLAB_INIT_PASSWORD_BRIZIA', _init_pass),
    email='brizia@prislab.mx',
    first_name='Brizia Itzel',
    last_name='Nolasco Polito',
    is_superuser=False,
    is_staff=False,
    rol='MEDICO',
    puede_usar_ia=True,
    nivel_ia='IA_TECNICA',
    departamento='Consultorio Medico',
    cedula_interna='11852035',
)
asignar_empresa(brizia_user)
crear_perfil_medico(
    nombre_completo='Brizia Itzel Nolasco Polito',
    cedula='11852035',
    especialidad='Medico Cirujano General',
)
vincular_firma_digital(
    user=brizia_user,
    cedula='11852035',
    imagen_path='firmas/firma_brizia_processed.png',
)

# ── 3. JONATHAN (CEO/Super Admin) ───────────────────────────────────────────
print("\n[3/8] Jonathan Alonso Samos Sanchez (CEO):")
jonathan_user = crear_o_actualizar_usuario(
    username='jonathan',
    password=os.environ.get('PRISLAB_INIT_PASSWORD_JONATHAN', _init_pass),
    email='jonathan@prislab.com',
    first_name='Jonathan Alonso',
    last_name='Samos Sanchez',
    is_superuser=True,
    is_staff=True,
    rol='ADMIN',
    puede_usar_ia=True,
    nivel_ia='IA_MASTER',
)
asignar_empresa(jonathan_user)

# ── 4. NANCY RAMÍREZ CRUZ (IQFB - Farmacia/Recepción) ──────────────────────
print("\n[4/8] Nancy Ramirez Cruz (IQFB):")
nancy_user = crear_o_actualizar_usuario(
    username='nancy',
    password=os.environ.get('PRISLAB_INIT_PASSWORD_NANCY', _init_pass),
    email='nancy@prislab.com',
    first_name='Nancy',
    last_name='Ramirez Cruz',
    is_superuser=False,
    is_staff=True,
    rol='farmacia',
    departamento='Farmacia/Recepcion/Toma de Muestra',
)
asignar_empresa(nancy_user)

# ── 5. GABRIELA ARAUJO MARTÍNEZ (QFB - Laboratorio) ────────────────────────
print("\n[5/8] Gabriela Araujo Martinez (QFB):")
gabriela_user = crear_o_actualizar_usuario(
    username='gabriela',
    password=os.environ.get('PRISLAB_INIT_PASSWORD_GABRIELA', _init_pass),
    email='gabriela@prislab.com',
    first_name='Gabriela',
    last_name='Araujo Martinez',
    is_superuser=False,
    is_staff=True,
    rol='laboratorio',
    departamento='Laboratorio/Proceso',
)
asignar_empresa(gabriela_user)

# ── ASIGNAR GRUPOS GERENCIALES A NANCY Y GABRIELA ──────────────────────────
# Ambas tienen autorizacion gerencial: acceso a TODAS las areas del sistema.
# Solo estan por debajo del Director (dueno).
from django.contrib.auth.models import Group
GRUPOS_GERENCIA = ['GERENCIA_OPERATIVA', 'LABORATORIO', 'FARMACIA', 'RECEPCION', 'GERENCIA', 'ENFERMERIA']
for usr in [nancy_user, gabriela_user]:
    if usr:
        for gname in GRUPOS_GERENCIA:
            grp, _ = Group.objects.get_or_create(name=gname)
            grp.user_set.add(usr)
        print(f"  -> {usr.username}: asignada a {', '.join(GRUPOS_GERENCIA)}")

# ── 6. JANETTE GARCÍA MUÑOZ (TLQ - Técnico Tomadora) ───────────────────────
print("\n[6/8] Janette Garcia Munoz (TLQ):")
janette_user = crear_o_actualizar_usuario(
    username='janette',
    password=os.environ.get('PRISLAB_INIT_PASSWORD_JANETTE', _init_pass),
    email='janette@prislab.com',
    first_name='Janette',
    last_name='Garcia Munoz',
    is_superuser=False,
    is_staff=False,
    rol='laboratorio',
    departamento='Toma de Muestra',
)
asignar_empresa(janette_user)

# ── 7. TANIA MELISSA CASTRO SÁNCHEZ (TLQ - Técnico) ────────────────────────
print("\n[7/8] Tania Melissa Castro Sanchez (TLQ):")
tania_user = crear_o_actualizar_usuario(
    username='tania',
    password=os.environ.get('PRISLAB_INIT_PASSWORD_TANIA', _init_pass),
    email='tania@prislab.com',
    first_name='Tania Melissa',
    last_name='Castro Sanchez',
    is_superuser=False,
    is_staff=False,
    rol='laboratorio',
    departamento='Laboratorio',
)
asignar_empresa(tania_user)

# ── 8. DEYANEIRA CRUZ ALDÁN (Auxiliar General) ──────────────────────────────
print("\n[8/8] Deyaneira Cruz Aldan (Auxiliar):")
deyaneira_user = crear_o_actualizar_usuario(
    username='deyaneira',
    password=os.environ.get('PRISLAB_INIT_PASSWORD_DEYANEIRA', _init_pass),
    email='deyaneira@prislab.com',
    first_name='Deyaneira',
    last_name='Cruz Aldan',
    is_superuser=False,
    is_staff=False,
    rol='recepcion',
    departamento='Auxiliar General',
)
asignar_empresa(deyaneira_user)

# ── RESUMEN ──────────────────────────────────────────────────────────────────
print("\n" + "=" * 70)
print("  CREDENCIALES DE ACCESO")
print("=" * 70)
print("  [ADMIN]     admin / (ver PRISLAB_INIT_ADMIN_PASSWORD o PRISLAB_INIT_PASSWORD)")
print("  [MEDICO]    brizia.nolasco / (ver PRISLAB_INIT_PASSWORD_*)")
print("  [CEO]       jonathan / (ver PRISLAB_INIT_PASSWORD_*)")
print("  [FARMACIA]  nancy / (ver PRISLAB_INIT_PASSWORD_*)")
print("  [LAB-JEFA]  gabriela / (ver PRISLAB_INIT_PASSWORD_*)")
print("  [LAB-TEC]   janette / (ver PRISLAB_INIT_PASSWORD_*)")
print("  [LAB-TEC]   tania / (ver PRISLAB_INIT_PASSWORD_*)")
print("  [AUXILIAR]  deyaneira / (ver PRISLAB_INIT_PASSWORD_*)")
print("=" * 70)
print("")
