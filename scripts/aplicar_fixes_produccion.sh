#!/bin/bash
set -euo pipefail

cd /opt/prislab/app
source .venv/bin/activate

echo "=== Aplicando fixes PRISLAB ==="
python scripts/run_manage_with_env.py migrate --noinput
python scripts/run_manage_with_env.py collectstatic --noinput
python scripts/run_manage_with_env.py crear_superusuarios_iniciales

echo "=== Reiniciando servicios ==="
sudo systemctl restart prislab-gunicorn
sudo systemctl restart prislab-celery
sudo systemctl restart prislab-celerybeat

echo "=== DONE ==="
