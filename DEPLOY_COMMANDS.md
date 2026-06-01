# 🚀 Comandos de Despliegue para PRISLAB

## Método 1: Usar Cloud Build (RECOMENDADO - Usa Dockerfile)

```bash
gcloud builds submit --config cloudbuild.yaml
```

Este es el método más confiable porque usa tu Dockerfile personalizado.

## Método 2: Construir y Desplegar Manualmente

```bash
# Paso 1: Construir la imagen
gcloud builds submit --tag gcr.io/elegant-device-477122-b5/prislab-farmacia

# Paso 2: Desplegar en Cloud Run
gcloud run deploy prislab-farmacia \
    --image gcr.io/elegant-device-477122-b5/prislab-farmacia \
    --region us-central1 \
    --platform managed \
    --allow-unauthenticated \
    --port 8080 \
    --memory 512Mi \
    --cpu 1 \
    --timeout 300 \
    --set-env-vars "DEBUG=False"
```

## Método 3: Usar Buildpacks (--source .)

Si quieres usar Buildpacks automáticos (ahora con archivos de configuración):

```bash
gcloud run deploy prislab-farmacia \
    --source . \
    --region us-central1 \
    --allow-unauthenticated \
    --port 8080 \
    --memory 512Mi \
    --cpu 1 \
    --set-env-vars "DEBUG=False"
```

## Ver Logs del Último Build

```bash
# Listar builds recientes
gcloud builds list --limit=5

# Ver logs de un build específico
gcloud builds log [BUILD_ID]
```

## Verificar el Despliegue

```bash
# Obtener la URL del servicio
gcloud run services describe prislab-farmacia \
    --region us-central1 \
    --format 'value(status.url)'

# Ver logs en tiempo real
gcloud run services logs read prislab-farmacia \
    --region us-central1 \
    --limit 50
```

## Configurar Variables de Entorno

```bash
gcloud run services update prislab-farmacia \
    --region us-central1 \
    --update-env-vars "DEBUG=False,GOOGLE_API_KEY=tu-api-key"
```

## Reiniciar el Servicio

```bash
gcloud run services update-traffic prislab-farmacia \
    --region us-central1 \
    --to-latest
```
