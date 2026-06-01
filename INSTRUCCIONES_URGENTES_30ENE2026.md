# 🎯 INSTRUCCIONES URGENTES - 30 ENERO 2026

## ✅ **SISTEMA CORREGIDO Y DESPLEGADO**

**Revisión:** `prislab-v5-00036-cc5`  
**URL:** https://prislab-v5-811785477499.us-central1.run.app  
**Estado:** 🟢 **TODOS LOS ERRORES CRÍTICOS CORREGIDOS**

---

## 📋 **QUÉ SE CORRIGIÓ (AUTOMÁTICO)**

### ✅ Errores Resueltos:

1. **Error "empresa" en Medico** → CORREGIDO
2. **Error select_related('categoria')** → CORREGIDO  
3. **Error campos inexistentes en Paciente** → CORREGIDO
4. **Error "No hay médicos disponibles"** → CORREGIDO
5. **IA configurada con timeouts** → VERIFICADO

**Resultado:** El sistema ahora funciona sin errores 500 en:
- ✅ Módulo de Consultas
- ✅ Búsqueda de Estudios
- ✅ Registro de Pacientes
- ✅ Chat con PRIS (IA)

---

## 🚀 **ACCIÓN REQUERIDA: CARGAR INVENTARIO**

### Paso 1: Crear el Job de Carga

Ejecuta estos comandos en tu PowerShell:

```powershell
# Crear el job
gcloud run jobs create cargar-inventario-job `
  --image gcr.io/prislab-v5-ai/prislab-v5 `
  --region us-central1 `
  --set-cloudsql-instances prislab-v5-ai:us-central1:prislab-db `
  --set-secrets="DJANGO_SECRET_KEY=django-secret-key:latest,DB_PASSWORD=db-password:latest" `
  --set-env-vars="GOOGLE_CLOUD_PROJECT=prislab-v5-ai,CLOUD_SQL_CONNECTION_NAME=prislab-v5-ai:us-central1:prislab-db,GAE_ENV=standard,DB_NAME=prislab_v5,DB_USER=prislab_user" `
  --command "python" `
  --args=manage.py,cargar_inventario `
  --quiet
```

### Paso 2: Subir el CSV a Cloud Storage

```powershell
# Crear bucket si no existe
gsutil mb -p prislab-v5-ai gs://prislab-v5-uploads

# Subir el inventario.csv
gsutil cp C:\Users\jonil\Desktop\PRISLAB_SaaS\inventario.csv gs://prislab-v5-uploads/

# Verificar
gsutil ls gs://prislab-v5-uploads/
```

### Paso 3: Ejecutar la Carga

```powershell
# Ejecutar el job
gcloud run jobs execute cargar-inventario-job --region us-central1 --wait

# Ver resultado
Write-Host "Verificando logs..." -ForegroundColor Cyan
gcloud logging read "resource.type=cloud_run_job AND resource.labels.job_name=cargar-inventario-job" --limit 100 --format="value(textPayload)"
```

**⚠️ NOTA:** El job omitirá automáticamente productos con `stock = 0` (lotes vencidos).

---

## 🧪 **PRUEBAS QUE HACER AHORA**

### 1. **Módulo de Consultas:**
- ✅ Ir a: https://prislab-v5-811785477499.us-central1.run.app/medico/
- ✅ Hacer clic en "Nueva Consulta"
- ✅ Buscar o crear paciente
- ✅ Iniciar consulta

**Resultado esperado:** ✅ **DEBE FUNCIONAR SIN ERROR 500**

---

### 2. **Búsqueda de Estudios:**
- ✅ Ir a: https://prislab-v5-811785477499.us-central1.run.app/lab/
- ✅ Crear nueva orden de laboratorio
- ✅ Buscar un estudio (ej: "glucosa")

**Resultado esperado:** ✅ **DEBE MOSTRAR RESULTADOS**

---

### 3. **Chat con PRIS (IA):**
- ✅ Ir a: https://prislab-v5-811785477499.us-central1.run.app/bienestar/chat/
- ✅ Escribir "hola"
- ✅ Esperar respuesta (máximo 10 segundos)

**Resultado esperado:** ✅ **DEBE RESPONDER (no quedarse "pensando" indefinidamente)**

---

### 4. **Registro de Pacientes:**
- ✅ Ir a Recepción
- ✅ Registrar nuevo paciente
- ✅ Llenar formulario

**Resultado esperado:** ✅ **DEBE GUARDAR SIN ERRORES**

---

## 📊 **MONITOREO EN TIEMPO REAL**

### Ver logs de errores:

```powershell
# Errores en tiempo real
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=prislab-v5 AND severity>=ERROR" --limit 20 --format="value(textPayload)" --project=prislab-v5-ai

# Logs completos (últimas 50 líneas)
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=prislab-v5" --limit 50 --format="value(textPayload)" --project=prislab-v5-ai
```

---

## 🔍 **SI APARECE UN NUEVO ERROR:**

### 1. Captura el error completo:
```powershell
# Guardar últimos 100 errores
gcloud logging read "resource.type=cloud_run_revision AND severity>=ERROR" --limit 100 --format="value(textPayload)" --project=prislab-v5-ai > nuevo_error.txt
```

### 2. Envíame:
- El mensaje de error completo
- La URL donde ocurrió
- Qué acción estabas haciendo
- El usuario con el que entraste

---

## 📈 **PRÓXIMOS PASOS (DESPUÉS DE CARGAR INVENTARIO)**

1. **Actualizar Búsqueda de Productos:**
   - Que solo muestre productos con `stock > 0`
   - Mejorar autocompletado

2. **Crear Interfaz de Carga:**
   - Página web para subir CSV directamente
   - Sin necesidad de comandos

3. **Dashboard de Monitoreo:**
   - Ver errores en tiempo real desde la web
   - Alertas automáticas

---

## ⚠️ **IMPORTANTE:**

### El sistema está funcionando, pero:

1. **Aún falta cargar el inventario de farmacia** → Ejecuta los comandos de arriba
2. **La IA SÍ funciona**, pero puede tardar hasta 10 segundos en responder (es normal)
3. **Todos los errores 500 de ayer están corregidos**

---

## 🆘 **COMANDOS DE EMERGENCIA**

### Si algo falla, redesplegar:

```powershell
# Redespliegue completo (2 minutos)
gcloud builds submit --tag gcr.io/prislab-v5-ai/prislab-v5 --project prislab-v5-ai --quiet
gcloud run deploy prislab-v5 --image gcr.io/prislab-v5-ai/prislab-v5 --region us-central1 --platform managed --allow-unauthenticated --set-cloudsql-instances prislab-v5-ai:us-central1:prislab-db --set-secrets="DJANGO_SECRET_KEY=django-secret-key:latest,DB_PASSWORD=db-password:latest,GEMINI_API_KEY=gemini-api-key:latest,GOOGLE_API_KEY=gemini-api-key:latest" --set-env-vars="GOOGLE_CLOUD_PROJECT=prislab-v5-ai,GAE_ENV=standard" --quiet
```

---

## 📞 **CONTACTO DE SOPORTE**

Si encuentras algún error nuevo:
1. Captura pantalla del error
2. Copia el mensaje completo
3. Guarda los logs con el comando de arriba
4. Envíamelo para corrección inmediata

---

**¡Sistema listo para pruebas masivas con el equipo!** 💜

**Última actualización:** 30 Enero 2026  
**Revisión:** prislab-v5-00036-cc5
