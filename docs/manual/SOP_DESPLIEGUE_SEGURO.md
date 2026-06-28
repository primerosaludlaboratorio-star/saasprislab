# SOP — Despliegue seguro PRISLAB (GCP / Cloud Run)

Documento de referencia para salidas a producción. Complementa **`DOCS_AUDIT_MAESTRO.md`** (§6.15 / §6.16) y el **Quality Gate** en GitHub Actions (`.github/workflows/main.yml`).

---

## 0. Checklist ejecutivo (4 pasos antes de dar por cerrado un release)

| # | Paso | Acción |
| :---: | :--- | :--- |
| **1** | **Luz verde GitHub** | En el repo → **Actions** → workflow **PRISLAB Quality Gate** → última corrida en **éxito** (✅). Si el repo es privado, hace falta sesión en GitHub (la API pública no expone runs). |
| **2** | **Migración producción** | **Estándar de producción:** la **auto-migración en Cloud Run** vía **`scripts/cloudrun_web_entrypoint.sh`** (`python manage.py migrate --noinput` antes de gunicorn) en **cada nueva revisión**. Solo en emergencia documentada: **`PRISLAB_SKIP_MIGRATE_ON_STARTUP=1`** (diagnóstico; no rutina). **Manual (opcional):** proxy + `migrate --noinput` — ver **§6**. |
| **3** | **Cloud Build** | `gcloud builds submit --config cloudbuild.yaml .` desde la raíz del repo (proyecto autenticado). Ver **§7**. |
| **4** | **Humo en producción** | Con usuario real: (a) PDF de orden con **saldo pendiente** debe **bloquearse** (candado financiero); (b) resultado sugerido por **IA** debe quedar en **borrador** hasta **Validar** en captura (**`aprobado_por_humano`**, Punto 18). |

---

## 1. Checklist de secretos (GCP Secret Manager)

Antes de cualquier deploy que consuma Cloud Run + Cloud SQL, verificar que existen y están referenciados en **`cloudbuild.yaml`** / configuración del servicio:

| Secreto / variable | Uso resumido |
| :--- | :--- |
| `django-secret-key` / `SECRET_KEY` | Sesiones Django; obligatorio en cloud (no valor por defecto). |
| `fernet-key` / `FERNET_KEY` | Cifrado (backups, datos sensibles). |
| `db-password` / credenciales Cloud SQL | Conexión Postgres. |
| `gemini-api-key` / `GOOGLE_API_KEY` | IA (dictado, OCR, etc.). |
| `drive-folder-id` / carpeta Drive | Media si aplica. |
| `vapid-private-key`, `vapid-public-key` | Notificaciones web push. |
| `github-token`, `github-repo` | Sentinel / reportes (si activos). |
| `telegram-bot-token`, `telegram-ciso-chat-id` | Alertas CISO (si activas). |
| `lab-validation-pin` | PIN laboratorio (≥8 caracteres; no en variable plana en prod). |
| `e2e-user`, `e2e-pass` | Solo para el gate **omni** en Cloud Build (suite contra cloud). |

**Acción:** En consola GCP → Secret Manager → comprobar versiones **habilitadas** y que el servicio Cloud Run tiene **permiso** de lectura (IAM).

### 1.1 Advertencia operativa — Cloud Run y variables de entorno

Al actualizar un servicio con **`gcloud run services update`**, use **`--update-env-vars`** (o **`--update-secrets`**) para **añadir o cambiar** claves sin reemplazar el mapa completo. **`--set-env-vars`** sustituye **todas** las variables planas del servicio por el conjunto indicado; si omite una clave (p. ej. **`FERNET_KEY`**, **`DEBUG`**, **`GCS_BACKUP_BUCKET`**, **`PRISLAB_ESCUDO_USUARIO_ID`** montadas como env), esa variable **desaparece** de la revisión y puede dejar el servicio inoperable o inseguro. Ver también **§3**.

### 1.2 Inventario exhaustivo — variables leídas desde `config/settings.py`

Referencia única en código: **`config/settings.py`** (y **`config/drive_credentials.py`** para Drive). La tabla siguiente agrupa **`os.environ`** relevantes; no todo es secreto (p. ej. flags booleanos). En producción GCP, los secretos deben ir preferentemente a **Secret Manager** y montarse como env o archivo según **`cloudbuild.yaml`**.

| Variable / familia | Tipo | Uso resumido |
| :--- | :---: | :--- |
| **`SECRET_KEY`** | Secreto | Sesiones Django; obligatorio en nube. |
| **`FERNET_KEY`** | Secreto | Cifrado (campos sensibles, backups `.fernet`). |
| **`LAB_VALIDATION_PIN`** | Secreto | PIN validación laboratorio (≥8 en prod). |
| **`PRISLAB_ESCUDO_USUARIO_ID`** | Crítico | ID de usuario sistema (HL7 / escudo clínico / trazabilidad **`validado_por`** en interfaz). |
| **`DB_PASSWORD`**, **`DB_NAME`**, **`DB_USER`**, **`DB_HOST`**, **`DB_PORT`** | Secreto / config | Postgres (Cloud SQL o remoto). |
| **`CLOUD_SQL_CONNECTION_NAME`** | Config | Socket Unix Cloud SQL en Cloud Run. |
| **`GOOGLE_CLOUD_PROJECT`**, **`GAE_ENV`** | Config | Detección entorno nube (activa validaciones estrictas). |
| **`DEBUG`** | Config | Debe ser **`False`** en nube. |
| **`GOOGLE_API_KEY`** / **`GEMINI_API_KEY`** (si se mapea) | Secreto | IA (dictado, OCR, PRIS). |
| **`OPENAI_API_KEY`** | Secreto | Integraciones OpenAI si activas. |
| **`GITHUB_TOKEN`**, **`GITHUB_REPO`** | Secreto / config | Sentinel / reportes. |
| **`VULTR_OBJECT_STORAGE_ENABLED`** | Config | Activa el backend operativo de archivos en Vultr S3. |
| **`VULTR_S3_ACCESS_KEY_ID`**, **`VULTR_S3_SECRET_ACCESS_KEY`**, **`VULTR_S3_ENDPOINT_URL`**, **`VULTR_S3_BUCKET_NAME`** | Secreto / config | Credenciales y endpoint del almacenamiento operativo. |
| **Google Drive** | Legacy | Retirado del flujo activo. Los secretos Drive ya no deben montarse en producción. |
| **`GS_BUCKET_NAME`** | Config | GCS legacy / fallback media. |
| **`GCS_BACKUP_BUCKET`** | Config / DRP | Bucket destino **`backup_database`** (pg_dump cifrado). |
| **`EMAIL_HOST_USER`**, **`EMAIL_HOST_PASSWORD`**, **`EMAIL_HOST`**, **`EMAIL_PORT`**, **`EMAIL_USE_TLS`** | Secreto / config | SMTP. |
| **`DEFAULT_FROM_EMAIL`**, **`DIRECTOR_EMAIL`**, **`CISO_EMAIL`** | Config | Origen y alertas. |
| **`PRISLAB_MASTER_RECOVERY_CODE`** | Secreto | Bypass recuperación 2FA (CISO). |
| **`TELEGRAM_BOT_TOKEN`**, **`TELEGRAM_CISO_CHAT_ID`** | Secreto | Alertas Telegram. |
| **`VAPID_PRIVATE_KEY`**, **`VAPID_PUBLIC_KEY`** | Secreto | Web Push. |
| **`FACTURAMA_USER`**, **`FACTURAMA_PASSWORD`** | Secreto | CFDI (prod/sandbox según **`FACTURAMA_SANDBOX`**). |
| **`HL7_API_KEY`**, **`HL7_ALLOWED_IPS`**, **`HL7_ACTIVE`** | Secreto / config | Receptor analizadores. |
| **`PRISLAB_READ_ONLY`** | Config DRP | Solo lectura HTTP (**`ReadOnlyMiddleware`**). |
| **`PRISLAB_DEPLOYMENT_MODE`** | Config | p. ej. **`training_sandbox`**. |
| **`PRISLAB_SKIP_MIGRATE_ON_STARTUP`** | Config | Emergencia: omite migrate en entrypoint. |
| **`BACKUP_IMMUTABLE_LOG_AUTO`**, **`SYSTEM_MAINTENANCE_MODE`**, **`MAINTENANCE_MESSAGE`**, **`MAINTENANCE_ETA`** | Config | Backups WORM / modo mantenimiento. |
| **`REDIS_URL`** | Secreto / config | Caché, Channels, Celery broker. |
| **`IPS_INTERNAS_2FA_BYPASS`**, **`NOM024_ALERTA_ACCESOS_UMBRAL`** | Config | Seguridad acceso expediente. |
| **`ADMIN_IP_RESTRICTION_ENABLED`**, **`ALLOWED_ADMIN_IPS`**, **`ADMIN_GROUP_RESTRICTION_ENABLED`** | Config | Bastión `/admin/`. |
| **`SENTINEL_WARN_QUERY_COUNT`**, **`SENTINEL_WARN_LATENCY_MS`** | Config | Centinela ORM. |
| **`SESSION_COOKIE_AGE_SECONDS`**, **`SESSION_SHORT_COOKIE_AGE_SECONDS`** | Config | Sesión. |
| **`FARMACIA_DIAS_CADUCIDAD_CRITICO`**, **`FARMACIA_DIAS_CADUCIDAD_ALERTA`** | Config | Alertas farmacia. |
| **`ZEBRA_PRINTER_HOST`**, **`ZEBRA_PRINTER_PORT`**, **`THERMAL_PRINTER_HOST`**, **`THERMAL_PRINTER_PORT`** | Config | Impresoras red. |
| **`PWA_APP_NAME`**, **`PWA_APP_SHORT_NAME`** (y afines) | Config | PWA (sin secreto). |
| **`USE_MANIFEST_STORAGE`** | Config | Build estáticos / WhiteNoise. |

**Mantenimiento:** Tras añadir variables en **`settings.py`**, actualizar esta subsección y **`cloudbuild.yaml`** en el mismo PR cuando aplique a producción.

### 1.3 Rotación de `FERNET_KEY` (gobernanza CISO)

**Riesgo:** Los volcados **`backup_database`** (`.sql.fernet`) y datos cifrados en BD **no** son legibles sin la clave vigente en Secret Manager. Una sola clave mal custodiada equivale a pérdida de recuperación.

**Principios (alto nivel; el Programador documenta el runbook operativo en el ticket):**

1. **Generar** nueva clave (`Fernet.generate_key()`), versionar en Secret Manager como nueva versión del secreto `fernet-key` (o secreto de rotación según política interna).
2. **Ventana controlada:** planificar si se requiere re-cifrar artefactos antiguos o mantener lectura dual (vieja+nueva) durante un intervalo acotado; los backups históricos siguen necesitando la clave con la que se cifraron.
3. **Montaje en Cloud Run:** usar **`--update-secrets`** (no **`--set-env-vars`** masivo) para apuntar la revisión a la versión nueva del secreto.
4. **Verificación:** restaurar un backup de prueba en entorno aislado con la clave nueva antes de destruir la versión antigua del secreto.

**`GCS_BACKUP_BUCKET`:** Debe existir en el proyecto, con IAM del servicio que ejecuta **`backup_database`**, y figurar en variables del servicio o documentación de deploy (ver **`DRP_RUNBOOK_ACAYUCAN.md`**). Comprobar que **`cloudbuild.yaml`** / revisión Cloud Run no omiten esta variable si el DRP está activo.

---

## 2. Verificación de migraciones

1. En rama de release, ejecutar localmente (o en CI de staging) contra una BD representativa:
   - `python manage.py showmigrations` — sin `[ ]` pendientes no aplicados en el entorno objetivo.
   - `python manage.py migrate --plan` — revisar orden y dependencias.
2. **No** desplegar si hay migraciones conflictivas con producción (deuda documentada en **§9.1** del maestro).
3. **Producción (canónico):** cada despliegue que crea una **nueva revisión** de Cloud Run aplica el esquema al arranque del contenedor mediante **`scripts/cloudrun_web_entrypoint.sh`** (`migrate --noinput`). **`PRISLAB_SKIP_MIGRATE_ON_STARTUP=1`** queda reservado a incidentes (ticket + reversión planificada); **no** sustituye este flujo en operación normal.

---

## 3. Validación de `cloudbuild.yaml`

Ante cambios en el pipeline:

- **Orden de deploy:** secuencial **SaaS → v5 → farmacia** (evita `migrate` concurrente en Postgres).
- **Variables de entorno en Cloud Run:** para **añadir o cambiar** variables planas sin tocar el resto del servicio, usar **`gcloud run services update … --update-env-vars CLAVE=valor,CLAVE2=valor2`**. **`--set-env-vars`** sustituye **todo** el conjunto de variables planas del servicio: un uso incorrecto **borra** claves no incluidas en la cadena (p. ej. **`FERNET_KEY`**, **`DEBUG`**, URLs) y deja el servicio inconsistente o caído. **`--update-secrets`** sigue siendo el mecanismo adecuado para montar secretos desde Secret Manager sin reemplazar el mapa completo de env.
- **Mismo** esquema de secretos / Cloud SQL en los tres servicios cuando aplique (**`cloudbuild.yaml`** como referencia).
- **PASO 3 (omni-suite-gate):** si `ok:false`, el build aborta; revisar `tools/last_suite_summary.json`.
- **PASO 6 (smoke-test):** debe completar verificación HTTP de los servicios desplegados.

Revisar comentarios en cabecera de **`cloudbuild.yaml`** (lista de secretos y pasos 1–6).

---

## 4. Protocolo de humo (smoke) post-despliegue

Ejecutar **después** de que Cloud Build marque éxito y el tráfico apunte a la nueva revisión:

1. **Salud HTTP:** `GET` a la URL del servicio (p. ej. raíz o `/health/` si existe) → **200** y sin timeouts anómalos.
2. **Login staff:** una sesión de prueba con usuario de bajo riesgo (no datos reales de pacientes).
3. **Ruta crítica mínima:** según módulo desplegado (p. ej. laboratorio: listado de órdenes; farmacia: una consulta de stock de solo lectura).
4. **Logs:** Cloud Logging → filtrar `[prislab-entrypoint]` y errores **500** en los primeros 15–30 minutos.
5. **Rollback:** si falla humo o sube tasa de error, revertir revisión en Cloud Run o redeploy de imagen anterior **antes** de continuar cambios funcionales.

---

## 5. Branch protection (recomendado)

Configurar en GitHub para **`master`** / **`main`**:

- Prohibir **force push** y borrado de rama.
- Exigir **pull request** antes de merge.
- Exigir que pasen las comprobaciones (incl. **PRISLAB Quality Gate**).
- Opcional: revisión de al menos un revisor.

---

## 6. Migración crítica `core.0067` (Ética IA) en producción

La migración añade **`ResultadoParametro.aprobado_por_humano`**, amplía **`metodo_captura`** con **`IA_BORRADOR`** y hace backfill de filas ya validadas.

### 6.1 Camino recomendado (automático con el deploy)

La imagen que incluye **`core.0067`** al arrancar en Cloud Run ejecuta **`python manage.py migrate --noinput`** vía **`scripts/cloudrun_web_entrypoint.sh`**, salvo **`PRISLAB_SKIP_MIGRATE_ON_STARTUP=1`**.

**Orden seguro:** desplegar primero **solo `prislab-saas`** (o el flujo completo **`cloudbuild.yaml`**, que ya serializa **SaaS → v5 → farmacia**). La primera revisión que suba con el código v1.40 aplicará **`0067`** contra la base configurada en **`DB_NAME`**.

### 6.2 Migración explícita antes del tráfico (opcional)

Si el Programador exige aplicar el esquema **antes** de exponer la nueva revisión:

1. **Cloud SQL Auth Proxy** (o conexión privada equivalente) hacia la instancia **`prislab-v5-ai:us-central1:prislab-db`**.
2. Variables de entorno apuntando a Postgres de producción (**`DB_HOST=127.0.0.1`**, **`DB_NAME`**, **`DB_USER`**, **`DB_PASSWORD`**, sin **`GOOGLE_CLOUD_PROJECT`** en local si se usa SQLite por error — en este flujo debe usarse Postgres).
3. Desde la raíz del repo, con el mismo commit desplegado:

```bash
python manage.py migrate core 0067_resultadoparametro_ia_ethics_p18 --noinput
# o migración completa:
python manage.py migrate --noinput
```

4. Verificar: **`python manage.py showmigrations core`** → **`0067`** marcada con **`[X]`**.

---

## 7. Disparar `cloudbuild.yaml` (SaaS, v5, Farmacia)

Desde la raíz del repositorio, con **`gcloud`** autenticado y proyecto **`prislab-v5-ai`** (o el que corresponda):

```bash
gcloud config set project prislab-v5-ai
gcloud builds submit --config cloudbuild.yaml .
```

**Qué hace el pipeline:** build de imagen → push → **PASO 3 suite omni contra la URL actual de producción** → si **`ok:true`**, deploy secuencial **prislab-saas** → **prislab-v5** → **prislab-farmacia** → Scheduler → smoke HTTP.

**Si el gate omni falla:** el build aborta y **no** se actualizan servicios; revisar logs del step **`omni-suite-gate`** y **`tools/last_suite_summary.json`**.

**Build en segundo plano (solo obtiene ID):**

```bash
gcloud builds submit --config cloudbuild.yaml . --async
```

Seguimiento: **Cloud Console → Cloud Build → Historial** o `gcloud builds log <BUILD_ID> --stream`.

### 7.1 Cloud Scheduler — jobs obligatorios (producción)

El paso **`setup-scheduler`** de **`cloudbuild.yaml`** crea o actualiza estos jobs contra la URL de **`prislab-saas`** (`us-central1`). **No** eliminarlos ni dejarlos pausados sin acta: la operación clínica y de inventario depende de ellos.

| Job (nombre GCP) | Ruta HTTP (POST) | Propósito |
| :--- | :--- | :--- |
| **`prislab-check-stock-critico`** | `/cron/check-stock-critico/` | Agregación de stock bajo mínimo (silos); alertas a War Room / director. |
| **`prislab-verify-escudo-clinico`** | `/cron/verify-escudo-clinico/` | Comprobación periódica de **`PRISLAB_ESCUDO_USUARIO_ID`** y escudo clínico LIMS. |
| **`prislab-check-metrologia`** | `/cron/check-metrologia/` | Certificados / metrología próximos a vencer (ISO 15189). |

**Verificación:** Consola GCP → **Cloud Scheduler** → estado **ENABLED** y últimas ejecuciones sin error. Los horarios vigentes están en **`cloudbuild.yaml`** (zona **`America/Mexico_City`**).

---

## 8. Cuarto servicio: Cloud Run **Sandbox** (`training_sandbox`)

Objetivo: misma **imagen** que producción, **base de datos Postgres distinta** y **`PRISLAB_DEPLOYMENT_MODE=training_sandbox`** (banner sandbox, Telegram suprimido, Facturama forzado a sandbox en código).

### 8.1 Prerrequisitos en Cloud SQL

1. Crear base dedicada, p. ej. **`prislab_sandbox`** (misma instancia **`prislab-db`** o instancia nueva según política de aislamiento).
2. Otorgar privilegios al usuario **`prislab_user`** (o usuario sandbox dedicado).
3. **Secretos recomendados** en Secret Manager (no reutilizar llaves de producción):
   - `sandbox-secret-key`, `sandbox-fernet-key`, opcionalmente credenciales **Facturama solo de pruebas** si se montan como secretos aparte.

### 8.2 Primera migración sobre la BD sandbox

Con proxy o job one-shot contra **`DB_NAME=prislab_sandbox`**:

```bash
python manage.py migrate --noinput
```

### 8.3 Deploy de `prislab-sandbox` (plantilla)

Ajustar nombres de secretos y URL de imagen a la **última** construida por Cloud Build (**`:latest`** o **`:${BUILD_ID}`**).

```bash
gcloud run deploy prislab-sandbox \
  --image gcr.io/prislab-v5-ai/prislab-v5:latest \
  --region us-central1 \
  --platform managed \
  --allow-unauthenticated \
  --port 8080 \
  --memory 2Gi \
  --cpu 1 \
  --min-instances 0 \
  --max-instances 3 \
  --timeout 300 \
  --add-cloudsql-instances prislab-v5-ai:us-central1:prislab-db \
  --set-env-vars "\
DEBUG=False,\
GOOGLE_CLOUD_PROJECT=prislab-v5-ai,\
CLOUD_SQL_CONNECTION_NAME=prislab-v5-ai:us-central1:prislab-db,\
DB_NAME=prislab_sandbox,\
DB_USER=prislab_user,\
PRISLAB_DEPLOYMENT_MODE=training_sandbox,\
GS_BUCKET_NAME=prislab-v5-media,\
GUNICORN_WORKERS=2,\
GUNICORN_THREADS=4,\
GITHUB_REPO=primerosaludlaboratorio-star/PRISLAB_SaaS,\
PRISLAB_SKIP_HEAVY_STARTUP=true,\
PRISLAB_ESCUDO_USUARIO_ID=1" \
  --update-secrets "\
SECRET_KEY=sandbox-secret-key:latest,\
DB_PASSWORD=db-password:latest,\
GEMINI_API_KEY=gemini-api-key:latest,\
GOOGLE_API_KEY=gemini-api-key:latest,\
DRIVE_FOLDER_ID=drive-folder-id:latest,\
VAPID_PRIVATE_KEY=vapid-private-key:latest,\
VAPID_PUBLIC_KEY=vapid-public-key:latest,\
GITHUB_TOKEN=github-token:latest,\
FERNET_KEY=sandbox-fernet-key:latest,\
TELEGRAM_BOT_TOKEN=telegram-bot-token:latest,\
TELEGRAM_CISO_CHAT_ID=telegram-ciso-chat-id:latest,\
LAB_VALIDATION_PIN=lab-validation-pin:latest"
```

**Notas:**

- **`PRISLAB_DEPLOYMENT_MODE=training_sandbox`** es la variable “mágica” del Punto 23.
- Para **máximo aislamiento**, use secretos sandbox y credenciales Facturama de **solo prueba**; en código, **`IS_SANDBOX`** ya fuerza **`FACTURAMA_SANDBOX=True`**.
- **Perímetro:** valorar **`--no-allow-unauthenticated`** + **IAP** o lista de invocadores, para que el simulador no sea público en Internet.
- Este servicio **no** está en **`cloudbuild.yaml`**; conviene desplegarlo **después** de tener una imagen reciente (**§7**) o fijar digest de imagen auditada.

---

## 9. Checklist Go-Live (configurado vs pendiente en producción)

| Área | Estado típico en prod | Acción |
| :--- | :--- | :--- |
| **DRP / backups** | **`GCS_BACKUP_BUCKET=prislab-drp-backups`** en los **tres** servicios Cloud Run + IAM de escritura | Incluido en **`cloudbuild.yaml`** y aplicable con **`gcloud run services update --update-env-vars`**. |
| **HL7** | **`HL7_ACTIVE=False`** hasta cablear analizador; luego **`True`** + **`HL7_ALLOWED_IPS`** + **`HL7_API_KEY`** (variable o secreto) | Por defecto **apagado** en pipeline; encender cuando el equipo esté en red. |
| **Bastión `/admin/`** | **`ADMIN_*` en `False`** hasta definir allowlist | Activar **`ADMIN_IP_RESTRICTION_ENABLED`** / **`ADMIN_GROUP_RESTRICTION_ENABLED`** cuando exista grupo **`ADMIN_SISTEMA`** e IPs fijas. |
| **CFDI / costos fiscales** | **`FACTURAMA_SANDBOX=True`** en pipeline (timbrado de prueba) | Para producción fiscal: **`FACTURAMA_SANDBOX=False`** + secretos **`FACTURAMA_USER`** / **`FACTURAMA_PASSWORD`** (montar vía Secret Manager y **`--update-secrets`**). |
| **Catálogo LIMS / precios** | Datos de negocio | Tras migraciones OK: **`ensamblar_lims_v75`**, import de precios/convenios según runbook interno (no automatizado en Cloud Build). |
| **Pruebas de laboratorio (costos)** | Tablas y políticas en BD | Configurar en **Django Admin** / módulos LIMS (convenios, listas de precios); verificar captura y cotización en humo **§4**. |
| **Sentinel / ruido** | Pre primer paciente real | **`python manage.py sentinel_amnistia_pre_produccion`** contra Postgres de prod (ver maestro **§9.22**). |
| **Impresoras / equipos físicos** | **Pendiente operativo** | **`ZEBRA_PRINTER_HOST`**, **`THERMAL_PRINTER_HOST`**, equipos HL7 en IP real, metrología en campo — configurar en sitio; **no** fijar en repo. |

**Migración `core.0073`:** si en Postgres la columna **`estudio_id`** ya fue retirada por **`0069`**, la versión idempotente de **`0073`** usa **`DROP COLUMN IF EXISTS`** para no bloquear el entrypoint.

---

**Versión SOP:** Punto 20 + Punto 23 + **§0** checklist ejecutivo + **§1.1–§1.3** + auto-migración entrypoint + **`--update-env-vars`** vs **`--set-env-vars`** + **§7.1** Scheduler + migración **0067** + Cloud Build + sandbox (**§8**) + **§9** Go-Live (DRP/HL7/Admin/Facturama en **`cloudbuild.yaml`**, **`core.0073`** idempotente). Actualizar cuando cambien secretos, `cloudbuild.yaml` o nombres de BD/servicio.
