#!/usr/bin/env python3
"""Ejecuta tests y guarda output a archivo para análisis posterior."""
import subprocess
import os

BASE = os.path.dirname(os.path.abspath(__file__))
PYTHON = os.path.join(BASE, '.venv', 'Scripts', 'python.exe')

cmd = [PYTHON, 'manage.py', 'test', '--keepdb', '--verbosity=2']

print("Ejecutando tests... esto puede tomar 2-3 minutos...")
with open(os.path.join(BASE, 'test_output.txt'), 'w', encoding='utf-8') as f:
    result = subprocess.run(cmd, stdout=f, stderr=subprocess.STDOUT, cwd=BASE, timeout=300)

print(f"Terminado con código: {result.returncode}")
print(f"Output guardado en: test_output.txt")
