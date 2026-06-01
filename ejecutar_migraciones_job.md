# Comando para Ejecutar Migraciones en Cloud SQL usando Cloud Run Job

## Problema Detectado
- Error: `Connection refused` al socket de Cloud SQL
- Las migraciones no se ejecutaron automáticamente
- El servicio no puede conectarse a la base de datos

## Solución: Cloud Run Job

Ejecuta este comando en tu terminal local:

```powershell
gcloud run jobs create prislab-migrate-job `
  --image gcr.io/prislab-core-v5/cloud-run-source-deploy/prislab-core:latest `
  --region us-central1 `
  --add-cloudsql-instances prislab-core-v5:us-central1:prislab-db `
  --set-env-vars="SECRET_KEY=AytJ3jR2NMJAlb_WmcrNOzxfQGUhhbsbd618nk-J92MS2SAQTyWB92cY8jEUBHsao0Y,DEBUG=False,DB_HOST=/cloudsql/prislab-core-v5:us-central1:prislab-db,DB_NAME=prislab_db,DB_USER=postgres,DB_PASSWORD=Prislab2026!,DB_PORT=5432" `
  --command="python" `
  --args="manage.py,migrate,--noinput" `
  --max-retries=3 `
  --task-timeout=600
```

## Ejecutar el Job

Después de crear el job, ejecútalo:

```powershell
gcloud run jobs execute prislab-migrate-job --region us-central1
```

## Ver Logs del Job

```powershell
gcloud run jobs executions list --job prislab-migrate-job --region us-central1
gcloud logging read "resource.type=cloud_run_job AND resource.labels.job_name=prislab-migrate-job" --limit=50
```

## Limpiar (Opcional)

Después de ejecutar las migraciones exitosamente, puedes eliminar el job:

```powershell
gcloud run jobs delete prislab-migrate-job --region us-central1
```
