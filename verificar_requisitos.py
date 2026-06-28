"""
VERIFICAR REQUISITOS PARA DESPLIEGUE
"""
import os
import sys
import subprocess
from pathlib import Path

print("=" * 80)
print("VERIFICACION DE REQUISITOS PARA DESPLIEGUE")
print("=" * 80)
print()

errores = []
advertencias = []

# ============================================================================
# 1. VERIFICAR GIT
# ============================================================================
print("[1/8] Verificando Git...")
try:
    result = subprocess.run(['git', '--version'], capture_output=True, text=True)
    if result.returncode == 0:
        version = result.stdout.strip()
        print(f"  [OK] {version}")
    else:
        errores.append("Git no esta instalado o no responde")
        print("  [ERROR] Git no funciona correctamente")
except FileNotFoundError:
    errores.append("Git no esta instalado")
    print("  [ERROR] Git no encontrado")
    print("         Descarga desde: https://git-scm.com/download/win")

# ============================================================================
# 2. VERIFICAR REPOSITORIO GIT
# ============================================================================
print("[2/8] Verificando repositorio Git...")
if Path('.git').exists():
    print("  [OK] Repositorio Git inicializado")
    
    # Verificar remote
    try:
        result = subprocess.run(['git', 'remote', '-v'], capture_output=True, text=True)
        if result.stdout.strip():
            print("  [OK] Remote configurado:")
            for line in result.stdout.strip().split('\n'):
                print(f"       {line}")
        else:
            advertencias.append("No hay remote configurado")
            print("  [AVISO] No hay remote configurado")
            print("          Ejecuta: git remote add origin <URL>")
    except:
        pass
else:
    advertencias.append("No hay repositorio Git")
    print("  [AVISO] No hay repositorio Git")
    print("          Ejecuta: git init")

# ============================================================================
# 3. VERIFICAR ARCHIVOS CSV
# ============================================================================
print("[3/8] Verificando archivos CSV...")
archivos_csv = [
    'tarifas.csv',
    'Productos-farmacia-2026-02-10-10-31.csv',
]

for archivo in archivos_csv:
    if Path(archivo).exists():
        size = Path(archivo).stat().st_size
        print(f"  [OK] {archivo} ({size:,} bytes)")
    else:
        advertencias.append(f"Falta {archivo}")
        print(f"  [AVISO] No se encuentra {archivo}")

# ============================================================================
# 4. VERIFICAR CARPETA datos_lims
# ============================================================================
print("[4/8] Verificando datos legacy...")
if Path('datos_lims').exists():
    archivos_legacy = ['Examenes.csv', 'Parametros.csv', 'Paquetes.csv', 'Valores_normalidad.csv']
    encontrados = 0
    for archivo in archivos_legacy:
        if Path(f'datos_lims/{archivo}').exists():
            encontrados += 1
    print(f"  [OK] Carpeta datos_lims ({encontrados}/4 archivos)")
else:
    advertencias.append("Falta carpeta datos_lims")
    print("  [AVISO] No se encuentra carpeta datos_lims")

# ============================================================================
# 5. VERIFICAR SCRIPTS DE DESPLIEGUE
# ============================================================================
print("[5/8] Verificando scripts de despliegue...")
scripts = [
    'crear_equipo_oficial.py',
    'DESPLIEGUE_COMPLETO.sh',
    'EJECUTAR_EN_SERVIDOR.sh',
]

for script in scripts:
    if Path(script).exists():
        print(f"  [OK] {script}")
    else:
        errores.append(f"Falta {script}")
        print(f"  [ERROR] Falta {script}")

# ============================================================================
# 6. VERIFICAR ESTRUCTURA DE MÓDULOS
# ============================================================================
print("[6/8] Verificando estructura de módulos...")
modulos = ['farmacia', 'laboratorio', 'consultorio', 'core']
for modulo in modulos:
    if Path(modulo).exists():
        print(f"  [OK] {modulo}/")
    else:
        errores.append(f"Falta módulo {modulo}")
        print(f"  [ERROR] Falta módulo {modulo}")

# ============================================================================
# 7. VERIFICAR ARCHIVOS DE CONFIGURACIÓN
# ============================================================================
print("[7/8] Verificando archivos de configuración...")
configs = [
    'manage.py',
    'config/settings.py',
    'app.yaml',
    '.gitignore',
]

for config in configs:
    if Path(config).exists():
        print(f"  [OK] {config}")
    else:
        if config == 'app.yaml':
            advertencias.append(f"Falta {config} (necesario para App Engine)")
        else:
            errores.append(f"Falta {config}")
        print(f"  [AVISO] Falta {config}")

# ============================================================================
# 8. VERIFICAR DJANGO
# ============================================================================
print("[8/8] Verificando Django...")
try:
    import django
    print(f"  [OK] Django {django.get_version()}")
except ImportError:
    errores.append("Django no esta instalado")
    print("  [ERROR] Django no encontrado")
    print("          Instala con: pip install django")

# ============================================================================
# RESUMEN
# ============================================================================
print()
print("=" * 80)
print("RESUMEN")
print("=" * 80)
print()

if not errores and not advertencias:
    print("[EXCELENTE] Todos los requisitos cumplidos")
    print()
    print("Puedes proceder con el despliegue:")
    print("  - Windows: DESPLEGAR_A_PRODUCCION.bat")
    print("  - Git Bash/WSL: bash DESPLIEGUE_COMPLETO.sh")
elif errores:
    print(f"[CRITICO] {len(errores)} error(es) que deben corregirse:")
    for error in errores:
        print(f"  [X] {error}")
    if advertencias:
        print()
        print(f"[ADVERTENCIA] {len(advertencias)} advertencia(s):")
        for advertencia in advertencias:
            print(f"  [!] {advertencia}")
    print()
    print("Corrige los errores antes de desplegar")
else:
    print(f"[ADVERTENCIA] {len(advertencias)} advertencia(s):")
    for advertencia in advertencias:
        print(f"  [!] {advertencia}")
    print()
    print("Puedes proceder, pero revisa las advertencias")

print("=" * 80)

# Código de salida
sys.exit(len(errores))
