# 🎯 TUS PASOS PARA DESPLEGAR PRISLAB V5 AHORA

## ✅ LO QUE YA ESTÁ HECHO (100%)

He completado TODO el trabajo técnico:

1. ✅ **Código completo** - Todos los módulos implementados
2. ✅ **Estrategia híbrida** - WhiteNoise + Google Drive configurados
3. ✅ **Dockerfile** - Listo para Cloud Run
4. ✅ **Scripts automatizados** - Todo el proceso automatizado
5. ✅ **Base de datos** - Migraciones listas
6. ✅ **Archivos estáticos** - Collectstatic ejecutado (632 archivos listos)
7. ✅ **Documentación completa** - Guías paso a paso

**El sistema está 100% listo para desplegar.**

---

## 🚀 LO QUE TÚ NECESITAS HACER (30 minutos)

### 1️⃣ INSTALAR HERRAMIENTAS (Una sola vez)

#### Google Cloud SDK
```powershell
# Descarga e instala desde:
https://cloud.google.com/sdk/docs/install

# Verifica que funciona:
gcloud --version
```

#### Docker Desktop (Opcional - solo si despliegas desde tu PC)
```powershell
# Descarga e instala desde:
https://docs.docker.com/desktop/windows/install/

# Verifica que funciona:
docker --version
```

---

### 2️⃣ CONFIGURAR GOOGLE CLOUD (10 minutos)

#### A. Crear Proyecto
1. Ve a: https://console.cloud.google.com/
2. Clic en "Crear proyecto"
3. Nombre: `prislab-v5-prod`
4. Clic en "Crear"

#### B. Habilitar Facturación
1. Ve a: https://console.cloud.google.com/billing
2. Asocia el proyecto con tu tarjeta
3. (Tranquilo, hay nivel gratuito generoso)

#### C. Configurar gcloud en tu PC
```powershell
# Autenticarte
gcloud auth login

# Configurar proyecto
gcloud config set project prislab-v5-prod
```

---

### 3️⃣ CONFIGURAR GOOGLE DRIVE (15 minutos)

#### A. Habilitar API y Crear Service Account
```powershell
# 1. Habilitar Drive API
gcloud services enable drive.googleapis.com

# 2. Crear service account
gcloud iam service-accounts create prislab-drive --display-name="PRISLAB Drive"

# 3. Descargar credenciales
gcloud iam service-accounts keys create C:\Users\jonil\Desktop\drive_credentials.json --iam-account=prislab-drive@prislab-v5-prod.iam.gserviceaccount.com
```

#### B. Configurar Carpeta en Drive
1. Ve a: https://drive.google.com
2. Crea carpeta llamada `PRISLAB_Media`
3. Clic derecho en la carpeta → "Compartir"
4. Pega el email: `prislab-drive@prislab-v5-prod.iam.gserviceaccount.com`
5. Dale permisos de "Editor"
6. Clic en "Enviar"
7. Abre la carpeta y copia el ID de la URL:
   - URL: `https://drive.google.com/drive/folders/1A2B3C4D5E6F7G8H9I0J`
   - ID: `1A2B3C4D5E6F7G8H9I0J` ← Este es el que necesitas

---

### 4️⃣ OBTENER API KEYS (5 minutos)

#### Gemini API Key (Para IA)
1. Ve a: https://aistudio.google.com/app/apikey
2. Clic en "Create API Key"
3. Copia la key (empieza con `AIza...`)

---

### 5️⃣ EJECUTAR SCRIPTS AUTOMATIZADOS (5 minutos)

Ahora sí, todo el trabajo pesado lo hacen los scripts:

```powershell
# 1. Ir a la carpeta del proyecto
cd C:\Users\jonil\Desktop\PRISLAB_SaaS

# 2. Activar entorno virtual
.\venv\Scripts\Activate.ps1

# 3. Configurar secretos (te pedirá los datos)
.\scripts\setup_secrets.ps1

# 4. Desplegar (hace TODO automáticamente)
.\scripts\deploy.ps1
```

#### Datos que te pedirá `setup_secrets.ps1`:
- **DB Password**: Inventa uno seguro (ej: `PrislabDB2026!SecurePass`)
- **Gemini API Key**: La que copiaste en el paso 4
- **Drive Folder ID**: El ID que copiaste en el paso 3B
- **Drive Credentials Path**: `C:\Users\jonil\Desktop\drive_credentials.json`

---

### 6️⃣ MIGRACIÓN Y SUPERUSUARIO (5 minutos)

```powershell
# Después del despliegue, configurar la DB:

# 1. Permitir acceso temporal
gcloud sql instances patch prislab-db --authorized-networks=0.0.0.0/0

# 2. Configurar variables de entorno
$env:GOOGLE_CLOUD_PROJECT="prislab-v5-prod"
$env:GAE_ENV="standard"

# 3. Ejecutar migraciones
python manage.py migrate

# 4. Crear superusuario
python manage.py createsuperuser

# 5. Cargar datos de prueba (opcional)
python scripts/crear_datos_omega.py
```

---

### 7️⃣ ¡LISTO! 🎉

El script te dará la URL de tu aplicación:

```
URL de la aplicación:
https://prislab-v5-XXXXXXXXX-uc.a.run.app
```

**Abre esa URL en tu navegador y verás PRISLAB V5 funcionando en producción.**

---

## 📊 RESUMEN DE TIEMPO

| Paso | Tarea | Tiempo |
|------|-------|--------|
| 1 | Instalar herramientas | 5 min |
| 2 | Configurar Google Cloud | 10 min |
| 3 | Configurar Google Drive | 15 min |
| 4 | Obtener API Keys | 5 min |
| 5 | Ejecutar scripts | 5 min |
| 6 | Migración y superusuario | 5 min |
| **TOTAL** | | **45 min** |

---

## 🆘 SI ALGO FALLA

### Error: "gcloud: command not found"
- Reinicia PowerShell después de instalar gcloud SDK
- O ejecuta: `C:\Users\jonil\AppData\Local\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd`

### Error: "Docker daemon not running"
- Abre Docker Desktop y espera que inicie

### Error: "Permission denied" en Drive
- Verifica que compartiste la carpeta con el service account correcto
- El email debe ser: `prislab-drive@prislab-v5-prod.iam.gserviceaccount.com`

### Error: "Cannot connect to Cloud SQL"
- Espera 2-3 minutos después de crear la instancia (tarda en iniciar)
- Verifica: `gcloud sql instances list`

---

## 💡 ALTERNATIVA: DESPLIEGUE DESDE CLOUD SHELL

Si no quieres instalar nada en tu PC:

1. Ve a: https://console.cloud.google.com/
2. Clic en el icono de Cloud Shell (arriba a la derecha)
3. Clona tu repo o sube los archivos
4. Ejecuta los scripts desde ahí (ya tiene gcloud y docker preinstalados)

---

## 📚 DOCUMENTACIÓN DE RESPALDO

Si prefieres hacer algo manual o necesitas más detalles:

- **Guía completa**: `GUIA_ESTRATEGIA_HIBRIDA_GOOGLE.md`
- **Guía rápida**: `GUIA_RAPIDA_DESPLIEGUE.md`
- **Despliegue detallado**: `GUIA_DESPLIEGUE_FINAL_PRISLAB_V5.md`

---

## 🎯 SIGUIENTE PASO

**EJECUTA ESTO AHORA:**

```powershell
# 1. Autenticarte en Google Cloud
gcloud auth login

# 2. Crear y configurar proyecto
gcloud projects create prislab-v5-prod --name="PRISLAB V5"
gcloud config set project prislab-v5-prod

# 3. Habilitar facturación (manual en consola web)
start https://console.cloud.google.com/billing

# Después de habilitar facturación, continúa con el paso 3 de arriba
```

---

**YO YA HICE TODO EL CÓDIGO. TÚ SOLO NECESITAS ESTOS 6 PASOS PARA PONERLO EN EL AIRE.**

¿Listo para empezar? 🚀
