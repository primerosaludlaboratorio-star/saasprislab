# PRISLAB SaaS — Plan de Recuperación ante Desastres (DR)

**Versión:** 1.0  
**Fecha:** 2026-07-09  
**Rama:** `release/v1.0-local`  
**Aplica a:** VPS Vultr Ubuntu 26.04 + Docker Compose

---

## 1. Objetivos de recuperación

| Métrica | Valor | Definición |
|---------|-------|------------|
| **RPO** | 6 horas | Máxima pérdida de datos aceptable. Backups automáticos cada 6h. |
| **RTO** | 4 horas | Tiempo máximo para restablecer el servicio en VPS alternativo. |
| **RTO crítico** | 1 hora | Restauración del mismo VPS si solo falló el contenedor de base de datos. |

---

## 2. Componentes protegidos

| Componente | Mecanismo de protección | Frecuencia |
|------------|------------------------|------------|
| Base de datos PostgreSQL | `pg_dump` formato custom + verificación `pg_restore -l` | Cada 6 horas |
| Archivos media (PDFs, firmas, imágenes) | Volumen Docker `media_data` + replica opcional a S3 | Continuo / snapshot diario |
| Archivos estáticos | `collectstatic` + volumen `static_data` | En cada deploy |
| Configuración y secretos | `.env` almacenado fuera del repositorio | Manual / por rotación |
| Redis (cache/sesiones) | Volumen `redis_data` (no crítico, reconstruible) | Reconstrucción en caliente |

---

## 3. Procedimiento de backup

### 3.1 Backup manual
```bash
cd /opt/prislab
docker compose exec -T app bash scripts/backup/backup_postgres.sh
```

### 3.2 Backup automatizado (crontab en host)
```cron
# PRISLAB backup cada 6 horas
0 */6 * * * cd /opt/prislab && docker compose exec -T app bash scripts/backup/backup_postgres.sh >> /var/log/prislab_backup.log 2>&1
```

### 3.3 Ubicación de backups
- Local: `/opt/prislab/backups` (host) o volumen equivalente.
- Remoto: `s3://<bucket>/backups/` si `S3_BACKUP_ENABLED=true`.
- Retención local: 30 días por defecto (`BACKUP_RETENTION_DAYS`).

---

## 4. Procedimiento de restore test

El restore test es **evidencia reproducible** de que los backups funcionan.

```bash
cd /opt/prislab
docker compose exec -T app bash scripts/backup/restore_test.sh
```

El script:
1. Selecciona el backup más reciente.
2. Crea una base `prislab_restore_test_<timestamp>`.
3. Restaura el backup con `pg_restore`.
4. Ejecuta consultas de verificación (`django_migrations`, `django_content_type`).
5. Elimina la base de prueba.

**Recomendación:** ejecutar al menos 1 vez por semana y guardar el output.

---

## 5. Escenarios de recuperación

### 5.1 Escenario A: Fallo del contenedor de base de datos

**RTO:** ~1 hora.

```bash
cd /opt/prislab
# 1. Detener servicios
docker compose down

# 2. Recrear volumen de postgres (solo si está corrupto)
docker volume rm prislab_postgres_data
docker compose up -d db

# 3. Esperar a que db esté healthy
# 4. Restaurar backup más reciente
LATEST=$(ls -t /opt/prislab/backups/prislab_*.dump | head -n 1)
docker compose exec -T db pg_restore \
  -U prislab_user -d prislab_v5 --clean --if-exists --no-owner --no-privileges < "${LATEST}"

# 5. Levantar app
docker compose up -d
```

### 5.2 Escenario B: Pérdida total del VPS

**RTO:** ~4 horas.

1. Preparar VPS de reemplazo con Ubuntu 26.04.
2. Instalar Docker, Docker Compose y awscli.
3. Clonar repositorio: `git clone -b release/v1.0-local <repo> /opt/prislab`.
4. Restaurar `.env` desde secret manager o copia segura.
5. Descargar backup más reciente desde S3:
   ```bash
   aws s3 cp s3://<bucket>/backups/<backup>.dump /opt/prislab/backups/
   ```
6. Ejecutar `bash scripts/deploy_vps.sh` o `docker compose up -d --build`.
7. Restaurar base de datos (ver Escenario A).
8. Verificar `/health/` y `/ready/`.

### 5.3 Escenario C: Corrupción lógica / rollback de datos

1. Identificar momento de la corrupción.
2. Restaurar el backup más reciente anterior a la corrupción.
3. Considerar impacto en datos generados entre el backup y el incidente.
4. Documentar causa raíz en bitácora de incidentes.

---

## 6. Runbooks de contacto y escalación

| Rol | Responsabilidad | Contacto |
|-----|-----------------|----------|
| CISO / Director | Decisión de failover, comunicación | `CISO_EMAIL` en `.env` |
| Operaciones SRE | Ejecución de restore y verificación | SRE on-call |
| Desarrollo | Corrección de causa raíz si aplica | Equipo de desarrollo |

---

## 7. Evidencia requerida para cierre del bloque

- [x] Script de backup automatizado con verificación.
- [x] Script de restore test automatizado.
- [x] Documento DR con RPO/RTO definidos.
- [ ] Ejecución exitosa de backup en producción al menos 1 vez.
- [ ] Ejecución exitosa de restore test al menos 1 vez.
- [ ] Backup replicado a S3 (opcional, recomendado).
- [ ] Crontab configurado en host de producción.
- [ ] Runbook de failover probado en staging.

---

## 8. Notas

- Los backups locales son volátiles si el VPS se pierde. **Recomendación fuerte:** habilitar `S3_BACKUP_ENABLED`.
- El restore test debe ejecutarse en un horario de baja carga para no afectar performance.
- Para cumplimiento COFEPRIS/LGPD, conservar evidencia de ejecución de backups y restore tests.
