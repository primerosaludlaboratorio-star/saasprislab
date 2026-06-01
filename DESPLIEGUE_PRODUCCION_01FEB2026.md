# 🚀 DESPLIEGUE A PRODUCCIÓN - CAMBIOS CRÍTICOS

**Fecha:** 1 de Febrero de 2026  
**Objetivo:** Aplicar cambios de Bloques 1-8 al servidor de Google Cloud Run  

---

## 📋 ARCHIVOS MODIFICADOS (CRÍTICOS)

### **1. Vistas (Backend)**
```
consultorio/views.py
  - Línea 781: Template cambiado a nueva_consulta_gemelo.html

core/views/laboratorio_captura.py
  - Línea 182: Template cambiado a capturar_resultados.html
```

### **2. Archivos Eliminados**
```
core/templates/includes/sidebar_clean.html (BORRADO)
```

### **3. Migraciones Nuevas**
```
laboratorio/migrations/0003_estudio_keywords.py (PENDIENTE DE APLICAR)
```

### **4. Management Commands Nuevos**
```
core/management/commands/crear_grupos_roles.py (NUEVO)
core/management/commands/seed_estudios.py (NUEVO)
```

---

## 🔧 COMANDOS PARA DESPLEGAR

### **OPCIÓN 1: Despliegue Completo (RECOMENDADO)**

```bash
# 1. Configurar proyecto
gcloud config set project prislab-v5-ai

# 2. Desplegar aplicación
gcloud run deploy prislab-v5 ^
  --source . ^
  --region us-central1 ^
  --platform managed ^
  --allow-unauthenticated ^
  --set-env-vars "DEBUG=False" ^
  --set-env-vars "SECRET_KEY=django-insecure-prislab-saas-key-2025" ^
  --memory 2Gi ^
  --cpu 2 ^
  --timeout 300

# 3. Aplicar migraciones en Cloud SQL
gcloud run jobs create prislab-migrations ^
  --image gcr.io/prislab-v5-ai/prislab-v5 ^
  --region us-central1 ^
  --command python ^
  --args manage.py,migrate ^
  --set-env-vars "DEBUG=False"

gcloud run jobs execute prislab-migrations --region us-central1

# 4. Crear grupos Django (NUEVO)
gcloud run jobs create prislab-crear-grupos ^
  --image gcr.io/prislab-v5-ai/prislab-v5 ^
  --region us-central1 ^
  --command python ^
  --args manage.py,crear_grupos_roles ^
  --set-env-vars "DEBUG=False"

gcloud run jobs execute prislab-crear-grupos --region us-central1
```

---

### **OPCIÓN 2: Despliegue Simplificado (Automático)**

```bash
# Cloud Build lo hará automáticamente
gcloud builds submit --config cloudbuild.yaml
```

---

## ⚠️ PREREQUISITOS

Antes de desplegar, verifica:

- [ ] Tienes `gcloud` instalado
- [ ] Estás autenticado: `gcloud auth login`
- [ ] Proyecto correcto: `gcloud config get-value project`
- [ ] Cloud SQL está corriendo

---

## 🎯 ORDEN DE EJECUCIÓN

1. **Desplegar código** (Cloud Run)
2. **Aplicar migraciones** (Cloud SQL)
3. **Crear grupos Django** (Management command)
4. **Verificar deployment**

---

## 📊 VERIFICACIÓN POST-DESPLIEGUE

Después del despliegue, verificar:

```bash
# Ver la URL del servicio
gcloud run services describe prislab-v5 --region us-central1 --format "value(status.url)"

# Ver logs en tiempo real
gcloud run services logs read prislab-v5 --region us-central1 --limit 50
```

Luego probar en el navegador:
- `https://[TU-URL]/consultorio/nueva-consulta/`
- `https://[TU-URL]/laboratorio/lista-trabajo/`
- `https://[TU-URL]/pacientes/lista/`

---

## 🚨 SI HAY ERRORES

```bash
# Ver logs detallados
gcloud run services logs read prislab-v5 --region us-central1 --limit 100

# Revisar revisiones
gcloud run revisions list --service prislab-v5 --region us-central1

# Rollback si es necesario
gcloud run services update-traffic prislab-v5 ^
  --to-revisions REVISION-NAME=100 ^
  --region us-central1
```

---

**ESTADO:** ⏳ LISTO PARA EJECUTAR
