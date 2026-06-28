web: python manage.py migrate --noinput || true && python manage.py collectstatic --noinput || true && gunicorn config.wsgi:application --bind 0.0.0.0:$PORT --workers 2 --threads 4 --timeout 120
