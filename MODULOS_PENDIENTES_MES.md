# 📋 MÓDULOS PENDIENTES PARA TRABAJAR EN EL MES

**Fecha de Creación:** 2026-01-23  
**Propósito:** Lista clara de módulos pendientes para trabajar con calma durante el mes  
**Estado Actual:** Sistema funcional, estos módulos son mejoras y optimizaciones

---

## 🟡 MÓDULOS PARCIALES (Funcionales pero Mejorables)

### **1. EJECUCIÓN AUTOMÁTICA DE VERIFICACIONES**
**Estado:** Funciones implementadas, falta automatización  
**Ubicación:** `core/utils/notificaciones.py` - `ejecutar_verificaciones_automaticas()`

**Qué falta:**
- Configurar cron job o tarea programada para ejecutar verificaciones periódicamente
- Recomendación: Cada hora o cada 6 horas
- Opciones: Django-crontab, Celery, o tarea programada del sistema

**Impacto:** Las verificaciones de stock bajo, caducidades, etc. deben ejecutarse manualmente

---

### **2. NOTIFICACIONES PUSH (Webhooks)**
**Estado:** Estructura lista, falta implementación de envío  
**Ubicación:** `core/models.py` - Modelo `Notificacion`

**Qué falta:**
- Implementar envío de notificaciones push vía webhook
- Integración con servicios externos (Firebase Cloud Messaging, OneSignal, etc.)
- Configuración de webhooks en `ConfiguracionNotificaciones`

**Impacto:** Las notificaciones se crean en BD pero no se envían como push automático

---

## 🔴 MÓDULOS PENDIENTES (No Urgentes - Para Trabajar con Calma)

### **1. MEJORAS DE UX/UI**

#### **1.1. Diseño Unificado**
**Qué falta:**
- CSS/JS compartido entre módulos
- Estilos consistentes en todos los templates
- Variables CSS centralizadas

**Archivos a crear/modificar:**
- `core/static/css/prislab_unified.css` (mejorar el existente)
- Unificar paleta de colores entre módulos

---

#### **1.2. Responsividad Móvil**
**Qué falta:**
- Optimizaciones específicas para dispositivos móviles
- Mejoras en tablas para móvil (scroll horizontal, cards)
- Menús adaptativos mejorados
- Touch gestures para operaciones frecuentes

**Nota:** Bootstrap responsive existe, pero se pueden hacer optimizaciones específicas

---

#### **1.3. Atajos de Teclado**
**Qué falta:**
- Sistema de atajos de teclado para operaciones frecuentes
- Ejemplos:
  - `Ctrl+N` - Nueva venta
  - `Ctrl+B` - Buscar producto
  - `Ctrl+P` - Imprimir
  - `F8` - Imprimir ticket (ya existe en algunos lugares)
  - `Esc` - Cerrar modales

**Archivo a crear:**
- `core/static/js/keyboard_shortcuts.js`

---

### **2. OPTIMIZACIONES**

#### **2.1. Caché de Métricas**
**Qué falta:**
- Implementar caché para métricas de analytics
- Reducir carga en consultas pesadas
- Usar Django cache framework (Redis o Memcached)

**Impacto:** Mejora de rendimiento en dashboards con muchos datos

---

#### **2.2. Índices Adicionales**
**Qué falta:**
- Revisar consultas lentas
- Agregar índices adicionales en modelos si es necesario
- Optimizar queries con `select_related` y `prefetch_related`

**Impacto:** Mejora de rendimiento en consultas complejas

---

## 🚫 MÓDULOS NO URGENTES (Postergados según tu indicación)

### **1. FACTURACIÓN**
**Estado:** No urgente  
**Nota:** Postergado según tu indicación

---

### **2. INTERFAZAR EQUIPOS (HL7/ASTM)**
**Estado:** No urgente - Trabajan sin interfaz por ahora  
**Ubicación:** Módulo Laboratorio

**Qué falta:**
- Conexión automática con equipos de laboratorio
- Protocolos HL7/ASTM
- Recepción automática de resultados

**Nota:** Postergado - Trabajan manualmente por ahora

---

### **3. TRANSFERENCIAS ENTRE SUCURSALES**
**Estado:** No urgente - No transfieren nada entre sucursales  
**Nota:** Backend completo, pero no se usa actualmente

---

### **4. IMPRESORAS TÉRMICAS**
**Estado:** No urgente - No usarán el lunes  
**Nota:** Postergado hasta que inicien el sistema

---

## 📊 RESUMEN POR PRIORIDAD

### **PRIORIDAD MEDIA (Trabajar este mes)**
1. ✅ Ejecución Automática de Verificaciones (Cron Job)
2. ✅ Notificaciones Push (Webhooks)
3. ✅ Mejoras de UX/UI (Diseño Unificado, Responsividad, Atajos)

### **PRIORIDAD BAJA (Mejoras/Optimizaciones)**
4. ✅ Caché de Métricas
5. ✅ Índices Adicionales

### **NO URGENTE (Postergado)**
- Facturación
- Interfazar Equipos
- Transferencias entre Sucursales
- Impresoras Térmicas

---

## 🎯 PLAN DE TRABAJO SUGERIDO PARA EL MES

### **Semana 1-2: Automatización**
- [ ] Configurar cron job para verificaciones automáticas
- [ ] Implementar notificaciones push (Firebase o OneSignal)

### **Semana 3: UX/UI**
- [ ] Unificar diseño entre módulos
- [ ] Mejorar responsividad móvil
- [ ] Implementar atajos de teclado

### **Semana 4: Optimizaciones**
- [ ] Implementar caché de métricas
- [ ] Revisar y optimizar índices de BD
- [ ] Pruebas de rendimiento

---

## 📝 NOTAS IMPORTANTES

- **Todo lo crítico está implementado y funcional**
- **Estos módulos son mejoras y optimizaciones**
- **No bloquean la operación del sistema**
- **Pueden trabajarse con calma durante el mes**

---

**Última Actualización:** 2026-01-23
