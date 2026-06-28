#!/usr/bin/env bash
# Verificación canónica para despliegue VPS PRISLAB

set -euo pipefail

echo "🔍 Verificando archivos y configuración de despliegue VPS..."

check_file() {
    local file="$1"
    local label="$2"
    if [ ! -f "$file" ]; then
        echo "❌ ERROR: $label no encontrado en $file"
        exit 1
    fi
    echo "✅ $label encontrado"
}

check_file "manage.py" "manage.py"
check_file "requirements.txt" "requirements.txt"
check_file "scripts/deploy_vps.sh" "scripts/deploy_vps.sh"
check_file "scripts/aplicar_fixes_produccion.sh" "scripts/aplicar_fixes_produccion.sh"
check_file "scripts/activar_wildcard_ssl.sh" "scripts/activar_wildcard_ssl.sh"
check_file "scripts/web_entrypoint.sh" "scripts/web_entrypoint.sh"
check_file "scripts/prislab-gunicorn.service" "prislab-gunicorn.service"
check_file "scripts/prislab-celery.service" "prislab-celery.service"
check_file "scripts/prislab-celerybeat.service" "prislab-celerybeat.service"
check_file "nginx/conf.d/prislab.conf" "nginx/conf.d/prislab.conf"
check_file ".env.production.example" ".env.production.example"

if ! grep -q "gunicorn" requirements.txt; then
    echo "❌ ERROR: gunicorn no está en requirements.txt"
    exit 1
fi
echo "✅ gunicorn encontrado en requirements.txt"

if ! grep -q "celery" requirements.txt; then
    echo "❌ ERROR: celery no está en requirements.txt"
    exit 1
fi
echo "✅ celery encontrado en requirements.txt"

if ! grep -q "prislab-gunicorn" scripts/deploy_vps.sh; then
    echo "❌ ERROR: deploy_vps.sh no referencia prislab-gunicorn"
    exit 1
fi
echo "✅ deploy_vps.sh usa servicios prislab-*"

if ! grep -q "prislab-celerybeat" scripts/aplicar_fixes_produccion.sh; then
    echo "❌ ERROR: aplicar_fixes_produccion.sh no reinicia prislab-celerybeat"
    exit 1
fi
echo "✅ aplicar_fixes_produccion.sh reinicia prislab-*"

if ! grep -q "prislab.labcorecloud.com" nginx/conf.d/prislab.conf; then
    echo "⚠️ ADVERTENCIA: no se detectó prislab.labcorecloud.com en nginx/conf.d/prislab.conf"
fi
echo "✅ Configuración nginx verificada"

if [ ! -x "scripts/deploy_vps.sh" ]; then
    echo "⚠️ ADVERTENCIA: scripts/deploy_vps.sh no tiene permisos de ejecución"
fi

echo
echo "✅ Verificación completada. El árbol está listo para el deploy VPS."
