#!/bin/bash
set -euo pipefail

cd /opt/prislab
if [ -f .env ]; then
  set -a
  source .env
  set +a
fi
source .venv/bin/activate

echo "=== Aplicando fixes PRISLAB ==="
python manage.py migrate --noinput
python manage.py collectstatic --noinput
python manage.py crear_superusuarios_iniciales

echo "=== Reiniciando servicios ==="
sudo systemctl restart gunicorn
sudo systemctl restart celery
sudo systemctl restart celerybeat

echo "=== DONE ==="
