# Comandos para Ejecutar Migraciones en Cloud SQL

## ✅ Job Creado Exitosamente

El job `prislab-migrate-job` ya está creado y configurado con acceso a Cloud SQL.

## 🔧 Comandos para Ejecutar

### 1. Ejecutar Migraciones (migrate)

```powershell
gcloud run jobs execute prislab-migrate-job --region us-central1
```

### 2. Crear Migraciones (makemigrations) - Si es necesario

```powershell
gcloud run jobs execute prislab-makemigrations-job --region us-central1
```

### 3. Ver Logs del Job

```powershell
# Ver últimas ejecuciones
gcloud run jobs executions list --job prislab-migrate-job --region us-central1

# Ver logs detallados
gcloud logging read "resource.type=cloud_run_job AND resource.labels.job_name=prislab-migrate-job" --limit=50 --format="value(textPayload)"
```

## ⚠️ Problema Detectado

El servicio principal necesita acceso a Cloud SQL. Ya se agregó con:

```powershell
gcloud run services update prislab-core --region us-central1 --add-cloudsql-instances prislab-core-v5:us-central1:prislab-db
```

## 📋 Orden de Ejecución Recomendado

1. **Primero**: Ejecutar makemigrations (si hay cambios en modelos):
   ```powershell
   gcloud run jobs execute prislab-makemigrations-job --region us-central1
   ```

2. **Segundo**: Ejecutar migrate:
   ```powershell
   gcloud run jobs execute prislab-migrate-job --region us-central1
   ```

3. **Verificar**: Probar el login en el admin

## 🧹 Limpiar Jobs (Opcional)

Después de ejecutar las migraciones exitosamente:

```powershell
gcloud run jobs delete prislab-migrate-job --region us-central1
gcloud run jobs delete prislab-makemigrations-job --region us-central1
```
