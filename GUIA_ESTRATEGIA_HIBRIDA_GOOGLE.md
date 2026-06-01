# 🚀 GUÍA: ESTRATEGIA HÍBRIDA WHITENOISE + GOOGLE DRIVE
## PRISLAB V5.0 - Rápido, Económico, Escalable

---

## ✅ IMPLEMENTACIÓN COMPLETADA

He implementado la estrategia híbrida completa. Ahora solo necesitas seguir estos pasos para configurarla.

---

## 🎯 QUÉ SE IMPLEMENTÓ

### 1. WhiteNoise para STATIC ⚡
**Archivos que van aquí:**
- Logos y iconos del sistema
- Archivos CSS (colores, estilos)
- Archivos JavaScript (menús, funcionalidades)
- Fuentes tipográficas
- Imágenes del tema (backgrounds, botones)

**Beneficios:**
- ✅ Carga INSTANTÁNEA (desde memoria)
- ✅ Sin latencia
- ✅ Sin costos adicionales
- ✅ Compresión automática
- ✅ Cache de 1 año

### 2. Google Drive para MEDIA 📁
**Archivos que van aquí:**
- Recetas escaneadas (OCR)
- PDFs de resultados de laboratorio
- Audio de consultas médicas
- Fotos de muestras
- Facturas CFDI
- Imágenes de estudios
- Backups

**Beneficios:**
- ✅ 10TB de almacenamiento (ya pagado)
- ✅ Backup automático de Google
- ✅ Compartir archivos fácilmente
- ✅ Sin límites de transferencia
- ✅ Accesible desde cualquier lugar

---

## 📋 LO QUE NECESITAS HACER

### PASO 1: Instalar Dependencias Actualizadas

```powershell
# En tu PC, con el entorno virtual activado
.\venv\Scripts\Activate.ps1

# Instalar nuevas dependencias
pip install -r requirements.txt

# Verificar instalación
pip list | Select-String "google"
```

**Deberías ver:**
```
google-api-python-client==2.160.0
google-auth==2.37.0
google-auth-oauthlib==1.2.0
google-cloud-speech==2.27.0
google-cloud-secret-manager==2.21.1
google-cloud-vision==3.7.3
google-generativeai>=0.8.3
```

---

### PASO 2: Crear Proyecto en Google Cloud Console

1. **Ir a:** https://console.cloud.google.com
2. **Crear proyecto nuevo:**
   - Nombre: `PRISLAB-Produccion`
   - Copiar el **PROJECT_ID** (lo usaremos mucho)

3. **Verificar facturación:**
   - Menú → Facturación
   - Verificar que tu tarjeta esté activa
   - Configurar alerta de presupuesto: $100 USD/mes

---

### PASO 3: Instalar Google Cloud SDK

```powershell
# Descargar e instalar
(New-Object Net.WebClient).DownloadFile("https://dl.google.com/dl/cloudsdk/channels/rapid/GoogleCloudSDKInstaller.exe", "$env:Temp\GoogleCloudSDKInstaller.exe")
& $env:Temp\GoogleCloudSDKInstaller.exe

# Reiniciar terminal después de instalar

# Inicializar
gcloud init

# Seleccionar:
# 1. Tu cuenta de Google
# 2. Proyecto: PRISLAB-Produccion
# 3. Región: us-central1
```

---

### PASO 4: Habilitar APIs de Google Cloud

```powershell
# Establecer proyecto
gcloud config set project PRISLAB-Produccion

# Habilitar TODAS las APIs necesarias
gcloud services enable run.googleapis.com
gcloud services enable sqladmin.googleapis.com
gcloud services enable storage.googleapis.com
gcloud services enable drive.googleapis.com
gcloud services enable secretmanager.googleapis.com
gcloud services enable aiplatform.googleapis.com
gcloud services enable vision.googleapis.com
gcloud services enable speech.googleapis.com
gcloud services enable cloudbuild.googleapis.com

# Verificar (deberías ver todas las APIs listadas)
gcloud services list --enabled
```

---

### PASO 5: Crear Cloud SQL (Base de Datos PostgreSQL)

```powershell
# Crear instancia
gcloud sql instances create prislab-db \
    --database-version=POSTGRES_14 \
    --tier=db-g1-small \
    --region=us-central1 \
    --root-password=TU_PASSWORD_SUPER_SEGURA_AQUI \
    --storage-size=20GB \
    --storage-type=SSD \
    --storage-auto-increase

# Crear base de datos
gcloud sql databases create prislab_v5 --instance=prislab-db

# Crear usuario
gcloud sql users create prislab_user \
    --instance=prislab-db \
    --password=TU_PASSWORD_USUARIO_AQUI

# Guardar CONNECTION_NAME (lo necesitarás)
gcloud sql instances describe prislab-db --format="value(connectionName)"
# Ejemplo: prislab-produccion:us-central1:prislab-db
```

---

### PASO 6: Configurar Google Drive (10TB)

#### A. Crear Cuenta de Servicio

```powershell
# Crear cuenta de servicio
gcloud iam service-accounts create prislab-drive-sa \
    --display-name="PRISLAB Drive Service Account"

# Obtener email de la cuenta
gcloud iam service-accounts list
# Copiar: prislab-drive-sa@PROYECTO.iam.gserviceaccount.com
```

#### B. Generar Credenciales

```powershell
# Descargar clave JSON
gcloud iam service-accounts keys create prislab-drive-key.json \
    --iam-account=prislab-drive-sa@PRISLAB-Produccion.iam.gserviceaccount.com

# El archivo prislab-drive-key.json se guardará en tu carpeta actual
```

#### C. Configurar Carpeta en Drive (MANUAL)

**⚠️ IMPORTANTE - Hacer esto en tu navegador:**

1. **Ir a:** https://drive.google.com
2. **Crear carpeta:** `PRISLAB_Storage`
3. **Compartir la carpeta:**
   - Click derecho en la carpeta
   - "Compartir"
   - Agregar: `prislab-drive-sa@PRISLAB-Produccion.iam.gserviceaccount.com`
   - Permisos: **Editor**
   - Enviar

4. **Copiar FOLDER_ID:**
   - Abrir la carpeta `PRISLAB_Storage`
   - En la URL: `https://drive.google.com/drive/folders/XXXXXXXXXXXXX`
   - Copiar el `XXXXXXXXXXXXX`
   - **GUARDAR ESTE ID** (lo necesitarás en el siguiente paso)

#### D. Crear Subcarpetas (AUTOMÁTICAS)

El sistema creará estas carpetas automáticamente cuando suba archivos:

```
PRISLAB_Storage/
├── recetas_ocr/
│   └── 2026/
│       └── 01/
├── transcripciones_voz/
│   └── 2026/
│       └── 01/
├── resultados_lab/
├── facturas_cfdi/
├── imagenes_consultas/
└── backups/
```

---

### PASO 7: Guardar Credenciales en Secret Manager

```powershell
# 1. SECRET_KEY de Django (generar uno nuevo)
$secretKey = -join ((65..90) + (97..122) + (48..57) | Get-Random -Count 64 | % {[char]$_})
echo -n $secretKey | gcloud secrets create django-secret-key --data-file=-

# 2. Password de Base de Datos
echo -n "TU_PASSWORD_BD_AQUI" | gcloud secrets create db-password --data-file=-

# 3. Gemini API Key
echo -n "TU_GOOGLE_API_KEY_AQUI" | gcloud secrets create gemini-api-key --data-file=-

# 4. Drive Credentials (archivo completo)
gcloud secrets create drive-credentials --data-file=prislab-drive-key.json

# 5. Drive Folder ID
echo -n "TU_DRIVE_FOLDER_ID_AQUI" | gcloud secrets create drive-folder-id --data-file=-

# 6. Cloud SQL Connection Name
echo -n "PRISLAB-Produccion:us-central1:prislab-db" | gcloud secrets create sql-connection-name --data-file=-
```

#### Dar Permisos a Cloud Run

```powershell
# Obtener número del proyecto
$PROJECT_NUMBER = gcloud projects describe PRISLAB-Produccion --format="value(projectNumber)"

# Dar permisos para cada secreto
$secrets = @("django-secret-key", "db-password", "gemini-api-key", "drive-credentials", "drive-folder-id", "sql-connection-name")

foreach ($secret in $secrets) {
    gcloud secrets add-iam-policy-binding $secret `
        --member="serviceAccount:${PROJECT_NUMBER}-compute@developer.gserviceaccount.com" `
        --role="roles/secretmanager.secretAccessor"
}
```

---

### PASO 8: Desplegar a Google Cloud Run

#### A. Construir Imagen Docker

```powershell
# Configurar región
gcloud config set run/region us-central1

# Construir y subir imagen (toma 5-10 minutos la primera vez)
gcloud builds submit --tag gcr.io/PRISLAB-Produccion/prislab-app

# ☕ Tomar un café mientras se construye...
```

#### B. Desplegar Aplicación

```powershell
# Desplegar a Cloud Run
gcloud run deploy prislab \
    --image gcr.io/PRISLAB-Produccion/prislab-app \
    --platform managed \
    --region us-central1 \
    --allow-unauthenticated \
    --memory 2Gi \
    --cpu 2 \
    --timeout 300 \
    --min-instances 0 \
    --max-instances 10 \
    --set-env-vars="GOOGLE_CLOUD_PROJECT=PRISLAB-Produccion" \
    --add-cloudsql-instances PRISLAB-Produccion:us-central1:prislab-db

# Copiar la URL que te da
# Ejemplo: https://prislab-xxxxx-uc.a.run.app
```

---

### PASO 9: Aplicar Migraciones

```powershell
# Crear job de migración
gcloud run jobs create prislab-migrate \
    --image gcr.io/PRISLAB-Produccion/prislab-app \
    --set-cloudsql-instances PRISLAB-Produccion:us-central1:prislab-db \
    --set-env-vars="GOOGLE_CLOUD_PROJECT=PRISLAB-Produccion" \
    --command="python" \
    --args="manage.py,migrate" \
    --region us-central1

# Ejecutar migraciones
gcloud run jobs execute prislab-migrate --region us-central1 --wait
```

---

### PASO 10: Crear Superusuario

```powershell
# Crear job para crear superusuario
gcloud run jobs create prislab-createsuperuser \
    --image gcr.io/PRISLAB-Produccion/prislab-app \
    --set-cloudsql-instances PRISLAB-Produccion:us-central1:prislab-db \
    --set-env-vars="GOOGLE_CLOUD_PROJECT=PRISLAB-Produccion" \
    --command="python" \
    --args="manage.py,createsuperuser,--noinput,--username=admin,--email=admin@prislab.com" \
    --region us-central1

# Ejecutar
gcloud run jobs execute prislab-createsuperuser --region us-central1
```

---

## 🎉 ¡LISTO! VERIFICACIÓN FINAL

### Acceder al Sistema

**URL:** La que te dio Cloud Run (ej: https://prislab-xxxxx-uc.a.run.app)

### Probar Funcionalidades

1. **Login:**
   - Usuario: `admin`
   - Password: (el que configuraste)

2. **Verificar WhiteNoise (STATIC):**
   - Los logos e iconos deben cargar INSTANTÁNEAMENTE
   - La página debe sentirse RÁPIDA
   - Inspeccionar red: archivos .css y .js con cache de 1 año

3. **Verificar Google Drive (MEDIA):**
   - Ir a IA → Procesar Receta OCR
   - Subir una imagen
   - Verificar en tu Drive: debe aparecer en `PRISLAB_Storage/recetas_ocr/`

4. **Verificar Pris Assistant:**
   - Debe aparecer en esquina inferior derecha
   - Click en el avatar: debe responder
   - Ejecutar: `window.pris.consultarIA("Test")`

---

## 💰 COSTOS ESTIMADOS

| Servicio | Uso Estimado | Costo Mensual |
|----------|--------------|---------------|
| **Cloud Run** | 1M requests/mes | $24 USD |
| **Cloud SQL** | db-g1-small | $25 USD |
| **Secret Manager** | 6 secretos | $0.18 USD |
| **Cloud Build** | 100 builds/mes | $0 (gratis) |
| **Google Drive** | 10TB | $0 (ya pagado) |
| **Gemini API** | 10K requests | $0-10 USD |
| **Vision API** | 1K imágenes | $1.50 USD |
| **Speech API** | 100 horas | $14.40 USD |
| **TOTAL** | | **~$65-75 USD/mes** |

**💡 Los 10TB de Drive NO tienen costo extra si ya los tienes en tu Workspace.**

---

## 🚀 VENTAJAS DE ESTA ESTRATEGIA

### 1. Rendimiento Óptimo ⚡
- STATIC desde WhiteNoise: **Carga en milisegundos**
- MEDIA desde Drive: **Archivos grandes sin problema**

### 2. Costos Mínimos 💰
- WhiteNoise: **$0** (incluido en Cloud Run)
- Drive: **$0** (ya pagado en tu Workspace)
- Solo pagas por Cloud Run y Cloud SQL

### 3. Escalabilidad Automática 📈
- Cloud Run: Escala de 0 a 10 instancias automáticamente
- Drive: 10TB disponibles desde el día 1

### 4. Backup Incluido 🔒
- Drive: Backup automático de Google
- Cloud SQL: Snapshots automáticos

---

## 📞 PRÓXIMOS PASOS

Una vez desplegado, puedes:

1. **Configurar Dominio Propio:**
   ```powershell
   gcloud run domain-mappings create \
       --service prislab \
       --domain tu-dominio.com \
       --region us-central1
   ```

2. **Configurar SSL Automático:**
   - Cloud Run lo hace automáticamente
   - Solo configura los DNS que te indique

3. **Monitoreo:**
   - Cloud Run: https://console.cloud.google.com/run
   - Logs: https://console.cloud.google.com/logs

---

## 🎊 RESUMEN

### Lo que implementé:
- ✅ `config/storage_backends.py` - Backend de Google Drive
- ✅ `config/settings.py` - Configuración híbrida
- ✅ `Dockerfile` - Optimizado para Cloud Run
- ✅ `requirements.txt` - Dependencias actualizadas

### Lo que TÚ debes hacer:
1. Instalar dependencias (`pip install -r requirements.txt`)
2. Crear proyecto en Google Cloud
3. Habilitar APIs (comandos arriba)
4. Crear Cloud SQL
5. Configurar Google Drive (carpeta + permisos)
6. Guardar secretos en Secret Manager
7. Desplegar a Cloud Run
8. Aplicar migraciones
9. Crear superusuario
10. ¡Disfrutar! 🎉

**Tiempo estimado: 2-3 horas**

---

## ✅ CHECKLIST DE VERIFICACIÓN

- [ ] Dependencias instaladas
- [ ] Proyecto Google Cloud creado
- [ ] Facturación verificada
- [ ] APIs habilitadas (11 APIs)
- [ ] Cloud SQL creado
- [ ] Cuenta de servicio creada
- [ ] Carpeta Drive compartida
- [ ] DRIVE_FOLDER_ID copiado
- [ ] Secretos guardados en Secret Manager (6)
- [ ] Permisos de Secret Manager configurados
- [ ] Imagen Docker construida
- [ ] Aplicación desplegada en Cloud Run
- [ ] Migraciones aplicadas
- [ ] Superusuario creado
- [ ] Acceso verificado
- [ ] STATIC carga rápido (WhiteNoise)
- [ ] MEDIA se guarda en Drive

---

**¡PRISLAB V5.0 corriendo 100% en Google Cloud con estrategia híbrida! 🚀**

---

**Autor:** PRISLAB Development Team  
**Fecha:** 27 de Enero de 2026  
**Versión:** 5.0 Hybrid Deployment

