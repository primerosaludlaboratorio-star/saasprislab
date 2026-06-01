#!/usr/bin/env python
"""
SCRIPT DE QA DETALLADO: Análisis de errores en formularios
"""
import requests
from bs4 import BeautifulSoup
import json
import re

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
print("ANÁLISIS DETALLADO DE ERRORES EN FORMULARIOS")
print("=" * 80)

# ==============================================================================
# ANÁLISIS 1: FORMULARIO DE NUEVO PACIENTE
# ==============================================================================
print("\n1. FORMULARIO DE NUEVO PACIENTE")
print("-" * 80)

response = session.get(f"{BASE_URL}/consultorio/paciente/nuevo/")
soup = BeautifulSoup(response.text, 'html.parser')

# Obtener todos los campos del formulario
form = soup.find('form')
if form:
    print("\nCAMPOS DEL FORMULARIO:")
    inputs = form.find_all(['input', 'select', 'textarea'])
    for inp in inputs:
        name = inp.get('name', 'N/A')
        tipo = inp.get('type', inp.name)
        required = '✓' if inp.get('required') else ' '
        placeholder = inp.get('placeholder', '')
        print(f"  [{required}] {name:25s} ({tipo:10s}) {placeholder}")

# Obtener CSRF y enviar formulario
csrf_token = soup.find('input', {'name': 'csrfmiddlewaretoken'}).get('value')

paciente_data = {
    'csrfmiddlewaretoken': csrf_token,
    'nombres': 'María',
    'apellido_paterno': 'García',
    'apellido_materno': 'López',
    'fecha_nacimiento': '1985-03-15',
    'sexo': 'F',
    'telefono': '5551234567',
    'email': 'maria.garcia@test.com',
}

print("\nDATOS ENVIADOS:")
for k, v in paciente_data.items():
    if k != 'csrfmiddlewaretoken':
        print(f"  {k}: {v}")

response = session.post(
    f"{BASE_URL}/consultorio/paciente/nuevo/",
    data=paciente_data,
    headers={'Referer': f"{BASE_URL}/consultorio/paciente/nuevo/"},
    allow_redirects=False
)

print(f"\nRESPUESTA: Status {response.status_code}")

if response.status_code in [301, 302]:
    print(f"✓ REDIRIGIDO A: {response.headers.get('Location')}")
    print("✓ PACIENTE CREADO EXITOSAMENTE")
    
    # Seguir la redirección para obtener el ID del paciente
    redirect_url = response.headers.get('Location')
    if redirect_url.startswith('/'):
        redirect_url = f"{BASE_URL}{redirect_url}"
    
    response = session.get(redirect_url)
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # Intentar extraer el ID del paciente de la URL o del contenido
    import re
    match = re.search(r'/paciente/(\d+)', redirect_url)
    if match:
        paciente_id = match.group(1)
        print(f"✓ ID DEL PACIENTE: {paciente_id}")
    else:
        # Buscar en la página
        print("⚠ No se pudo extraer el ID del paciente de la URL")
        print(f"  URL de redirección: {redirect_url}")
        
        # Intentar buscar el paciente recién creado en la lista
        response = session.get(f"{BASE_URL}/consultorio/pacientes/")
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            # Buscar enlaces con href que contengan /paciente/
            pacientes = soup.find_all('a', href=re.compile(r'/paciente/(\d+)'))
            if pacientes:
                # Tomar el último (más reciente)
                ultimo_paciente = pacientes[-1]
                href = ultimo_paciente.get('href')
                match = re.search(r'/paciente/(\d+)', href)
                if match:
                    paciente_id = match.group(1)
                    print(f"✓ ID DEL PACIENTE (de lista): {paciente_id}")
        
elif response.status_code == 200:
    print("⚠ FORMULARIO RETORNADO (posibles errores)")
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # Buscar mensajes de error
    errores = soup.find_all(class_=lambda x: x and ('error' in x.lower() or 'invalid' in x.lower()))
    if errores:
        print("\nERRORES ENCONTRADOS:")
        for error in errores:
            print(f"  ✗ {error.get_text(strip=True)}")
    
    # Buscar campos con error específico
    error_fields = soup.find_all(class_=lambda x: x and 'is-invalid' in x.lower())
    if error_fields:
        print("\nCAMPOS CON ERROR:")
        for field in error_fields:
            name = field.get('name', 'N/A')
            print(f"  ✗ Campo: {name}")
    
    # Buscar alertas generales
    alertas = soup.find_all(class_=lambda x: x and 'alert' in x.lower())
    if alertas:
        print("\nALERTAS:")
        for alerta in alertas:
            print(f"  ⚠ {alerta.get_text(strip=True)[:200]}")
    
    if not errores and not error_fields and not alertas:
        print("\n⚠ No se encontraron mensajes de error explícitos")
        print("  El formulario puede haber sido procesado pero sin redirección")
else:
    print(f"✗ ERROR: Status {response.status_code}")

# ==============================================================================
# ANÁLISIS 2: BUSCAR PACIENTE RECIÉN CREADO
# ==============================================================================
print("\n\n2. VERIFICAR PACIENTE EN LA BASE DE DATOS")
print("-" * 80)

# Intentar buscar el paciente recién creado
response = session.get(f"{BASE_URL}/consultorio/pacientes/")
if response.status_code == 200:
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # Buscar "María" en la página
    if 'María' in response.text or 'García' in response.text:
        print("✓ Paciente encontrado en la lista de pacientes")
        
        # Buscar el enlace específico
        import re
        pacientes = soup.find_all(string=re.compile(r'María.*García', re.IGNORECASE))
        if pacientes:
            for pac in pacientes[:3]:
                parent = pac.find_parent('a')
                if parent:
                    href = parent.get('href', '')
                    print(f"  Enlace: {href}")
                    match = re.search(r'/(\d+)', href)
                    if match:
                        global_paciente_id = match.group(1)
                        print(f"  ✓ ID del paciente: {global_paciente_id}")
                else:
                    print(f"  Texto encontrado: {str(pac)[:100]}")
    else:
        print("⚠ Paciente NO encontrado en la lista")
else:
    print(f"✗ No se pudo cargar la lista de pacientes: {response.status_code}")

# ==============================================================================
# ANÁLISIS 3: FORMULARIO DE NUEVA CONSULTA
# ==============================================================================
print("\n\n3. FORMULARIO DE NUEVA CONSULTA (SIN CITA)")
print("-" * 80)

response = session.get(f"{BASE_URL}/consultorio/medico/consulta-sin-cita/")
soup = BeautifulSoup(response.text, 'html.parser')

if response.status_code == 200:
    print("\nCAMPOS DEL FORMULARIO:")
    form = soup.find('form')
    if form:
        inputs = form.find_all(['input', 'select', 'textarea'])
        for inp in inputs:
            name = inp.get('name', 'N/A')
            tipo = inp.get('type', inp.name)
            required = '✓' if inp.get('required') else ' '
            placeholder = inp.get('placeholder', '')
            id_field = inp.get('id', '')
            print(f"  [{required}] {name:25s} ({tipo:10s}) id={id_field:20s} {placeholder}")
    
    # Buscar select de pacientes
    select_paciente = soup.find('select', id=re.compile(r'paciente', re.IGNORECASE))
    if not select_paciente:
        select_paciente = soup.find('select', {'name': re.compile(r'paciente', re.IGNORECASE)})
    
    if select_paciente:
        print("\nOPCIONES DE PACIENTE DISPONIBLES:")
        options = select_paciente.find_all('option')
        for opt in options[:10]:
            value = opt.get('value', '')
            text = opt.get_text(strip=True)
            print(f"  value={value:10s} {text}")
            
            # Si encontramos a María, guardar su ID
            if 'María' in text or 'García' in text:
                print(f"  ✓ PACIENTE MARÍA ENCONTRADO: ID={value}")
                global_paciente_id = value
    else:
        print("\n⚠ No se encontró select de pacientes")
        
        # Buscar input de búsqueda de paciente
        input_paciente = soup.find('input', id=re.compile(r'paciente', re.IGNORECASE))
        if input_paciente:
            print(f"  Se encontró input de búsqueda: {input_paciente.get('id')}")
else:
    print(f"✗ ERROR al cargar formulario: {response.status_code}")

print("\n" + "=" * 80)
print("FIN DEL ANÁLISIS")
print("=" * 80)
