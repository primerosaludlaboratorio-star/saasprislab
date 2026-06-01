import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.conf import settings

from core.models import Empresa, Sucursal, Usuario, Paciente, OrdenDeServicio, Estudio, DetalleOrden
from django.contrib.auth.hashers import make_password
from datetime import datetime


def _validar_ejecucion():
    if not settings.DEBUG and os.environ.get('PRISLAB_ALLOW_LEGACY_SCRIPTS', '').lower() != 'true':
        raise SystemExit('BLOQUEADO: defina PRISLAB_ALLOW_LEGACY_SCRIPTS=true o use un management command.')


def main():
    _validar_ejecucion()
    print("\n" + "="*60)
    print("CREANDO DATOS DE PRUEBA PARA PRISLAB")
    print("="*60)

    empresa, created = Empresa.objects.get_or_create(
        nombre='PRISLAB S.A. de C.V.',
        defaults={
            'rfc': 'PRI180101ABC',
            'direccion': 'Av. Reforma 123, Col. Centro',
            'telefono': '5512345678',
            'activa': True
        }
    )
    if created:
        print("\n[OK] Empresa creada: PRISLAB S.A. de C.V.")
    else:
        print("\n[INFO] Empresa ya existia: PRISLAB S.A. de C.V.")

    sucursal, created = Sucursal.objects.get_or_create(
        empresa=empresa,
        nombre='Matriz',
        defaults={
            'codigo_sucursal': 'SUC-001',
            'direccion': 'Av. Principal 123, Col. Centro',
            'telefono': '5512345678',
            'email': 'matriz@prislab.com',
            'activa': True
        }
    )
    if created:
        print("[OK] Sucursal creada: Matriz")
    else:
        print("[INFO] Sucursal ya existia: Matriz")

    usuario, created = Usuario.objects.get_or_create(
        username='admin',
        defaults={
            'email': 'admin@prislab.com',
            'password': make_password('admin123'),
            'empresa': empresa,
            'sucursal': sucursal,
            'rol': 'ADMIN',
            'is_staff': True,
            'is_superuser': True,
            'first_name': 'Admin',
            'last_name': 'PRISLAB'
        }
    )
    if created:
        print("[OK] Usuario creado: admin / admin123")
    else:
        print("[INFO] Usuario ya existia: admin")

    paciente, created = Paciente.objects.get_or_create(
        empresa=empresa,
        email='juan.perez@email.com',
        defaults={
            'nombre_completo': 'Juan Perez Garcia',
            'fecha_nacimiento': datetime(1990, 5, 15).date(),
            'sexo': 'M',
            'telefono': '5512345678'
        }
    )
    if created:
        print(f"[OK] Paciente creado: {paciente.nombre_completo}")
    else:
        print(f"[INFO] Paciente ya existia: {paciente.nombre_completo}")

    estudio, created = Estudio.objects.get_or_create(
        codigo='QS-001',
        defaults={
            'nombre': 'Quimica Sanguinea',
            'precio': 350.00,
            'tiempo_entrega_horas': 24,
            'activo': True
        }
    )
    if created:
        print(f"[OK] Estudio creado: {estudio.nombre}")
    else:
        print(f"[INFO] Estudio ya existia: {estudio.nombre}")

    folio = f'ORD-{datetime.now().strftime("%Y%m%d%H%M%S")}'
    orden = OrdenDeServicio.objects.create(
        empresa=empresa,
        sucursal=sucursal,
        paciente=paciente,
        folio_orden=folio,
        fecha_creacion=datetime.now(),
        estado='PAGADO',
        total=350.00,
        anticipo=350.00,
        responsable_ingreso=usuario
    )
    print(f"[OK] Orden creada: {orden.folio_orden} (ID: {orden.id})")

    DetalleOrden.objects.create(
        orden=orden,
        estudio=estudio,
        precio_momento=350.00
    )
    print(f"[OK] Detalle de orden creado para: {estudio.nombre}")

    print("\n" + "="*60)
    print("DATOS DE PRUEBA CREADOS EXITOSAMENTE")
    print("="*60)
    print(f"\nCREDENCIALES DE ACCESO:")
    print(f"   Usuario: admin")
    print(f"   Password: admin123")
    print(f"\nURL DE CAPTURA DE RESULTADOS:")
    print(f"   http://127.0.0.1:8000/laboratorio/captura/{orden.id}/")
    print(f"\nOTRAS URLs IMPORTANTES:")
    print(f"   Login: http://127.0.0.1:8000/")
    print(f"   Admin: http://127.0.0.1:8000/admin/")
    print(f"   Dashboard: http://127.0.0.1:8000/farmacia/dashboard/")
    print(f"   LIMS: http://127.0.0.1:8000/lims/estudios/")
    print("\n" + "="*60)


if __name__ == '__main__':
    main()
