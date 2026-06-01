# Configurar GOOGLE_API_KEY en Cloud Run

## Opción 1: Agregar/Actualizar sin sobrescribir otras variables (Recomendado)

```bash
gcloud run services update prislab-farmacia \
    --region us-central1 \
    --update-env-vars "GOOGLE_API_KEY=TU_API_KEY_AQUI"
```

**Reemplaza `TU_API_KEY_AQUI` con tu API key real de Google.**

## Opción 2: Establecer todas las variables (sobrescribe las existentes)

Si quieres establecer todas las variables de entorno de una vez:

```bash
gcloud run services update prislab-farmacia \
    --region us-central1 \
    --set-env-vars "DEBUG=False,GOOGLE_API_KEY=TU_API_KEY_AQUI"
```

⚠️ **Advertencia**: `--set-env-vars` reemplaza TODAS las variables de entorno existentes. Usa `--update-env-vars` si solo quieres agregar/actualizar una variable.

## Opción 3: Usar archivo de variables de entorno

Si tienes múltiples variables, puedes crear un archivo `env.yaml`:

```yaml
GOOGLE_API_KEY: "TU_API_KEY_AQUI"
DEBUG: "False"
SECRET_KEY: "tu-secret-key"
```

Y luego:

```bash
gcloud run services update prislab-farmacia \
    --region us-central1 \
    --update-env-vars-file env.yaml
```

## Verificar la configuración

Para ver las variables de entorno actuales:

```bash
gcloud run services describe prislab-farmacia \
    --region us-central1 \
    --format 'value(spec.template.spec.containers[0].env)'
```

## Obtener tu API Key de Google

Si necesitas obtener o crear una API key:

1. Ve a [Google Cloud Console](https://console.cloud.google.com/)
2. Navega a "APIs & Services" > "Credentials"
3. Crea una nueva API Key o usa una existente
4. Restringe la API key a los servicios necesarios (recomendado para producción)

## Ejemplo completo con múltiples variables

```bash
gcloud run services update prislab-farmacia \
    --region us-central1 \
    --update-env-vars "GOOGLE_API_KEY=AIzaSy...,DEBUG=False,SECRET_KEY=tu-secret-key-seguro"
```
