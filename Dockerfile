# ==============================================================================
# PRISLAB V5 — Dockerfile de Producción
# Compatible: Google Cloud Run + Docker Compose (Ubuntu VPS)
# Python 3.12 + Django 5 + Gunicorn
# ==============================================================================
# Cloud Run: PORT=8080 (inyectado automáticamente)
# Docker Compose: PORT=8000 (definido en docker-compose.yml)
# ==============================================================================

FROM python:3.12-slim AS builder

LABEL maintainer="Jonathan Alonso <admin@prislab.com>" \
      description="PRISLAB V5.2 SaaS — Sistema Clínico Integral (Emporio)" \
      version="5.2"

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DJANGO_SETTINGS_MODULE=config.settings \
    PORT=8080

# ── Herramientas de compilacion, solo en la etapa builder ────────────────────
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    python3-dev \
    libpq-dev \
    libffi-dev \
    libjpeg62-turbo-dev \
    zlib1g-dev \
    libfreetype6-dev \
    liblcms2-dev \
    libopenjp2-7-dev \
    libtiff5-dev \
    libwebp-dev \
    && rm -rf /var/lib/apt/lists/*

# ── Directorio de trabajo ────────────────────────────────────────────────────
WORKDIR /build

# ── Instalar dependencias Python (cache de Docker por capa) ──────────────────
COPY requirements.txt /build/requirements.txt
COPY requirements.lock /build/requirements.lock
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir --prefix=/install --require-hashes -r requirements.lock

FROM python:3.12-slim AS runtime

LABEL maintainer="Jonathan Alonso <admin@prislab.com>" \
      description="PRISLAB V5.2 SaaS - Sistema Clinico Integral (Emporio)" \
      version="5.2"

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DJANGO_SETTINGS_MODULE=config.settings \
    PORT=8080

# Solo bibliotecas de ejecucion; no se incluyen gcc, headers ni toolchains.
RUN apt-get update && apt-get install -y --no-install-recommends \
    postgresql-client \
    libcairo2 \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libgdk-pixbuf-2.0-0 \
    shared-mime-info \
    libjpeg62-turbo \
    zlib1g \
    libfreetype6 \
    liblcms2-2 \
    libopenjp2-7 \
    libtiff6 \
    libwebp7 \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY --from=builder /install /usr/local

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
