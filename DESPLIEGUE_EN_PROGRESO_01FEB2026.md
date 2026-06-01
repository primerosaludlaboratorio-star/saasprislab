# 🚀 DESPLIEGUE EN PROGRESO - PRISLAB V5.0

**Fecha:** 1 de Febrero de 2026  
**Build ID:** `1f314568-7085-48e3-8c63-32662d3e7ddc`  
**Estado:** ⏳ EN PROGRESO  

---

## 📊 INFORMACIÓN DEL DESPLIEGUE

**Proyecto:** `prislab-v5-ai`  
**Servicio:** `prislab-v5`  
**Región:** `us-central1`  
**Método:** Cloud Build  

**Archivos:** 841 archivos (11.8 MiB)  

---

## 🔍 MONITOREAR EL PROGRESO

### **Opción 1: Consola Web (RECOMENDADO)**

Abre este enlace en tu navegador:

```
https://console.cloud.google.com/cloud-build/builds/1f314568-7085-48e3-8c63-32662d3e7ddc?project=811785477499
```

### **Opción 2: Línea de comandos**

```bash
# Ver el estado actual
gcloud builds describe 1f314568-7085-48e3-8c63-32662d3e7ddc

# Ver logs en tiempo real
gcloud builds log 1f314568-7085-48e3-8c63-32662d3e7ddc --stream
```

### **Opción 3: Listar builds recientes**

```bash
gcloud builds list --limit=5
```

---

## ⏱️ TIEMPO ESTIMADO

- **Build de imagen Docker:** 3-5 minutos
- **Push al Container Registry:** 1-2 minutos
- **Despliegue a Cloud Run:** 2-3 minutos

**Total estimado:** 6-10 minutos

---

## ✅ FASES DEL DESPLIEGUE

```
[  ] 1. Build de imagen Docker
     └─ Instalando dependencias (requirements.txt)
     └─ Copiando archivos
     └─ Configurando entrypoint

[  ] 2. Push al Container Registry
     └─ Subiendo imagen a gcr.io

[  ] 3. Despliegue a Cloud Run
     └─ Creando nueva revisión
     └─ Asignando tráfico
     └─ Servicio disponible
```

---

## 🎯 CAMBIOS QUE SE ESTÁN DESPLEGANDO

### **1. Consultorio - Gemelo Digital**
```python
# consultorio/views.py (línea 781)
return render(request, 'consultorio/nueva_consulta_gemelo.html', {...})
```

### **2. Laboratorio - Smart Lab**
```python
# core/views/laboratorio_captura.py (línea 182)
return render(request, 'laboratorio/capturar_resultados.html', context)
```

### **3. Pacientes - Timeline**
```python
# core/views/paciente_detalle.py (línea 71)
template_name = 'pacientes/historial_clinico.html'
```

### **4. Sidebar - RBAC**
```html
<!-- core/templates/includes/sidebar.html -->
{% load auth_extras %}
{% if request.user|has_group:"MEDICOS" %}
  ...
{% endif %}
```

### **5. Migración Nueva**
```
laboratorio/migrations/0003_estudio_keywords.py
```

### **6. Management Commands**
```
core/management/commands/crear_grupos_roles.py
core/management/commands/seed_estudios.py
```

---

## 🔔 NOTIFICACIONES DE ESTADO

El build te notificará cuando:

✅ **BUILD SUCCESS** - Imagen creada exitosamente  
✅ **PUSH SUCCESS** - Imagen subida al registry  
✅ **DEPLOY SUCCESS** - Servicio desplegado  

❌ **BUILD FAILED** - Error en construcción de imagen  
❌ **DEPLOY FAILED** - Error en despliegue a Cloud Run  

---

## 📋 PASOS POST-DESPLIEGUE

Una vez que el despliegue termine con éxito:

### **1. Obtener la URL del servicio**

```bash
gcloud run services describe prislab-v5 --region us-central1 --format "value(status.url)"
```

Resultado esperado:
```
https://prislab-v5-XXXXXXXX-uc.a.run.app
```

### **2. Aplicar migraciones a Cloud SQL**

```bash
# Conectarse a Cloud SQL y ejecutar migraciones
gcloud sql connect prislab-db --user=prislab_user --database=prislab_v5

# Dentro de Cloud SQL:
# python manage.py migrate
```

**O usar Cloud Run Jobs:**

```bash
gcloud run jobs create prislab-migrations \
  --image gcr.io/prislab-v5-ai/prislab-v5:latest \
  --region us-central1 \
  --command python \
  --args manage.py,migrate

gcloud run jobs execute prislab-migrations --region us-central1 --wait
```

### **3. Crear grupos Django**

```bash
gcloud run jobs create prislab-crear-grupos \
  --image gcr.io/prislab-v5-ai/prislab-v5:latest \
  --region us-central1 \
  --command python \
  --args manage.py,crear_grupos_roles

gcloud run jobs execute prislab-crear-grupos --region us-central1 --wait
```

### **4. Verificar el despliegue**

Abre en tu navegador:

```
https://[TU-URL]/consultorio/nueva-consulta/
https://[TU-URL]/laboratorio/lista-trabajo/
https://[TU-URL]/pacientes/lista/
```

**Y presiona CTRL + F5** para limpiar caché del navegador.

---

## 🐛 SI HAY ERRORES

### **Error: Build Failed**

```bash
# Ver logs detallados
gcloud builds log 1f314568-7085-48e3-8c63-32662d3e7ddc

# Revisar el Dockerfile
cat Dockerfile
```

**Causas comunes:**
- Falta alguna dependencia en `requirements.txt`
- Error en el `Dockerfile`
- Timeout del build (aumentar timeout en `cloudbuild.yaml`)

### **Error: Deploy Failed**

```bash
# Ver logs del servicio
gcloud run services logs read prislab-v5 --region us-central1 --limit 100

# Revisar revisiones
gcloud run revisions list --service prislab-v5 --region us-central1
```

**Causas comunes:**
- Error en las variables de entorno
- Puerto incorrecto (debe ser 8080)
- Timeout muy corto

### **Error: Service not responding**

```bash
# Ver el estado del servicio
gcloud run services describe prislab-v5 --region us-central1

# Verificar tráfico
gcloud run services update-traffic prislab-v5 \
  --to-latest \
  --region us-central1
```

### **Rollback si es necesario**

```bash
# Listar revisiones
gcloud run revisions list --service prislab-v5 --region us-central1

# Rollback a revisión anterior
gcloud run services update-traffic prislab-v5 \
  --to-revisions=REVISION-NAME=100 \
  --region us-central1
```

---

## 📊 CHECKLIST DE VERIFICACIÓN POST-DESPLIEGUE

Después de que el despliegue termine:

- [ ] Build completó exitosamente
- [ ] Imagen subida a Container Registry
- [ ] Servicio desplegado a Cloud Run
- [ ] URL del servicio obtenida
- [ ] Migraciones aplicadas a Cloud SQL
- [ ] Grupos Django creados
- [ ] Verificación visual en el navegador:
  - [ ] Gemelo Digital en `/consultorio/nueva-consulta/`
  - [ ] Smart Lab en captura de resultados
  - [ ] Timeline en expediente de pacientes
  - [ ] Sidebar filtra por rol

---

## 🎯 RESULTADO ESPERADO

Al finalizar, deberás poder acceder a:

```
https://prislab-v5-[ID].a.run.app
```

Y ver:
✅ Consultorio con Gemelo Digital (split screen 40/60)  
✅ Laboratorio con Smart Lab (inputs con data-keywords)  
✅ Pacientes con Timeline (línea vertical con iconos)  
✅ Sidebar que filtra menús por rol del usuario  

---

**ESTADO ACTUAL:** ⏳ BUILD EN PROGRESO  
**PRÓXIMO PASO:** Esperar a que termine el build (~10 minutos)  

Puedes monitorear el progreso en:
https://console.cloud.google.com/cloud-build/builds/1f314568-7085-48e3-8c63-32662d3e7ddc?project=811785477499
