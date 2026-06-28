#!/usr/bin/env python
"""
Verificar si los pacientes se están guardando en la base de datos
"""
import os
import sys
import django

# Configurar Django
sys.path.append(r'C:\Users\jonil\Desktop\PRISLAB_SaaS')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from core.models import Paciente

print("=" * 80)
print("VERIFICACIÓN DE PACIENTES EN LA BASE DE DATOS")
print("=" * 80)

# Buscar pacientes recientes con nombre María
pacientes = Paciente.objects.filter(nombres__icontains='María').order_by('-id')[:10]

print(f"\nPacientes encontrados con nombre 'María': {pacientes.count()}")

if pacientes.exists():
    print("\nÚltimos pacientes creados:")
    for pac in pacientes:
        print(f"  ID: {pac.id}")
        print(f"  Nombre: {pac.nombres} {pac.apellido_paterno} {pac.apellido_materno}")
        print(f"  Teléfono: {pac.telefono}")
        print(f"  Email: {pac.email}")
        print(f"  Fecha de nacimiento: {pac.fecha_nacimiento}")
        print(f"  Creado: {pac.created_at if hasattr(pac, 'created_at') else 'N/A'}")
        print("-" * 80)
else:
    print("\n✗ No se encontraron pacientes con nombre 'María'")
    print("  Esto confirma que el formulario de nuevo paciente NO está guardando en la BD")

print("\nTotal de pacientes en la base de datos:", Paciente.objects.count())
