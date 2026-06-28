#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script de análisis detallado de hallazgos del módulo de laboratorio
"""
import requests
import sys
import os
from io import BytesIO

# Configurar encoding para Windows
if os.name == 'nt':
    os.system('chcp 65001 > nul')
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

BASE_URL = "http://127.0.0.1:8000"
USERNAME = "jonathan"
PASSWORD = "Admin2024!"

def login():
    """Login y retornar sesión autenticada"""
    session = requests.Session()
    
    # Obtener CSRF token
    login_page = session.get(f"{BASE_URL}/login/")
    csrf_token = session.cookies.get('csrftoken')
    
    # Login
    login_data = {
        'username': USERNAME,
        'password': PASSWORD,
        'csrfmiddlewaretoken': csrf_token
    }
    headers = {'Referer': f"{BASE_URL}/login/"}
    session.post(f"{BASE_URL}/login/", data=login_data, headers=headers)
    
    return session

def analyze_pdf(session, url, name):
    """Analiza el contenido de un PDF"""
    print("\n" + "="*80)
    print(f"📄 Analizando PDF: {name}")
    print(f"URL: {url}")
    print("="*80)
    
    response = session.get(url)
    
    print(f"Status: {response.status_code}")
    print(f"Content-Type: {response.headers.get('Content-Type')}")
    print(f"Tamaño: {len(response.content)} bytes")
    
    # Guardar PDF para inspección
    filename = f"test_{name.replace(' ', '_').replace('(', '').replace(')', '')}.pdf"
    with open(filename, 'wb') as f:
        f.write(response.content)
    print(f"✓ PDF guardado en: {filename}")
    
    # Analizar contenido
    content = response.content
    
    # Verificar headers PDF
    if content.startswith(b'%PDF'):
        print("✅ Archivo tiene header PDF válido")
        
        # Buscar elementos comunes
        if b'/Type /Catalog' in content:
            print("✅ Contiene catálogo de PDF")
        if b'/Type /Page' in content:
            print("✅ Contiene definición de páginas")
        if b'stream' in content:
            print("✅ Contiene streams de contenido")
        else:
            print("⚠️  No se encontraron streams de contenido")
            
        # Ver si hay texto visible
        if b'BT' in content and b'ET' in content:
            print("✅ Contiene operadores de texto (BT/ET)")
        else:
            print("⚠️  No se encontraron operadores de texto")
            
        # Contar páginas
        page_count = content.count(b'/Type /Page')
        print(f"📄 Páginas detectadas: {page_count}")
        
    else:
        print("❌ NO es un PDF válido (falta header %PDF)")
        print(f"Primeros 50 bytes: {content[:50]}")
    
    return len(response.content)

def analyze_html_errors(session, url, name):
    """Analiza errores en páginas HTML"""
    print("\n" + "="*80)
    print(f"🔍 Analizando errores en: {name}")
    print(f"URL: {url}")
    print("="*80)
    
    response = session.get(url)
    html = response.text
    
    # Buscar indicadores de error comunes
    error_patterns = [
        ('Exception', 'Excepciones de Python'),
        ('Traceback', 'Stack traces'),
        ('Error:', 'Mensajes de error explícitos'),
        ('class="alert-danger"', 'Alertas de peligro'),
        ('class="error"', 'Clases de error'),
        ('console.error', 'Errores de JavaScript'),
        ('{% error', 'Errores de template Django'),
    ]
    
    found_errors = []
    for pattern, description in error_patterns:
        if pattern.lower() in html.lower():
            found_errors.append((pattern, description))
    
    if found_errors:
        print("⚠️  Se encontraron indicadores de error:")
        for pattern, description in found_errors:
            count = html.lower().count(pattern.lower())
            print(f"   - {description} ({pattern}): {count} ocurrencias")
            
            # Extraer contexto
            idx = html.lower().find(pattern.lower())
            if idx != -1:
                start = max(0, idx - 100)
                end = min(len(html), idx + 200)
                context = html[start:end].replace('\n', ' ').strip()
                print(f"     Contexto: ...{context}...")
    else:
        print("✅ No se encontraron patrones de error comunes")
    
    # Verificar contenido útil
    if '<table' in html:
        table_count = html.count('<table')
        print(f"✅ Contiene {table_count} tablas")
    
    if 'data-orden' in html or 'orden-' in html:
        print("✅ Contiene referencias a órdenes de laboratorio")
    
    if '<form' in html:
        form_count = html.count('<form')
        print(f"✅ Contiene {form_count} formularios")
    
    return len(found_errors)

def main():
    print("="*80)
    print("🔬 ANÁLISIS DETALLADO - MÓDULO DE LABORATORIO")
    print("="*80)
    
    # Login
    print("\n🔐 Iniciando sesión...")
    session = login()
    print("✅ Sesión iniciada")
    
    # Analizar PDFs problemáticos
    print("\n" + "="*80)
    print("📑 ANÁLISIS DE PDFs")
    print("="*80)
    
    pdf_urls = [
        ("http://127.0.0.1:8000/laboratorio/imprimir/28/", "PDF_Orden_28"),
        ("http://127.0.0.1:8000/laboratorio/imprimir/29/", "PDF_Orden_29"),
    ]
    
    pdf_sizes = []
    for url, name in pdf_urls:
        size = analyze_pdf(session, url, name)
        pdf_sizes.append((name, size))
    
    # Analizar páginas HTML con errores
    print("\n" + "="*80)
    print("🔍 ANÁLISIS DE PÁGINAS HTML")
    print("="*80)
    
    html_urls = [
        ("http://127.0.0.1:8000/laboratorio/recepcion/", "Recepción"),
        ("http://127.0.0.1:8000/laboratorio/lista-trabajo/", "Lista de Trabajo"),
        ("http://127.0.0.1:8000/laboratorio/captura/28/", "Captura Orden 28"),
    ]
    
    error_counts = []
    for url, name in html_urls:
        error_count = analyze_html_errors(session, url, name)
        error_counts.append((name, error_count))
    
    # Resumen final
    print("\n" + "="*80)
    print("📊 RESUMEN DE ANÁLISIS DETALLADO")
    print("="*80)
    
    print("\n📄 PDFs analizados:")
    for name, size in pdf_sizes:
        status = "⚠️  VACÍO" if size < 1000 else "✅ OK"
        print(f"   {status} {name}: {size} bytes")
    
    print("\n🔍 Páginas HTML analizadas:")
    for name, error_count in error_counts:
        status = "⚠️  CON ERRORES" if error_count > 0 else "✅ SIN ERRORES"
        print(f"   {status} {name}: {error_count} patrones de error encontrados")
    
    print("\n" + "="*80)
    print("🏁 ANÁLISIS COMPLETADO")
    print("="*80)

if __name__ == "__main__":
    main()
