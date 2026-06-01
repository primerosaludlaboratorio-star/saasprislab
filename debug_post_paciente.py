#!/usr/bin/env python
"""
Debug: ¿Por qué el POST de paciente retorna 200 en lugar de redirigir?
"""
import requests
from bs4 import BeautifulSoup

BASE_URL = "http://127.0.0.1:8000"
session = requests.Session()

# Login
response = session.get(f"{BASE_URL}/")
soup = BeautifulSoup(response.text, 'html.parser')
csrf_token = soup.find('input', {'name': 'csrfmiddlewaretoken'}).get('value')

login_data = {
    'username': 'jonathan',
    'password': 'Admin2024!',
    'csrfmiddlewaretoken': csrf_token
}
session.post(f"{BASE_URL}/login/", data=login_data, headers={'Referer': f"{BASE_URL}/"})

print("=" * 80)
print("DEBUG: POST a /consultorio/paciente/nuevo/")
print("=" * 80)

# Obtener CSRF token fresco del dashboard
response = session.get(f"{BASE_URL}/consultorio/")
soup = BeautifulSoup(response.text, 'html.parser')

# Buscar el CSRF token en el modal
csrf_input = soup.find('input', {'name': 'csrfmiddlewaretoken'})
if csrf_input:
    csrf_token = csrf_input.get('value')
    print(f"✓ CSRF Token obtenido: {csrf_token[:20]}...")
else:
    print("✗ No se encontró CSRF token")

# Enviar POST con datos
paciente_data = {
    'csrfmiddlewaretoken': csrf_token,
    'nombres': 'TestDebug',
    'apellido_paterno': 'Apellido1',
    'apellido_materno': 'Apellido2',
    'fecha_nacimiento': '1990-01-01',
    'sexo': 'M',
    'telefono': '5555555555',
    'email': 'test.debug@example.com',
}

print("\nDatos enviados:")
for k, v in paciente_data.items():
    if k != 'csrfmiddlewaretoken':
        print(f"  {k}: {v}")

response = session.post(
    f"{BASE_URL}/consultorio/paciente/nuevo/",
    data=paciente_data,
    headers={
        'Referer': f"{BASE_URL}/consultorio/",
        'X-Requested-With': 'XMLHttpRequest'  # Simular AJAX
    },
    allow_redirects=False  # No seguir redirects automáticamente
)

print(f"\nStatus Code: {response.status_code}")
print(f"Content-Type: {response.headers.get('content-type', 'N/A')}")

if response.status_code in [301, 302, 303, 307, 308]:
    redirect_url = response.headers.get('Location', 'N/A')
    print(f"✓ REDIRECCIÓN: {redirect_url}")
elif response.status_code == 200:
    print("⚠ Retornó 200 (sin redirección)")
    
    # Analizar el contenido
    content_type = response.headers.get('content-type', '')
    
    if 'json' in content_type:
        print("  Contenido es JSON:")
        try:
            import json
            data = response.json()
            print(f"    {json.dumps(data, indent=2)}")
        except:
            print("    (No se pudo parsear JSON)")
    elif 'html' in content_type:
        print("  Contenido es HTML")
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Buscar mensajes de error
        errores = soup.find_all(class_=lambda x: x and ('error' in x.lower() or 'alert-danger' in x.lower()))
        if errores:
            print("\n  Errores encontrados:")
            for error in errores[:5]:
                texto = error.get_text(strip=True)
                if texto:
                    print(f"    ✗ {texto}")
        
        # Buscar mensajes de éxito
        success = soup.find_all(class_=lambda x: x and ('success' in x.lower() or 'alert-success' in x.lower()))
        if success:
            print("\n  Mensajes de éxito:")
            for msg in success[:5]:
                texto = msg.get_text(strip=True)
                if texto:
                    print(f"    ✓ {texto}")
        
        if not errores and not success:
            print("  No se encontraron mensajes de error ni éxito")
            
            # Ver las primeras líneas del HTML
            print("\n  Primeras 500 caracteres del HTML:")
            print(f"    {response.text[:500]}")
else:
    print(f"✗ ERROR: Status {response.status_code}")

# Verificar si el paciente se guardó
print("\n" + "=" * 80)
print("VERIFICACIÓN EN BASE DE DATOS")
print("=" * 80)

import sys
import os
import django
sys.path.append(r'C:\Users\jonil\Desktop\PRISLAB_SaaS')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from core.models import Paciente

paciente = Paciente.objects.filter(nombres__icontains='TestDebug').first()
if paciente:
    print("✓ PACIENTE ENCONTRADO EN LA BASE DE DATOS")
    print(f"  ID: {paciente.id}")
    print(f"  Nombre: {paciente.nombres} {paciente.apellido_paterno} {paciente.apellido_materno}")
    print(f"  UUID: {paciente.uuid}")
    print(f"  Teléfono: {paciente.telefono}")
else:
    print("✗ PACIENTE NO ENCONTRADO EN LA BASE DE DATOS")
    print("  El formulario NO está guardando los datos")
