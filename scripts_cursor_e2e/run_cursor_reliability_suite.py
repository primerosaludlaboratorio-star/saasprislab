#!/usr/bin/env python
"""
Guardián de la Norma — orquestador de la suite Cursor E2E (v1.49).

Uso (raíz del repositorio):
    python scripts_cursor_e2e/run_cursor_reliability_suite.py

Variables de entorno: las mismas que el Quality Gate (SECRET_KEY, FERNET_KEY, etc.).
"""
from __future__ import annotations

import os
import subprocess
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

CURSOR_E2E_MODULES = [
    'scripts_cursor_e2e.tests.test_robot_chemist_flows',
    'scripts_cursor_e2e.tests.test_01_guardian_golden_lifecycle',
    'scripts_cursor_e2e.tests.test_02_lims_inventory_sync',
    'scripts_cursor_e2e.tests.test_03_math_ui_integrity',
    'scripts_cursor_e2e.tests.test_04_finance_caja_sync',
    'scripts_cursor_e2e.tests.test_05_hl7_mock_device',
    'scripts_cursor_e2e.tests.test_06_role_permission_hygiene',
    'scripts_cursor_e2e.tests.test_07_pdf_branding_consistency',
    'scripts_cursor_e2e.tests.test_08_jarvis_escudo_ui',
    'scripts_cursor_e2e.tests.test_09_sucursal_modo_inventario_ui',
]


def main() -> int:
    os.chdir(REPO_ROOT)
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
    cmd = [sys.executable, 'manage.py', 'test', *CURSOR_E2E_MODULES, '--verbosity=1']
    return subprocess.call(cmd, env=os.environ.copy())


if __name__ == '__main__':
    raise SystemExit(main())
