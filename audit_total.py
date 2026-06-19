#!/usr/bin/env python3
"""Auditoría arquitectónica total de PRISLAB SaaS.
Ejecuta: python audit_total.py
Genera: audit_total_report.md y carpeta audit_artifacts/
"""

import os
import subprocess
import sys
import json
import re
import time
from pathlib import Path
from datetime import datetime

BASE_DIR = Path(__file__).parent
ARTIFACTS_DIR = BASE_DIR / "audit_artifacts"
ARTIFACTS_DIR.mkdir(exist_ok=True)

REPORT = []
def log(msg):
    print(msg)
    REPORT.append(msg)

def run_cmd(cmd, cwd=None, timeout=60, check=False):
    try:
        result = subprocess.run(cmd, shell=True, cwd=cwd or BASE_DIR,
                                capture_output=True, text=True, timeout=timeout)
        return result.returncode, result.stdout, result.stderr
    except Exception as e:
        return -1, "", str(e)

def write_artifact(name, content):
    (ARTIFACTS_DIR / name).write_text(content, encoding='utf-8')

def main():
    log(f"# Auditoría total - PRISLAB SaaS\nFecha: {datetime.now().isoformat()}\n")
    
    # 1. Estática: funciones sospechosas, marcadores, pass, csrf_exempt
    log("## 1. Análisis estático")
    # Buscar TODO/PENDIENTE/FIXME en archivos .py (excluyendo tests y migrations)
    rc, out, err = run_cmd("grep -r -n 'TODO\\|PENDIENTE\\|FIXME' --include='*.py' --exclude-dir=tests --exclude-dir=migrations")
    write_artifact("todos.txt", out)
    todo_count = len([l for l in out.splitlines() if l.strip()])
    log(f"- Marcadores TODO/PENDIENTE: {todo_count}")
    
    # Buscar 'pass' como línea independiente en funciones (heurístico)
    rc, out, err = run_cmd("grep -r -n '^\\s*pass\\s*$' --include='*.py' --exclude-dir=tests --exclude-dir=migrations")
    write_artifact("pass_lines.txt", out)
    pass_count = len([l for l in out.splitlines() if l.strip()])
    log(f"- Líneas 'pass' en producción: {pass_count}")
    
    # Listar endpoints @csrf_exempt
    rc, out, err = run_cmd("grep -r -n '@csrf_exempt' --include='*.py'")
    write_artifact("csrf_exempt.txt", out)
    csrf_count = len([l for l in out.splitlines() if l.strip()])
    log(f"- Endpoints @csrf_exempt encontrados: {csrf_count}")
    
    # 2. Pruebas unitarias y cobertura
    log("\n## 2. Pruebas unitarias y cobertura")
    rc, out, err = run_cmd("python manage.py test --noinput --verbosity=1")
    write_artifact("test_output.log", out + err)
    if rc == 0:
        log("- Unitarias: OK")
    else:
        log(f"- Unitarias: FALLARON (código {rc})")
    
    rc, out, err = run_cmd("coverage run manage.py test")
    rc2, out2, err2 = run_cmd("coverage report -m")
    write_artifact("coverage_report.txt", out2 + err2)
    # Extraer porcentaje total
    cov_match = re.search(r"TOTAL\s+(\d+)\s+(\d+)\s+(\d+)", out2)
    if cov_match:
        total_cov = int(cov_match.group(3))
        log(f"- Cobertura total: {total_cov}%")
    else:
        log("- Cobertura total: no se pudo determinar")
    
    # 3. E2E (si es posible) – intentar npm run omni:local
    log("\n## 3. Suite E2E (Playwright)")
    rc, out, err = run_cmd("npm run omni:local -- --headless", timeout=120)
    write_artifact("omni_local.log", out + err)
    # Comprobar si el último suite summary dice ok=true
    summary_file = BASE_DIR / "tools" / "last_suite_summary.json"
    e2e_ok = False
    if summary_file.exists():
        try:
            data = json.loads(summary_file.read_text())
            e2e_ok = data.get("ok", False)
        except:
            pass
    if e2e_ok:
        log("- E2E: OK (green)")
    else:
        log("- E2E: FALLÓ o no se ejecutó correctamente")
    
    # 4. Seguridad y despliegue
    log("\n## 4. Seguridad y despliegue")
    rc, out, err = run_cmd("python manage.py check --deploy")
    write_artifact("check_deploy.log", out + err)
    warnings = len([l for l in out.splitlines() if l.startswith("WARNINGS") or l.startswith("WARNING:")])
    log(f"- `check --deploy` advertencias: {warnings}")
    
    # 5. Tenant isolation (prueba simple)
    log("\n## 5. Aislamiento multi-tenant")
    # Intentar ejecutar un comando que verifique fuga (si existe)
    rc, out, err = run_cmd("python manage.py verificar_aislamiento_multitenant")
    if rc == 0:
        log("- Comando verificar_aislamiento OK")
    else:
        log("- No se pudo verificar aislamiento (comando no encontrado o falló)")
    
    # 6. RBAC Prisci (pruebas específicas)
    log("\n## 6. RBAC y Prisci")
    rc, out, err = run_cmd("python manage.py test core.tests.test_prisci_unified_ai --noinput")
    write_artifact("prisci_rbac.log", out + err)
    if rc == 0:
        log("- Prisci RBAC: OK")
    else:
        log("- Prisci RBAC: FALLÓ")
    
    # 7. Webhook externo (simular con curl)
    log("\n## 7. Webhook externo")
    # Iniciar servidor en segundo plano? Difícil. Se sugiere ejecutar manual.
    log("  (requiere servidor corriendo; prueba manual sugerida)")
    
    # 8. Migraciones pendientes
    log("\n## 8. Migraciones")
    rc, out, err = run_cmd("python manage.py makemigrations --check --dry-run")
    if rc == 0 and "No changes detected" in out:
        log("- Migraciones: OK (sin cambios pendientes)")
    else:
        log("- Migraciones: HAY CAMBIOS PENDIENTES o error")
    
    # 9. Archivos con BOM
    log("\n## 9. Archivos con BOM (U+FEFF)")
    rc, out, err = run_cmd("grep -r -l $'\\xEF\\xBB\\xBF' --include='*.py'")
    bom_files = [f for f in out.splitlines() if f.strip()]
    log(f"- Archivos con BOM: {len(bom_files)}")
    
    # 10. Resumen de hallazgos
    log("\n## 10. Resumen de hallazgos críticos")
    critical = []
    if todo_count > 50:
        critical.append(f"Exceso de marcadores TODO/PENDIENTE ({todo_count})")
    if pass_count > 100:
        critical.append(f"Exceso de 'pass' en producción ({pass_count})")
    if 'total_cov' in dir() or 'total_cov' in vars():
        if total_cov < 50:
            critical.append(f"Cobertura insuficiente ({total_cov}%)")
    if not e2e_ok:
        critical.append("Suite E2E fallida o no ejecutada")
    if warnings > 0:
        critical.append(f"{warnings} advertencias de seguridad en --deploy")
    if not critical:
        log("✅ No se encontraron hallazgos críticos automáticos.")
    else:
        for c in critical:
            log(f"❌ {c}")
    
    log("\n## 11. Artefactos generados")
    log(f"Carpeta: {ARTIFACTS_DIR}")
    log("Revisa los archivos para detalles.")

    # Escribir reporte completo
    report_path = BASE_DIR / "audit_total_report.md"
    report_path.write_text("\n".join(REPORT), encoding='utf-8')
    log(f"\nReporte guardado en: {report_path}")

if __name__ == "__main__":
    main()
