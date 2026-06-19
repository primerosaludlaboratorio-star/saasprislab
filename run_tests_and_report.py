#!/usr/bin/env python3
"""Script to run tests and generate coverage report."""
import os
import sys
import subprocess
import time

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

print("=" * 70)
print("EJECUTANDO TESTS CON COBERTURA")
print("=" * 70)

# First run the coverage tests
print("\n[1] Ejecutando tests de cobertura...")
result = subprocess.run(
    ['.venv/Scripts/python.exe', 'manage.py', 'test', 'core.tests.test_coverage_boost', '--noinput', '-v', '1'],
    capture_output=True,
    text=True,
    timeout=180
)

print("STDOUT:", result.stdout[-3000:] if len(result.stdout) > 3000 else result.stdout)
if result.stderr:
    print("STDERR:", result.stderr[-1000:] if len(result.stderr) > 1000 else result.stderr)
print("Return code:", result.returncode)

if result.returncode != 0:
    print("\n❌ Tests fallaron")
    sys.exit(1)

print("\n✅ Tests pasaron")

# Now run coverage report
print("\n[2] Generando reporte de cobertura...")
result = subprocess.run(
    ['.venv/Scripts/coverage.exe', 'report', '-m'],
    capture_output=True,
    text=True,
    timeout=30
)

print("COVERAGE REPORT:")
print(result.stdout)
if result.stderr:
    print("STDERR:", result.stderr)

print("\n" + "=" * 70)
print("FIN DEL REPORTE")
print("=" * 70)
