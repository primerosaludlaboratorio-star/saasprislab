#!/usr/bin/env python
"""
Debug: Ver el HTML completo retornado por PRIS Sentinel
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

# Obtener CSRF token fresco
response = session.get(f"{BASE_URL}/consultorio/")
soup = BeautifulSoup(response.text, 'html.parser')
csrf_token = soup.find('input', {'name': 'csrfmiddlewaretoken'}).get('value')

# Enviar POST
paciente_data = {
    'csrfmiddlewaretoken': csrf_token,
    'nombres': 'DebugTest2',
    'apellido_paterno': 'Apellido1',
    'apellido_materno': 'Apellido2',
    'fecha_nacimiento': '1990-01-01',
    'sexo': 'M',
    'telefono': '5555555555',
    'email': 'debug.test2@example.com',
}

response = session.post(
    f"{BASE_URL}/consultorio/paciente/nuevo/",
    data=paciente_data,
    headers={'Referer': f"{BASE_URL}/consultorio/"},
    allow_redirects=False
)

print("=" * 100)
print("HTML RETORNADO POR PRIS SENTINEL")
print("=" * 100)

soup = BeautifulSoup(response.text, 'html.parser')

# Buscar el mensaje de error
error_msg = soup.find(id='error-message')
if error_msg:
    print("\nMENSAJE DE ERROR:")
    print(error_msg.get_text(strip=True))

# Buscar detalles técnicos
tech_details = soup.find(id='tech-details')
if tech_details:
    print("\nDETALLES TÉCNICOS:")
    print(tech_details.get_text(strip=True)[:1000])

# Buscar cualquier texto que contenga "error" o "exception"
all_text = soup.get_text()
if 'error' in all_text.lower() or 'exception' in all_text.lower():
    lines = all_text.split('\n')
    print("\nLÍNEAS CON 'ERROR' O 'EXCEPTION':")
    for line in lines:
        if 'error' in line.lower() or 'exception' in line.lower():
            line_clean = ' '.join(line.split())
            if line_clean:
                print(f"  {line_clean[:150]}")

# Guardar HTML completo a archivo para inspección
with open("debug_sentinel_response.html", "w", encoding="utf-8") as f:
    f.write(response.text)

print("\n✓ HTML completo guardado en: debug_sentinel_response.html")
