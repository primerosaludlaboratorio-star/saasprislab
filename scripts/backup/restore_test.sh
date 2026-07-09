#!/usr/bin/env bash
# =============================================================================
# PRISLAB SaaS — Restore Test Automatizado
# =============================================================================
# Toma el backup más reciente, lo restaura en una base de datos temporal de
# prueba, ejecuta consultas de verificación y limpia. Sirve como evidencia
# reproducible de que los backups son válidos.
#
# Uso:
#   bash scripts/backup/restore_test.sh
#   docker compose exec app bash scripts/backup/restore_test.sh
# =============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "${SCRIPT_DIR}/../.." && pwd)"
ENV_FILE="${PROJECT_DIR}/.env"

# ── Cargar variables de entorno si .env existe ───────────────────────────────
if [ -f "${ENV_FILE}" ]; then
  set -a
  # shellcheck source=/dev/null
  source "${ENV_FILE}"
  set +a
fi

# ── Configuración ────────────────────────────────────────────────────────────
BACKUP_DIR="${BACKUP_DIR:-${PROJECT_DIR}/backups}"
BACKUP_PREFIX="${BACKUP_PREFIX:-prislab}"

DB_NAME="${DB_NAME:-prislab_v5}"
DB_USER="${DB_USER:-prislab_user}"
DB_HOST="${DB_HOST:-db}"
DB_PORT="${DB_PORT:-5432}"
DB_PASSWORD="${DB_PASSWORD:-}"

TEST_DB_NAME="prislab_restore_test_$(date -u +%s)"
TEST_QUERIES=(
  "SELECT COUNT(*) FROM django_migrations;"
  "SELECT COUNT(*) FROM django_content_type;"
  "SELECT 1;"
)

# ── Helpers ────────────────────────────────────────────────────────────────────
log()  { echo "[RESTORE_TEST $(date -u +%Y-%m-%dT%H:%M:%SZ)] $1"; }
fail() { echo "[RESTORE_TEST ERROR $(date -u +%Y-%m-%dT%H:%M:%SZ)] $1" >&2; exit 1; }

# ── Validaciones ───────────────────────────────────────────────────────────────
command -v pg_restore >/dev/null 2>&1 || fail "pg_restore no encontrado. Instala postgresql-client."
command -v psql >/dev/null 2>&1 || fail "psql no encontrado. Instala postgresql-client."
command -v createdb >/dev/null 2>&1 || fail "createdb no encontrado. Instala postgresql-client."
command -v dropdb >/dev/null 2>&1 || fail "dropdb no encontrado. Instala postgresql-client."

[ -n "${DB_PASSWORD}" ] || fail "DB_PASSWORD no configurada."

# ── Buscar backup más reciente ─────────────────────────────────────────────────
LATEST_BACKUP=$(find "${BACKUP_DIR}" -maxdepth 1 -type f -name "${BACKUP_PREFIX}_*.dump" | sort | tail -n 1)
[ -n "${LATEST_BACKUP}" ] || fail "No se encontró ningún backup en ${BACKUP_DIR}"
[ -f "${LATEST_BACKUP}" ] || fail "Backup no existe: ${LATEST_BACKUP}"
[ -s "${LATEST_BACKUP}" ] || fail "Backup está vacío: ${LATEST_BACKUP}"

log "Backup seleccionado: ${LATEST_BACKUP}"
log "Base de prueba: ${TEST_DB_NAME}"

# ── Crear base de prueba ───────────────────────────────────────────────────────
export PGPASSWORD="${DB_PASSWORD}"

log "Creando base de datos temporal de prueba..."
dropdb -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" --if-exists "${TEST_DB_NAME}" >/dev/null 2>&1 || true
createdb -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" "${TEST_DB_NAME}" || fail "No se pudo crear ${TEST_DB_NAME}"

# ── Restaurar backup ───────────────────────────────────────────────────────────
log "Restaurando backup en base de prueba..."
pg_restore \
  -h "${DB_HOST}" \
  -p "${DB_PORT}" \
  -U "${DB_USER}" \
  -d "${TEST_DB_NAME}" \
  --no-owner \
  --no-privileges \
  --clean \
  --if-exists \
  "${LATEST_BACKUP}" \
  || fail "pg_restore falló al restaurar ${LATEST_BACKUP}"

log "Restore completado."

# ── Verificaciones ───────────────────────────────────────────────────────────
log "Ejecutando consultas de verificación..."
for QUERY in "${TEST_QUERIES[@]}"; do
  RESULT=$(psql -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -d "${TEST_DB_NAME}" -tAc "${QUERY}") \
    || fail "Consulta de verificación falló: ${QUERY}"
  log "  ${QUERY} -> ${RESULT}"
done

# ── Limpieza ───────────────────────────────────────────────────────────────────
log "Limpiando base de prueba..."
dropdb -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" --if-exists "${TEST_DB_NAME}" || fail "No se pudo eliminar ${TEST_DB_NAME}"

unset PGPASSWORD

# ── Reporte final ──────────────────────────────────────────────────────────────
log "Restore test PASSED."
log "Backup verificado: ${LATEST_BACKUP}"
log "Base de prueba: ${TEST_DB_NAME} (eliminada)"

exit 0
