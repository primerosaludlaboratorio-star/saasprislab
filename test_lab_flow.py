#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script de verificación QA para el módulo de laboratorio de PRISLAB
"""
import requests
from requests.exceptions import RequestException
import sys
import os
import logging

# Configurar encoding para Windows
if os.name == 'nt':
    os.system('chcp 65001 > nul')
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

BASE_URL = "http://127.0.0.1:8000"
USERNAME = "jonathan"
PASSWORD = "Admin2024!"

# URLs a verificar
URLS_TO_TEST = [
    {
        "name": "1. Login",
        "url": f"{BASE_URL}/login/",
        "method": "GET",
        "requires_auth": False
    },
    {
        "name": "2. Recepción de Laboratorio",
        "url": f"{BASE_URL}/laboratorio/recepcion/",
        "method": "GET",
        "requires_auth": True
    },
    {
        "name": "3. Lista de Trabajo",
        "url": f"{BASE_URL}/laboratorio/lista-trabajo/",
        "method": "GET",
        "requires_auth": True
    },
    {
        "name": "4. Captura de Resultados (Orden 28)",
        "url": f"{BASE_URL}/laboratorio/captura/28/",
        "method": "GET",
        "requires_auth": True
    },
    {
        "name": "5. Reporte PDF Resultados (Orden 28)",
        "url": f"{BASE_URL}/laboratorio/imprimir/28/",
        "method": "GET",
        "requires_auth": True,
        "is_pdf": True
    },
    {
        "name": "6. Ticket de Laboratorio (Orden 28)",
        "url": f"{BASE_URL}/laboratorio/ticket/28/",
        "method": "GET",
        "requires_auth": True
    },
    {
        "name": "7. Reporte PDF (Orden 29)",
        "url": f"{BASE_URL}/laboratorio/imprimir/29/",
        "method": "GET",
        "requires_auth": True,
        "is_pdf": True
    }
]

def login(session):
    """Realiza el login y retorna la sesión autenticada"""
    print("\n" + "="*80)
    print("🔐 INICIANDO SESIÓN")
    print("="*80)
    
    try:
        # Obtener página de login para obtener CSRF token
        login_page = session.get(f"{BASE_URL}/login/")
        print(f"✓ GET {BASE_URL}/login/ - Status: {login_page.status_code}")
        
        if login_page.status_code != 200:
            print(f"❌ ERROR: No se pudo cargar la página de login (Status: {login_page.status_code})")
            return False
        
        # Extraer CSRF token
        csrf_token = None
        if 'csrftoken' in session.cookies:
            csrf_token = session.cookies['csrftoken']
        
        if not csrf_token:
            print("❌ ERROR: No se pudo obtener el CSRF token")
            return False
        
        print(f"✓ CSRF Token obtenido: {csrf_token[:20]}...")
        
        # Realizar login
        login_data = {
            'username': USERNAME,
            'password': PASSWORD,
            'csrfmiddlewaretoken': csrf_token
        }
        
        headers = {
            'Referer': f"{BASE_URL}/login/"
        }
        
        response = session.post(f"{BASE_URL}/login/", data=login_data, headers=headers, allow_redirects=False)
        print(f"✓ POST {BASE_URL}/login/ - Status: {response.status_code}")
        
        # Verificar si el login fue exitoso (redirect o 200)
        if response.status_code in [200, 302, 301]:
            # Verificar si tenemos sessionid
            if 'sessionid' in session.cookies:
                print(f"✅ LOGIN EXITOSO - Session ID: {session.cookies['sessionid'][:20]}...")
                return True
            else:
                print("⚠️  Login retornó status correcto pero no hay sessionid en cookies")
                print(f"Cookies: {list(session.cookies.keys())}")
                # Intentar acceder al dashboard para confirmar
                dashboard = session.get(f"{BASE_URL}/dashboard/", allow_redirects=False)
                if dashboard.status_code == 200:
                    print("✅ LOGIN CONFIRMADO (acceso a dashboard exitoso)")
                    return True
                else:
                    print(f"❌ No se pudo confirmar login (dashboard status: {dashboard.status_code})")
                    return False
        else:
            print(f"❌ ERROR: Login falló con status {response.status_code}")
            return False
            
    except RequestException as e:
        print(f"❌ ERROR en login: {str(e)}")
        return False

def test_url(session, test_config):
    """Prueba una URL específica y retorna el resultado"""
    url = test_config["url"]
    name = test_config["name"]
    is_pdf = test_config.get("is_pdf", False)
    
    print("\n" + "-"*80)
    print(f"🔍 {name}")
    print(f"URL: {url}")
    print("-"*80)
    
    result = {
        "name": name,
        "url": url,
        "status": None,
        "success": False,
        "error": None,
        "has_content": False,
        "content_type": None,
        "content_length": 0,
        "observations": []
    }
    
    try:
        response = session.get(url, timeout=30)
        result["status"] = response.status_code
        result["content_type"] = response.headers.get('Content-Type', 'Unknown')
        result["content_length"] = len(response.content)
        
        print(f"Status Code: {response.status_code}")
        print(f"Content-Type: {result['content_type']}")
        print(f"Content-Length: {result['content_length']} bytes")
        
        # Evaluar resultado
        if response.status_code == 200:
            result["success"] = True
            result["has_content"] = result["content_length"] > 0
            
            if is_pdf:
                # Verificar si es realmente un PDF
                if 'application/pdf' in result["content_type"]:
                    print("✅ PDF descargado correctamente")
                    # Verificar que el PDF tenga contenido mínimo
                    if result["content_length"] > 1000:
                        print(f"✅ PDF tiene contenido ({result['content_length']} bytes)")
                        result["observations"].append("PDF con contenido válido")
                    else:
                        print(f"⚠️  PDF muy pequeño ({result['content_length']} bytes)")
                        result["observations"].append("PDF posiblemente vacío o incompleto")
                else:
                    print(f"⚠️  Se esperaba PDF pero se recibió: {result['content_type']}")
                    result["observations"].append(f"Content-Type incorrecto: {result['content_type']}")
            else:
                # Verificar HTML
                if 'text/html' in result["content_type"]:
                    print("✅ Página HTML cargada")
                    # Buscar indicadores de error en el HTML
                    content_lower = response.text.lower()
                    if 'error' in content_lower or 'exception' in content_lower:
                        print("⚠️  La página contiene palabras relacionadas con errores")
                        result["observations"].append("Posibles errores en el contenido HTML")
                    if '<body' in content_lower and '</body>' in content_lower:
                        print("✅ HTML con estructura completa")
                        result["observations"].append("HTML bien formado")
                else:
                    print(f"⚠️  Se esperaba HTML pero se recibió: {result['content_type']}")
                    result["observations"].append(f"Content-Type inesperado: {result['content_type']}")
        
        elif response.status_code == 404:
            result["error"] = "Página no encontrada (404)"
            print(f"❌ {result['error']}")
            
        elif response.status_code == 403:
            result["error"] = "Acceso prohibido (403)"
            print(f"❌ {result['error']}")
            
        elif response.status_code == 500:
            result["error"] = "Error interno del servidor (500)"
            print(f"❌ {result['error']}")
            # Intentar extraer mensaje de error
            if 'text/html' in result["content_type"]:
                if 'exception' in response.text.lower():
                    print("⚠️  La respuesta contiene información de excepción")
                    
        elif response.status_code in [301, 302]:
            redirect_url = response.headers.get('Location', 'Unknown')
            result["error"] = f"Redirección ({response.status_code}) a: {redirect_url}"
            print(f"⚠️  {result['error']}")
            result["observations"].append(f"Redirige a: {redirect_url}")
        
        else:
            result["error"] = f"Status code inesperado: {response.status_code}"
            print(f"⚠️  {result['error']}")
            
    except RequestException as e:
        result["error"] = f"Excepción de red: {str(e)}"
        print(f"❌ ERROR: {result['error']}")
    except Exception as e:
        logging.getLogger(__name__).exception("Error inesperado en test_url (test_lab_flow.py)")
        result["error"] = f"Error inesperado: {str(e)}"
        print(f"❌ ERROR: {result['error']}")
    
    return result

def generate_report(results):
    """Genera el reporte final de la verificación"""
    print("\n" + "="*80)
    print("📊 REPORTE FINAL DE VERIFICACIÓN QA - MÓDULO DE LABORATORIO")
    print("="*80)
    
    total = len(results)
    successful = sum(1 for r in results if r["success"])
    failed = total - successful
    
    print(f"\n📈 RESUMEN:")
    print(f"   Total de URLs probadas: {total}")
    print(f"   ✅ Exitosas: {successful}")
    print(f"   ❌ Fallidas: {failed}")
    print(f"   📊 Tasa de éxito: {(successful/total*100):.1f}%")
    
    print(f"\n📋 DETALLE POR URL:\n")
    
    for i, result in enumerate(results, 1):
        status_icon = "✅" if result["success"] else "❌"
        print(f"{status_icon} {result['name']}")
        print(f"   URL: {result['url']}")
        print(f"   Status HTTP: {result['status']}")
        print(f"   Content-Type: {result['content_type']}")
        print(f"   Tamaño: {result['content_length']} bytes")
        
        if result["error"]:
            print(f"   ❌ Error: {result['error']}")
        
        if result["observations"]:
            print(f"   📝 Observaciones:")
            for obs in result["observations"]:
                print(f"      - {obs}")
        
        print()
    
    print("="*80)
    print("🏁 VERIFICACIÓN COMPLETADA")
    print("="*80)
    
    return successful == total

def main():
    """Función principal"""
    print("="*80)
    print("🧪 INICIANDO VERIFICACIÓN QA - MÓDULO DE LABORATORIO PRISLAB")
    print("="*80)
    print(f"Servidor: {BASE_URL}")
    print(f"Usuario: {USERNAME}")
    print(f"Total de URLs a verificar: {len(URLS_TO_TEST)}")
    
    # Crear sesión
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'PRISLAB-QA-Agent/1.0'
    })
    
    # Realizar login
    if not login(session):
        print("\n❌ ERROR CRÍTICO: No se pudo iniciar sesión. Abortando verificación.")
        sys.exit(1)
    
    # Ejecutar pruebas
    print("\n" + "="*80)
    print("🧪 EJECUTANDO PRUEBAS DE URLs")
    print("="*80)
    
    results = []
    for test_config in URLS_TO_TEST:
        if test_config.get("requires_auth", False):
            result = test_url(session, test_config)
            results.append(result)
    
    # Generar reporte
    all_passed = generate_report(results)
    
    # Retornar código de salida
    sys.exit(0 if all_passed else 1)

if __name__ == "__main__":
    main()