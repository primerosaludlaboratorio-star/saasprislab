# PRISLAB SaaS — Runbooks de Operación (SRE)

**Versión:** 1.0  
**Fecha:** 2026-07-09  
**Rama:** `release/v1.0-local`

---

## 1. Endpoints de salud y métricas

| Endpoint | Uso | Código esperado |
|----------|-----|-----------------|
| `/live/` | Liveness probe: ¿el proceso responde? | 200 |
| `/ready/` | Readiness probe: ¿DB y caché están OK? | 200 / 503 |
| `/health/` | Alias de `/ready/` | 200 / 503 |
| `/metrics/` | Métricas Prometheus (SRE) | 200 |

---

## 2. Runbook: Base de datos no disponible

### Síntomas
- `/ready/` retorna 503, componente `database=error`.
- Usuarios reportan error 500 en operaciones que escriben.
- Logs: `readiness_view: database no disponible`.

### Pasos
1. Verificar conectividad de red al host `DB_HOST`.
2. Revisar estado del contenedor/servicio PostgreSQL:
   ```bash
   docker compose ps db
   docker compose logs --tail 100 db
   ```
3. Si el contenedor está detenido, iniciarlo:
   ```bash
   docker compose up -d db
   ```
4. Si el volumen está corrupto, seguir el **Escenario A** de `docs/DR_PLAN.md`.
5. Validar `/ready/` hasta obtener 200.

### Escalación
- Si no se recupera en 30 minutos, activar failover por DR plan.

---

## 3. Runbook: Caché Redis no disponible

### Síntomas
- `/ready/` retorna 503, componente `cache=error`.
- Performance visiblemente degradada.

### Pasos
1. Verificar contenedor Redis:
   ```bash
   docker compose ps redis
   docker compose logs --tail 100 redis
   ```
2. Si Redis está caído, reiniciar:
   ```bash
   docker compose restart redis
   ```
3. Django tiene fallback a `LocMemCache`; no hay pérdida de datos críticos, pero pueden perderse sesiones distribuidas entre workers.
4. Validar `/ready/`.

---

## 4. Runbook: Picos de latencia HTTP

### Síntomas
- Alerta `SENTINEL_WARN_LATENCY_MS` > 800 ms.
- `/metrics/` muestra `prislab_request_duration_seconds_bucket` acumulado en buckets altos.

### Pasos
1. Revisar logs de Gunicorn: `journalctl -u prislab-gunicorn -f`.
2. Identificar endpoint lento con `core.middleware.performance.PerformanceMiddleware` logs.
3. Revisar cantidad de queries por request:
   ```python
   # Ejecutar localmente contra BD representativa
   python manage.py shell -c "from django.db import connection; ..."
   ```
4. Aplicar mitigaciones:
   - Activar caché en query pesada.
   - Añadir `select_related` / `prefetch_related`.
   - Escalar workers de Gunicorn temporalmente.

---

## 5. Runbook: Disco lleno en VPS

### Síntomas
- Backups fallan, media no se escribe, certbot falla.
- `df -h` muestra uso > 90 %.

### Pasos
1. Identificar carpetas grandes:
   ```bash
   du -h /opt/prislab/backups | sort -hr | head -n 20
   du -h /var/log | sort -hr | head -n 20
   ```
2. Aplicar retención de backups (`BACKUP_RETENTION_DAYS`).
3. Rotar logs con logrotate.
4. Liberar imágenes Docker no usadas:
   ```bash
   docker system prune -a --volumes
   ```

---

## 6. Runbook: Backup fallido

### Síntomas
- No hay backup nuevo en `/opt/prislab/backups`.
- Email/alerta de cron con error.
- Workflow `backup-restore-test` en GitHub falla.

### Pasos
1. Revisar log del cron:
   ```bash
   tail -n 200 /var/log/prislab_backup.log
   ```
2. Verificar credenciales `DB_PASSWORD` y `BACKUP_DIR`.
3. Ejecutar backup manual:
   ```bash
   docker compose exec -T app bash scripts/backup/backup_postgres.sh
   ```
4. Si persiste, revisar espacio en disco y permisos del volumen.
5. Ejecutar restore test después de recuperar.

---

## 7. Comandos de verificación rápida

```bash
# Salud completa
curl -s https://<dominio>/health/ | python -m json.tool
curl -s https://<dominio>/live/
curl -s https://<dominio>/ready/

# Métricas
curl -s https://<dominio>/metrics/ | head -n 40

# Estado de servicios systemd
systemctl status prislab-gunicorn prislab-celery prislab-celerybeat
```
