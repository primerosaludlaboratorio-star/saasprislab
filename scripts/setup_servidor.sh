#!/bin/bash
# ==============================================================================
# PRISLAB SaaS — Setup completo del servidor VPS
# Ejecutar como root en Ubuntu 26.04+
# ==============================================================================
set -e

DB_PASSWORD="feTLeV3skPy%3I8B6O^RO12BqKr@B6iz"
DB_NAME="prislab_db"
DB_USER="prislab_user"
ROOT_DIR="/opt/prislab"
APP_DIR="$ROOT_DIR/app"
APP_USER="prislab"

echo "=============================================="
echo "  PRISLAB VPS Setup — Iniciando..."
echo "=============================================="

# 1. Sistema base
echo "[1/10] Actualizando sistema..."
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get upgrade -y -qq
apt-get install -y --no-install-recommends \
    nginx postgresql postgresql-contrib \
    python3 python3-venv python3-dev python3-pip \
    build-essential git curl wget unzip \
    certbot python3-certbot-nginx \
    ufw redis-server \
    libpq-dev libssl-dev libffi-dev \
    supervisor htop nano

echo "[1/10] Sistema actualizado ✓"

# 2. Firewall
echo "[2/10] Configurando UFW..."
ufw --force reset
ufw default deny incoming
ufw default allow outgoing
ufw allow 22/tcp    # SSH
ufw allow 80/tcp    # HTTP
ufw allow 443/tcp   # HTTPS
ufw --force enable
echo "[2/10] Firewall configurado ✓"

# 3. PostgreSQL
echo "[3/10] Configurando PostgreSQL..."
systemctl enable postgresql
systemctl start postgresql

sudo -u postgres psql -tc "SELECT 1 FROM pg_user WHERE usename='$DB_USER'" | grep -q 1 2>/dev/null || \
    sudo -u postgres createuser "$DB_USER"
sudo -u postgres psql -tc "SELECT 1 FROM pg_database WHERE datname='$DB_NAME'" | grep -q 1 2>/dev/null || \
    sudo -u postgres createdb "$DB_NAME" -O "$DB_USER"
sudo -u postgres psql -c "ALTER USER $DB_USER WITH PASSWORD '$DB_PASSWORD';" 2>/dev/null || true

echo "[3/10] PostgreSQL listo ✓"

# 4. Redis
echo "[4/10] Configurando Redis..."
systemctl enable redis-server
systemctl start redis-server
echo "[4/10] Redis listo ✓"

# 5. Usuario y directorio
echo "[5/10] Creando usuario $APP_USER..."
id "$APP_USER" &>/dev/null || useradd --system --shell /bin/bash --home "$ROOT_DIR" --create-home "$APP_USER"
mkdir -p "$ROOT_DIR/logs" "$APP_DIR" "$APP_DIR/media" "$APP_DIR/staticfiles" "$APP_DIR/media/buffer"
echo "[5/10] Usuario y directorios creados ✓"

echo "=============================================="
echo "  Setup base COMPLETADO"
echo "  Siguiente: clonar repositorio y continuar"
echo "=============================================="

# Mostrar versiones instaladas
echo ""
echo "Versiones instaladas:"
python3 --version
nginx -v 2>&1
psql --version
redis-cli --version
echo ""
echo "PostgreSQL:"
echo "  DB: $DB_NAME"
echo "  User: $DB_USER"
echo "  Password: $DB_PASSWORD"
echo ""
echo "LISTO PARA CLONAR EL REPOSITORIO EN $APP_DIR"
