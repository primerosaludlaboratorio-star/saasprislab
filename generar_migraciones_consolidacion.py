#!/usr/bin/env python
"""
Script para generar migraciones de consolidación de forma no-interactiva.
Responde automáticamente "1" a la pregunta de Django sobre UUID field.
"""

import os
import sys
import subprocess

def main():
    print("=" * 70)
    print("  GENERADOR DE MIGRACIONES - PRISLAB V5 CONSOLIDACIÓN FINAL")
    print("=" * 70)
    print()
    
    # Cambiar al directorio del proyecto
    project_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(project_dir)
    
    print(f"Directorio de trabajo: {project_dir}")
    print()
    
    # Comando para generar migraciones
    apps_to_migrate = ['core', 'farmacia']
    
    for app in apps_to_migrate:
        print(f"Generando migraciones para {app}...")
        print("-" * 70)
        
        try:
            # Usar subprocess con input automático
            process = subprocess.Popen(
                [sys.executable, 'manage.py', 'makemigrations', app],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True
            )
            
            # Enviar "1" como respuesta a la pregunta interactiva
            output, _ = process.communicate(input="1\n", timeout=60)
            
            print(output)
            
            if process.returncode == 0:
                print(f"✅ Migraciones de {app} generadas exitosamente")
            else:
                print(f"❌ Error al generar migraciones de {app}")
                print(f"Código de salida: {process.returncode}")
        
        except subprocess.TimeoutExpired:
            print(f"⏱️ Timeout al generar migraciones de {app}")
            process.kill()
        except Exception as e:
            print(f"❌ Error inesperado: {e}")
        
        print()
    
    print("=" * 70)
    print("PROCESO COMPLETADO")
    print()
    print("Siguiente paso: python manage.py migrate")
    print("=" * 70)


if __name__ == '__main__':
    main()
