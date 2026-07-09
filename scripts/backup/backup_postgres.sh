#!/usr/bin/env bash
# =============================================================================
# PRISLAB SaaS — PostgreSQL Backup Enterprise
# =============================================================================
# Realiza backup completo de PostgreSQL en formato custom (-Fc), verifica
# integridad con pg_restore --list, aplica retención local y opcionalmente
# replica a object storage S3-compatible.
#
# Uso dentro del contenedor app:
#   docker compose exec app bash scripts/backup/backup_postgres.sh
#
# Uso en host (con pg_dump disponible):
#   bash scripts/backup/backup_postgres.sh
#
# Crontab sugerido (host):
#   0 */6 * * * cd /opt/prislab && docker compose exec -T app bash scripts/backup/backup_postgres.sh
# =============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "${SCRIPT_DIR}/../.." && pwd)"
ENV_FILE="${PROJECT_DIR}/.env"

# ── Cargar variables de entorno si .env existe ───────────────────────────────
if [ -f "${ENV_FILE}" ]; then
  # shellcheck source=/dev/null
  set -a
  # shellcheck source=/dev/null
  source "${ENV_FILE}"
  set +a
fi

# ── Configuración con defaults razonables ────────────────────────────────────
BACKUP_DIR="${BACKUP_DIR:-${PROJECT_DIR}/backups}"
RETENTION_DAYS="${BACKUP_RETENTION_DAYS:-30}"
COMPRESSION_LEVEL="${BACKUP_COMPRESSION_LEVEL:-6}"
TIMESTAMP=$(date -u +%Y%m%d_%H%M%S)

DB_NAME="${DB_NAME:-prislab_v5}"
DB_USER="${DB_USER:-prislab_user}"
DB_HOST="${DB_HOST:-db}"
DB_PORT="${DB_PORT:-5432}"
DB_PASSWORD="${DB_PASSWORD:-}"

BACKUP_PREFIX="${BACKUP_PREFIX:-prislab}"
BACKUP_FILE="${BACKUP_DIR}/${BACKUP_PREFIX}_${DB_NAME}_${TIMESTAMP}.dump"

S3_BACKUP_ENABLED="${S3_BACKUP_ENABLED:-false}"
S3_BUCKET="${S3_BACKUP_BUCKET:-}"
S3_ENDPOINT="${S3_BACKUP_ENDPOINT:-}"
S3_ACCESS_KEY="${S3_BACKUP_ACCESS_KEY:-}"
S3_SECRET_KEY="${S3_BACKUP_SECRET_KEY:-}"
S3_REGION="${S3_BACKUP_REGION:-us-east-1}"

# ── Helpers ──────────────────────────────────────────────────────────────────
log()  { echo "[BACKUP $(date -u +%Y-%m-%dT%H:%M:%SZ)] $1"; }
fail() { echo "[BACKUP ERROR $(date -u +%Y-%m-%dT%H:%M:%SZ)] $1" >&2; exit 1; }

# ── Validaciones ─────────────────────────────────────────────────────────────
command -v pg_dump >/dev/null 2>&1 || fail "pg_dump no encontrado. Instala postgresql-client."
command -v pg_restore >/dev/null 2>&1 || fail "pg_restore no encontrado. Instala postgresql-client."

[ -n "${DB_PASSWORD}" ] || fail "DB_PASSWORD no configurada."

log "Iniciando backup de ${DB_NAME} @ ${DB_HOST}:${DB_PORT}"
log "Destino: ${BACKUP_FILE}"
log "Compresión: ${COMPRESSION_LEVEL}, retención local: ${RETENTION_DAYS} días"

# ── Crear directorio de backups ────────────────────────────────────────────────
mkdir -p "${BACKUP_DIR}"

# ── Ejecutar pg_dump formato custom ────────────────────────────────────────────
export PGPASSWORD="${DB_PASSWORD}"

pg_dump \
  -h "${DB_HOST}" \
  -p "${DB_PORT}" \
  -U "${DB_USER}" \
  -d "${DB_NAME}" \
  -F c \
  -Z "${COMPRESSION_LEVEL}" \
  -v \
  --clean \
  --if-exists \
  --no-owner \
  --no-privileges \
  -f "${BACKUP_FILE}"

unset PGPASSWORD

# ── Verificar integridad del backup ────────────────────────────────────────────
log "Verificando integridad del backup..."
pg_restore -l "${BACKUP_FILE}" >/dev/null || fail "El backup no es restaurable (pg_restore --list falló)."

BACKUP_SIZE=$(stat -c %s "${BACKUP_FILE}" 2>/dev/null || stat -f %z "${BACKUP_FILE}" 2>/dev/null)
log "Backup creado: ${BACKUP_FILE} ($((BACKUP_SIZE / 1024 / 1024)) MB)"

# ── Replicar a S3 si está configurado ────────────────────────────────────────
if [ "${S3_BACKUP_ENABLED}" = "true" ] || [ "${S3_BACKUP_ENABLED}" = "1" ]; then
  [ -n "${S3_BUCKET}" ] || fail "S3_BACKUP_ENABLED=true pero S3_BACKUP_BUCKET vacío."
  command -v aws >/dev/null 2>&1 || fail "awscli no instalado. Requerido para replica S3."

  log "Replicando backup a s3://${S3_BUCKET}/backups/"
  aws s3 cp "${BACKUP_FILE}" "s3://${S3_BUCKET}/backups/$(basename "${BACKUP_FILE}")" \
    --endpoint-url "${S3_ENDPOINT}" \
    --region "${S3_REGION}" \
    || fail "No se pudo replicar a S3."
  log "Replica S3 completada."
fi

# ── Rotación local ─────────────────────────────────────────────────────────────
log "Aplicando retención local: ${RETENTION_DAYS} días..."
DELETED=$(find "${BACKUP_DIR}" -maxdepth 1 -type f \
  \( -name "${BACKUP_PREFIX}_*.dump" -o -name "backup_*.sql.gz" \) \
  -mtime +${RETENTION_DAYS} -print)
if [ -n "${DELETED}" ]; then
  echo "${DELETED}" | xargs -r rm -f
  log "Archivos eliminados por retención:"
  echo "${DELETED}" | sed 's/^/  - /'
else
  log "No hay archivos locales para eliminar."
fi

# ── Reporte final ──────────────────────────────────────────────────────────────
log "Backup enterprise completado exitosamente."
log "Archivo: ${BACKUP_FILE}"
log "Verificación: pg_restore --list OK"
if [ "${S3_BACKUP_ENABLED}" = "true" ] || [ "${S3_BACKUP_ENABLED}" = "1" ]; then
  log "Replica S3: s3://${S3_BUCKET}/backups/$(basename "${BACKUP_FILE}")"
fi

exit 0
