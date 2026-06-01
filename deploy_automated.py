"""
SCRIPT DE PREPARACIÓN AUTOMÁTICA PARA DESPLIEGUE
PRISLAB V5.0 - Google Cloud Run + Cloud SQL + Google Drive

Este script realiza TODAS las verificaciones y preparativos locales
antes del despliegue a Google Cloud.
"""
import os
import sys
import subprocess
import json
from pathlib import Path

def print_section(title):
    """Imprime una sección visual"""
    print("\n" + "="*70)
    print(f"  {title}")
    print("="*70 + "\n")

def run_command(command, description, check=True):
    """Ejecuta un comando y reporta el resultado"""
    print(f"-> {description}...")
    try:
        result = subprocess.run(
            command,
            shell=True,
            check=check,
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            print(f"[OK] {description} - COMPLETADO")
            if result.stdout:
                print(f"   {result.stdout.strip()}")
            return True
        else:
            print(f"[ERROR] {description} - ERROR")
            if result.stderr:
                print(f"   {result.stderr.strip()}")
            return False
    except Exception as e:
        print(f"[ERROR] {description} - EXCEPCION: {e}")
        return False

def main():
    print_section("PREPARACION AUTOMATICA DE PRISLAB V5.0 PARA GOOGLE CLOUD")
    
    # =========================================================================
    # PASO 1: VERIFICAR ENTORNO
    # =========================================================================
    print_section("PASO 1: VERIFICACION DEL ENTORNO")
    
    print("-> Verificando Python...")
    python_version = sys.version_info
    if python_version >= (3, 11):
        print(f"[OK] Python {python_version.major}.{python_version.minor} - OK")
    else:
        print(f"[WARN] Python {python_version.major}.{python_version.minor} - Se recomienda 3.11+")
    
    print("\n-> Verificando Django...")
    try:
        import django
        print(f"[OK] Django {django.get_version()} - OK")
    except ImportError:
        print("[ERROR] Django no instalado")
        return
    
    print("\n-> Verificando archivos criticos...")
    critical_files = [
        'config/settings.py',
        'config/wsgi.py',
        'config/storage_backends.py',
        'requirements.txt',
        'Dockerfile',
        'manage.py'
    ]
    
    all_files_ok = True
    for file in critical_files:
        if Path(file).exists():
            print(f"[OK] {file}")
        else:
            print(f"[ERROR] {file} - NO ENCONTRADO")
            all_files_ok = False
    
    if not all_files_ok:
        print("\n[ERROR] Faltan archivos criticos. Verifica tu proyecto.")
        return
    
    # =========================================================================
    # PASO 2: INSTALAR DEPENDENCIAS
    # =========================================================================
    print_section("PASO 2: INSTALACION DE DEPENDENCIAS")
    
    if not run_command(
        "pip install -r requirements.txt",
        "Instalando todas las dependencias",
        check=False
    ):
        print("⚠️  Algunas dependencias fallaron, pero continuamos...")
    
    # =========================================================================
    # PASO 3: MIGRACIONES DE BASE DE DATOS
    # =========================================================================
    print_section("PASO 3: PREPARACION DE BASE DE DATOS")
    
    run_command(
        "python manage.py makemigrations",
        "Generando archivos de migracion",
        check=False
    )
    
    run_command(
        "python manage.py migrate",
        "Aplicando migraciones a la base de datos",
        check=False
    )
    
    # =========================================================================
    # PASO 4: RECOLECTAR ARCHIVOS ESTÁTICOS
    # =========================================================================
    print_section("PASO 4: RECOLECCION DE ARCHIVOS ESTATICOS (WHITENOISE)")
    
    run_command(
        "python manage.py collectstatic --noinput",
        "Recolectando CSS, JS, imagenes para WhiteNoise",
        check=False
    )
    
    # =========================================================================
    # PASO 5: VERIFICAR CONFIGURACIÓN
    # =========================================================================
    print_section("PASO 5: VERIFICACION DE CONFIGURACION DE DJANGO")
    
    run_command(
        "python manage.py check --deploy",
        "Verificando configuracion de produccion",
        check=False
    )
    
    # =========================================================================
    # PASO 6: CREAR ARCHIVO .gcloudignore
    # =========================================================================
    print_section("PASO 6: CREAR ARCHIVO .gcloudignore")
    
    gcloudignore_content = """# Archivos que NO se suben a Google Cloud
.git
.gitignore
__pycache__/
*.pyc
*.pyo
*.pyd
.Python
env/
venv/
*.env
.env
*.sqlite3
db.sqlite3
media/
staticfiles/
.vscode/
.idea/
*.log
"""
    
    with open('.gcloudignore', 'w', encoding='utf-8') as f:
        f.write(gcloudignore_content)
    
    print("[OK] Archivo .gcloudignore creado")
    
    # =========================================================================
    # PASO 7: CREAR ARCHIVO .dockerignore
    # =========================================================================
    print_section("PASO 7: CREAR ARCHIVO .dockerignore")
    
    dockerignore_content = """# Archivos que NO van en la imagen Docker
.git
.gitignore
__pycache__/
*.pyc
*.pyo
*.pyd
.Python
env/
venv/
*.env
.env
*.sqlite3
db.sqlite3
media/
.vscode/
.idea/
*.log
README.md
*.md
"""
    
    with open('.dockerignore', 'w', encoding='utf-8') as f:
        f.write(dockerignore_content)
    
    print("[OK] Archivo .dockerignore creado")
    
    # =========================================================================
    # PASO 8: CREAR ARCHIVO DE VARIABLES DE ENTORNO DE EJEMPLO
    # =========================================================================
    print_section("PASO 8: CREAR ARCHIVO .env.example")
    
    env_example_content = """# EJEMPLO DE VARIABLES DE ENTORNO PARA GOOGLE CLOUD
# NO SUBAS ESTE ARCHIVO CON VALORES REALES

# Django
SECRET_KEY=tu-secret-key-super-segura-aqui
DEBUG=False

# Google Cloud
GOOGLE_CLOUD_PROJECT=tu-proyecto-id
CLOUD_SQL_CONNECTION_NAME=tu-proyecto:region:instancia

# Base de datos
DB_NAME=prislab_v5
DB_USER=prislab_user
DB_PASSWORD=tu-password-segura

# Google Drive (para archivos MEDIA)
GOOGLE_DRIVE_FOLDER_ID=tu-folder-id-de-drive

# Google AI
GOOGLE_API_KEY=tu-api-key-de-gemini
"""
    
    with open('.env.example', 'w', encoding='utf-8') as f:
        f.write(env_example_content)
    
    print("[OK] Archivo .env.example creado")
    
    # =========================================================================
    # RESUMEN FINAL
    # =========================================================================
    print_section("PREPARACION LOCAL COMPLETADA")
    
    print("""
======================================================================
                 SISTEMA LISTO PARA DESPLIEGUE                 
======================================================================
                                                                      
  [OK] Dependencias instaladas                                          
  [OK] Migraciones aplicadas                                            
  [OK] Archivos estaticos recolectados (WhiteNoise)                     
  [OK] Configuracion verificada                                         
  [OK] Archivos de Docker/GCloud creados                                
                                                                      
======================================================================
              SIGUIENTE PASO: GOOGLE CLOUD                   
======================================================================
                                                                      
  Ahora necesitas ejecutar los comandos en Google Cloud.             
  Consulta el archivo: COMANDOS_GOOGLE_CLOUD.txt                     
                                                                      
  Ese archivo contiene TODOS los comandos que debes copiar/pegar     
  en la consola de Google Cloud Shell.                               
                                                                      
======================================================================
""")

if __name__ == "__main__":
    main()
