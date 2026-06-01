#!/bin/bash
# Script para configurar GOOGLE_API_KEY en Cloud Run

# Reemplaza 'TU_API_KEY_AQUI' con tu API key real de Google
GOOGLE_API_KEY="TU_API_KEY_AQUI"

# Comando para agregar/actualizar la variable de entorno (sin sobrescribir las existentes)
gcloud run services update prislab-farmacia \
    --region us-central1 \
    --update-env-vars "GOOGLE_API_KEY=${GOOGLE_API_KEY}"

echo "✅ Variable de entorno GOOGLE_API_KEY configurada exitosamente"
