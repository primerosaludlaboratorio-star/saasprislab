# Checklist de Integración Final — PRISLAB SaaS

**Versión:** 1.0  
**Fecha:** 2026-07-09  
**Uso:** Fase 5 del plan secuencial (Editor 1: Cascade)

---

## 1. Revisión de PRs previos

- [ ] Fase 1 (infra/CI/CD/monitoreo) mergeado y CI verde.
- [ ] Fase 2 (migración P0) revisado y aprobado.
- [ ] Fase 3 (security/SDLC) mergeado y CI verde.
- [ ] Fase 4 (governance/performance) revisado y aprobado.

---

## 2. Tests

- [ ] `python manage.py test` pasa localmente.
- [ ] `python manage.py makemigrations --check --dry-run` no detecta migraciones faltantes.
- [ ] Workflows de CI verdes:
  - [ ] `main.yml`
  - [ ] `sre-health-check.yml`
  - [ ] `backup-restore-test.yml`
  - [ ] `secret-scan.yml`
  - [ ] `sbom-audit.yml`
- [ ] `python manage.py check --deploy` sin errores críticos.

---

## 3. Seguridad

- [ ] `SECRET_KEY` configurado y seguro en producción.
- [ ] `.env` tiene permisos `600`.
- [ ] No hay secretos hardcodeados en el código (validar con `gitleaks`).
- [ ] Dependencias críticas actualizadas (#13, #35 resueltos).
- [ ] Branch protection activo en `release/v1.0-local` sin bypass.

---

## 4. Infraestructura y despliegue

- [ ] `deploy-vps.yml` configurado con secretos `DEPLOY_HOST`, `DEPLOY_USER`, `DEPLOY_SSH_KEY`.
- [ ] Deploy a staging exitoso.
- [ ] Smoke tests post-deploy pasan:
  - [ ] `/live/` → 200
  - [ ] `/ready/` → 200
  - [ ] `/health/` → 200
  - [ ] `/metrics/` → 200
- [ ] Stack de monitoreo levantado y consumiendo métricas.
- [ ] Backup automático configurado y probado.

---

## 5. Validación funcional

- [ ] Bloques P0 cerrados con evidencia:
  - [ ] Bloque 1: Catálogo LIMS
  - [ ] Bloque 2: Valores de referencia y PDF
  - [ ] Bloque 3: Recepción y órdenes
  - [ ] Bloque 8: Cobranza
  - [ ] Bloque 13: Reportes críticos
- [ ] Comparativa con sistema legado documentada o aprobada.
- [ ] Pruebas de carga ejecutadas y SLO de latencia cumplido.

---

## 6. Documentación

- [ ] `README.md` actualizado.
- [ ] `docs/SRE_RUNBOOKS.md` y `docs/SLO_SLI.md` vigentes.
- [ ] `docs/DR_PLAN.md` vigente.
- [ ] ADRs creados para decisiones arquitectónicas clave.
- [ ] Definition of Done aprobado.
- [ ] Matriz RBAC documentada.

---

## 7. Go/No-Go

| Criterio | Estado |
|----------|--------|
| CI verde | ⬜ |
| Deploy staging OK | ⬜ |
| Smoke tests OK | ⬜ |
| Monitoreo OK | ⬜ |
| Validación funcional OK | ⬜ |
| Seguridad OK | ⬜ |

**Decisión final:** ___________________

**Fecha de Go/No-Go:** ___________________
