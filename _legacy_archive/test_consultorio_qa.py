#!/usr/bin/env python
"""
SCRIPT DE QA: Flujo completo del módulo de consulta médica PRISLAB
Fecha: 22 de Febrero de 2026
"""
import requests
from bs4 import BeautifulSoup
import json
from datetime import datetime
import logging

# Configuración
BASE_URL = "http://127.0.0.1:8000"
USERNAME = "jonathan"
PASSWORD = "Admin2024!"

# Sesión persistente para mantener cookies
session = requests.Session()

def log_paso(paso, mensaje, status="✓", detalles=None):
    """Registra un paso del test con formato."""
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"\n[{timestamp}] {status} PASO {paso}: {mensaje}")
    if detalles:
        print(f"  Detalles: {detalles}")

def log_error(mensaje, detalles=None):
    """Registra un error."""
    print(f"\n❌ ERROR: {mensaje}")
    if detalles:
        print(f"  Detalles: {detalles}")

def log_url(url, status_code, headers=None):
    """Registra información de la URL visitada."""
    status_icon = "✓" if status_code == 200 else "✗"
    print(f"  {status_icon} URL: {url}")
    print(f"  {status_icon} Status Code: {status_code}")
    if headers:
        print(f"  Content-Type: {headers.get('content-type', 'N/A')}")

# ==============================================================================
# PASO 1: LOGIN
# ==============================================================================
def test_login():
    log_paso(1, "Intentando hacer login")
    
    # Primero obtener la página de login para el token CSRF
    try:
        response = session.get(f"{BASE_URL}/")
        log_url(f"{BASE_URL}/", response.status_code, response.headers)
        
        if response.status_code != 200:
            log_error(f"No se pudo cargar la página de inicio", f"Status: {response.status_code}")
            return False
        
        # Extraer CSRF token
        soup = BeautifulSoup(response.text, 'html.parser')
        csrf_token = None
        
        # Buscar el token en el formulario de login
        csrf_input = soup.find('input', {'name': 'csrfmiddlewaretoken'})
        if csrf_input:
            csrf_token = csrf_input.get('value')
        
        if not csrf_token:
            log_error("No se encontró el token CSRF en la página de login")
            return False
        
        # Hacer login
        login_data = {
            'username': USERNAME,
            'password': PASSWORD,
            'csrfmiddlewaretoken': csrf_token
        }
        
        response = session.post(
            f"{BASE_URL}/login/",
            data=login_data,
            headers={'Referer': f"{BASE_URL}/"}
        )
        
        log_url(f"{BASE_URL}/login/", response.status_code, response.headers)
        
        # Verificar si el login fue exitoso (redirección o status 200)
        if response.status_code in [200, 302, 301]:
            # Verificar si tenemos la cookie de sesión
            if 'sessionid' in session.cookies:
                log_paso(1, "Login exitoso", "✓", f"Usuario: {USERNAME}")
                return True
            else:
                log_error("Login falló: no se obtuvo cookie de sesión")
                return False
        else:
            log_error(f"Login falló con status {response.status_code}")
            return False
            
    except Exception as e:
        logging.getLogger(__name__).exception("Error inesperado en test_login (test_consultorio_qa.py)")
        log_error(f"Excepción durante el login: {str(e)}")
        return False

# ==============================================================================
# PASO 2: NAVEGAR AL DASHBOARD DE CONSULTORIO
# ==============================================================================
def test_dashboard_consultorio():
    log_paso(2, "Navegando al dashboard de consultorio")
    
    try:
        response = session.get(f"{BASE_URL}/consultorio/")
        log_url(f"{BASE_URL}/consultorio/", response.status_code, response.headers)
        
        if response.status_code == 200:
            log_paso(2, "Dashboard de consultorio cargado correctamente", "✓")
            
            # Analizar el contenido de la página
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Buscar botones importantes
            botones = soup.find_all('a', class_=lambda x: x and ('btn' in x or 'button' in x))
            log_paso(2, f"Botones encontrados: {len(botones)}", "ℹ")
            
            for btn in botones[:10]:  # Mostrar los primeros 10
                texto = btn.get_text(strip=True)
                href = btn.get('href', '')
                print(f"    - {texto}: {href}")
            
            return True
        elif response.status_code == 404:
            log_error("Dashboard de consultorio no encontrado (404)")
            return False
        elif response.status_code == 500:
            log_error("Error 500 en el dashboard de consultorio")
            # Intentar extraer el mensaje de error
            if 'text/html' in response.headers.get('content-type', ''):
                soup = BeautifulSoup(response.text, 'html.parser')
                error_msg = soup.find('div', class_='exception_value')
                if error_msg:
                    print(f"  Mensaje de error: {error_msg.get_text(strip=True)}")
            return False
        else:
            log_error(f"Dashboard retornó status inesperado: {response.status_code}")
            return False
            
    except Exception as e:
        logging.getLogger(__name__).exception("Error inesperado en test_dashboard_consultorio (test_consultorio_qa.py)")
        log_error(f"Excepción al navegar al dashboard: {str(e)}")
        return False

# ==============================================================================
# PASO 3: BUSCAR PÁGINA DE NUEVO PACIENTE
# ==============================================================================
def test_buscar_nuevo_paciente():
    log_paso(3, "Buscando página para crear nuevo paciente")
    
    urls_a_probar = [
        "/consultorio/paciente/nuevo/",
        "/pacientes/nuevo/",
        "/core/paciente/nuevo/",
        "/consultorio/pacientes/nuevo/",
    ]
    
    for url in urls_a_probar:
        try:
            response = session.get(f"{BASE_URL}{url}")
            log_url(f"{BASE_URL}{url}", response.status_code, response.headers)
            
            if response.status_code == 200:
                log_paso(3, f"Página de nuevo paciente encontrada en {url}", "✓")
                
                # Analizar el formulario
                soup = BeautifulSoup(response.text, 'html.parser')
                form = soup.find('form')
                
                if form:
                    inputs = form.find_all(['input', 'select', 'textarea'])
                    log_paso(3, f"Formulario encontrado con {len(inputs)} campos", "ℹ")
                    
                    for inp in inputs[:15]:  # Mostrar los primeros 15
                        name = inp.get('name', 'N/A')
                        tipo = inp.get('type', inp.name)
                        required = 'required' if inp.get('required') else ''
                        print(f"    - {name} ({tipo}) {required}")
                    
                    return url
                else:
                    log_paso(3, "No se encontró formulario en la página", "⚠")
                    
        except Exception as e:
            logging.getLogger(__name__).exception("Error inesperado en test_buscar_nuevo_paciente (test_consultorio_qa.py)")
            log_error(f"Error al probar URL {url}: {str(e)}")
    
    log_error("No se encontró la página de nuevo paciente en ninguna URL probada")
    return None

# ==============================================================================
# PASO 4: CREAR NUEVO PACIENTE
# ==============================================================================
def test_crear_paciente(url_formulario):
    log_paso(4, "Intentando crear nuevo paciente")
    
    try:
        # Primero obtener el formulario para el token CSRF
        response = session.get(f"{BASE_URL}{url_formulario}")
        soup = BeautifulSoup(response.text, 'html.parser')
        
        csrf_token = None
        csrf_input = soup.find('input', {'name': 'csrfmiddlewaretoken'})
        if csrf_input:
            csrf_token = csrf_input.get('value')
        
        if not csrf_token:
            log_error("No se encontró el token CSRF en el formulario")
            return None
        
        # Datos del paciente
        paciente_data = {
            'csrfmiddlewaretoken': csrf_token,
            'nombre': 'María García López',
            'telefono': '555-1234567',
            'fecha_nacimiento': '1985-03-15',
            # Intentar diferentes nombres de campos comunes
            'nombres': 'María',
            'apellido_paterno': 'García',
            'apellido_materno': 'López',
            'email': 'maria.garcia@example.com',
            'sexo': 'F',
            'curp': 'GAPM850315MDFRRR09',
        }
        
        # Enviar el formulario
        response = session.post(
            f"{BASE_URL}{url_formulario}",
            data=paciente_data,
            headers={'Referer': f"{BASE_URL}{url_formulario}"}
        )
        
        log_url(f"{BASE_URL}{url_formulario}", response.status_code, response.headers)
        
        if response.status_code == 200:
            # Verificar si hay errores en el formulario
            soup = BeautifulSoup(response.text, 'html.parser')
            errores = soup.find_all(class_=lambda x: x and ('error' in x.lower() or 'invalid' in x.lower()))
            
            if errores:
                log_error("El formulario retornó errores de validación")
                for error in errores[:5]:
                    print(f"  - {error.get_text(strip=True)}")
                return None
            else:
                log_paso(4, "Formulario enviado, verificando si se creó el paciente", "⚠")
                # Puede haber quedado en la misma página si no redirigió
                return None
                
        elif response.status_code in [302, 301]:
            # Redirección - probablemente exitoso
            redirect_url = response.headers.get('Location', 'N/A')
            log_paso(4, f"Paciente creado exitosamente (redirigido a {redirect_url})", "✓")
            
            # Intentar extraer el ID del paciente de la URL de redirección
            import re
            match = re.search(r'/(\d+)/?$', redirect_url)
            if match:
                return match.group(1)
            return True
            
        elif response.status_code == 500:
            log_error("Error 500 al crear el paciente")
            if 'text/html' in response.headers.get('content-type', ''):
                soup = BeautifulSoup(response.text, 'html.parser')
                error_msg = soup.find('div', class_='exception_value')
                if error_msg:
                    print(f"  Mensaje de error: {error_msg.get_text(strip=True)}")
            return None
        else:
            log_error(f"Error inesperado al crear paciente: {response.status_code}")
            return None
            
    except Exception as e:
        logging.getLogger(__name__).exception("Error inesperado en test_crear_paciente (test_consultorio_qa.py)")
        log_error(f"Excepción al crear paciente: {str(e)}")
        return None

# ==============================================================================
# PASO 5: BUSCAR PÁGINA DE NUEVA CONSULTA
# ==============================================================================
def test_buscar_nueva_consulta():
    log_paso(5, "Buscando página de nueva consulta")
    
    urls_a_probar = [
        "/consultorio/medico/consulta-sin-cita/",
        "/consultorio/nueva-consulta/",
        "/consultorio/consulta/nueva/",
        "/consultorio/medico/nueva-consulta/",
    ]
    
    for url in urls_a_probar:
        try:
            response = session.get(f"{BASE_URL}{url}")
            log_url(f"{BASE_URL}{url}", response.status_code, response.headers)
            
            if response.status_code == 200:
                log_paso(5, f"Página de nueva consulta encontrada en {url}", "✓")
                
                # Analizar el formulario
                soup = BeautifulSoup(response.text, 'html.parser')
                form = soup.find('form')
                
                if form:
                    inputs = form.find_all(['input', 'select', 'textarea'])
                    log_paso(5, f"Formulario encontrado con {len(inputs)} campos", "ℹ")
                    
                    for inp in inputs[:20]:  # Mostrar los primeros 20
                        name = inp.get('name', 'N/A')
                        tipo = inp.get('type', inp.name)
                        required = 'required' if inp.get('required') else ''
                        print(f"    - {name} ({tipo}) {required}")
                    
                    return url
                else:
                    log_paso(5, "No se encontró formulario en la página", "⚠")
                    
        except Exception as e:
            logging.getLogger(__name__).exception("Error inesperado en test_buscar_nueva_consulta (test_consultorio_qa.py)")
            log_error(f"Error al probar URL {url}: {str(e)}")
    
    log_error("No se encontró la página de nueva consulta en ninguna URL probada")
    return None

# ==============================================================================
# PASO 6: CREAR CONSULTA Y GENERAR RECETA
# ==============================================================================
def test_crear_consulta(url_formulario, paciente_id=None):
    log_paso(6, "Intentando crear consulta y generar receta")
    
    try:
        # Primero obtener el formulario para el token CSRF
        response = session.get(f"{BASE_URL}{url_formulario}")
        soup = BeautifulSoup(response.text, 'html.parser')
        
        csrf_token = None
        csrf_input = soup.find('input', {'name': 'csrfmiddlewaretoken'})
        if csrf_input:
            csrf_token = csrf_input.get('value')
        
        if not csrf_token:
            log_error("No se encontró el token CSRF en el formulario")
            return None
        
        # Datos de la consulta (SOAP)
        consulta_data = {
            'csrfmiddlewaretoken': csrf_token,
            # Datos del paciente
            'paciente_id': paciente_id or '',
            'paciente': paciente_id or '',
            # SOAP
            'subjetivo': 'Paciente refiere dolor de cabeza intenso desde hace 3 días',
            'objetivo': 'TA: 120/80, FC: 72 lpm, FR: 16 rpm, Temp: 36.5°C. Paciente alerta y orientado.',
            'analisis': 'Cefalea tensional',
            'plan': 'Paracetamol 500mg cada 8 horas por 3 días. Descanso y evitar pantallas.',
            # Motivo de consulta
            'motivo_consulta': 'Dolor de cabeza',
            'exploracion_fisica': 'Sin datos de alarma neurológica',
            'diagnostico': 'Cefalea tensional',
            'tratamiento': 'Paracetamol 500mg c/8h por 3 días',
        }
        
        # Enviar el formulario
        response = session.post(
            f"{BASE_URL}{url_formulario}",
            data=consulta_data,
            headers={'Referer': f"{BASE_URL}{url_formulario}"}
        )
        
        log_url(f"{BASE_URL}{url_formulario}", response.status_code, response.headers)
        
        if response.status_code == 200:
            # Verificar si hay errores en el formulario
            soup = BeautifulSoup(response.text, 'html.parser')
            errores = soup.find_all(class_=lambda x: x and ('error' in x.lower() or 'invalid' in x.lower()))
            
            if errores:
                log_error("El formulario retornó errores de validación")
                for error in errores[:5]:
                    print(f"  - {error.get_text(strip=True)}")
                return None
            else:
                log_paso(6, "Formulario enviado, verificando resultado", "⚠")
                return None
                
        elif response.status_code in [302, 301]:
            # Redirección - probablemente exitoso
            redirect_url = response.headers.get('Location', 'N/A')
            log_paso(6, f"Consulta creada exitosamente (redirigido a {redirect_url})", "✓")
            
            # Intentar extraer el ID de la consulta
            import re
            match = re.search(r'/(\d+)/?$', redirect_url)
            if match:
                return match.group(1)
            return True
            
        elif response.status_code == 500:
            log_error("Error 500 al crear la consulta")
            if 'text/html' in response.headers.get('content-type', ''):
                soup = BeautifulSoup(response.text, 'html.parser')
                error_msg = soup.find('div', class_='exception_value')
                if error_msg:
                    print(f"  Mensaje de error: {error_msg.get_text(strip=True)}")
            return None
        else:
            log_error(f"Error inesperado al crear consulta: {response.status_code}")
            return None
            
    except Exception as e:
        logging.getLogger(__name__).exception("Error inesperado en test_crear_consulta (test_consultorio_qa.py)")
        log_error(f"Excepción al crear consulta: {str(e)}")
        return None

# ==============================================================================
# PASO 7: BUSCAR Y DESCARGAR RECETA PDF
# ==============================================================================
def test_descargar_receta_pdf(consulta_id=None):
    log_paso(7, "Buscando y descargando receta PDF")
    
    urls_a_probar = [
        f"/consultorio/receta/{consulta_id}/pdf/" if consulta_id else None,
        f"/consultorio/consulta/{consulta_id}/receta/pdf/" if consulta_id else None,
        "/consultorio/recetas/ultima/pdf/",
        "/consultorio/receta/pdf/",
    ]
    
    urls_a_probar = [url for url in urls_a_probar if url]
    
    for url in urls_a_probar:
        try:
            response = session.get(f"{BASE_URL}{url}")
            log_url(f"{BASE_URL}{url}", response.status_code, response.headers)
            
            if response.status_code == 200:
                content_type = response.headers.get('content-type', '')
                
                if 'pdf' in content_type.lower():
                    log_paso(7, f"PDF de receta descargado exitosamente desde {url}", "✓")
                    log_paso(7, f"Tamaño del PDF: {len(response.content)} bytes", "ℹ")
                    return True
                else:
                    log_paso(7, f"La URL retorna contenido no-PDF: {content_type}", "⚠")
                    
        except Exception as e:
            logging.getLogger(__name__).exception("Error inesperado en test_descargar_receta_pdf (test_consultorio_qa.py)")
            log_error(f"Error al probar URL {url}: {str(e)}")
    
    log_error("No se pudo descargar el PDF de la receta")
    return False

# ==============================================================================
# EJECUTAR TODOS LOS TESTS
# ==============================================================================
def main():
    print("=" * 80)
    print("REPORTE DE QA: Módulo de Consulta Médica PRISLAB")
    print("=" * 80)
    print(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Base URL: {BASE_URL}")
    print(f"Usuario: {USERNAME}")
    print("=" * 80)
    
    resultados = {}
    
    # PASO 1: Login
    resultados['login'] = test_login()
    if not resultados['login']:
        print("\n❌ FLUJO INTERRUMPIDO: No se pudo hacer login")
        return
    
    # PASO 2: Dashboard de consultorio
    resultados['dashboard'] = test_dashboard_consultorio()
    
    # PASO 3: Buscar página de nuevo paciente
    url_nuevo_paciente = test_buscar_nuevo_paciente()
    resultados['buscar_nuevo_paciente'] = url_nuevo_paciente is not None
    
    # PASO 4: Crear paciente
    paciente_id = None
    if url_nuevo_paciente:
        paciente_id = test_crear_paciente(url_nuevo_paciente)
        resultados['crear_paciente'] = paciente_id is not None
    else:
        resultados['crear_paciente'] = False
        log_paso(4, "OMITIDO: No se encontró la página de nuevo paciente", "⊘")
    
    # PASO 5: Buscar página de nueva consulta
    url_nueva_consulta = test_buscar_nueva_consulta()
    resultados['buscar_nueva_consulta'] = url_nueva_consulta is not None
    
    # PASO 6: Crear consulta
    consulta_id = None
    if url_nueva_consulta:
        consulta_id = test_crear_consulta(url_nueva_consulta, paciente_id)
        resultados['crear_consulta'] = consulta_id is not None
    else:
        resultados['crear_consulta'] = False
        log_paso(6, "OMITIDO: No se encontró la página de nueva consulta", "⊘")
    
    # PASO 7: Descargar receta PDF
    if consulta_id or resultados['crear_consulta']:
        resultados['descargar_pdf'] = test_descargar_receta_pdf(consulta_id)
    else:
        resultados['descargar_pdf'] = False
        log_paso(7, "OMITIDO: No se creó la consulta", "⊘")
    
    # ==============================================================================
    # RESUMEN FINAL
    # ==============================================================================
    print("\n" + "=" * 80)
    print("RESUMEN DE RESULTADOS")
    print("=" * 80)
    
    total_tests = len(resultados)
    tests_exitosos = sum(1 for v in resultados.values() if v)
    tests_fallidos = total_tests - tests_exitosos
    
    for paso, resultado in resultados.items():
        icono = "✓" if resultado else "✗"
        print(f"{icono} {paso.replace('_', ' ').title()}: {'EXITOSO' if resultado else 'FALLIDO'}")
    
    print("\n" + "-" * 80)
    print(f"Total de tests: {total_tests}")
    print(f"Tests exitosos: {tests_exitosos}")
    print(f"Tests fallidos: {tests_fallidos}")
    print(f"Porcentaje de éxito: {(tests_exitosos/total_tests*100):.1f}%")
    print("=" * 80)

if __name__ == "__main__":
    main()