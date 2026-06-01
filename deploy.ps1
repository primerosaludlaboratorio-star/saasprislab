# Script legacy: despliega solo prislab-farmacia desde fuente (buildpack).
# Despliegue completo unificado (prislab-saas + prislab-v5 + prislab-farmacia + Scheduler):
#   gcloud builds submit --config cloudbuild.yaml .
gcloud run deploy prislab-farmacia `
  --source . `
  --region us-central1 `
  --platform managed `
  --allow-unauthenticated `
  --port 8080 `
  --memory 2Gi `
  --cpu 2 `
  --timeout 300 `
  --max-instances 10 `
  --min-instances 0 `
  --add-cloudsql-instances "prislab-v5-ai:us-central1:prislab-db" `
  --update-secrets "DB_PASSWORD=db-password:latest" `
  --update-secrets "SECRET_KEY=django-secret-key:latest" `
  --update-secrets "GOOGLE_API_KEY=gemini-api-key:latest" `
  --update-secrets "DRIVE_FOLDER_ID=drive-folder-id:latest" `
  --update-secrets "VAPID_PRIVATE_KEY=vapid-private-key:latest" `
  --update-secrets "VAPID_PUBLIC_KEY=vapid-public-key:latest" `
  --set-env-vars "DEBUG=False" `
  --set-env-vars "DB_NAME=prislab_v5" `
  --set-env-vars "DB_USER=postgres" `
  --set-env-vars "DB_HOST=/cloudsql/prislab-v5-ai:us-central1:prislab-db" `
  --set-env-vars "GOOGLE_CLOUD_PROJECT=prislab-v5-ai"
