#!/usr/bin/env bash
# ==============================================================================
# PRISLAB V5 — Script de Despliegue Automatizado (Ubuntu/Linux)
# ==============================================================================
# Uso:
#   chmod +x deploy.sh
#   ./deploy.sh                 # Despliegue completo (primera vez)
#   ./deploy.sh --update        # Actualizar solo la app (rebuild + migrate)
#   ./deploy.sh --ssl           # Solo obtener/renovar certificados SSL
#   ./deploy.sh --backup        # Solo hacer backup de la base de datos
#   ./deploy.sh --status        # Ver estado de los servicios
#   ./deploy.sh --logs          # Ver logs en tiempo real
# ==============================================================================

set -euo pipefail

# ── Colores ──────────────────────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# ── Variables ────────────────────────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="${SCRIPT_DIR}/.env"
BACKUP_DIR="${SCRIPT_DIR}/backups"
COMPOSE_CMD="docker compose"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# ── Funciones de utilidad ────────────────────────────────────────────────────
log_info()  { echo -e "${BLUE}[INFO]${NC} $1"; }
log_ok()    { echo -e "${GREEN}[  OK]${NC} $1"; }
log_warn()  { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }
log_step()  { echo -e "\n${CYAN}═══════════════════════════════════════════════════════${NC}"; echo -e "${CYAN}  $1${NC}"; echo -e "${CYAN}═══════════════════════════════════════════════════════${NC}\n"; }

# ── Verificar que existe .env ────────────────────────────────────────────────
check_env() {
    if [ ! -f "$ENV_FILE" ]; then
        log_error "No se encontró el archivo .env"
        log_info "Copia .env.example → .env y configura las variables:"
        log_info "  cp .env.example .env && nano .env"
        exit 1
    fi
    source "$ENV_FILE"
    log_ok "Archivo .env cargado"
}

# ── Verificar dependencias ───────────────────────────────────────────────────
check_dependencies() {
    log_step "Verificando dependencias del sistema"

    local deps=("docker" "curl")
    for dep in "${deps[@]}"; do
        if command -v "$dep" &>/dev/null; then
            log_ok "$dep instalado ($(command -v "$dep"))"
        else
            log_error "$dep no está instalado"
            exit 1
        fi
    done

    # Verificar Docker Compose (v2 integrado)
    if docker compose version &>/dev/null; then
        log_ok "Docker Compose $(docker compose version --short)"
    elif docker-compose --version &>/dev/null; then
        COMPOSE_CMD="docker-compose"
        log_warn "Usando docker-compose legacy"
    else
        log_error "Docker Compose no está instalado"
        exit 1
    fi

    # Verificar que Docker esté corriendo
    if docker info &>/dev/null; then
        log_ok "Docker daemon activo"
    else
        log_error "Docker daemon no está corriendo. Ejecuta: sudo systemctl start docker"
        exit 1
    fi
}

# ── Crear directorios necesarios ─────────────────────────────────────────────
create_directories() {
    log_step "Creando directorios necesarios"
    mkdir -p "$BACKUP_DIR"
    mkdir -p "${SCRIPT_DIR}/nginx/conf.d"
    mkdir -p "${SCRIPT_DIR}/logs"
    log_ok "Directorios creados"
}

# ── Reemplazar dominio en Nginx ──────────────────────────────────────────────
configure_domain() {
    log_step "Configurando dominio: ${DOMAIN:-prislab.example.com}"

    if [ -n "${DOMAIN:-}" ] && [ "$DOMAIN" != "prislab.example.com" ]; then
        sed -i "s/prislab.example.com/${DOMAIN}/g" "${SCRIPT_DIR}/nginx/conf.d/prislab.conf"
        log_ok "Dominio actualizado a: $DOMAIN"
    else
        log_warn "Usando dominio por defecto (prislab.example.com)"
        log_warn "Cambia DOMAIN en .env para tu dominio real"
    fi
}

# ── Backup de la base de datos ───────────────────────────────────────────────
backup_database() {
    log_step "Respaldo de base de datos"

    if docker ps --format '{{.Names}}' | grep -q prislab_db; then
        local BACKUP_FILE="${BACKUP_DIR}/prislab_db_${TIMESTAMP}.sql.gz"
        
        docker exec prislab_db pg_dump \
            -U "${DB_USER:-prislab_user}" \
            -d "${DB_NAME:-prislab_v5}" \
            --clean --if-exists --no-owner \
            | gzip > "$BACKUP_FILE"

        local SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
        log_ok "Backup creado: $BACKUP_FILE ($SIZE)"

        # Mantener solo los últimos 30 backups
        cd "$BACKUP_DIR" && ls -t prislab_db_*.sql.gz 2>/dev/null | tail -n +31 | xargs -r rm --
        log_info "Limpieza: manteniendo últimos 30 backups"
    else
        log_warn "Contenedor de BD no está corriendo, saltando backup"
    fi
}

# ── Obtener certificados SSL ─────────────────────────────────────────────────
obtain_ssl() {
    log_step "Configurando certificados SSL (Let's Encrypt)"

    local DOMAIN="${DOMAIN:-prislab.example.com}"
    local EMAIL="${SSL_EMAIL:-admin@prislab.com}"

    if [ "$DOMAIN" = "prislab.example.com" ]; then
        log_warn "DOMAIN no configurado. SSL desactivado (usando HTTP)"
        log_warn "Para activar SSL: configura DOMAIN y SSL_EMAIL en .env"
        
        # Crear configuración HTTP-only temporal
        cat > "${SCRIPT_DIR}/nginx/conf.d/prislab.conf" << 'HTTPCONF'
# Configuración HTTP (sin SSL) — Temporal hasta configurar dominio
server {
    listen 80;
    listen [::]:80;
    server_name _;

    client_max_body_size 500M;

    location /health/ {
        access_log off;
        return 200 'OK';
        add_header Content-Type text/plain;
    }

    location /static/ {
        alias /app/staticfiles/;
        expires 30d;
        add_header Cache-Control "public, immutable";
        access_log off;
        gzip_static on;
    }

    location /media/ {
        alias /app/media/;
        expires 7d;
        add_header Cache-Control "public";
    }

    location / {
        proxy_pass http://prislab_app;
        proxy_set_header Host $http_host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_connect_timeout 60s;
        proxy_send_timeout 300s;
        proxy_read_timeout 300s;
    }
}
HTTPCONF
        log_ok "Configuración HTTP-only aplicada"
        return
    fi

    # Iniciar Nginx temporalmente para validación ACME
    $COMPOSE_CMD up -d nginx

    # Solicitar certificado
    docker run --rm \
        -v prislab_certbot_conf:/etc/letsencrypt \
        -v prislab_certbot_www:/var/www/certbot \
        certbot/certbot certonly \
        --webroot \
        --webroot-path=/var/www/certbot \
        --email "$EMAIL" \
        --agree-tos \
        --no-eff-email \
        -d "$DOMAIN" \
        -d "www.${DOMAIN}" \
        --non-interactive

    log_ok "Certificado SSL obtenido para $DOMAIN"
}

# ── Build y despliegue ───────────────────────────────────────────────────────
deploy_full() {
    log_step "Construyendo imágenes Docker"
    $COMPOSE_CMD build --no-cache app
    log_ok "Imagen de la aplicación construida"

    log_step "Levantando servicios"
    $COMPOSE_CMD up -d db redis
    log_info "Esperando que PostgreSQL esté listo..."
    sleep 10  # Esperar health check

    # Verificar que la BD esté lista
    local retries=30
    while [ $retries -gt 0 ]; do
        if docker exec prislab_db pg_isready -U "${DB_USER:-prislab_user}" &>/dev/null; then
            log_ok "PostgreSQL listo"
            break
        fi
        retries=$((retries - 1))
        sleep 2
    done

    if [ $retries -eq 0 ]; then
        log_error "PostgreSQL no respondió a tiempo"
        exit 1
    fi

    log_step "Ejecutando migraciones de Django"
    $COMPOSE_CMD run --rm app python manage.py migrate --noinput
    log_ok "Migraciones aplicadas"

    log_step "Creando superusuario"
    $COMPOSE_CMD run --rm app python crear_superusuario_admin.py || true
    log_ok "Superusuario verificado"

    log_step "Recolectando archivos estáticos"
    $COMPOSE_CMD run --rm app python manage.py collectstatic --noinput
    log_ok "Archivos estáticos recolectados"

    log_step "Levantando todos los servicios"
    $COMPOSE_CMD up -d
    log_ok "Todos los servicios iniciados"
}

# ── Solo actualizar la app ───────────────────────────────────────────────────
deploy_update() {
    log_step "Actualizando aplicación (sin tocar BD)"

    # Backup antes de actualizar
    backup_database

    log_info "Reconstruyendo imagen..."
    $COMPOSE_CMD build app
    log_ok "Imagen reconstruida"

    log_info "Ejecutando migraciones..."
    $COMPOSE_CMD run --rm app python manage.py migrate --noinput
    log_ok "Migraciones aplicadas"

    log_info "Recolectando estáticos..."
    $COMPOSE_CMD run --rm app python manage.py collectstatic --noinput
    log_ok "Estáticos actualizados"

    log_info "Reiniciando app y nginx..."
    $COMPOSE_CMD up -d --no-deps app nginx
    log_ok "Servicios reiniciados"
}

# ── Estado de los servicios ──────────────────────────────────────────────────
show_status() {
    log_step "Estado de los servicios PRISLAB"
    $COMPOSE_CMD ps -a
    echo ""
    log_info "Uso de disco de volúmenes:"
    docker system df -v 2>/dev/null | grep prislab || true
}

# ── Ver logs ─────────────────────────────────────────────────────────────────
show_logs() {
    log_step "Logs en tiempo real (Ctrl+C para salir)"
    $COMPOSE_CMD logs -f --tail=100
}

# ── Verificación post-despliegue ─────────────────────────────────────────────
verify_deployment() {
    log_step "Verificación post-despliegue"

    sleep 5  # Dar tiempo a que los servicios inicien

    # Verificar cada servicio
    local services=("prislab_db" "prislab_redis" "prislab_app" "prislab_nginx")
    for svc in "${services[@]}"; do
        if docker ps --format '{{.Names}}' | grep -q "$svc"; then
            log_ok "$svc corriendo"
        else
            log_error "$svc NO está corriendo"
        fi
    done

    # Verificar respuesta HTTP
    echo ""
    log_info "Probando conexión HTTP..."
    local HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost/login/ 2>/dev/null || echo "000")
    if [ "$HTTP_CODE" = "200" ] || [ "$HTTP_CODE" = "302" ]; then
        log_ok "HTTP responde: $HTTP_CODE"
    else
        log_warn "HTTP respondió: $HTTP_CODE (puede necesitar unos segundos más)"
    fi

    echo ""
    echo -e "${GREEN}══════════════════════════════════════════════════════════${NC}"
    echo -e "${GREEN}  ✅ PRISLAB V5 — Despliegue Completo${NC}"
    echo -e "${GREEN}══════════════════════════════════════════════════════════${NC}"
    echo ""
    echo -e "  🌐 URL:      ${CYAN}http://${DOMAIN:-localhost}${NC}"
    echo -e "  👤 Usuario:  ${CYAN}admin${NC}"
    echo -e "  🔑 Password: ${CYAN}PrislabV5_2026${NC}"
    echo ""
    echo -e "  📦 Servicios:"
    echo -e "     Django:    http://localhost:8000"
    echo -e "     Postgres:  localhost:5432"
    echo -e "     Redis:     localhost:6379"
    echo -e "     Nginx:     http://localhost (80/443)"
    echo ""
    echo -e "  📋 Comandos útiles:"
    echo -e "     ./deploy.sh --status    Ver estado"
    echo -e "     ./deploy.sh --logs      Ver logs"
    echo -e "     ./deploy.sh --backup    Backup de BD"
    echo -e "     ./deploy.sh --update    Actualizar app"
    echo ""
}


# ==============================================================================
# MAIN — Punto de entrada
# ==============================================================================
main() {
    echo ""
    echo -e "${CYAN}╔══════════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║     PRISLAB V5 — Sistema de Despliegue Automatizado    ║${NC}"
    echo -e "${CYAN}║     Servidor de Producción (Ubuntu/Linux + Docker)      ║${NC}"
    echo -e "${CYAN}╚══════════════════════════════════════════════════════════╝${NC}"
    echo ""

    cd "$SCRIPT_DIR"

    case "${1:-}" in
        --update|-u)
            check_env
            deploy_update
            verify_deployment
            ;;
        --ssl)
            check_env
            obtain_ssl
            ;;
        --backup|-b)
            check_env
            backup_database
            ;;
        --status|-s)
            show_status
            ;;
        --logs|-l)
            show_logs
            ;;
        --help|-h)
            echo "Uso: ./deploy.sh [opción]"
            echo ""
            echo "Opciones:"
            echo "  (sin args)    Despliegue completo (primera vez)"
            echo "  --update, -u  Actualizar solo la app"
            echo "  --ssl         Obtener/renovar certificados SSL"
            echo "  --backup, -b  Backup de la base de datos"
            echo "  --status, -s  Ver estado de los servicios"
            echo "  --logs, -l    Ver logs en tiempo real"
            echo "  --help, -h    Mostrar esta ayuda"
            ;;
        *)
            # Despliegue completo (primera vez)
            check_env
            check_dependencies
            create_directories
            configure_domain
            obtain_ssl
            deploy_full
            verify_deployment
            ;;
    esac
}

main "$@"
