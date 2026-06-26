"""
Script para crear el Responsable Sanitario del laboratorio.
Ejecutar DESPUÉS del reset nuclear y las migraciones.
"""
import os
import django
import logging

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth import get_user_model
from laboratorio.models import ResponsableSanitario

User = get_user_model()

# Datos del Responsable Sanitario
NOMBRE = "GISELL MARGATITA LOPEZ GUTIERRES"
CEDULA = "9439502"
UNIVERSIDAD = "UNIVERSIDAD VERACRUZANA"
ESPECIALIDAD = "Químico Farmacobiólogo"

try:
    # Buscar o crear usuario admin
    admin_user, created = User.objects.get_or_create(
        username='admin',
        defaults={
            'first_name': 'GISELL MARGATITA',
            'last_name': 'LOPEZ GUTIERRES',
            'email': 'admin@prislab.com',
            'is_staff': True,
            'is_superuser': True
        }
    )
    
    if created:
        admin_user.set_password('admin123')
        admin_user.save()
        print(f"[OK] Usuario admin creado: {admin_user.get_full_name()}")
    else:
        # Actualizar nombre si el usuario ya existe
        admin_user.first_name = 'GISELL MARGATITA'
        admin_user.last_name = 'LOPEZ GUTIERRES'
        admin_user.save()
        print(f"[OK] Usuario admin actualizado: {admin_user.get_full_name()}")
    
    # Crear o actualizar Responsable Sanitario
    responsable, created = ResponsableSanitario.objects.get_or_create(
        usuario=admin_user,
        defaults={
            'cedula_profesional': CEDULA,
            'universidad_titulo': UNIVERSIDAD,
            'especialidad': ESPECIALIDAD,
            'activo': True
        }
    )
    
    if not created:
        # Actualizar si ya existe
        responsable.cedula_profesional = CEDULA
        responsable.universidad_titulo = UNIVERSIDAD
        responsable.especialidad = ESPECIALIDAD
        responsable.activo = True
        responsable.save()
        print(f"[OK] Responsable Sanitario actualizado")
    else:
        print(f"[OK] Responsable Sanitario creado correctamente")
    
    print("\n" + "="*60)
    print("DATOS DEL RESPONSABLE SANITARIO:")
    print("="*60)
    print(f"Nombre: Q.F.B. {responsable.usuario.get_full_name()}")
    print(f"Cedula Profesional: {responsable.cedula_profesional}")
    print(f"Universidad: {responsable.universidad_titulo}")
    print(f"Especialidad: {responsable.especialidad}")
    print(f"Estado: {'ACTIVO' if responsable.activo else 'INACTIVO'}")
    print("="*60)
    print("\n[OK] SISTEMA LISTO PARA GENERAR REPORTES CON CUMPLIMIENTO NOM-007")

except Exception as e:
    logging.getLogger(__name__).exception("Error inesperado en funcion_desconocida (crear_responsable_sanitario.py)")
    print(f"[ERROR] Error: {e}")
    import traceback
    traceback.print_exc()