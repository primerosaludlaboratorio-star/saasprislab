# ==============================================================================
# PRISLAB V5 — Dockerfile de Producción
# Compatible: Google Cloud Run + Docker Compose (Ubuntu VPS)
# Python 3.12 + Django 5 + Gunicorn
# ==============================================================================
# Cloud Run: PORT=8080 (inyectado automáticamente)
# Docker Compose: PORT=8000 (definido en docker-compose.yml)
# ==============================================================================

FROM python:3.12-slim

LABEL maintainer="Jonathan Alonso <admin@prislab.com>" \
      description="PRISLAB V5.2 SaaS — Sistema Clínico Integral (Emporio)" \
      version="5.2"

# Variables de entorno
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DJANGO_SETTINGS_MODULE=config.settings \
    PORT=8080

# ── Dependencias del sistema ─────────────────────────────────────────────────
# Incluye: PostgreSQL client, WeasyPrint, Pillow, ReportLab, Cairo (PDF)
RUN apt-get update && apt-get install -y --no-install-recommends \
    # Compiladores (necesarios para psycopg2, cffi)
    gcc \
    python3-dev \
    libpq-dev \
    libffi-dev \
    # PostgreSQL client (pg_isready, pg_dump para backups)
    postgresql-client \
    # WeasyPrint / ReportLab / Cairo runtime
    libcairo2 \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libgdk-pixbuf-2.0-0 \
    shared-mime-info \
    # Pillow runtime
    libjpeg62-turbo-dev \
    zlib1g-dev \
    libfreetype6-dev \
    liblcms2-dev \
    libopenjp2-7-dev \
    libtiff5-dev \
    libwebp-dev \
    # Utilidades
    curl \
    && rm -rf /var/lib/apt/lists/*

# ── Directorio de trabajo ────────────────────────────────────────────────────
WORKDIR /app

# ── Instalar dependencias Python (cache de Docker por capa) ──────────────────
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir \
        gunicorn==22.0.0 \
        redis==5.0.4

# ── Copiar código fuente ─────────────────────────────────────────────────────
COPY . .

# ── Crear directorios necesarios ─────────────────────────────────────────────
RUN mkdir -p /app/staticfiles /app/media /app/logs

# ── Recolectar archivos estáticos (WhiteNoise + Manifest) ────────────────────
# IMPORTANTE: Se fuerza USE_MANIFEST_STORAGE=1 para que el build genere el
# staticfiles.json que CompressedManifestStaticFilesStorage necesita en runtime.
# Sin esto, el build usa StaticFilesStorage (simple) y en producción se obtiene
# ValueError: Missing staticfiles manifest entry.
RUN USE_MANIFEST_STORAGE=1 python manage.py collectstatic --noinput

# ── Crear usuario no-root y ceder propiedad de /app ──────────────────────────
RUN groupadd -r appgroup && useradd -r -g appgroup appuser \
    && chown -R appuser:appgroup /app

# ── Puerto ───────────────────────────────────────────────────────────────────
EXPOSE ${PORT}

# ── Comando de inicio ─────────────────────────────────────
# scripts/web_entrypoint.sh: migrate (salvo PRISLAB_SKIP_MIGRATE_ON_STARTUP=1) + gunicorn.
# sed quita CR (\r) si el repo se clonó en Windows — sin esto: env: 'sh\r': No such file (exit 127).
RUN sed -i 's/\r$//' /app/scripts/web_entrypoint.sh && chmod +x /app/scripts/web_entrypoint.sh

USER appuser
CMD ["/app/scripts/web_entrypoint.sh"]
