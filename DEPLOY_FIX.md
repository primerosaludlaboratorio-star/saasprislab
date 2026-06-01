# 🔧 Solución al Error de Build con Buildpacks

## Problema Identificado

Estás usando `gcloud run deploy --source .` que intenta usar **Buildpacks automáticos** de Google Cloud, pero estos pueden no detectar correctamente tu aplicación Django.

## Solución 1: Usar Dockerfile Explícitamente (RECOMENDADO)

En lugar de `--source .`, usa el Dockerfile directamente:

```bash
# Opción A: Usar Cloud Build (recomendado)
gcloud builds submit --config cloudbuild.yaml

# Opción B: Construir y desplegar manualmente
gcloud builds submit --tag gcr.io/elegant-device-477122-b5/prislab-farmacia

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

## Solución 2: Configurar Buildpacks Correctamente

Si prefieres usar `--source .`, he creado estos archivos para que Buildpacks funcione:

- ✅ `Procfile` - Define el comando de inicio
- ✅ `.runtimeconfig.json` - Especifica Python 3.11
- ✅ `app.yaml` - Configuración para App Engine (opcional)

**Comando con Buildpacks:**
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

## Ver Logs del Build Fallido

Para ver qué falló exactamente:

1. Ve a: https://console.cloud.google.com/cloud-build/builds?project=elegant-device-477122-b5
2. Busca el build con ID: `e0029a6f-6ddc-4e65-9dc5-5279c395be73`
3. O ejecuta en tu terminal:

```bash
gcloud builds log e0029a6f-6ddc-4e65-9dc5-5279c395be73
```

## Recomendación

**Usa la Solución 1 (Dockerfile)** porque:
- ✅ Tienes control total sobre el proceso de build
- ✅ Ya tienes un Dockerfile optimizado
- ✅ Es más predecible y confiable
- ✅ Puedes ver exactamente qué se está construyendo

## Comando Rápido (Copia y Pega)

```bash
gcloud builds submit --config cloudbuild.yaml
```

Este comando:
1. Construye la imagen usando tu Dockerfile
2. La sube a Container Registry
3. La despliega automáticamente en Cloud Run
