# PRISLAB SaaS — Backup & Restore Scripts

Scripts enterprise para respaldo, verificación y prueba de restauración de PostgreSQL.

## Archivos

| Archivo | Propósito |
|---------|-----------|
| `backup_postgres.sh` | Backup completo en formato custom, verificación de integridad, retención local y replica opcional a S3. |
| `restore_test.sh` | Restaura el backup más reciente en una base de datos temporal y ejecuta consultas de verificación. |
| `backup.env.example` | Variables de entorno requeridas. |
| `README.md` | Este documento. |

## Requisitos

- `bash`
- `postgresql-client` (pg_dump, pg_restore, psql, createdb, dropdb)
- `awscli` (solo si se habilita replica S3)
- Variables de entorno cargadas (`.env` o exportadas)

## Uso rápido

```bash
# 1. Copiar y ajustar configuración
cp scripts/backup/backup.env.example .env
# editar .env con credenciales reales

# 2. Ejecutar backup
bash scripts/backup/backup_postgres.sh

# 3. Ejecutar restore test
bash scripts/backup/restore_test.sh
```

## Uso con Docker Compose

```bash
# Backup
docker compose exec -T app bash scripts/backup/backup_postgres.sh

# Restore test
docker compose exec -T app bash scripts/backup/restore_test.sh
```

## Automatización sugerida

```cron
# Backup cada 6 horas
0 */6 * * * cd /opt/prislab && docker compose exec -T app bash scripts/backup/backup_postgres.sh >> /var/log/prislab_backup.log 2>&1

# Restore test semanal (domingo 03:00)
0 3 * * 0 cd /opt/prislab && docker compose exec -T app bash scripts/backup/restore_test.sh >> /var/log/prislab_restore_test.log 2>&1
```

## Variables de entorno

Ver `backup.env.example` para la lista completa.

## Integración con DR

Ver `docs/DR_PLAN.md` para el plan completo de recuperación ante desastres.
