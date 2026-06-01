# 🎯 ESTRATEGIA EFICIENTE PARA COMPLETAR LO PENDIENTE

**Fecha:** 2026-01-23  
**Objetivo:** Completar lo crítico de la manera más eficiente posible  
**Tiempo estimado:** 2-3 horas de desarrollo

---

## 📊 ANÁLISIS DE PRIORIDADES (Basado en tu feedback)

### ✅ NO URGENTE (Postergar)
- ❌ Facturación
- ❌ Interfazar equipos (trabajan sin interfaz por ahora)
- ❌ Transferencias entre sucursales (no transfieren nada)
- ❌ Impresoras (no usarán el lunes)

### ✅ SÍ URGENTE (Completar)
- ✅ **Dashboard Unificado** (crítico para pruebas y visualización)
- ✅ **Templates de Notificaciones** (sistema completo pero sin UI)
- ✅ **Integración Marketing-Ventas en PDV** (backend listo, falta UI)
- ✅ **Integración Consultorio-Laboratorio** (backend listo, falta UI)
- ✅ **Reportes Financieros** (solo para dueño, pero importante)

---

## 🚀 PLAN DE ACCIÓN PRIORIZADO

### **FASE 1: CRÍTICO (30-45 min) - Hacer PRIMERO**

#### 1.1. Template Dashboard Unificado
**Prioridad:** 🔴 CRÍTICA  
**Tiempo:** 15-20 min  
**Archivo:** `core/templates/core/dashboard_unificado.html`

**Qué hacer:**
- Crear template basado en `core/templates/core/analytics/dashboard.html`
- Mostrar todos los KPIs de forma visual
- Gráficas con Chart.js (ya está en analytics)
- Diseño limpio y profesional

**Impacto:** Permite probar el dashboard unificado inmediatamente

---

#### 1.2. Template Básico de Notificaciones (Lista)
**Prioridad:** 🔴 CRÍTICA  
**Tiempo:** 10-15 min  
**Archivo:** `core/templates/core/notificaciones/lista.html`

**Qué hacer:**
- Template simple con lista de notificaciones
- Badge de contador de no leídas
- Botón para marcar como leída
- Filtros básicos (tipo, prioridad, leída)

**Impacto:** Permite ver y gestionar notificaciones

---

#### 1.3. Badge de Notificaciones en Base Template
**Prioridad:** 🔴 CRÍTICA  
**Tiempo:** 5-10 min  
**Archivo:** `core/templates/base.html` (o donde esté el navbar)

**Qué hacer:**
- Agregar badge de notificaciones en el navbar
- Llamar a `/notificaciones/api/no-leidas/` cada 30 segundos
- Mostrar contador de no leídas
- Link a `/notificaciones/`

**Impacto:** Notificaciones visibles en toda la aplicación

---

### **FASE 2: IMPORTANTE (45-60 min) - Hacer DESPUÉS**

#### 2.1. Campo de Cupón en PDV
**Prioridad:** 🟡 IMPORTANTE  
**Tiempo:** 15-20 min  
**Archivo:** `core/templates/core/pdv_farmacia.html`

**Qué hacer:**
- Agregar campo de texto "Código de Cupón" en el formulario de venta
- Botón "Aplicar Cupón" que valida y aplica descuento
- Mostrar descuento aplicado visualmente
- Enviar `codigo_cupon` en el POST de venta

**Impacto:** Integración Marketing-Ventas completamente funcional

---

#### 2.2. Botón Crear Orden Lab en Consulta
**Prioridad:** 🟡 IMPORTANTE  
**Tiempo:** 15-20 min  
**Archivo:** `consultorio/templates/consultorio/captura_consulta.html`

**Qué hacer:**
- Agregar sección "Solicitar Estudios de Laboratorio"
- Selector múltiple de estudios disponibles
- Botón "Crear Orden de Laboratorio"
- Modal o formulario para crear orden
- Mostrar órdenes creadas desde esta consulta

**Impacto:** Integración Consultorio-Laboratorio completamente funcional

---

#### 2.3. Template de Configuración de Notificaciones
**Prioridad:** 🟡 IMPORTANTE  
**Tiempo:** 10-15 min  
**Archivo:** `core/templates/core/notificaciones/configurar.html`

**Qué hacer:**
- Formulario con todos los campos de `ConfiguracionNotificaciones`
- Checkboxes para habilitar/deshabilitar alertas
- Campos numéricos para umbrales
- Guardar y mostrar mensaje de éxito

**Impacto:** Permite configurar alertas automáticas

---

### **FASE 3: MEJORAS (Opcional, si hay tiempo)**

#### 3.1. Mejorar Template de Analytics
**Prioridad:** 🟢 OPCIONAL  
**Tiempo:** 10-15 min  
**Archivo:** `core/templates/core/analytics/dashboard.html`

**Qué hacer:**
- Agregar sección de análisis predictivo visual
- Mostrar productos en riesgo
- Mejorar diseño de gráficas

---

## 📝 CHECKLIST DE IMPLEMENTACIÓN

### Fase 1 (Crítico)
- [ ] Crear `core/templates/core/dashboard_unificado.html`
- [ ] Crear `core/templates/core/notificaciones/lista.html`
- [ ] Agregar badge de notificaciones en `base.html`

### Fase 2 (Importante)
- [ ] Agregar campo de cupón en `pdv_farmacia.html`
- [ ] Agregar botón crear orden lab en `captura_consulta.html`
- [ ] Crear `core/templates/core/notificaciones/configurar.html`

### Fase 3 (Opcional)
- [ ] Mejorar template de analytics

---

## ⚡ ORDEN DE EJECUCIÓN RECOMENDADO

1. **Dashboard Unificado** (más crítico para pruebas)
2. **Lista de Notificaciones** (sistema completo)
3. **Badge de Notificaciones** (visibilidad)
4. **Campo de Cupón en PDV** (integración visible)
5. **Botón Crear Orden Lab** (integración visible)
6. **Configuración de Notificaciones** (completar sistema)

---

## 🎯 RESULTADO ESPERADO

Al finalizar esta estrategia tendrás:
- ✅ Dashboard Unificado completamente funcional y visible
- ✅ Sistema de Notificaciones con UI completa
- ✅ Integración Marketing-Ventas visible en PDV
- ✅ Integración Consultorio-Laboratorio visible en consulta
- ✅ Sistema listo para pruebas completas

**Tiempo Total Estimado:** 1.5 - 2 horas de desarrollo enfocado

---

## 💡 RECOMENDACIÓN FINAL

**Ejecuta Fase 1 COMPLETA primero** (Dashboard + Notificaciones básicas). Esto te dará:
- Visibilidad completa del sistema
- Capacidad de probar todas las funcionalidades
- Base sólida para continuar

Luego, **Fase 2** completa las integraciones visibles.

**Fase 3 es opcional** y puede hacerse después de las pruebas iniciales.
