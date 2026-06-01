# 🚀 COMANDOS DE DESPLIEGUE - PRISLAB V5
# Proyecto: prislab-v5-ai
# Tu número de proyecto: 811785477499

## ✅ PASO 1: CONFIGURAR GCLOUD (2 minutos)

# Abre PowerShell y ejecuta:

# 1.1 Autenticarte (abrirá navegador)
gcloud auth login

# 1.2 Configurar tu proyecto
gcloud config set project prislab-v5-ai

# 1.3 Verificar que está configurado
gcloud config get-value project

# Debe mostrar: prislab-v5-ai

## ✅ PASO 2: HABILITAR FACTURACIÓN (3 minutos)

# 2.1 Abrir consola de facturación
start https://console.cloud.google.com/billing/linkedaccount?project=prislab-v5-ai

# Sigue estos pasos en el navegador:
# - Si ya tienes una cuenta de facturación, selecciónala
# - Si no, clic en "Crear cuenta de facturación"
# - Ingresa tu tarjeta (no te cobrarán sin tu autorización)
# - Asocia la cuenta con el proyecto prislab-v5-ai

## ✅ PASO 3: HABILITAR APIS NECESARIAS (2 minutos)

gcloud services enable cloudbuild.googleapis.com run.googleapis.com sqladmin.googleapis.com secretmanager.googleapis.com drive.googleapis.com vision.googleapis.com speech.googleapis.com --project=prislab-v5-ai

## ✅ PASO 4: CONFIGURAR GOOGLE DRIVE (10 minutos)

# 4.1 Crear service account
gcloud iam service-accounts create prislab-drive --display-name="PRISLAB Drive Storage" --project=prislab-v5-ai

# 4.2 Descargar credenciales (se guarda en tu Desktop)
gcloud iam service-accounts keys create C:\Users\jonil\Desktop\drive_credentials.json --iam-account=prislab-drive@prislab-v5-ai.iam.gserviceaccount.com

# 4.3 AHORA HAZ ESTO MANUALMENTE EN GOOGLE DRIVE:
# a) Ve a: https://drive.google.com
# b) Crea una carpeta llamada: PRISLAB_Media
# c) Clic derecho en la carpeta → "Compartir"
# d) Pega este email: prislab-drive@prislab-v5-ai.iam.gserviceaccount.com
# e) Dale permisos de "Editor"
# f) Clic en "Enviar"
# g) Abre la carpeta y COPIA EL ID de la URL:
#    Ejemplo: https://drive.google.com/drive/folders/1A2B3C4D5E6F7G8H9I0J
#    El ID es: 1A2B3C4D5E6F7G8H9I0J
# h) GUARDA ESE ID, lo necesitarás en el siguiente paso

## ✅ PASO 5: OBTENER GEMINI API KEY (2 minutos)

# 5.1 Abrir Google AI Studio
start https://aistudio.google.com/app/apikey

# 5.2 En la página que se abre:
# - Clic en "Create API Key"
# - Selecciona tu proyecto: prislab-v5-ai
# - Copia la API Key (empieza con AIza...)
# - GUÁRDALA, la necesitarás en el siguiente paso

## ✅ PASO 6: CREAR CLOUD SQL (5 minutos)

# 6.1 Crear instancia de PostgreSQL
gcloud sql instances create prislab-db --database-version=POSTGRES_14 --tier=db-f1-micro --region=us-central1 --project=prislab-v5-ai

# Esto tarda 3-5 minutos. Espera a que termine.

# 6.2 Crear base de datos
gcloud sql databases create prislab_v5 --instance=prislab-db --project=prislab-v5-ai

# 6.3 Crear usuario (INVENTA UN PASSWORD SEGURO)
# Reemplaza TU_PASSWORD_SEGURO_AQUI con algo como: PrislabDB2026!SecurePass
gcloud sql users create prislab_user --instance=prislab-db --password=TU_PASSWORD_SEGURO_AQUI --project=prislab-v5-ai

# GUARDA ESE PASSWORD, lo necesitarás en el siguiente paso

## ✅ PASO 7: CONFIGURAR SECRETOS (5 minutos)

# 7.1 Navegar al proyecto
cd C:\Users\jonil\Desktop\PRISLAB_SaaS

# 7.2 Activar entorno virtual
.\venv\Scripts\Activate.ps1

# 7.3 Ejecutar script de configuración de secretos
.\scripts\setup_secrets.ps1

# El script te pedirá:
# - DB Password: El que creaste en el paso 6.3
# - Gemini API Key: La que copiaste en el paso 5.2
# - Drive Folder ID: El ID que copiaste en el paso 4.3
# - Drive Credentials: C:\Users\jonil\Desktop\drive_credentials.json

## ✅ PASO 8: DESPLEGAR A CLOUD RUN (10 minutos)

# 8.1 Asegúrate de estar en la carpeta del proyecto
cd C:\Users\jonil\Desktop\PRISLAB_SaaS

# 8.2 Asegúrate de que el entorno virtual esté activado
.\venv\Scripts\Activate.ps1

# 8.3 Ejecutar script de despliegue
.\scripts\deploy.ps1

# Este script hace TODO automáticamente:
# - Construye la imagen Docker
# - La sube a Container Registry
# - Despliega a Cloud Run
# - Configura las variables de entorno
# - Conecta con Cloud SQL

# ESPERA 5-10 MINUTOS. Al final te dará la URL de tu aplicación.

## ✅ PASO 9: EJECUTAR MIGRACIONES (5 minutos)

# 9.1 Permitir acceso temporal a Cloud SQL desde tu IP
gcloud sql instances patch prislab-db --authorized-networks=0.0.0.0/0 --project=prislab-v5-ai

# 9.2 Configurar variables de entorno
$env:GOOGLE_CLOUD_PROJECT="prislab-v5-ai"
$env:CLOUD_SQL_CONNECTION_NAME="prislab-v5-ai:us-central1:prislab-db"
$env:GAE_ENV="standard"

# 9.3 Ejecutar migraciones
python manage.py migrate

# 9.4 Crear superusuario
python manage.py createsuperuser

# Te pedirá:
# - Username: admin (o el que quieras)
# - Email: tu email
# - Password: el que quieras (para el admin)

# 9.5 Cargar datos de prueba (opcional)
python scripts\crear_datos_omega.py

## ✅ PASO 10: ¡LISTO! 🎉

# Obtener la URL de tu aplicación
gcloud run services describe prislab-v5 --platform=managed --region=us-central1 --format="value(status.url)" --project=prislab-v5-ai

# Abre esa URL en tu navegador y ¡PRISLAB V5 estará funcionando!

## 📊 COMANDOS ÚTILES

# Ver logs en tiempo real
gcloud run services logs read prislab-v5 --region=us-central1 --follow --project=prislab-v5-ai

# Ver estado del servicio
gcloud run services describe prislab-v5 --region=us-central1 --project=prislab-v5-ai

# Ver instancias de Cloud SQL
gcloud sql instances list --project=prislab-v5-ai

# Ver secretos configurados
gcloud secrets list --project=prislab-v5-ai

# Actualizar servicio después de cambios en el código
gcloud run deploy prislab-v5 --source . --region=us-central1 --project=prislab-v5-ai

## 🆘 SI ALGO FALLA

# Error: "gcloud: command not found"
# Solución: Reinicia PowerShell o usa la ruta completa:
# C:\Users\jonil\AppData\Local\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd

# Error: "Permission denied"
# Solución: Ejecuta PowerShell como Administrador

# Error: "Billing not enabled"
# Solución: Ve a https://console.cloud.google.com/billing/linkedaccount?project=prislab-v5-ai

# Error: "Cloud SQL taking too long"
# Solución: Es normal, puede tardar hasta 10 minutos en crearse

# Ver errores específicos en los logs
gcloud run services logs read prislab-v5 --region=us-central1 --limit=50 --project=prislab-v5-ai
