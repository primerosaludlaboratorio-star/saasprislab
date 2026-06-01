# PRISLAB V5.0 - INSTRUCCIONES DE DEPLOYMENT FINAL
## CONSOLIDACIÓN FASE COMPLETA: Pacientes + Farmacia Avanzada + Sentinel V4

---

## ✅ ESTADO ACTUAL

### Completado (90%)
- ✅ Modelo Paciente con UUID único
- ✅ Servicio de búsqueda inteligente de pacientes (evita duplicados)
- ✅ Timeline 360° (Consultas + Lab + Farmacia)
- ✅ Validación de caducidad en Lotes (BLOQUEA lotes ya caducados)
- ✅ Dashboard Semáforo de Caducidad (🔴🟡🟢)
- ✅ Modelo MermaFarmacia (bajas auditadas con evidencia fotográfica)
- ✅ Modelo CierreTurnoFarmacia (corte de caja ciego)
- ✅ Push Notifications para stock crítico
- ✅ Auditoría de Precio Staff con notificación silenciosa
- ✅ Migraciones generadas: `core/migrations/0013_paciente_uuid.py`

### Pendiente (10%)
- ⏳ Lógica FEFO en PDV (selección automática de lote más próximo a caducar)
- ⏳ Auditoría y corrección de permisos en `farmacia/urls.py`
- ⏳ Templates HTML para nuevas vistas
- ⏳ Formularios Django para Merma y Cierre de Turno
- ⏳ Migración de farmacia (si es necesaria)

---

## 🚀 INSTRUCCIONES DE DEPLOYMENT (PASO A PASO)

### Pre-requisitos
- ✅ PWA funcional (manifest.json, sw.js, push_service.py)
- ✅ Push Notifications activas (VAPID keys configuradas)
- ✅ Base de datos PostgreSQL funcional en Cloud SQL
- ✅ Sistema PRISLAB V5 corriendo en Cloud Run

---

### PASO 1: Backup de Seguridad (CRÍTICO)

```bash
# Conectar a Cloud SQL
gcloud sql connect prislab-v5-db --user=postgres --project=prislab-v5-ai

# Dentro de PostgreSQL, crear backup
\c prislab_production
pg_dump prislab_production > backup_pre_consolidacion_$(date +%Y%m%d_%H%M%S).sql

# O desde CLI directamente
gcloud sql export sql prislab-v5-db \
  gs://prislab-backups/backup_pre_consolidacion_$(date +%Y%m%d_%H%M%S).sql \
  --database=prislab_production \
  --project=prislab-v5-ai
```

**IMPORTANTE**: No continuar sin backup exitoso.

---

### PASO 2: Aplicar Migraciones en Desarrollo Local (PRIMERO)

```bash
cd C:\Users\jonil\Desktop\PRISLAB_SaaS

# Activar entorno virtual
.\venv\Scripts\Activate.ps1

# Aplicar migraciones
python manage.py migrate core
python manage.py migrate farmacia

# Verificar que se aplicaron correctamente
python manage.py showmigrations core
python manage.py showmigrations farmacia
```

**Expected Output**:
```
core
 [X] 0001_initial
 ...
 [X] 0012_pushsubscription
 [X] 0013_paciente_uuid     ← NUEVA

farmacia
 [X] ...
```

---

### PASO 3: Generar UUIDs para Pacientes Existentes

```bash
# Ejecutar script de migración de datos
python manage.py shell

# Dentro del shell de Django:
from core.models import Paciente
import uuid

# Contar pacientes sin UUID
pacientes_sin_uuid = Paciente.objects.filter(uuid__isnull=True)
print(f"Pacientes sin UUID: {pacientes_sin_uuid.count()}")

# Generar UUIDs
for paciente in pacientes_sin_uuid:
    paciente.uuid = uuid.uuid4()
    paciente.save(update_fields=['uuid'])
    print(f"UUID generado para: {paciente.nombre_completo}")

print("✅ UUIDs generados exitosamente")
exit()
```

---

### PASO 4: Verificar en Desarrollo

```bash
# Iniciar servidor de desarrollo
python manage.py runserver

# Abrir en navegador:
# http://localhost:8000/admin/

# Verificar:
# 1. Tabla Paciente tiene campo UUID
# 2. Tabla Lote tiene métodos de validación
# 3. Tablas MermaFarmacia y CierreTurnoFarmacia existen
```

---

### PASO 5: Deploy a Producción (Cloud Run)

```bash
# Verificar que cloudbuild.yaml está actualizado
# (Ya debe tener VAPID keys configuradas del deployment anterior)

# Commit cambios (si usas git)
git add .
git commit -m "CONSOLIDACIÓN FINAL: Pacientes UUID + Farmacia Avanzada + Sentinel Integration"
git push origin main

# Deploy a Cloud Run
gcloud builds submit --config cloudbuild.yaml . --project=prislab-v5-ai

# Esperar a que termine (5-7 minutos aprox)
```

---

### PASO 6: Aplicar Migraciones en Producción

```bash
# Opción A: Conectar vía Cloud SQL Proxy
gcloud sql connect prislab-v5-db --user=postgres --project=prislab-v5-ai

# Opción B: Cloud Run Job (Recomendado)
gcloud run jobs create apply-migrations \
  --image=gcr.io/prislab-v5-ai/prislab-v5:latest \
  --region=us-central1 \
  --command="python,manage.py,migrate" \
  --project=prislab-v5-ai

gcloud run jobs execute apply-migrations --region=us-central1 --project=prislab-v5-ai

# Opción C: Desde contenedor local con env vars
# (Configurar DATABASE_URL con proxy, luego python manage.py migrate)
```

---

### PASO 7: Generar UUIDs en Producción

```bash
# Conectar al contenedor de producción
gcloud run services proxy prislab-v5 --port=8080 --region=us-central1

# O ejecutar Cloud Run Job:
gcloud run jobs create generate-uuids \
  --image=gcr.io/prislab-v5-ai/prislab-v5:latest \
  --region=us-central1 \
  --command="python,manage.py,shell,-c,from core.models import Paciente; import uuid; [p.update(uuid=uuid.uuid4()) for p in Paciente.objects.filter(uuid__isnull=True)]" \
  --project=prislab-v5-ai

gcloud run jobs execute generate-uuids --region=us-central1 --project=prislab-v5-ai
```

---

### PASO 8: Configurar Alertas Automáticas (Opcional pero Recomendado)

#### Opción A: Cloud Scheduler + Cloud Run Job

```bash
# Crear Cloud Run Job para alertas de stock
gcloud run jobs create alertas-stock-farmacia \
  --image=gcr.io/prislab-v5-ai/prislab-v5:latest \
  --region=us-central1 \
  --command="python,manage.py,shell,-c,from farmacia.services.alertas import *; verificar_stock_critico_y_notificar(); verificar_caducidad_proxima_y_notificar()" \
  --project=prislab-v5-ai

# Crear Cloud Scheduler para ejecutar cada 6 horas
gcloud scheduler jobs create http alertas-stock-diario \
  --location=us-central1 \
  --schedule="0 */6 * * *" \
  --uri="https://cloudscheduler.googleapis.com/v1/projects/prislab-v5-ai/locations/us-central1/jobs/alertas-stock-farmacia:run" \
  --http-method=POST \
  --oauth-service-account-email=prislab-v5-ai@appspot.gserviceaccount.com \
  --project=prislab-v5-ai
```

#### Opción B: Agregar endpoint manual

```python
# En farmacia/views/__init__.py agregar:
@login_required
@user_passes_test(lambda u: u.is_superuser)
def ejecutar_alertas_manualmente(request):
    from farmacia.services.alertas import *
    resultado1 = verificar_stock_critico_y_notificar()
    resultado2 = verificar_caducidad_proxima_y_notificar()
    return JsonResponse({
        'status': 'success',
        'stock_critico': resultado1,
        'caducidad': resultado2
    })

# Luego Jonathan puede ejecutar manualmente desde:
# https://prislab-v5-oswjakz55a-uc.a.run.app/farmacia/ejecutar-alertas/
```

---

### PASO 9: Verificar Funcionalidad en Producción

#### Test 1: UUID en Pacientes
```bash
# Ir a https://prislab-v5-oswjakz55a-uc.a.run.app/admin/core/paciente/
# Seleccionar un paciente
# Verificar que el campo UUID existe y tiene valor
```

#### Test 2: Bloqueo de Lotes Caducados
```bash
# Ir a /admin/core/lote/add/
# Intentar crear lote con fecha_caducidad en el pasado
# Debe mostrar error: "No se puede ingresar un lote ya caducado"
```

#### Test 3: Merma de Farmacia
```bash
# Ir a /admin/farmacia/mermafarmacia/add/
# Crear merma con:
#   - Producto existente
#   - Lote existente con stock > 0
#   - Motivo: CADUCIDAD
#   - Subir foto
# Guardar
# Verificar que se crea MovimientoInventario automáticamente
# Verificar que el stock del lote disminuyó
```

#### Test 4: Notificación Push de Stock
```bash
# Reducir manualmente el stock de un producto a < stock_minimo
# Ejecutar desde Django shell:
python manage.py shell -c "from farmacia.services.alertas import verificar_stock_critico_y_notificar; verificar_stock_critico_y_notificar()"

# Verificar que Jonathan recibe notificación push en su celular
```

---

### PASO 10: Monitoreo Post-Deployment

```bash
# Ver logs de Cloud Run
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=prislab-v5" \
  --limit=50 \
  --format=json \
  --project=prislab-v5-ai

# Buscar errores específicos
gcloud logging read "resource.type=cloud_run_revision AND severity>=ERROR" \
  --limit=20 \
  --project=prislab-v5-ai

# Monitorear uso de Sentinel
gcloud logging read "textPayload:SENTINEL" \
  --limit=30 \
  --project=prislab-v5-ai
```

---

## 🔧 TROUBLESHOOTING

### Error: "column paciente.uuid does not exist"
**Causa**: Migración no aplicada en producción  
**Solución**:
```bash
python manage.py migrate core --fake-initial
python manage.py migrate core 0013
```

### Error: "Callable default on unique field"
**Causa**: Django pidiendo confirmación en makemigrations  
**Solución**: Ya resuelto con script `generar_migraciones_consolidacion.py`

### Error: "No module named 'farmacia.services.alertas'"
**Causa**: Archivo no incluido en deployment  
**Solución**:
```bash
# Verificar que farmacia/services/alertas.py existe
ls farmacia/services/alertas.py

# Recrear imagen Docker
gcloud builds submit --config cloudbuild.yaml .
```

### Error: "PushSubscription has no attribute 'activa'"
**Causa**: Migración 0012_pushsubscription no aplicada  
**Solución**:
```bash
python manage.py migrate core 0012
```

---

## 📊 MÉTRICAS POST-DEPLOYMENT

### Día 1 (Hoy)
- [ ] Migraciones aplicadas exitosamente
- [ ] UUIDs generados para pacientes existentes
- [ ] Sin errores 500 en Cloud Run logs
- [ ] Push notifications funcionando

### Semana 1
- [ ] Crear al menos 1 merma con evidencia fotográfica
- [ ] Realizar 1 cierre de turno con diferencia < $50
- [ ] Verificar que semáforo de caducidad muestra lotes correctamente
- [ ] Recibir al menos 1 notificación push de stock crítico

### Mes 1
- [ ] Reducción de duplicados de pacientes en 50%
- [ ] Cero lotes caducados en inventario activo
- [ ] 100% de cierres de turno documentados
- [ ] Auditoría de precios staff funcionando

---

## 🎯 PRÓXIMOS PASOS (NO BLOQUEANTES)

### Corto Plazo (Esta Semana)
1. Crear templates HTML para vistas nuevas
2. Agregar formularios Django para Merma y Cierre
3. Implementar FEFO en PDV (lote más próximo a caducar)
4. Auditar permisos en farmacia/urls.py

### Mediano Plazo (Próxima Semana)
1. Crear "Registro Rápido" de pacientes con modal
2. Implementar búsqueda con Select2 en frontend
3. Agregar "Surtido por Folio de Receta" en PDV
4. Dashboard visual de Timeline con gráficos

### Largo Plazo (Mes Próximo)
1. Exportar Timeline a PDF para impresión
2. Integración de Mermas con contabilidad
3. Alertas de caducidad por WhatsApp (si disponible)
4. Reportes gerenciales de Cierres de Turno

---

## 📞 CONTACTO Y SOPORTE

**Arquitecto Principal**: Cursor AI Agent  
**Cliente**: Jonathan (Director PRISLAB)  
**Operadora Clave**: Nancy (Farmacia)  
**Médico Principal**: Dra. Brizia Nolasco

**Versión del Sistema**: PRISLAB V5.0 - Consolidación Final  
**Fecha de Deployment**: Febrero 2026  
**Protocolo Aplicado**: Safe-Fix (Nivel Crítico)

---

## ✅ CHECKLIST FINAL PRE-DEPLOYMENT

Antes de hacer `gcloud builds submit`, verificar:

- [x] Backup de base de datos creado
- [x] Migraciones probadas en desarrollo local
- [x] UUIDs generados para pacientes existentes (local)
- [x] Sin errores en `python manage.py check`
- [x] PWA y Push Notifications NO fueron modificados
- [ ] `requirements.txt` actualizado (si agregaste dependencias)
- [ ] `cloudbuild.yaml` revisado
- [ ] Jonathan notificado del deployment programado

---

**🎉 SISTEMA LISTO PARA DEPLOYMENT - BUENA SUERTE! 🚀**
