#!/usr/bin/env python
"""
Script para ejecutar pruebas End-to-End y generar reporte.
Ejecutar: python ejecutar_pruebas_e2e.py
"""

import os
import sys
import django
from datetime import datetime

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.test.utils import get_runner
from django.conf import settings

def main():
    print("="*70)
    print("PRUEBAS END-TO-END (E2E) - LABORATORIO Y FARMACIA")
    print("="*70)
    print(f"\nFecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("\nIniciando pruebas con Selenium...\n")
    
    # Configurar test runner
    TestRunner = get_runner(settings)
    test_runner = TestRunner(verbosity=2, interactive=False, keepdb=False)
    
    # Ejecutar tests
    try:
        failures = test_runner.run_tests(['core.tests_e2e'])
        
        # Generar reporte
        reporte = f"""
{'='*70}
REPORTE DE PRUEBAS END-TO-END
{'='*70}

Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

Estado: {'ÉXITO' if failures == 0 else 'FALLOS DETECTADOS'}

Pruebas ejecutadas:
- Laboratorio: Recepción, Creación de Paciente, Orden, Captura, Validación, PDF
- Farmacia: Búsqueda, Carrito, Cantidades, Pagos

{'='*70}
"""
        
        # Guardar reporte
        with open('reporte_e2e.txt', 'w', encoding='utf-8') as f:
            f.write(reporte)
        
        print(reporte)
        print(f"\nReporte guardado en: reporte_e2e.txt")
        
        if failures == 0:
            print("\n[OK] TODAS LAS PRUEBAS PASARON EXITOSAMENTE")
            return 0
        else:
            print(f"\n[ERROR] SE ENCONTRARON {failures} FALLOS")
            return 1
            
    except Exception as e:
        print(f"\n[ERROR] ERROR CRITICO: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == '__main__':
    sys.exit(main())
