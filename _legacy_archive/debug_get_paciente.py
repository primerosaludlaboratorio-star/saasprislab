#!/usr/bin/env python
"""
Debug: ¿Qué pasa cuando hago GET a /consultorio/paciente/nuevo/?
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
print("DEBUG: GET a /consultorio/paciente/nuevo/")
print("=" * 80)

response = session.get(f"{BASE_URL}/consultorio/paciente/nuevo/", allow_redirects=True)

print(f"\nStatus Code: {response.status_code}")
print(f"URL Final: {response.url}")
print(f"Content-Type: {response.headers.get('content-type')}")
print(f"\nRedirecciones:")
for r in response.history:
    print(f"  {r.status_code} → {r.url}")

soup = BeautifulSoup(response.text, 'html.parser')
title = soup.find('title')
if title:
    print(f"\nTítulo de la página: {title.get_text(strip=True)}")

# Buscar si hay un formulario
forms = soup.find_all('form')
print(f"\nFormularios encontrados: {len(forms)}")

# Buscar si hay un modal de paciente
modal_paciente = soup.find(id=lambda x: x and 'paciente' in x.lower())
if modal_paciente:
    print(f"\nSe encontró modal de paciente: {modal_paciente.get('id')}")
    
    # Buscar formulario dentro del modal
    form_modal = modal_paciente.find('form')
    if form_modal:
        print("  ✓ Hay formulario dentro del modal")
        
        # Obtener action del formulario
        action = form_modal.get('action', 'N/A')
        method = form_modal.get('method', 'N/A')
        print(f"  Action: {action}")
        print(f"  Method: {method}")
        
        # Campos del formulario
        inputs = form_modal.find_all(['input', 'select', 'textarea'])
        print(f"\n  Campos ({len(inputs)}):")
        for inp in inputs[:15]:
            name = inp.get('name', 'N/A')
            tipo = inp.get('type', inp.name)
            if tipo != 'hidden':
                print(f"    - {name} ({tipo})")
