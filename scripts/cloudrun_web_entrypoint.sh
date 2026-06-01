#!/usr/bin/env sh
# Arranque Cloud Run: migrate opcional + gunicorn.
# Si migrate falla o tarda demasiado, Cloud Run muestra "failed to listen on PORT";
# los echo van a Cloud Logging para ver la fase exacta.
set -e
PORT="${PORT:-8080}"
export PORT

echo "[prislab-entrypoint] $(date -u +%Y-%m-%dT%H:%M:%SZ) inicio — PORT=${PORT}"

if [ "${PRISLAB_SKIP_MIGRATE_ON_STARTUP:-0}" = "1" ]; then
  echo "[prislab-entrypoint] PRISLAB_SKIP_MIGRATE_ON_STARTUP=1 — migrate OMITIDO (solo diagnóstico / emergencia)"
else
  echo "[prislab-entrypoint] migrate --noinput (si falla, revisar logs y BD / Cloud SQL API)..."
  python manage.py migrate --noinput
  echo "[prislab-entrypoint] migrate terminó OK"
fi

echo "[prislab-entrypoint] gunicorn workers=${GUNICORN_WORKERS:-2} threads=${GUNICORN_THREADS:-4} bind=0.0.0.0:${PORT}"
exec gunicorn config.wsgi:application \
  --bind "0.0.0.0:${PORT}" \
  --workers "${GUNICORN_WORKERS:-2}" \
  --threads "${GUNICORN_THREADS:-4}" \
  --worker-class gthread \
  --worker-tmp-dir /dev/shm \
  --timeout 300 \
  --graceful-timeout 30 \
  --keep-alive 5 \
  --max-requests 1000 \
  --max-requests-jitter 50 \
  --access-logfile - \
  --error-logfile - \
  --log-level info \
  --capture-output
