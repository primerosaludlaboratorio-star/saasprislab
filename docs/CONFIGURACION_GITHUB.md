# Configuración Requerida en GitHub — PRISLAB SaaS

**Versión:** 1.0  
**Fecha:** 2026-07-09  
**Rama:** `release/v1.0-local`

---

## 1. Branch Protection para `release/v1.0-local`

Debe configurarse manualmente en GitHub: **Settings > Branches > Add rule**.

### Reglas obligatorias

| Regla | Valor |
|-------|-------|
| Branch name pattern | `release/v1.0-local` |
| Require a pull request before merging | ✅ Sí |
| Require approvals | 1 mínimo |
| Dismiss stale PR approvals | ✅ Sí |
| Require status checks to pass | ✅ Sí |
| Status checks requeridos | `PRISLAB Quality Gate`, `PRISLAB SRE Health Check`, `PRISLAB Backup/Restore Test` |
| Require branches to be up to date before merging | ✅ Sí |
| Restrict who can push to matching branches | ✅ Sí (solo admins / mantainers) |
| Do not allow bypassing the above settings | ✅ Sí |
| Include administrators | ✅ Sí |

> **Nota:** Hasta la fecha los últimos commits se han hecho con bypass de esta regla. Esta configuración debe aplicarse y verificarse para evitar pushes directos.

---

## 2. Secretos necesarios para el deploy automatizado

Ir a **Settings > Secrets and variables > Actions** y agregar:

| Secreto | Descripción |
|---------|-------------|
| `DEPLOY_HOST` | IP o dominio del VPS (ej. `vps.prislab.app`) |
| `DEPLOY_USER` | Usuario SSH en el VPS (ej. `deploy`) |
| `DEPLOY_SSH_KEY` | Clave privada SSH completa (incluyendo `BEGIN OPENSSH PRIVATE KEY`) |

### Variables de repositorio (opcionales)

Ir a **Settings > Secrets and variables > Actions > Variables**:

| Variable | Valor por defecto | Descripción |
|----------|-------------------|-------------|
| `DEPLOY_DIR` | `/opt/prislab` | Directorio de despliegue en VPS |
| `COMPOSE_FILE` | `docker-compose.yml` | Archivo compose principal |

---

## 3. Entornos de GitHub

Crear los entornos: **staging** y **production** en **Settings > Environments**.

Cada entorno debe tener sus propios secretos `DEPLOY_HOST`, `DEPLOY_USER`, `DEPLOY_SSH_KEY` si difieren del entorno general.

---

## 4. Cierre de PRs pendientes

Los siguientes PRs quedan obsoletos o resueltos en la rama actual y deben cerrarse manualmente:

- **#8** — Reemplazo de `migrate --check` por `makemigrations --check`: ya está aplicado en `.github/workflows/main.yml`.
- **#9** — Fix de patch target en `scripts_cursor_e2e/tests/test_robot_chemist_flows.py`: archivo ya no existe en la estructura actual.

---

## 5. Verificación

Después de configurar:

1. Intentar hacer push directo a `release/v1.0-local` debe fallar.
2. Crear un PR trivial; los status checks deben aparecer y ser requeridos.
3. Ejecutar manualmente `PRISLAB Deploy to VPS` desde **Actions > deploy-vps.yml > Run workflow**.
