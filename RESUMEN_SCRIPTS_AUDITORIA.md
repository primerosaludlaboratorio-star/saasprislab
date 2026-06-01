# 📋 SCRIPTS DE AUDITORÍA Y VERIFICACIÓN DEL SISTEMA

## 🔍 Scripts Disponibles

### 1. **Auditoría Completa del Sistema** (`auditar_sistema`)

**Comando:**
```bash
python manage.py auditar_sistema
```

**Qué verifica:**
- ✅ **Modelos**: Todos los modelos, campos y registros
- ✅ **Vistas**: Todas las vistas implementadas por módulo
- ✅ **URLs**: Todas las rutas configuradas
- ✅ **Migraciones**: Estado de migraciones por app
- ✅ **Dependencias**: Paquetes instalados y versiones
- ✅ **Archivos Media**: Directorios y archivos multimedia
- ✅ **Funcionalidades**: Estado de funcionalidades críticas

**Salida:**
- Lista detallada de cada componente
- Resumen final con estadísticas
- Estado general del sistema

---

### 2. **Verificación Rápida** (`verificar_funcionalidades`)

**Comando:**
```bash
python manage.py verificar_funcionalidades
```

**Qué verifica:**
- ✅ Multi-Tenant (Empresas activas)
- ✅ FEFO (Lotes)
- ✅ Auditoría Forense (Logs)
- ✅ Triple Llave (Órdenes)
- ✅ Perfiles Laboratorio
- ✅ Backup Nocturno
- ✅ Receta Digital 4.0
- ✅ RH - Bitácora 39-A

**Salida:**
- Estado OK/Error de cada funcionalidad
- Resumen rápido
- Sin detalles extensos

---

### 3. **Script Rápido Standalone** (`verificar_estado_sistema.py`)

**Comando:**
```bash
python verificar_estado_sistema.py
```

**Qué hace:**
- Ejecuta la auditoría completa sin necesidad de usar `manage.py`
- Útil para scripts externos o automatización

---

## 📊 Comparación de Scripts

| Característica | `auditar_sistema` | `verificar_funcionalidades` | `verificar_estado_sistema.py` |
|----------------|-------------------|----------------------------|-------------------------------|
| **Detalle** | ⭐⭐⭐ Completo | ⭐⭐ Rápido | ⭐⭐⭐ Completo |
| **Tiempo** | ~30-60s | ~5-10s | ~30-60s |
| **Modelos** | ✅ Sí | ❌ No | ✅ Sí |
| **Vistas** | ✅ Sí | ❌ No | ✅ Sí |
| **URLs** | ✅ Sí | ❌ No | ✅ Sí |
| **Funcionalidades** | ✅ Sí | ✅ Sí | ✅ Sí |

---

## 🚀 Uso Recomendado

### **Para Desarrollo Diario:**
```bash
python manage.py verificar_funcionalidades
```

### **Para Auditoría Completa:**
```bash
python manage.py auditar_sistema
```

### **Para Scripts Automatizados:**
```bash
python verificar_estado_sistema.py
```

---

## ✅ Verificaciones Realizadas

### **Modelos Verificados:**
- `core`: Empresa, Sucursal, Usuario, Producto, Venta, Paciente, Lote, etc.
- `laboratorio`: Estudio, PerfilLaboratorio, Orden, DetalleOrden
- `pacientes`: Modelos de pacientes
- `seguridad`: ConfiguracionSeguridad, AlertaPanico
- `iot`: Kiosco, VerificacionKiosco
- `ia`: TranscripcionVoz, CotizacionOCR

### **Funcionalidades Verificadas:**
1. ✅ Multi-Tenant (Aislamiento por empresa)
2. ✅ FEFO (First Expired, First Out)
3. ✅ Auditoría Forense (SHA-256)
4. ✅ Triple Llave (WhatsApp)
5. ✅ Perfiles de Laboratorio
6. ✅ Backup Nocturno (AES-256)
7. ✅ Receta Digital 4.0 (QR)
8. ✅ RH - Bitácora 39-A

### **Dependencias Verificadas:**
- Django
- qrcode
- reportlab
- cryptography
- pillow
- pandas
- openpyxl
- selenium
- psycopg2-binary

---

## 📝 Ejemplo de Salida

### **Auditoría Completa:**
```
================================================================================
🔍 AUDITORÍA COMPLETA DEL SISTEMA PRISLAB
================================================================================

📦 AUDITANDO MODELOS...
   ✅ core.Empresa - 12 campos, 1 registros
   ✅ core.Producto - 25 campos, 150 registros
   ...

📄 AUDITANDO VISTAS...
   ✅ farmacia.pdv_farmacia
   ✅ farmacia.lista_ventas_farmacia
   ...

🌐 AUDITANDO URLs...
   ✅ /farmacia/pdv/ -> pdv_farmacia
   ✅ /laboratorio/recepcion/ -> recepcion_lab
   ...

================================================================================
📊 REPORTE FINAL DE AUDITORÍA
================================================================================
📦 MODELOS: 45 modelos, 1,250 registros totales
📄 VISTAS: 38 vistas implementadas
🌐 URLs: 42 rutas configuradas
🔄 MIGRACIONES: 15 archivos de migración
📚 DEPENDENCIAS: 9/9 instaladas
📁 MEDIA: 125 archivos (45.32 MB)
⚙️  FUNCIONALIDADES: 8/8 implementadas

================================================================================
✅ ESTADO DEL SISTEMA: OPTIMO
================================================================================
```

### **Verificación Rápida:**
```
================================================================================
⚡ VERIFICACIÓN RÁPIDA DE FUNCIONALIDADES
================================================================================

✅ Multi-Tenant: OK
✅ FEFO: OK
✅ Auditoría Forense: OK
✅ Triple Llave: OK
✅ Perfiles Laboratorio: OK
✅ Backup Nocturno: OK
✅ Receta Digital 4.0: OK
✅ RH - Bitácora 39-A: OK

================================================================================
RESUMEN: 8/8 verificaciones exitosas
🎉 TODAS LAS FUNCIONALIDADES OPERATIVAS
================================================================================
```

---

## 🔧 Troubleshooting

### **Si un modelo no aparece:**
- Verificar que la app esté en `INSTALLED_APPS`
- Verificar que el modelo esté en el archivo `models.py`

### **Si una funcionalidad marca error:**
- Verificar que las migraciones estén aplicadas
- Verificar que los modelos necesarios existan
- Revisar los logs de error para más detalles

### **Si una dependencia no está instalada:**
```bash
pip install -r requirements.txt
```

---

**✅ TODOS LOS SCRIPTS LISTOS PARA USO**
