# 🚀 Instrucciones de Despliegue - Paso a Paso

## ⚠️ IMPORTANTE: Ejecutar desde el Directorio del Proyecto

El comando debe ejecutarse desde el directorio raíz de tu proyecto, NO desde el directorio de Google Cloud SDK.

## Paso 1: Navegar al Directorio del Proyecto

```bash
cd C:\Users\jonil\Desktop\PRISLAB_SaaS
```

## Paso 2: Verificar que los Archivos Estén Presentes

```bash
# Verificar que cloudbuild.yaml existe
dir cloudbuild.yaml

# Verificar que Dockerfile existe
dir Dockerfile

# Verificar que requirements.txt existe
dir requirements.txt
```

## Paso 3: Configurar el Proyecto de Google Cloud

```bash
gcloud config set project elegant-device-477122-b5
```

## Paso 4: Desplegar

```bash
gcloud builds submit --config cloudbuild.yaml
```

## Comando Completo (Todo en Uno)

```bash
cd C:\Users\jonil\Desktop\PRISLAB_SaaS && gcloud config set project elegant-device-477122-b5 && gcloud builds submit --config cloudbuild.yaml
```

## Si Prefieres Usar --source . (Buildpacks)

```bash
cd C:\Users\jonil\Desktop\PRISLAB_SaaS
gcloud run deploy prislab-farmacia \
    --source . \
    --region us-central1 \
    --allow-unauthenticated \
    --port 8080 \
    --memory 512Mi \
    --cpu 1 \
    --set-env-vars "DEBUG=False"
```

## Verificar Archivos Necesarios

Asegúrate de tener estos archivos en `C:\Users\jonil\Desktop\PRISLAB_SaaS\`:

- ✅ `cloudbuild.yaml`
- ✅ `Dockerfile`
- ✅ `requirements.txt`
- ✅ `manage.py`
- ✅ `entrypoint.sh`
- ✅ `Procfile` (para Buildpacks)
- ✅ `config/settings.py`
- ✅ `core/` (directorio con la aplicación)
