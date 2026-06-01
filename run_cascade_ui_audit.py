#!/usr/bin/env python
import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SCRIPT = ROOT / 'scripts_cascade_e2e' / 'octogono_ui_audit.mjs'
OUTPUT = ROOT / 'scripts_cascade_e2e' / 'output'


def main() -> int:
    parser = argparse.ArgumentParser(description='Lanza la auditoría Octógono de Interfaz (Playwright).')
    parser.add_argument('--base-url', default=os.environ.get('BASE_URL', 'http://127.0.0.1:8000'))
    parser.add_argument('--user', default=os.environ.get('E2E_USER', ''))
    parser.add_argument('--password', default=os.environ.get('E2E_PASS', ''))
    parser.add_argument('--orden-id', default=os.environ.get('ORDEN_ID', ''))
    parser.add_argument('--paciente-id', default=os.environ.get('PACIENTE_ID', ''))
    parser.add_argument('--bypass-token', default=os.environ.get('OMNI_BYPASS_TOKEN', ''))
    parser.add_argument('--headful', action='store_true')
    args = parser.parse_args()

    if not SCRIPT.exists():
        print(f'No existe el script: {SCRIPT}', file=sys.stderr)
        return 2

    node = shutil.which('node')
    if not node:
        print('Node.js no está disponible en PATH.', file=sys.stderr)
        return 2

    env = os.environ.copy()
    env['BASE_URL'] = args.base_url
    env['E2E_USER'] = args.user
    env['E2E_PASS'] = args.password
    env['ORDEN_ID'] = str(args.orden_id or '')
    env['PACIENTE_ID'] = str(args.paciente_id or '')
    env['OMNI_BYPASS_TOKEN'] = args.bypass_token
    env['HEADLESS'] = 'false' if args.headful else env.get('HEADLESS', 'true')

    OUTPUT.mkdir(parents=True, exist_ok=True)
    print('=== Octógono de Interfaz v1.56 ===')
    print(f'BASE_URL: {env["BASE_URL"]}')
    print(f'OUTPUT:   {OUTPUT}')
    print('Requiere credenciales válidas y, para pruebas profundas, ORDEN_ID/PACIENTE_ID.')

    cmd = [node, str(SCRIPT)]
    proc = subprocess.run(cmd, cwd=str(ROOT), env=env)
    print(f'Código de salida: {proc.returncode}')
    report_path = OUTPUT / 'octogono_ui_audit_report.json'
    if report_path.exists():
        print(f'Reporte JSON: {report_path}')
    return proc.returncode


if __name__ == '__main__':
    raise SystemExit(main())
