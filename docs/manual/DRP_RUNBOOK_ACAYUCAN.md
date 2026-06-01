# DRP — Runbook de resurrección (Acayucan / PRISLAB SaaS)

**Versión:** 1.2 (v8.5 §2.4 bypass tenant + `audit_tenant_readiness`)  
**Auditoría:** `docs/audit/DOCS_AUDIT_MAESTRO.md` §9.4  
**Audiencia:** Ingeniero en turno con acceso a GCP (proyecto **prislab-v5-ai** u homólogo) y Secret Manager.

Este documento es un **extintor de incendios**: comandos pensados para copiar y pegar en **Cloud Shell** o terminal con `gcloud` autenticado. Sustituir placeholders `<...>` por valores reales de su entorno.

---

## 0. Metadatos y alcance

| Campo | Valor canónico (referencia repo) |
| :--- | :--- |
| Proyecto GCP (ejemplo) | `prislab-v5-ai` |
| Región primaria actual | `us-central1` |
| Instancia Cloud SQL (ejemplo) | `prislab-v5-ai:us-central1:prislab-db` |
| Imagen contenedor | `gcr.io/PROJECT_ID/prislab-v5:latest` (o tag de build) |
| Servicios Cloud Run | `prislab-saas`, `prislab-v5`, `prislab-farmacia` |

**Supuestos:** PostgreSQL en Cloud SQL, misma imagen Docker para los tres servicios, secretos en **Secret Manager** según `cloudbuild.yaml`.

---

## 1. Declaración de incidente

Activar DRP si ocurre alguno de:

- Región primaria indisponible (Cloud Run / Cloud SQL).
- Pérdida de integridad de datos o sospecha de ransomware.
- Restauración obligatoria desde backup inmutable (huella en `core_backupinmutablelog`).

**Comunicación:** avisar a dirección clínica y TI; activar **solo lectura** (§2) antes de exponer tráfico si hay riesgo de corrupción adicional.

---

## 2. Modo inmediato — Búnker (solo lectura)

**Objetivo:** permitir **GET** (consulta de historiales, listados) y bloquear **cualquier mutación** salvo login/logout/2FA.

### 2.1 Activar (Cloud Run — los 3 servicios)

```bash
export PROJECT_ID=prislab-v5-ai
export REGION=us-central1

for SVC in prislab-saas prislab-v5 prislab-farmacia; do
  gcloud run services update "$SVC" \
    --project "$PROJECT_ID" \
    --region "$REGION" \
    --update-env-vars PRISLAB_READ_ONLY=1
done
```

### 2.2 Desactivar (volver a escritura)

```bash
for SVC in prislab-saas prislab-v5 prislab-farmacia; do
  gcloud run services update "$SVC" \
    --project "$PROJECT_ID" \
    --region "$REGION" \
    --remove-env-vars PRISLAB_READ_ONLY
done
```

**Nota:** `gcloud run services update --set-env-vars` **reemplaza** el conjunto completo de variables planas si se usa mal. Para añadir solo una variable use `--update-env-vars` como arriba, o edite el YAML del servicio con cuidado.

### 2.3 Modelo de amenaza — capa HTTP vs trabajos en segundo plano

**`PRISLAB_READ_ONLY=1`** activa **`ReadOnlyMiddleware`**: bloquea **mutaciones vía HTTP** (POST/PUT/PATCH/DELETE salvo excepciones documentadas en el middleware: login, logout, 2FA, etc.). Eso **no** detiene por sí mismo:

- Workers o hilos ya en ejecución dentro de un request que terminó.
- Tareas **asíncronas** o procesos externos (p. ej. Cloud Scheduler que invoca `/cron/...`, jobs de sincronización, colas) que **no** pasan por el mismo middleware de petición de usuario.

**Comportamiento esperado en modo búnker:** la superficie **web** queda en solo lectura para operadores; los **cron** y otros invocadores pueden seguir ejecutando escrituras si sus rutas están exentas o no usan el middleware de la misma forma. Si el incidente exige **congelar también** escrituras por cron o por servicios internos, documentar medidas adicionales (deshabilitar Scheduler, feature flags, o cambios de configuración específicos) en el ticket del incidente — no se asume que el búnker las cubre automáticamente.

**Variables relacionadas (referencia `config/settings.py` y `cloudbuild.yaml`):**

| Variable | Rol |
| :--- | :--- |
| `PRISLAB_READ_ONLY` | `1` / `true` → kill switch estricto (`ReadOnlyMiddleware`). |
| `SYSTEM_MAINTENANCE_MODE` | Modo mantenimiento distinto (503, exenciones admin); no sustituye al búnker DRP. |
| `DEBUG` | Debe ser `False` en nube (`cloudbuild` ya fija `DEBUG=False`). |

### 2.4 Bypass de emergencia — filtro tenant ORM (v8.5 Fase 0)

**Objetivo:** si el blindaje multi-tenant o una migración bloquea la operación, **sin reinstalar** la aplicación, relajar temporalmente el filtro `TenantManager` (los `QuerySet` ven datos de **todas** las empresas mientras el bypass esté activo).

**Riesgo:** fuga de datos entre clientes SaaS si se deja activo. Usar solo en incidente; auditar logs (`CRITICAL` en `core.middleware.empresa`).

**Activación (Cloud Run — repetir por servicio):**

```bash
export PROJECT_ID=<PROJECT>
export REGION=<REGION>

for SVC in prislab-saas prislab-v5 prislab-farmacia; do
  gcloud run services update "$SVC" \
    --project "$PROJECT_ID" \
    --region "$REGION" \
    --update-env-vars PRISLAB_EMERGENCY_TENANT_BYPASS=1
done
```

**Desactivación (volver a aislamiento normal):**

```bash
for SVC in prislab-saas prislab-v5 prislab-farmacia; do
  gcloud run services update "$SVC" \
    --project "$PROJECT_ID" \
    --region "$REGION" \
    --remove-env-vars PRISLAB_EMERGENCY_TENANT_BYPASS
done
```

**Implementación:** `core.middleware.empresa.EmpresaIdentityMiddleware` llama a `set_tenant_bypass(True)` cuando la variable es verdadera (`1`, `true`, `yes`, `on`) y la restablece en `finally` por request.

**Gate operativo:** antes de considerar el entorno “listo” para Fase 1, ejecutar `python manage.py audit_tenant_readiness` y obtener **RESULTADO: VERDE** (sin migraciones pendientes ni filas `empresa_id` NULL en modelos tenant obligatorios).

### 2.5 Fase 0 Sprint 1 — LIMS, mantenimiento y `core` (referencia auditoría)

- **LIMS (`lims`):** la app **sí tiene migraciones propias** en `lims/migrations/` (`0001_initial` … `0008_tenant_empresa_row_isolation`). Los modelos viven en `lims/models.py` y enlazan a `core.Empresa`. La cadena **0007b → amnistía → 0008** evita el rollback atómico que dejaba columnas inexistentes: **`0007b_empresa_nullable_lims`** crea `empresa_id` nullable en `lims_analito`, `lims_perfillims`, `lims_paquetelims`, `lims_precioitem`; luego **`python manage.py lims_amnistia_empresa`** (con `--empresa-id` o `--confirmar-multi-tenant` según política) asigna la empresa principal a huérfanos; por último **`0008`** ejecuta el `RunPython` de comprobación y el `ALTER` a `NOT NULL`. El semáforo `audit_tenant_readiness` sigue exigiendo migraciones aplicadas: no se debilita el fallo de `0008` si quedan NULL.
- **Mantenimiento (`mantenimiento`):** una sola migración inicial `0001_cmms_v8_2_inicial.py` con dependencias explícitas (`core`, `laboratorio`, etc.). Saneamiento: validar orden de aplicación y que `showmigrations mantenimiento` esté `[X]` antes de profundizar en `core`.
- **`core`:** cadena más larga de migraciones; analizar **al final** del Sprint 0 (sin squash en caliente). Priorizar coherencia `empresa_id` y dependencias `lims` ↔ `core` (p. ej. `0073` / `0074`).

---

## 3. Inventario de artefactos a recuperar

1. **Último volcado cifrado:** objeto en `gs://<GCS_BACKUP_BUCKET>/...` generado por `python manage.py backup_database` (extensión `.sql.fernet`).
2. **Huella WORM:** tabla `core_backupinmutablelog`, campo `sha256_manifest` (64 hex) debe coincidir con hash **del SQL en claro** antes de cifrar.
3. **Secretos** (nombres en Secret Manager según `cloudbuild.yaml`):  
   `django-secret-key`, `db-password`, `fernet-key`, `gemini-api-key`, `drive-folder-id`, `vapid-private-key`, `vapid-public-key`, `github-token`, `telegram-bot-token`, `telegram-ciso-chat-id`, `omni-bypass-token`, `e2e-pass` (como `PRISLAB_INIT_ADMIN_PASSWORD`), `lab-validation-pin`.
4. **Variables planas** desplegadas hoy (ejemplo en `cloudbuild.yaml`):  
   `GOOGLE_CLOUD_PROJECT`, `CLOUD_SQL_CONNECTION_NAME`, `DB_NAME`, `DB_USER`, `GS_BUCKET_NAME`, `GUNICORN_WORKERS`, `GUNICORN_THREADS`, `GITHUB_REPO`, `PRISLAB_SKIP_HEAVY_STARTUP`, `PRISLAB_ESCUDO_USUARIO_ID`.

**Definir para backups:** `GCS_BACKUP_BUCKET` (bucket dedicado, distinto de `GS_BUCKET_NAME` / media). Añadir a `--set-env-vars` en el próximo deploy o vía `gcloud run services update`.

---

## 4. Restauración de base de datos (PostgreSQL)

### 4.1 Descargar objeto cifrado desde GCS

```bash
export BUCKET=<GCS_BACKUP_BUCKET>
export OBJECT=pgdump/2026/04/02/prislab_prislab_v5_YYYYMMDD_HHMMSS.sql.fernet

gcloud storage cp "gs://${BUCKET}/${OBJECT}" ./dump.sql.fernet
```

### 4.2 Descifrar (requiere misma `FERNET_KEY` que en producción)

```bash
# Obtener clave (ejemplo: imprimir a stdout en Cloud Shell — no guardar en historial compartido)
gcloud secrets versions access latest --secret=fernet-key --project=$PROJECT_ID > /tmp/fernet.key
chmod 600 /tmp/fernet.key

python3 << 'PY'
from pathlib import Path
from cryptography.fernet import Fernet
key = Path("/tmp/fernet.key").read_text().strip().encode()
f = Fernet(key)
enc = Path("dump.sql.fernet").read_bytes()
Path("dump_plain.sql").write_bytes(f.decrypt(enc))
print("OK: dump_plain.sql")
PY
```

Calcule SHA-256 del plano y compárelo con `core_backupinmutablelog.sha256_manifest`:

```bash
sha256sum dump_plain.sql
# Linux/macOS Cloud Shell: sha256sum; otros: shasum -a 256
```

### 4.3 Restaurar en instancia nueva (región objetivo, ej. us-east1)

1. Crear instancia Cloud SQL PostgreSQL en **us-east1** (consola GCP o `gcloud sql instances create ...`).
2. Crear base `DB_NAME` (ej. `prislab_v5`) y usuario `DB_USER` con contraseña almacenada en Secret `db-password`.
3. Importar:

```bash
# Si Cloud SQL acepta import desde GCS, suba dump_plain.sql a un bucket temporal y use "Import" en consola,
# o use psql desde una VM / Cloud Run Job con conectividad a la IP privada:

export PGPASSWORD='<db-password>'
psql -h <HOST_O_IP_SQL> -U prislab_user -d prislab_v5 -f dump_plain.sql
```

**Cloud SQL Auth Proxy (recomendado en recuperación):**

```bash
cloud-sql-proxy PROJECT_ID:REGION:INSTANCE_NAME --port 5432 &
export PGPASSWORD='...'
psql -h 127.0.0.1 -p 5432 -U prislab_user -d prislab_v5 -f dump_plain.sql
```

### 4.3.1 Migraciones Django tras restore (obligatorio)

Un backup restaurado puede tener el **esquema en un punto histórico** distinto al **código** que se va a ejecutar. Sin alinear migraciones, la aplicación puede fallar al arrancar (columnas faltantes, p. ej. ética IA **`aprobado_por_humano`** / **`IA_BORRADOR`** en **`core.0067_resultadoparametro_ia_ethics_p18`**).

**Procedimiento (con el mismo commit/tag de imagen que desplegará):**

1. Exportar variables **`DB_*`** (o proxy **`127.0.0.1`**) apuntando a la **base ya restaurada**.
2. Ejecutar:

```bash
python manage.py migrate --noinput
python manage.py showmigrations core | tail -n 5
```

3. Confirmar que **`core.0067`** (y dependencias previas de la cadena) aparecen aplicadas **`[X]`** antes de abrir tráfico o dar por cerrado el RTO.

**Alternativa:** la primera revisión Cloud Run con **`scripts/cloudrun_web_entrypoint.sh`** corre **`migrate --noinput`** al arrancar; aun así, en DRP conviene validar **`showmigrations`** en un entorno de control tras el restore.

### 4.4 Conmutación de conexión para Cloud Run

Actualizar en **los tres** servicios:

- `CLOUD_SQL_CONNECTION_NAME` → nueva instancia `PROJECT:us-east1:nueva-instancia`.
- Secreto `db-password` si cambió la contraseña.
- Mantener `--add-cloudsql-instances` en deploy apuntando a la nueva instancia.

---

## 5. Despliegue de los 3 servicios Cloud Run en región alternativa

### 5.1 Plantilla mínima (ajustar imagen y secretos)

Variables **idénticas** a `cloudbuild.yaml` (pasos `deploy-prislab-saas`, `deploy-prislab-v5`, `deploy-prislab-farmacia`), cambiando solo `--region`:

```bash
export PROJECT_ID=prislab-v5-ai
export REGION=us-east1
export IMAGE="gcr.io/${PROJECT_ID}/prislab-v5:latest"
export SQL_CONN="<PROJECT_ID>:${REGION}:<NUEVA_INSTANCIA_SQL>"

gcloud run deploy prislab-saas \
  --project "$PROJECT_ID" \
  --region "$REGION" \
  --image "$IMAGE" \
  --platform managed \
  --allow-unauthenticated \
  --port 8080 \
  --memory 4Gi \
  --cpu 2 \
  --add-cloudsql-instances "$SQL_CONN" \
  --set-env-vars "DEBUG=False,GOOGLE_CLOUD_PROJECT=${PROJECT_ID},CLOUD_SQL_CONNECTION_NAME=${SQL_CONN},DB_NAME=prislab_v5,DB_USER=prislab_user,GS_BUCKET_NAME=prislab-v5-media,GUNICORN_WORKERS=2,GUNICORN_THREADS=4,GITHUB_REPO=primerosaludlaboratorio-star/PRISLAB_SaaS,PRISLAB_SKIP_HEAVY_STARTUP=true,PRISLAB_ESCUDO_USUARIO_ID=1" \
  --update-secrets "SECRET_KEY=django-secret-key:latest,DB_PASSWORD=db-password:latest,GEMINI_API_KEY=gemini-api-key:latest,GOOGLE_API_KEY=gemini-api-key:latest,DRIVE_FOLDER_ID=drive-folder-id:latest,VAPID_PRIVATE_KEY=vapid-private-key:latest,VAPID_PUBLIC_KEY=vapid-public-key:latest,GITHUB_TOKEN=github-token:latest,FERNET_KEY=fernet-key:latest,TELEGRAM_BOT_TOKEN=telegram-bot-token:latest,TELEGRAM_CISO_CHAT_ID=telegram-ciso-chat-id:latest,OMNI_BYPASS_TOKEN=omni-bypass-token:latest,PRISLAB_INIT_ADMIN_PASSWORD=e2e-pass:latest,LAB_VALIDATION_PIN=lab-validation-pin:latest"
```

Repita el mismo bloque para `prislab-v5` y `prislab-farmacia` (en `cloudbuild`, `prislab-saas` usa `min-instances=1`; v5 y farmacia `min-instances=0` — añada esos flags si los necesita).

### 5.2 DNS y tráfico

- Actualice **mapeo de dominio** o **Load Balancer** hacia las nuevas URLs `*.run.app` de **us-east1**.
- Revise certificados SSL y **TTL** DNS antes del cutover.

### 5.3 Verificación

```bash
curl -sS -o /dev/null -w "%{http_code}" "https://<URL_SAAS>/login/"
```

Login manual, abrir expediente en solo lectura, confirmar que `PRISLAB_READ_ONLY` está alineado con el estado del incidente.

---

## 6. Backup on-demand (antes o después del evento)

En un entorno con **PostgreSQL** y herramientas cliente:

```bash
export GCS_BACKUP_BUCKET=<su_bucket_dr>
export FERNET_KEY=<misma_que_secret_fernet-key>
cd /ruta/PRISLAB_SaaS
python manage.py backup_database
```

Opciones:

- `--prefix prislab-dr/manual` — carpeta lógica dentro del bucket.
- `--dry-run` — solo `pg_dump` + SHA-256, sin subir.

**Scheduler (opcional):** Cloud Scheduler → Cloud Run Job o VM con servicio account que ejecute el comando y suba a `GCS_BACKUP_BUCKET`.

---

## 7. Lecciones aprendidas (plantilla)

- Fecha / duración del incidente.  
- Causa raíz.  
- Tiempo hasta activación de `PRISLAB_READ_ONLY`.  
- Tiempo hasta RTO (servicio mínimo) y RPO (datos perdidos).  
- Acciones para evitar repetición.

---

## Anexos

### A. Variables de entorno (resumen)

| Variable | Origen típico | Uso |
| :--- | :--- | :--- |
| `DB_NAME` | plana | Nombre base PostgreSQL (`prislab_v5`). |
| `DB_USER` | plana | Usuario SQL (`prislab_user`). |
| `DB_PASSWORD` | Secret `db-password` | Contraseña SQL. |
| `DB_HOST` | plana / socket | En Cloud Run: socket `/cloudsql/CONN_NAME`. |
| `CLOUD_SQL_CONNECTION_NAME` | plana | `project:region:instance`. |
| `SECRET_KEY` | Secret | Django. |
| `FERNET_KEY` | Secret | Cifrado de campos y backups `backup_database`. |
| `PRISLAB_ESCUDO_USUARIO_ID` | plana | ID usuario sistema (HL7 / escudo). |
| `GS_BUCKET_NAME` | plana | Media Django (no confundir con DR). |
| `GCS_BACKUP_BUCKET` | plana (añadir) | Solo volcados `backup_database`. |
| `PRISLAB_READ_ONLY` | plana | `1` = búnker. |
| `PRISLAB_EMERGENCY_TENANT_BYPASS` | plana | `1` = desactiva filtro ORM por tenant (incidente; v8.5). |

### B. Comando útil — listar revisiones actuales

```bash
gcloud run services describe prislab-saas --region us-central1 --format='value(status.latestReadyRevisionName)'
```

### C. Referencias de código

- Middleware: `core/middleware/read_only.py`  
- Comando: `core/management/commands/backup_database.py`  
- Comando: `core/management/commands/audit_tenant_readiness.py` (gate Fase 0 / Fase 1)  
- WORM: `core.models.BackupInmutableLog`  
- Deploy secuencial: `cloudbuild.yaml` (evita `migrate` concurrente en Postgres)

---

**Fin del runbook.** Mantener este archivo actualizado cuando cambien nombres de secretos, región primaria o imagen base.
