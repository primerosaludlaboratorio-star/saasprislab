#!/bin/bash
# ==============================================================================
# PRISLAB — Activar certificado Wildcard SSL con Certbot + Cloudflare DNS
# ==============================================================================
# Prerrequisitos:
#   1. Crear un API Token en Cloudflare con acceso a la zona labcorecloud.com
#   2. Correr este script como root en la VPS
#
# Cómo obtener el token de Cloudflare con permisos correctos:
#   Cloudflare → My Profile → API Tokens → Create Token
#   → Template: "Edit zone DNS"
#   → Zone Resources: labcorecloud.com (específico, NO "All zones")
#   → Copiar el token generado
# ==============================================================================
set -e

DOMAIN="labcorecloud.com"
WILDCARD="*.labcorecloud.com"
EMAIL="primerosaludlaboratorio@gmail.com"
CF_TOKEN_FILE="/root/.cloudflare/cf_token.ini"
NGINX_CONF="/etc/nginx/conf.d/prislab.conf"
LEGACY_NGINX_CONF="/etc/nginx/sites-available/prislab"

echo "=============================================="
echo "  PRISLAB — Wildcard SSL Setup"
echo "  Dominio: $DOMAIN"
echo "=============================================="

# ── 1. Instalar plugin Cloudflare ─────────────────────────────────────────
echo "[1/4] Instalando certbot-dns-cloudflare..."
pip3 install certbot-dns-cloudflare --quiet 2>/dev/null || \
    apt-get install -y python3-certbot-dns-cloudflare 2>/dev/null || \
    pip install certbot-dns-cloudflare --quiet

# ── 2. Configurar token de Cloudflare ─────────────────────────────────────
echo "[2/4] Configurando credenciales de Cloudflare..."
mkdir -p /root/.cloudflare
chmod 700 /root/.cloudflare

if [ -z "${CF_API_TOKEN:-}" ]; then
    echo ""
    echo "Ingresa tu Cloudflare API Token (Zone.DNS:Edit para labcorecloud.com):"
    read -r CF_API_TOKEN
fi

cat > "$CF_TOKEN_FILE" << EOF
dns_cloudflare_api_token = $CF_API_TOKEN
EOF
chmod 600 "$CF_TOKEN_FILE"

# Verificar que el token funciona
echo "[2/4] Verificando token de Cloudflare..."
curl -s -X GET "https://api.cloudflare.com/client/v4/zones?name=$DOMAIN" \
    -H "Authorization: Bearer $CF_API_TOKEN" \
    -H "Content-Type: application/json" | python3 -c "
import sys, json
data = json.load(sys.stdin)
if data.get('success') and data.get('result'):
    zone = data['result'][0]
    print(f'  ✓ Zona encontrada: {zone[\"name\"]} (ID: {zone[\"id\"]})')
else:
    print(f'  ✗ Token inválido o zona no encontrada')
    print(f'    Verifica que el token tenga acceso a la zona labcorecloud.com con permiso DNS Edit')
    sys.exit(1)
"

# ── 3. Emitir certificado wildcard ────────────────────────────────────────
echo "[3/4] Emitiendo certificado wildcard para *.$DOMAIN..."
certbot certonly \
    --dns-cloudflare \
    --dns-cloudflare-credentials "$CF_TOKEN_FILE" \
    --dns-cloudflare-propagation-seconds 60 \
    -d "$DOMAIN" \
    -d "$WILDCARD" \
    --email "$EMAIL" \
    --agree-tos \
    --non-interactive \
    --expand

# ── 4. Actualizar nginx para usar el wildcard ──────────────────────────────
echo "[4/4] Actualizando Nginx con certificado wildcard..."
CERT_PATH="/etc/letsencrypt/live/$DOMAIN/fullchain.pem"

# Actualizar la ruta del certificado en la configuración real de la VPS
if [ -f "$CERT_PATH" ]; then
    if [ -f "$NGINX_CONF" ]; then
        sed -i "s|/etc/letsencrypt/live/prislab\.$DOMAIN/|/etc/letsencrypt/live/$DOMAIN/|g" "$NGINX_CONF"
    fi

    if [ -f "$LEGACY_NGINX_CONF" ]; then
        sed -i "s|/etc/letsencrypt/live/prislab\.$DOMAIN/|/etc/letsencrypt/live/$DOMAIN/|g" "$LEGACY_NGINX_CONF"
    fi

    nginx -t && systemctl reload nginx
    echo "  ✓ Nginx recargado con certificado wildcard"
fi

echo ""
echo "=============================================="
echo "  WILDCARD SSL ACTIVADO"
echo "  Cubre: $DOMAIN y *.$DOMAIN"
echo "  Certbot renovará automáticamente antes de expirar"
echo "=============================================="
