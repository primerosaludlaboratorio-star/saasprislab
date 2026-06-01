#!/usr/bin/env python
"""
Script Rápido de Verificación del Estado del Sistema Prislab
Ejecuta verificaciones básicas sin necesidad de Django setup completo.

Uso:
    python verificar_estado_sistema.py
"""
import os
import sys
import django

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.core.management import call_command
from django.core.management.base import CommandError

if __name__ == '__main__':
    print('\n' + '='*80)
    print('🔍 VERIFICACIÓN RÁPIDA DEL SISTEMA PRISLAB')
    print('='*80 + '\n')
    
    try:
        # Ejecutar auditoría
        call_command('auditar_sistema')
        print('\n✅ Verificación completada exitosamente')
    except CommandError as e:
        print(f'\n❌ Error: {str(e)}')
        sys.exit(1)
    except Exception as e:
        print(f'\n❌ Error inesperado: {str(e)}')
        sys.exit(1)
