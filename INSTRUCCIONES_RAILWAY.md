# 🚂 DESPLIEGUE EN RAILWAY - PRISLAB V5.0

**Fecha:** 10 de Febrero 2026  
**Decisión:** Cambiar de Cloud Run a Railway por simplicidad y compatibilidad con Django

---

## 🎯 POR QUÉ RAILWAY

Railway es **10x más simple** que Cloud Run para Django:
- ✅ Detecta automáticamente Django
- ✅ PostgreSQL incluido (con una variable)
- ✅ Deploy directo desde GitHub
- ✅ Logs en tiempo real
- ✅ $5 USD de crédito gratis

---

## 📋 PASOS PARA DESPLEGAR

### 1. Crear Cuenta en Railway
1. Ve a https://railway.app
2. Click en "Login" → "Login with GitHub"
3. Autoriza Railway a acceder a tus repos

### 2. Crear Proyecto Nuevo
1. Click en "New Project"
2. Selecciona "Deploy from GitHub repo"
3. Busca y selecciona `PRISLAB_SaaS`
4. Railway iniciará el deploy automáticamente

### 3. Agregar Base de Datos PostgreSQL
1. En tu proyecto, click en "+ New"
2. Selecciona "Database" → "Add PostgreSQL"
3. Railway creará la base de datos automáticamente
4. **IMPORTANTE:** La variable `DATABASE_URL` se crea automáticamente

### 4. Configurar Variables de Entorno

Click en tu servicio → "Variables" → Agregar las siguientes:

```bash
# Django
SECRET_KEY=django-insecure-prislab-saas-key-2025-cambiar-en-produccion
DEBUG=False
ALLOWED_HOSTS=*.up.railway.app

# Base de datos (Railway la genera automáticamente)
# DATABASE_URL=postgresql://... (ya existe, no tocar)

# Google APIs
GOOGLE_API_KEY=tu-api-key-de-gemini
GOOGLE_CLOUD_PROJECT=prislab-v5-ai
DRIVE_FOLDER_ID=tu-folder-id

# VAPID (para notificaciones push)
VAPID_PUBLIC_KEY=tu-vapid-public-key
VAPID_PRIVATE_KEY=tu-vapid-private-key

# Django Settings
DJANGO_SETTINGS_MODULE=config.settings
PORT=8080
```

### 5. Configurar Dominio (Opcional)
1. En "Settings" → "Networking"
2. Railway te da un dominio automático: `prislab-farmacia.up.railway.app`
3. Puedes conectar tu propio dominio si quieres

### 6. Deploy Automático
Railway detecta los archivos que agregamos:
- `railway.json` (configuración principal)
- `railway.toml` (alternativa)
- `nixpacks.toml` (instrucciones de build)
- `Procfile` (comando de inicio)

El deploy tarda 3-5 minutos.

---

## 🔍 VERIFICAR DESPLIEGUE

### Ver Logs en Tiempo Real
1. Click en tu servicio
2. Pestaña "Deployments"
3. Click en el deploy más reciente
4. Los logs se muestran en tiempo real

### Buscar Errores Comunes
```bash
# ✅ BUENO - Deploy exitoso
"Listening at: http://0.0.0.0:8080"
"Starting gunicorn"
"Booting worker with pid"

# ❌ MALO - Errores
"ModuleNotFoundError"
"ImproperlyConfigured"
"OperationalError"
```

### Acceder al Sistema
1. Click en "Settings" → "Networking"
2. Copia la URL pública
3. Pégala en el navegador
4. Deberías ver el login de PRISLAB

---

## 🎨 ARCHIVOS DE CONFIGURACIÓN CREADOS

### `railway.json`
Configuración principal de Railway en formato JSON.

### `railway.toml`
Alternativa en formato TOML (Railway usa el que encuentre primero).

### `nixpacks.toml`
Instrucciones específicas para el build system de Railway.

### `Procfile` (ya existía)
Define el comando de inicio para el servidor.

---

## 🚨 TROUBLESHOOTING

### Error: "Application failed to respond"
**Causa:** El servidor no está escuchando en `$PORT`  
**Solución:** Railway inyecta la variable `PORT`, nuestro Gunicorn ya la usa correctamente.

### Error: "Build failed"
**Causa:** Dependencias faltantes o incompatibles  
**Solución:** Revisa los logs de build, todas las dependencias están en `requirements.txt`

### Error: "Database connection refused"
**Causa:** Variable `DATABASE_URL` no configurada  
**Solución:** Asegúrate de que agregaste PostgreSQL al proyecto.

### Error: "Static files not found"
**Causa:** `collectstatic` no se ejecutó  
**Solución:** Ya está en el buildCommand, debería ejecutarse automáticamente.

---

## 💰 COSTOS

Railway usa un sistema de créditos:

- **Tier Gratuito:** $5 USD de crédito mensual
- **Uso típico PRISLAB:**
  - Web Service: ~$3-5 USD/mes
  - PostgreSQL: ~$2-3 USD/mes
  - **Total estimado:** $5-8 USD/mes

Para empezar es gratis con el crédito inicial.

---

## 🔄 PRÓXIMOS PASOS DESPUÉS DEL DEPLOY

### 1. Crear Superusuario
Conéctate por SSH o usa el comando en Railway:
```bash
python manage.py createsuperuser
```

O usa el script:
```bash
python crear_superusuario_admin.py
```

### 2. Cargar Datos Iniciales

**Inventario de Farmacia:**
```bash
python manage.py shell < cargar_excel_robusto.py
```

**Catálogo de Laboratorio:**
```bash
python manage.py migrar_lab_completo
```

**Tarifas:**
```bash
python cargar_tarifas.py
```

### 3. Verificar Módulos
Ingresa al sistema y verifica que todos los módulos funcionen:
- ✅ Login
- ✅ Dashboard
- ✅ Farmacia (PDV)
- ✅ Laboratorio (órdenes)
- ✅ Consultorio (consultas)

---

## 📱 CONECTAR DOMINIO PERSONALIZADO (OPCIONAL)

Si quieres usar tu propio dominio (ej: `app.prislab.com`):

1. En Railway: Settings → Networking → Custom Domain
2. Agrega tu dominio
3. Railway te da un registro CNAME
4. En tu proveedor DNS (GoDaddy, Cloudflare, etc.):
   - Agrega registro CNAME
   - Apunta a Railway
5. Espera propagación DNS (5-30 minutos)

---

## 🎉 LISTO

Si todo sale bien, en **5-10 minutos** tendrás PRISLAB v5.0 desplegado en:

```
https://prislab-farmacia-production.up.railway.app
```

(El nombre exacto te lo da Railway)

---

**¡Éxito con el despliegue! 🚀**
