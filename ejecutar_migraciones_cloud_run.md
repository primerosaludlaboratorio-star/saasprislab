# Comandos para Ejecutar Migraciones en Cloud SQL

## Opción 1: Usando Cloud SQL Proxy (Recomendado para desarrollo local)

### Paso 1: Instalar Cloud SQL Proxy
```powershell
# Descargar Cloud SQL Proxy para Windows
# Desde: https://cloud.google.com/sql/docs/postgres/sql-proxy#install
# O usar Chocolatey:
choco install cloud-sql-proxy
```

### Paso 2: Iniciar Cloud SQL Proxy en una terminal separada
```powershell
# Conectar a Cloud SQL usando el proxy
cloud-sql-proxy.exe prislab-core-v5:us-central1:prislab-db --port 5432
```

### Paso 3: Ejecutar migraciones (en otra terminal)
```powershell
# Configurar variables de entorno
$env:DB_HOST = "127.0.0.1"
$env:DB_PORT = "5432"
$env:DB_NAME = "prislab_db"
$env:DB_USER = "postgres"
$env:DB_PASSWORD = "Prislab2026!"
$env:SECRET_KEY = "AytJ3jR2NMJAlb_WmcrNOzxfQGUhhbsbd618nk-J92MS2SAQTyWB92cY8jEUBHsao0Y"
$env:DEBUG = "False"

# Ejecutar migraciones
python manage.py migrate --noinput
```

## Opción 2: Ejecutar directamente en Cloud Run (Más rápido)

### Usando gcloud run jobs (Requiere imagen Docker)
```powershell
# Crear un job temporal para ejecutar migraciones
gcloud run jobs create prislab-migrate-temp `
  --image gcr.io/prislab-core-v5/cloud-run-source-deploy/prislab-core:latest `
  --region us-central1 `
  --set-env-vars="SECRET_KEY=AytJ3jR2NMJAlb_WmcrNOzxfQGUhhbsbd618nk-J92MS2SAQTyWB92cY8jEUBHsao0Y,DEBUG=False,DB_HOST=/cloudsql/prislab-core-v5:us-central1:prislab-db,DB_NAME=prislab_db,DB_USER=postgres,DB_PASSWORD=Prislab2026!,DB_PORT=5432" `
  --command="python" `
  --args="manage.py,migrate,--noinput"

# Ejecutar el job
gcloud run jobs execute prislab-migrate-temp --region us-central1

# Eliminar el job después de ejecutar
gcloud run jobs delete prislab-migrate-temp --region us-central1
```

## Opción 3: Modificar entrypoint.sh para forzar migraciones (Ya está configurado)

El `entrypoint.sh` ya ejecuta migraciones automáticamente al iniciar el contenedor. Si las migraciones no se están ejecutando, verifica los logs:

```powershell
gcloud run services logs read prislab-core --region=us-central1 --limit=100 | Select-String -Pattern "migrate|Migration|Applying|Creating|Error"
```

## Opción 4: Conectar directamente a Cloud SQL (Requiere IP autorizada)

```powershell
# Obtener la IP pública de tu máquina
$myIP = (Invoke-WebRequest -Uri "https://api.ipify.org").Content

# Autorizar tu IP en Cloud SQL (una sola vez)
gcloud sql instances patch prislab-db --authorized-networks=$myIP

# Configurar variables de entorno
$env:DB_HOST = "<IP_PUBLICA_DE_CLOUD_SQL>"
$env:DB_PORT = "5432"
$env:DB_NAME = "prislab_db"
$env:DB_USER = "postgres"
$env:DB_PASSWORD = "Prislab2026!"
$env:SECRET_KEY = "AytJ3jR2NMJAlb_WmcrNOzxfQGUhhbsbd618nk-J92MS2SAQTyWB92cY8jEUBHsao0Y"
$env:DEBUG = "False"

# Ejecutar migraciones
python manage.py migrate --noinput
```

## Verificar que las migraciones se aplicaron

```powershell
# Conectar a Cloud SQL y verificar tablas
gcloud sql connect prislab-db --user=postgres --database=prislab_db

# En PostgreSQL:
\dt core_*
# Deberías ver todas las tablas de core, incluyendo core_controlcalidad, core_tomamuestra, etc.
```
