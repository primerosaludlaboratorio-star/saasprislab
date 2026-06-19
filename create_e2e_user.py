#!/usr/bin/env python3
"""Create E2E test user"""
import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

from django.contrib.auth import get_user_model
from core.models import Empresa, Sucursal

User = get_user_model()

# Create test user
username = 'e2e_admin'
password = 'e2e_test_pass_123'
email = 'e2e@test.com'

try:
    # Create empresa if not exists
    empresa, _ = Empresa.objects.get_or_create(
        nombre='E2E Test Company',
        defaults={'rfc': 'TEST1234567890'}
    )
    
    # Create sucursal if not exists
    sucursal, _ = Sucursal.objects.get_or_create(
        empresa=empresa,
        nombre='Sucursal Principal',
        defaults={
            'codigo_sucursal': f'SUC-E2E-{empresa.id}',
            'direccion': 'Test Address',
            'telefono': '5555555555',
            'email': 'sucursal@test.com',
            'responsable': 'E2E Admin'
        }
    )
    
    # Create or update user
    user, created = User.objects.get_or_create(
        username=username,
        defaults={
            'email': email,
            'is_staff': True,
            'is_superuser': True,
            'rol': 'ADMIN',
            'empresa': empresa,
            'sucursal': sucursal,
        }
    )
    
    # Set password
    user.set_password(password)
    user.save()
    
    print(f"✅ User {username} {'created' if created else 'updated'} with password: {password}")
    print(f"   Empresa: {empresa.nombre} (ID: {empresa.id})")
    print(f"   Sucursal: {sucursal.nombre} (ID: {sucursal.id})")
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
