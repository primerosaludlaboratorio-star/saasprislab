#!/usr/bin/env bash
# ==============================================================================
# PRISLAB SaaS — Deploy automatizado en VPS Vultr / Ubuntu 26.04+
# ==============================================================================
# USO: sudo bash deploy_vps.sh
#
# Antes de correr este script:
#   1. Tener acceso root a la VPS
#   2. Tener el repo clonado o el tarball del código
#   3. Tener tu archivo .env listo (basado en .env.production.example)
#   4. Apuntar tu dominio DNS a la IP de la VPS
# ==============================================================================
set -euo pipefail

# ── Configuración ─────────────────────────────────────────────────────────────
ROOT_DIR="/opt/prislab"
APP_DIR="$ROOT_DIR/app"
APP_USER="prislab"
DOMAIN="${DOMAIN:-tu-dominio.com}"          # Sobreescribir: DOMAIN=mi-dominio.com bash deploy_vps.sh
PYTHON_VERSION="python3"
VENV_DIR="$APP_DIR/.venv"
LOG_DIR="$ROOT_DIR/logs"
MEDIA_DIR="$APP_DIR/media"
STATIC_DIR="$APP_DIR/staticfiles"

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'
log()  { echo -e "${GREEN}[DEPLOY]${NC} $1"; }
warn() { echo -e "${YELLOW}[WARN]${NC}  $1"; }
err()  { echo -e "${RED}[ERROR]${NC} $1"; exit 1; }

[[ $EUID -ne 0 ]] && err "Este script debe correrse como root (sudo bash deploy_vps.sh)"

log "=== PRISLAB VPS Deploy ==="
log "Dominio: $DOMAIN"
log "Directorio app: $APP_DIR"
log "Directorio raíz: $ROOT_DIR"

# ── 1. Dependencias del sistema ───────────────────────────────────────────────
log "Instalando dependencias del sistema..."
apt-get update -qq
apt-get install -y --no-install-recommends \
    nginx postgresql postgresql-contrib \
    python3 python3-venv python3-dev python3-pip \
    build-essential git curl wget unzip \
    certbot python3-certbot-nginx \
    ufw redis-server \
    libpq-dev libssl-dev libffi-dev \
    supervisor

# ── 2. Firewall ───────────────────────────────────────────────────────────────
log "Configurando firewall UFW..."
ufw allow OpenSSH
ufw allow 80/tcp
ufw allow 443/tcp
ufw --force enable

# ── 3. Usuario de la aplicación ───────────────────────────────────────────────
log "Creando usuario $APP_USER..."
if ! id "$APP_USER" &>/dev/null; then
    useradd --system --shell /bin/bash --home "$APP_DIR" --create-home "$APP_USER"
fi

# ── 4. PostgreSQL ─────────────────────────────────────────────────────────────
log "Configurando PostgreSQL..."
systemctl enable postgresql
systemctl start postgresql

# Leer contraseña desde .env si existe
DB_PASSWORD="${DB_PASSWORD:-$(openssl rand -base64 24)}"
DB_NAME="${DB_NAME:-prislab_db}"
DB_USER="${DB_USER:-prislab_user}"

sudo -u postgres psql -tc "SELECT 1 FROM pg_user WHERE usename='$DB_USER'" | grep -q 1 || \
    sudo -u postgres createuser "$DB_USER"
sudo -u postgres psql -tc "SELECT 1 FROM pg_database WHERE datname='$DB_NAME'" | grep -q 1 || \
    sudo -u postgres createdb "$DB_NAME" -O "$DB_USER"
sudo -u postgres psql -c "ALTER USER $DB_USER WITH PASSWORD '$DB_PASSWORD';"

log "PostgreSQL listo: base=$DB_NAME usuario=$DB_USER"

# ── 5. Directorio de la aplicación ────────────────────────────────────────────
log "Preparando directorios..."
mkdir -p "$ROOT_DIR" "$APP_DIR" "$LOG_DIR" "$MEDIA_DIR" "$STATIC_DIR"
chown -R "$APP_USER:$APP_USER" "$APP_DIR"
chown -R "$APP_USER:$APP_USER" "$LOG_DIR"

# ── 6. Verificar que el código está en $APP_DIR ───────────────────────────────
if [ ! -f "$APP_DIR/manage.py" ]; then
    err "No se encontró manage.py en $APP_DIR. Clona el repositorio primero:
    git clone https://github.com/tu-usuario/prislab.git $APP_DIR"
fi

# ── 7. Verificar que .env existe ─────────────────────────────────────────────
if [ ! -f "$APP_DIR/.env" ]; then
    warn ".env no encontrado en $APP_DIR"
    warn "Copia .env.production.example a $APP_DIR/.env y llena los valores"
    err "Abortando — configura .env antes de continuar"
fi
chmod 600 "$APP_DIR/.env"

# ── 8. Entorno Python ─────────────────────────────────────────────────────────
log "Creando entorno virtual Python..."
sudo -u "$APP_USER" $PYTHON_VERSION -m venv "$VENV_DIR"
sudo -u "$APP_USER" "$VENV_DIR/bin/pip" install --upgrade pip --quiet
sudo -u "$APP_USER" "$VENV_DIR/bin/pip" install -r "$APP_DIR/requirements.txt" --quiet

log "Dependencias Python instaladas"

# ── 9. Migraciones y estáticos ───────────────────────────────────────────────
log "Ejecutando migraciones..."
cd "$APP_DIR"
sudo -u "$APP_USER" "$VENV_DIR/bin/python" scripts/run_manage_with_env.py migrate --noinput

log "Recolectando archivos estáticos..."
sudo -u "$APP_USER" "$VENV_DIR/bin/python" scripts/run_manage_with_env.py collectstatic --noinput

# ── 10. Nginx ────────────────────────────────────────────────────────────────
log "Configurando Nginx para $DOMAIN..."

# Reemplazar el placeholder del dominio en la config
sed "s/prislab.example.com/$DOMAIN/g" \
    "$APP_DIR/nginx/conf.d/prislab.conf" \
    > /etc/nginx/sites-available/prislab

ln -sf /etc/nginx/sites-available/prislab /etc/nginx/sites-enabled/prislab
rm -f /etc/nginx/sites-enabled/default

nginx -t && systemctl reload nginx
log "Nginx configurado"

# ── 11. Systemd services ──────────────────────────────────────────────────────
log "Instalando servicios systemd..."

for SERVICE in prislab-gunicorn prislab-celery prislab-celerybeat; do
    if [ -f "$APP_DIR/scripts/$SERVICE.service" ]; then
        # Reemplazar /opt/prislab con APP_DIR real si es diferente
        sed "s|/opt/prislab|$APP_DIR|g" \
            "$APP_DIR/scripts/$SERVICE.service" \
            > "/etc/systemd/system/$SERVICE.service"
        log "  Instalado: $SERVICE.service"
    fi
done

systemctl daemon-reload
systemctl enable prislab-gunicorn
systemctl start prislab-gunicorn
systemctl enable prislab-celery
systemctl start prislab-celery
systemctl enable prislab-celerybeat
systemctl start prislab-celerybeat

log "Gunicorn iniciado"
log "Celery iniciado"
log "Celery Beat iniciado"

# ── 12. SSL con Certbot ───────────────────────────────────────────────────────
if [[ "$DOMAIN" != "tu-dominio.com" ]]; then
    log "Emitiendo certificado SSL para $DOMAIN..."
    if certbot --nginx -d "$DOMAIN" --non-interactive --agree-tos --email "admin@$DOMAIN" --redirect; then
        log "SSL activado con Let's Encrypt"
    else
        warn "Certbot falló — verifica que el DNS de $DOMAIN apunte a esta IP"
        warn "Puedes emitir SSL después con: certbot --nginx -d $DOMAIN"
    fi
else
    warn "Dominio no configurado todavía; se omite Certbot por ahora"
fi

# ── 13. Redis ────────────────────────────────────────────────────────────────
log "Configurando Redis..."
systemctl enable redis-server
systemctl start redis-server

# ── 14. Verificación final ───────────────────────────────────────────────────
log ""
log "=========================================="
log "  PRISLAB SaaS — Deploy completado"
log "=========================================="
log "  URL:        https://$DOMAIN"
log "  Código:     $APP_DIR"
log "  Logs:       journalctl -u prislab-gunicorn -f"
log "  DB:         $DB_NAME @ 127.0.0.1"
log ""
log "SIGUIENTE PASO: Crear superusuario"
log "  cd $APP_DIR"
log "  sudo -u $APP_USER $VENV_DIR/bin/python manage.py seed_super_master_role"
log ""
log "VERIFICAR: https://$DOMAIN/login/"
log "=========================================="
