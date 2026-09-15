#!/usr/bin/env python
"""
PRISLAB Audit Freeze Generator

Genera FREEZE.json congelando el estado actual del repositorio.
Incluye: commit SHA, versiones, hashes, variables de entorno (sin secretos).

Uso:
    python scripts/audit/generate_freeze.py --run-id PRISLAB_AUDIT_20260915_001

Salida:
    audit/FREEZE.json
"""

import json
import subprocess
import sys
import os
from datetime import datetime
from pathlib import Path
import hashlib
import argparse


def run_cmd(cmd, capture=True):
    """Ejecuta comando y retorna stdout o returncode."""
    try:
        if capture:
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, check=True)
            return result.stdout.strip()
        else:
            subprocess.run(cmd, shell=True, check=True)
            return "OK"
    except subprocess.CalledProcessError as e:
        print(f"⚠️ Error ejecutando: {cmd}")
        print(f"   {e.stderr}")
        return None


def get_git_info():
    """Extrae información de git."""
    return {
        "commit_sha": run_cmd("git rev-parse HEAD"),
        "commit_short": run_cmd("git rev-parse --short HEAD"),
        "branch": run_cmd("git rev-parse --abbrev-ref HEAD"),
        "remote": run_cmd("git config --get remote.origin.url"),
        "tree_hash": run_cmd("git rev-parse HEAD^{tree}"),
        "committer_name": run_cmd("git log -1 --format=%an"),
        "committer_email": run_cmd("git log -1 --format=%ae"),
        "commit_date": run_cmd("git log -1 --format=%ai"),
    }


def get_versions():
    """Extrae versiones de dependencias críticas."""
    versions = {}
    
    # Python
    versions["python"] = run_cmd("python --version")
    
    # Django
    try:
        import django
        versions["django"] = f"Django {django.VERSION[0]}.{django.VERSION[1]}.{django.VERSION[2]}"
    except:
        versions["django"] = "N/A"
    
    # PostgreSQL (si está disponible)
    versions["postgresql"] = run_cmd("psql --version") or "N/A"
    
    # Node.js (si está disponible)
    versions["nodejs"] = run_cmd("node --version") or "N/A"
    
    # pip
    versions["pip"] = run_cmd("pip --version")
    
    # requirements.lock hash
    if Path("requirements.lock").exists():
        with open("requirements.lock", "rb") as f:
            versions["requirements_lock_sha256"] = hashlib.sha256(f.read()).hexdigest()
    
    return versions


def get_file_stats():
    """Cuenta archivos versionados y no versionados."""
    versionados = int(run_cmd("git ls-files | wc -l") or "0")
    no_versionados = int(run_cmd("git ls-files --others --exclude-standard | wc -l") or "0")
    
    return {
        "versionados": versionados,
        "no_versionados": no_versionados,
        "total": versionados + no_versionados
    }


def get_environment_safe():
    """Extrae variables de entorno (redactando secretos)."""
    env = {}
    secretos_patterns = [
        'SECRET', 'PASSWORD', 'TOKEN', 'KEY', 'API', 'CREDENTIAL',
        'AUTH', 'GITHUB', 'AWS', 'GOOGLE', 'FERNET'
    ]
    
    for key, value in os.environ.items():
        if any(pattern in key.upper() for pattern in secretos_patterns):
            env[key] = "[REDACTED]"
        elif key.startswith(('DJANGO', 'PYTHON', 'LC_', 'LANG', 'PATH')):
            env[key] = value[:50] + "..." if len(value) > 50 else value
    
    return env


def get_django_info():
    """Extrae información de Django settings."""
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
    
    django_info = {
        "settings_module": os.environ.get('DJANGO_SETTINGS_MODULE'),
        "database_engine": "PostgreSQL" if 'postgres' in os.environ.get('DB_HOST', '') else "SQLite (CI)",
        "installed_apps_count": 0,
    }
    
    try:
        import django
        django.setup()
        from django.conf import settings
        django_info["installed_apps_count"] = len(settings.INSTALLED_APPS)
        django_info["debug"] = settings.DEBUG
        django_info["use_tz"] = settings.USE_TZ
    except Exception as e:
        django_info["error"] = str(e)
    
    return django_info


def get_migrations_status():
    """Verifica estado de migraciones."""
    check_result = run_cmd("python manage.py makemigrations --check --no-input 2>&1")
    return {
        "status": "clean" if "No changes detected" in check_result else "pending",
        "output": check_result[:200]
    }


def generate_freeze(run_id, output_path="audit/FREEZE.json"):
    """Genera archivo FREEZE.json."""
    
    print(f"🔧 Generando FREEZE.json para RUN_ID={run_id}...")
    
    freeze = {
        # Identificadores
        "run_id": run_id,
        "timestamp_generated": datetime.utcnow().isoformat() + "Z",
        "operator": "GitHub Actions / Local Audit",
        
        # Git
        "git": get_git_info(),
        
        # Versiones
        "versions": get_versions(),
        
        # Archivos
        "files": get_file_stats(),
        
        # Django
        "django": get_django_info(),
        
        # Migraciones
        "migrations": get_migrations_status(),
        
        # Ambiente (sin secretos)
        "environment": {
            "django_settings": os.environ.get('DJANGO_SETTINGS_MODULE'),
            "pythonunbuffered": os.environ.get('PYTHONUNBUFFERED'),
            "database_host": "[REDACTED]" if os.environ.get('DB_HOST') else "localhost (CI)",
            "ci_environment": "GitHub Actions" if os.environ.get('GITHUB_ACTIONS') else "Local",
        },
        
        # Configuración de prueba
        "test_config": {
            "database": "PostgreSQL 16 Alpine",
            "test_company": "CI_TEST_001",
            "test_branch": "CENTRAL_CI",
            "data_synthetic": True,
            "destructive_operations_allowed": False,
            "secrets_redacted": True,
        },
        
        # Propósito
        "purpose": "Quality Gate + Coverage + SCA + Audit",
        "phase": "Phase 2 - Automated Gates",
        "branch_audited": "release/v1.0-local",
    }
    
    # Crear directorio si no existe
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    
    # Escribir JSON
    with open(output_path, 'w') as f:
        json.dump(freeze, f, indent=2)
    
    print(f"✅ FREEZE.json generado en: {output_path}")
    print(f"   Commit: {freeze['git']['commit_sha']}")
    print(f"   Branch: {freeze['git']['branch']}")
    print(f"   Files: {freeze['files']['versionados']} versionados, {freeze['files']['no_versionados']} no versionados")
    
    return freeze


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Genera FREEZE.json para auditoría PRISLAB")
    parser.add_argument("--run-id", default=f"PRISLAB_AUDIT_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                       help="Identificador único de la corrida de auditoría")
    parser.add_argument("--output", default="audit/FREEZE.json", help="Ruta de salida")
    
    args = parser.parse_args()
    
    try:
        freeze = generate_freeze(args.run_id, args.output)
        print(f"\n📦 Congelación completada exitosamente")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
