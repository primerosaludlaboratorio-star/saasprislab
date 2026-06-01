# 🚀 PRISLAB V5.0 - GUÍA RÁPIDA DE DESPLIEGUE

## ✅ Estado Actual del Sistema

**TODO EL CÓDIGO ESTÁ LISTO.** Solo necesitas configurar Google Cloud y ejecutar los scripts automatizados.

---

## 📋 PRE-REQUISITOS

Antes de empezar, asegúrate de tener instalado:

1. **Google Cloud SDK** (gcloud CLI)
   - Descarga: https://cloud.google.com/sdk/docs/install
   - Verifica: `gcloud --version`

2. **Docker Desktop** (solo si despliegas desde tu PC)
   - Descarga: https://docs.docker.com/get-docker/
   - Verifica: `docker --version`

3. **Cuenta de Google Cloud con tarjeta registrada**
   - Crea proyecto en: https://console.cloud.google.com/

---

## 🎯 OPCIÓN 1: DESPLIEGUE AUTOMATIZADO (RECOMENDADO)

### Paso 1: Configurar Google Cloud (5 minutos)

```powershell
# 1. Instalar gcloud SDK (si no lo tienes)
# Descargar de: https://cloud.google.com/sdk/docs/install

# 2. Autenticarte
gcloud auth login

# 3. Crear proyecto (o usar uno existente)
gcloud projects create prislab-v5-prod --name="PRISLAB V5"

# 4. Configurar proyecto activo
gcloud config set project prislab-v5-prod

# 5. Habilitar facturación
# Ve a: https://console.cloud.google.com/billing
# Asocia el proyecto con tu cuenta de facturación
```

### Paso 2: Configurar Google Drive API (10 minutos)

```powershell
# 1. Habilitar Google Drive API
gcloud services enable drive.googleapis.com

# 2. Crear Service Account
gcloud iam service-accounts create prislab-drive `
    --display-name="PRISLAB Drive Storage"

# 3. Descargar credenciales
$PROJECT_ID = gcloud config get-value project
gcloud iam service-accounts keys create drive_credentials.json `
    --iam-account=prislab-drive@$PROJECT_ID.iam.gserviceaccount.com

# 4. Configurar carpeta de Drive:
# - Ve a https://drive.google.com
# - Crea una carpeta llamada "PRISLAB_Media"
# - Haz clic derecho > Compartir
# - Agrega el email: prislab-drive@TU-PROJECT-ID.iam.gserviceaccount.com
# - Dale permisos de "Editor"
# - Copia el ID de la carpeta (está en la URL: /folders/ESTE-ES-EL-ID)
```

### Paso 3: Configurar Secrets (5 minutos)

```powershell
# Ejecutar el script automatizado (desde la raíz del proyecto)
cd C:\Users\jonil\Desktop\PRISLAB_SaaS
.\scripts\setup_secrets.ps1
```

El script te pedirá:
- **DB Password**: Inventa uno seguro (mínimo 16 caracteres)
- **Gemini API Key**: Obtén una gratis en https://aistudio.google.com/app/apikey
- **Drive Folder ID**: El ID que copiaste en el paso anterior
- **Drive Credentials**: Ruta al archivo `drive_credentials.json`

### Paso 4: Crear Cloud SQL (5 minutos)

```powershell
# Crear instancia de PostgreSQL
gcloud sql instances create prislab-db `
    --database-version=POSTGRES_14 `
    --tier=db-f1-micro `
    --region=us-central1

# Crear base de datos
gcloud sql databases create prislab_v5 --instance=prislab-db

# Crear usuario
gcloud sql users create prislab_user `
    --instance=prislab-db `
    --password=TU-PASSWORD-SEGURO-AQUI
```

### Paso 5: Desplegar (10 minutos)

```powershell
# Ejecutar el script de despliegue automatizado
cd C:\Users\jonil\Desktop\PRISLAB_SaaS
.\scripts\deploy.ps1
```

El script hará TODO automáticamente:
1. Habilitar APIs necesarias
2. Construir la imagen Docker
3. Subir al Container Registry
4. Desplegar a Cloud Run
5. Configurar Cloud SQL
6. Mostrarte la URL de tu aplicación

### Paso 6: Ejecutar Migraciones (Primera Vez)

```powershell
# Instalar Cloud SQL Proxy
gcloud sql instances patch prislab-db --authorized-networks=0.0.0.0/0

# Desde tu PC local (con el entorno virtual activado):
.\venv\Scripts\Activate.ps1

# Configurar variables de entorno temporalmente
$env:GOOGLE_CLOUD_PROJECT="prislab-v5-prod"
$env:CLOUD_SQL_CONNECTION_NAME="prislab-v5-prod:us-central1:prislab-db"
$env:GAE_ENV="standard"

# Ejecutar migraciones
python manage.py migrate

# Crear superusuario
python manage.py createsuperuser
```

---

## 🎯 OPCIÓN 2: DESPLIEGUE MANUAL (ALTERNATIVO)

Si prefieres hacerlo paso a paso sin scripts, sigue la **GUIA_ESTRATEGIA_HIBRIDA_GOOGLE.md** completa.

---

## ✅ VERIFICACIÓN POST-DESPLIEGUE

Una vez desplegado, verifica que todo funciona:

```powershell
# 1. Obtener URL del servicio
gcloud run services describe prislab-v5 `
    --platform=managed `
    --region=us-central1 `
    --format='value(status.url)'

# 2. Ver logs en tiempo real
gcloud run services logs read prislab-v5 `
    --region=us-central1 `
    --follow

# 3. Verificar secretos
gcloud secrets list

# 4. Verificar Cloud SQL
gcloud sql instances list
```

Abre la URL en tu navegador. Deberías ver la pantalla de login de PRISLAB V5.

---

## 🔧 CONFIGURACIÓN ADICIONAL

### Configurar Dominio Personalizado

```powershell
# 1. Mapear dominio
gcloud run domain-mappings create `
    --service=prislab-v5 `
    --domain=tu-dominio.com `
    --region=us-central1

# 2. Actualizar ALLOWED_HOSTS en Secret Manager
echo "tu-dominio.com,www.tu-dominio.com" | `
    gcloud secrets versions add allowed-hosts --data-file=-
```

### Habilitar HTTPS (Automático en Cloud Run)

Cloud Run habilita HTTPS automáticamente. Solo asegúrate de:
- Actualizar `ALLOWED_HOSTS` en secretos
- Configurar DNS apuntando a Google

---

## 📊 COSTOS ESTIMADOS (Mensual)

- **Cloud Run**: $0-25 (según tráfico, nivel gratuito incluye 2M requests)
- **Cloud SQL (db-f1-micro)**: ~$7.50/mes
- **Cloud Storage (Backups)**: $0.026/GB/mes
- **Secret Manager**: Gratis (10,000 accesos/mes incluidos)
- **Google Drive**: $0 (ya tienes 10TB)

**Total estimado**: $10-35/mes para empezar.

---

## 🆘 SOLUCIÓN DE PROBLEMAS

### Error: "Permission denied" en Secret Manager
```powershell
# Otorgar permisos al service account de Cloud Run
$PROJECT_NUM = gcloud projects describe prislab-v5-prod --format='value(projectNumber)'
gcloud projects add-iam-policy-binding prislab-v5-prod `
    --member="serviceAccount:$PROJECT_NUM-compute@developer.gserviceaccount.com" `
    --role="roles/secretmanager.secretAccessor"
```

### Error: "Cannot connect to Cloud SQL"
```powershell
# Verificar que la conexión está configurada
gcloud run services describe prislab-v5 `
    --region=us-central1 `
    --format='get(spec.template.spec.containers[0].env)'
```

### Error: "Drive API not enabled"
```powershell
# Habilitar manualmente
gcloud services enable drive.googleapis.com
```

### Logs muestran errores
```powershell
# Ver logs detallados
gcloud run services logs read prislab-v5 `
    --region=us-central1 `
    --limit=100
```

---

## 📞 COMANDOS ÚTILES

```powershell
# Ver servicios desplegados
gcloud run services list

# Actualizar servicio (después de cambios)
gcloud run deploy prislab-v5 `
    --image=gcr.io/prislab-v5-prod/prislab-v5 `
    --region=us-central1

# Conectarse a Cloud SQL localmente
gcloud sql connect prislab-db --user=prislab_user

# Ver uso de recursos
gcloud monitoring dashboards list

# Descargar logs
gcloud run services logs read prislab-v5 `
    --region=us-central1 `
    --limit=1000 > logs.txt
```

---

## 🎉 ¡LISTO!

Tu sistema PRISLAB V5.0 está ahora en producción en Google Cloud con:

- ✅ **WhiteNoise** sirviendo estáticos instantáneos
- ✅ **Google Drive** almacenando 10TB de archivos media
- ✅ **Cloud SQL** con PostgreSQL seguro
- ✅ **Secret Manager** protegiendo credenciales
- ✅ **Cloud Run** escalando automáticamente
- ✅ **HTTPS** habilitado por defecto

**URL de producción**: https://prislab-v5-XXXXXXXXX-uc.a.run.app

**Panel de admin**: https://TU-URL/admin/

---

## 📚 DOCUMENTACIÓN ADICIONAL

- **Guía completa**: `GUIA_ESTRATEGIA_HIBRIDA_GOOGLE.md`
- **Despliegue detallado**: `GUIA_DESPLIEGUE_FINAL_PRISLAB_V5.md`
- **Resumen del sistema**: `RESUMEN_IMPLEMENTACION_COMPLETA_26ENE2026.md`

---

**¿Necesitas ayuda?** Los scripts están diseñados para ser autoexplicativos. Si algo falla, revisa los logs con `gcloud run services logs read prislab-v5 --region=us-central1 --follow`
