#!/usr/bin/env python
"""
Script para ejecutar pruebas E2E con Playwright - Usuario Fantasma
Incluye instalación automática de Playwright si no está instalado.

Uso:
    python ejecutar_pruebas_playwright.py
"""
import os
import sys
import subprocess
import django
import logging

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

def verificar_playwright():
    """Verifica si Playwright está instalado."""
    try:
        import playwright
        return True
    except ImportError:
        return False

def instalar_playwright():
    """Instala Playwright y Chromium."""
    print('📦 Instalando Playwright...')
    try:
        subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'playwright'])
        print('📦 Instalando navegadores de Playwright...')
        subprocess.check_call([sys.executable, '-m', 'playwright', 'install', 'chromium'])
        print('✅ Playwright instalado correctamente')
        return True
    except Exception as e:
        logging.getLogger(__name__).exception("Error inesperado en instalar_playwright (ejecutar_pruebas_playwright.py)")
        print(f'❌ Error al instalar Playwright: {str(e)}')
        return False

def ejecutar_pruebas():
    """Ejecuta las pruebas E2E."""
    from django.core.management import call_command
    
    print('\n' + '='*80)
    print('🚀 EJECUTANDO PRUEBAS E2E - USUARIO FANTASMA')
    print('='*80 + '\n')
    
    try:
        # Ejecutar pruebas
        call_command('test', 'core.tests_e2e_playwright', verbosity=2)
        print('\n✅ Pruebas completadas')
    except Exception as e:
        logging.getLogger(__name__).exception("Error inesperado en ejecutar_pruebas (ejecutar_pruebas_playwright.py)")
        print(f'\n❌ Error al ejecutar pruebas: {str(e)}')
        sys.exit(1)

if __name__ == '__main__':
    if not verificar_playwright():
        print('⚠️  Playwright no está instalado')
        respuesta = input('¿Deseas instalar Playwright ahora? (s/n): ')
        if respuesta.lower() == 's':
            if instalar_playwright():
                ejecutar_pruebas()
            else:
                print('❌ No se pudo instalar Playwright')
                sys.exit(1)
        else:
            print('❌ Playwright es requerido para ejecutar las pruebas')
            sys.exit(1)
    else:
        ejecutar_pruebas()