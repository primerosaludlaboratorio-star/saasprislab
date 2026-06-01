# ⚡ DEPLOY RÁPIDO EN RAILWAY - 5 PASOS

## 🎯 TODO ESTÁ LISTO - SOLO EJECUTA ESTOS PASOS

---

## PASO 1: Subir Código a GitHub (Si no está ya)

```bash
# Si no tienes repositorio en GitHub, créalo:
# 1. Ve a github.com
# 2. Click en "+" → "New repository"
# 3. Nombre: PRISLAB_SaaS
# 4. Click "Create repository"

# Luego conecta tu código local:
git remote add origin https://github.com/TU_USUARIO/PRISLAB_SaaS.git
git branch -M main
git push -u origin main
```

**Si ya tienes el repo, solo haz push:**
```bash
git push
```

---

## PASO 2: Crear Cuenta en Railway (30 segundos)

1. Ve a **https://railway.app**
2. Click "Login with GitHub"
3. Autoriza Railway
4. ¡Listo!

---

## PASO 3: Crear Proyecto (1 minuto)

1. Click **"New Project"**
2. Selecciona **"Deploy from GitHub repo"**
3. Busca **"PRISLAB_SaaS"**
4. Click en el repo
5. Railway empieza a deployar automáticamente

---

## PASO 4: Agregar PostgreSQL (30 segundos)

1. En tu proyecto, click **"+ New"**
2. Selecciona **"Database"**
3. Click **"Add PostgreSQL"**
4. ¡Listo! Railway conecta automáticamente

---

## PASO 5: Configurar Variables de Entorno (2 minutos)

1. Click en tu servicio (el que dice "PRISLAB_SaaS")
2. Pestaña **"Variables"**
3. Click **"+ New Variable"**
4. Agrega estas (una por una):

```bash
SECRET_KEY=django-insecure-prislab-saas-key-2025-CAMBIAR
DEBUG=False
ALLOWED_HOSTS=*.up.railway.app
GOOGLE_API_KEY=tu-api-key-aqui
GOOGLE_CLOUD_PROJECT=prislab-v5-ai
```

5. Click **"Deploy"** (arriba a la derecha)

---

## ✅ VERIFICAR QUE FUNCIONÓ

### Ver Logs:
1. Click en tu servicio
2. Pestaña "Deployments"
3. Click en el deploy activo
4. Busca esta línea:
```
✅ "Listening at: http://0.0.0.0:XXXX"
```

### Obtener URL:
1. Pestaña "Settings"
2. Sección "Networking"
3. Ahí está tu URL pública

### Probar:
1. Copia la URL
2. Pégala en el navegador
3. Deberías ver el login de PRISLAB

---

## 🎉 TIEMPO TOTAL: 5 MINUTOS

Railway despliega en **3-5 minutos** la primera vez.

---

## 🆘 SI ALGO FALLA

**Error en Build:**
- Revisa que `requirements.txt` esté completo
- Railway lo instala automáticamente

**Error "Application failed to respond":**
- Espera 1 minuto más, a veces tarda
- Revisa los logs para ver si hay errores Python

**Error de Base de Datos:**
- Verifica que agregaste PostgreSQL
- Railway crea `DATABASE_URL` automáticamente

---

## 📱 DESPUÉS DEL DEPLOY

### Crear Superusuario
Railway tiene una terminal integrada:

1. Click en tu servicio → Pestaña "Settings"
2. Busca "Service Domain" o "Connect to Service"  
3. O usa el script que ya tienes:

El sistema creará automáticamente el usuario `admin` con la contraseña `PrislabV5_2026` cuando inicie.

---

## 💰 COSTO

- **Gratis** los primeros $5 USD (suficiente para 1 mes de pruebas)
- Después: ~$5-8 USD/mes

---

**¡Listo! En 5 minutos tendrás PRISLAB en línea. 🚀**
