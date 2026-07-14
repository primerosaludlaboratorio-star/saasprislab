# Auditoría de Infraestructura — PRISLAB SaaS

**Auditoría:** AUD-20260713-210000  
**Rama:** `release/v1.0-local`  
**Commit:** `2b6e98360bd9edd74cd605e0c3a6aaadf47ef9f5`

---

## EV-INF-001 — Docker Compose de producción

**Criticidad:** ALTA  
**Archivo:** `docker-compose.yml`  
**Estado:** IMPLEMENTADO  
**Explicación:** Define servicios: PostgreSQL, Redis, Django app (Gunicorn), Nginx, Certbot. Incluye healthchecks, variables de entorno y volúmenes. Esquema estándar para Django SaaS en VPS.
**Riesgos:** Certbot en contenedor requiere mapeo correcto de puertos 80/443 y DNS funcional. Renew automático no verificado.

---

## EV-INF-002 — Stack de monitoreo

**Criticidad:** ALTA  
**Archivo:** `docker-compose.monitoring.yml`, `monitoring/prometheus/prometheus.yml`, `monitoring/alertmanager/alertmanager.yml`, `monitoring/grafana/provisioning/`, `monitoring/grafana/dashboards/prislab_sre.json`  
**Estado:** IMPLEMENTADO  
**Explicación:** Prometheus + Alertmanager + Grafana configurados. Scrape a `/metrics/`. Reglas de alerta para DB, cache, error rate y latencia. Dashboard SRE básico.
**Riesgos:** Configuración de SMTP en Alertmanager depende de variables no versionadas. No se verificó en ejecución por falta de Docker.

---

## EV-INF-003 — Pipeline de CI/CD

**Criticidad:** ALTA  
**Archivo:** `.github/workflows/main.yml`, `.github/workflows/deploy-vps.yml`, `.github/workflows/sre-health-check.yml`, `.github/workflows/backup-restore-test.yml`, `.github/workflows/secret-scan.yml`, `.github/workflows/sbom-audit.yml`  
**Estado:** IMPLEMENTADO  
**Explicación:**
- `main.yml`: lint, tests, migrations check, quality gate.
- `deploy-vps.yml`: deploy a VPS con smoke tests post-deploy.
- `sre-health-check.yml`: validación de endpoints /live/, /ready/, /metrics/.
- `backup-restore-test.yml`: prueba de backup/restore.
- `secret-scan.yml`: gitleaks.
- `sbom-audit.yml`: pip-audit + SBOM.
**Riesgos:** Workflows que requieren secretos (`DEPLOY_*`, `GITLEAKS_LICENSE`) fallarán si no están configurados.

---

## EV-INF-004 — Health checks de la aplicación

**Criticidad:** ALTA  
**Archivo:** `config/urls/core_views.py`  
**Estado:** IMPLEMENTADO  
**Explicación:** Endpoints `/live/` (liveness), `/ready/` (readiness con DB+cache), `/health/`, `/metrics/` (métricas Prometheus) expuestos.
**Riesgos:** `/metrics/` podría exponer información interna si no está protegido por red o autenticación. El workflow de deploy verifica que responda 200.

---

## EV-INF-005 — Dockerfile

**Criticidad:** MEDIA  
**Archivo:** `Dockerfile`  
**Estado:** IMPLEMENTADO  
**Explicación:** Python 3.12, dependencias del sistema (PostgreSQL client, WeasyPrint, Pillow), instalación de requirements, collectstatic. Uso de usuario no-root no verificado en este fragmento.
**Riesgos:** Imágenes con dependencias de sistema extensas aumentan superficie de ataque. WeasyPrint requiere librerías GTK.

---

## EV-INF-006 — Scripts de backup

**Criticidad:** MEDIA  
**Archivo:** `scripts/backup/backup_postgres.sh`, `scripts/backup/upload_to_drive.py`  
**Estado:** IMPLEMENTADO  
**Explicación:** Backup de PostgreSQL y opcional subida a Google Drive. El script legacy `backup_to_drive.py` fue eliminado en Fase 1.
**Riesgos:** Backup automático depende de cron/GitHub Actions; no se verificó en ejecución.

---

## EV-INF-007 — Nginx

**Criticidad:** MEDIA  
**Archivo:** `nginx/nginx.conf`, `nginx/prislab.conf`  
**Estado:** IMPLEMENTADO  
**Explicación:** Configuración de Nginx como reverse proxy con SSL, gzip, proxy headers. SSL gestionado por Certbot.
**Riesgos:** No se verificó la configuración de rate limiting en Nginx; el rate limiting parece estar en middleware Django.

---

## EV-INF-008 — Limitaciones de verificación local

**Criticidad:** INFORMATIVA  
**Archivo:** N/A  
**Estado:** NO EJECUTABLE EN ESTE ENTORNO  
**Explicación:** Docker no está disponible en el entorno de auditoría (Windows 11, PowerShell). No se puede levantar el stack completo ni validar health checks, monitoreo ni despliegue end-to-end.
**Evidencia:**
```
docker: The term 'docker' is not recognized as a name of a cmdlet, function, script file, or executable program.
```
