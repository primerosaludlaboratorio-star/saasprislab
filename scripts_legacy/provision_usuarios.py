#!/usr/bin/env python
"""
PRISLAB V5 — Provisionamiento de Usuarios para Producción
===========================================================
Crea/actualiza todos los usuarios base del sistema:
  1. admin (Superusuario / Director)
  2. brizia.nolasco (Dra. Brizia Itzel Nolasco Polito — Médico Cirujano)
  3. Perfil Medico + FirmaDigital vinculada

Se ejecuta automáticamente en cada despliegue (idempotente).

CICLO 12: Contraseñas desde env. Use PRISLAB_INIT_PASSWORD en producción.
"""
import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth import get_user_model
from core.models import Empresa, Medico, FirmaDigital

User = get_user_model()


def obtener_empresa():
    """Obtiene o crea la empresa principal."""
    empresa, created = Empresa.objects.get_or_create(
        nombre='PRISLAB S.A. de C.V.',
        defaults={
            'rfc': 'PRI260101XXX',
            'periodo_vigencia': '2024-2030',
            'color_primario': '#D9230F',
            'color_secundario': '#2B3A42',
        }
    )
    if created:
        print(f"[+] Empresa creada: {empresa.nombre}")
    return empresa


def crear_admin(empresa):
    """Crea o actualiza el superusuario admin."""
    username = 'admin'
    password = os.environ.get('PRISLAB_INIT_PASSWORD', os.environ.get('PRISLAB_INIT_ADMIN_PASSWORD', 'PrislabV5_2026'))
    email = 'admin@prislab.com'

    user, created = User.objects.get_or_create(
        username=username,
        defaults={
            'email': email,
            'first_name': 'Administrador',
            'last_name': 'Sistema',
            'is_superuser': True,
            'is_staff': True,
            'is_active': True,
            'empresa': empresa,
            'rol': 'ADMIN',
            'puede_usar_ia': True,
            'nivel_ia': 'IA_MASTER',
        }
    )

    # Siempre actualizar datos críticos
    user.set_password(password)
    user.is_superuser = True
    user.is_staff = True
    user.is_active = True
    user.empresa = empresa
    user.rol = 'ADMIN'
    user.puede_usar_ia = True
    user.nivel_ia = 'IA_MASTER'
    user.save()

    action = "CREADO" if created else "ACTUALIZADO"
    print(f"[OK] Admin {action}: {username} / {password}")
    return user


def crear_dra_brizia(empresa):
    """Crea o actualiza el usuario de la Dra. Brizia + perfil Médico + Firma."""
    username = 'brizia.nolasco'
    password = os.environ.get('PRISLAB_INIT_PASSWORD_BRIZIA', os.environ.get('PRISLAB_INIT_PASSWORD', 'Prislab2026!'))
    cedula = '11852035'

    # ── 1. Usuario Django ────────────────────────────────────────────────
    user, created = User.objects.get_or_create(
        username=username,
        defaults={
            'first_name': 'Brizia Itzel',
            'last_name': 'Nolasco Polito',
            'email': 'brizia@prislab.mx',
            'empresa': empresa,
            'rol': 'MEDICO',
            'puede_usar_ia': True,
            'nivel_ia': 'IA_TECNICA',
            'departamento': 'Consultorio Médico',
            'cedula_interna': cedula,
            'is_staff': False,
            'is_active': True,
        }
    )

    if created:
        user.set_password(password)
        user.save()
        print(f"[OK] Dra. Brizia CREADA: {username} / {password}")
    else:
        # Actualizar datos no-destructivos (no resetear password si ya existe)
        user.first_name = 'Brizia Itzel'
        user.last_name = 'Nolasco Polito'
        user.empresa = empresa
        user.rol = 'MEDICO'
        user.puede_usar_ia = True
        user.nivel_ia = 'IA_TECNICA'
        user.departamento = 'Consultorio Médico'
        user.cedula_interna = cedula
        user.is_active = True
        user.save()
        print(f"[OK] Dra. Brizia ACTUALIZADA: {username}")

    # ── 2. Perfil Médico ─────────────────────────────────────────────────
    medico, m_created = Medico.objects.get_or_create(
        cedula_profesional=cedula,
        defaults={
            'nombre_completo': 'Brizia Itzel Nolasco Polito',
            'especialidad': 'Médico Cirujano General',
        }
    )
    if m_created:
        print(f"[OK] Perfil Médico CREADO: {medico.nombre_completo} (Cédula: {cedula})")
    else:
        medico.nombre_completo = 'Brizia Itzel Nolasco Polito'
        medico.especialidad = 'Médico Cirujano General'
        medico.save()
        print(f"[OK] Perfil Médico ACTUALIZADO: {medico.nombre_completo}")

    # ── 3. Firma Digital ─────────────────────────────────────────────────
    firma_path = 'firmas/firma_brizia_processed.png'

    # Limpiar duplicados: quedarse con una sola firma activa por cédula
    firmas_existentes = FirmaDigital.objects.filter(
        medico=user, cedula_profesional=cedula
    )
    if firmas_existentes.count() > 1:
        # Mantener la más reciente, eliminar el resto
        firma_principal = firmas_existentes.order_by('-fecha_registro').first()
        firmas_existentes.exclude(id=firma_principal.id).delete()
        firma_principal.imagen_firma = firma_path
        firma_principal.activa = True
        firma_principal.save()
        print(f"[OK] Firma Digital LIMPIADA (duplicados eliminados) para cédula {cedula}")
    elif firmas_existentes.count() == 1:
        firma = firmas_existentes.first()
        firma.imagen_firma = firma_path
        firma.activa = True
        firma.save()
        print(f"[OK] Firma Digital ACTUALIZADA para cédula {cedula}")
    else:
        FirmaDigital.objects.create(
            medico=user,
            cedula_profesional=cedula,
            imagen_firma=firma_path,
            activa=True,
        )
        print(f"[OK] Firma Digital CREADA para cédula {cedula}")

    return user


def main():
    print("")
    print("=" * 70)
    print("  PRISLAB V5 — Provisionamiento de Usuarios")
    print("=" * 70)

    empresa = obtener_empresa()
    admin_user = crear_admin(empresa)
    brizia_user = crear_dra_brizia(empresa)

    print("")
    print("=" * 70)
    print("  USUARIOS DEL SISTEMA:")
    print("=" * 70)
    print(f"  [ADMIN]  admin           / PrislabV5_2026  (Director/Admin)")
    print(f"  [MEDICO] brizia.nolasco  / Prislab2026!    (Dra. Brizia - Medico Cirujano)")
    print("=" * 70)
    print(f"  Empresa: {empresa.nombre}")
    print(f"  Total usuarios: {User.objects.count()}")
    print("=" * 70)
    print("")


if __name__ == '__main__':
    main()
