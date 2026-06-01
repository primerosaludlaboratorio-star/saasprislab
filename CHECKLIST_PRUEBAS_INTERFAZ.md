# ✅ CHECKLIST MAESTRA: PREPARACIÓN PARA PRUEBAS DE INTERFAZ
**Sistema:** PRISLAB V5.0 OMEGA  
**Fecha:** 26 de Enero de 2026  
**Objetivo:** Verificar que los 3 módulos aprobados estén listos para pruebas con personal

---

## 📋 ÍNDICE DE VERIFICACIÓN

1. [Módulo Farmacia/POS](#módulo-farmaciapos)
2. [Módulo Laboratorio Clínico](#módulo-laboratorio-clínico)
3. [Módulo Consultorio Médico](#módulo-consultorio-médico)
4. [Infraestructura y Seguridad](#infraestructura-y-seguridad)
5. [Capacitación y Documentación](#capacitación-y-documentación)
6. [Plan de Pruebas](#plan-de-pruebas)

---

# MÓDULO FARMACIA/POS

## ✅ FUNCIONALIDAD CORE

### Punto de Venta (POS)
- [x] Búsqueda de productos por nombre
- [x] Búsqueda por código de barras
- [x] Agregar productos al carrito
- [x] Modificar cantidades
- [x] Aplicar descuentos
- [x] Selección de lote y caducidad
- [x] Múltiples formas de pago
- [x] Imprimir ticket de venta
- [x] Generar factura electrónica
- [x] Registro de cliente

### Sistema Kardex
- [x] Movimientos de entrada
- [x] Movimientos de salida
- [x] Ajustes de inventario
- [x] Consulta de saldos
- [x] Historial por producto
- [x] Filtros por fecha/tipo

### Alertas y Reportes
- [x] Alertas de caducidad (30/60/90 días)
- [x] Alertas de stock mínimo
- [ ] Dashboard de alertas visual ⚠️ **FALTA TEMPLATE**
- [ ] Reporte de rotación ABC ⚠️ **PENDIENTE**
- [x] Reporte de ventas diarias

## ⚠️ PENDIENTES ANTES DE PRODUCCIÓN

### Templates Faltantes (2 semanas)
- [ ] `templates/farmacia/dashboard.html`
- [ ] `templates/farmacia/kardex_list.html`
- [ ] `templates/farmacia/kardex_detalle.html`
- [ ] `templates/farmacia/proveedor_list.html`
- [ ] `templates/farmacia/proveedor_form.html`
- [ ] `templates/farmacia/entrada_mercancia.html`

### Funcionalidad Adicional
- [ ] Gestión de proveedores (CRUD completo)
- [ ] Entrada de mercancía con UI
- [ ] Generación de órdenes de compra
- [ ] Impresión de etiquetas de precio

## 🧪 ESCENARIOS DE PRUEBA

### Caso 1: Venta Simple
**Usuario:** Cajero  
**Flujo:**
1. Abrir POS
2. Buscar producto "Paracetamol 500mg"
3. Agregar 2 cajas
4. Cobrar $50 en efectivo
5. Imprimir ticket
6. Verificar movimiento en Kardex

**Resultado esperado:** ✅ Venta registrada, ticket impreso, inventario actualizado

---

### Caso 2: Venta con Factura
**Usuario:** Cajero  
**Flujo:**
1. Venta de $1,000
2. Cliente solicita factura
3. Capturar datos fiscales (RFC, razón social)
4. Generar CFDI 4.0
5. Descargar PDF + XML

**Resultado esperado:** ⚠️ **REQUIERE FACTURACIÓN IMPLEMENTADA**

---

### Caso 3: Alerta de Caducidad
**Usuario:** Gerente  
**Flujo:**
1. Acceder a dashboard de alertas
2. Ver productos próximos a caducar
3. Aplicar descuento del 50%
4. Generar reporte de productos

**Resultado esperado:** ⚠️ **REQUIERE TEMPLATE DE DASHBOARD**

---

# MÓDULO LABORATORIO CLÍNICO

## ✅ FUNCIONALIDAD CORE

### Recepción de Orden
- [x] Crear orden de servicio
- [x] Buscar paciente existente
- [x] Registrar nuevo paciente
- [x] Seleccionar estudios
- [x] Calcular totales
- [x] Aplicar descuentos por convenio
- [x] Generar folio único
- [x] Imprimir orden para toma de muestra

### Toma de Muestra
- [x] Lista de órdenes pendientes
- [x] Registrar toma de muestra
- [x] Imprimir etiquetas
- [x] Marcar como tomada

### Captura de Resultados
- [x] Vista de captura masiva
- [x] Autoguardado cada 30s
- [x] Validación de rangos (min/max)
- [x] Alertas de valores críticos
- [x] Navegación por teclado (Tab/Enter)
- [x] Marcadores de calidad (QC/CV)
- [x] Comentarios técnicos

### IA y Reportes
- [x] Interpretación con Google Gemini
- [x] Detección de valores anormales
- [x] Sugerencias de estudios complementarios
- [x] Gráficas de tendencias
- [x] PDF profesional del reporte
- [x] Firma digital del QFB

## ⚠️ PENDIENTES ANTES DE PRODUCCIÓN

### Funcionalidad Adicional
- [ ] Microbiología (cultivos y antibiogramas) - 4 semanas
- [ ] Control de calidad estadístico (Levey-Jennings)
- [ ] Interoperabilidad HL7/FHIR - 4 semanas
- [ ] Portal web para pacientes (ver resultados)

## 🧪 ESCENARIOS DE PRUEBA

### Caso 1: Orden Básica
**Usuario:** Recepcionista  
**Flujo:**
1. Crear nueva orden
2. Buscar paciente "Juan Pérez"
3. Agregar estudios: Biometría Hemática + Química Sanguínea
4. Aplicar descuento del 10%
5. Cobrar en efectivo
6. Imprimir orden

**Resultado esperado:** ✅ Orden creada con folio LAB-2026-00001

---

### Caso 2: Captura de Resultados
**Usuario:** Químico  
**Flujo:**
1. Acceder a captura masiva
2. Buscar orden LAB-2026-00001
3. Capturar resultados de Biometría:
   - Hemoglobina: 12.5 g/dL
   - Leucocitos: 7,500 /μL
   - Plaquetas: 250,000 /μL
4. Guardar automáticamente
5. Validar técnicamente

**Resultado esperado:** ✅ Resultados guardados, marcados como validados

---

### Caso 3: Interpretación con IA
**Usuario:** QFB  
**Flujo:**
1. Ver orden con resultados capturados
2. Hacer clic en "Interpretar con IA"
3. Esperar respuesta de Gemini
4. Revisar interpretación
5. Editar si es necesario
6. Validar finalmente

**Resultado esperado:** ✅ IA proporciona interpretación coherente

---

### Caso 4: Impresión de Reporte
**Usuario:** QFB  
**Flujo:**
1. Orden validada completamente
2. Hacer clic en "Imprimir Reporte"
3. PDF se genera automáticamente
4. Verificar:
   - Logo de la empresa
   - Datos del paciente
   - Tabla de resultados con rangos
   - Valores anormales resaltados
   - Firma digital del QFB
   - Código QR de verificación

**Resultado esperado:** ✅ PDF profesional generado

---

# MÓDULO CONSULTORIO MÉDICO

## ✅ FUNCIONALIDAD CORE

### Recepción
- [x] Tablero de citas del día
- [x] Agendar nueva cita
- [x] Check-in de paciente
- [x] Marcar como "En sala de espera"

### Enfermería (Triage)
- [x] Lista de pacientes en sala
- [x] Captura de signos vitales:
  - Peso, Talla, IMC (auto-calculado)
  - Presión arterial (sistólica/diastólica)
  - Temperatura, FC, FR, SatO2
  - Glucosa capilar, perímetro abdominal
- [x] Guardar y marcar como "En triage"

### Consultorio Médico
- [x] Lista de trabajo del médico
- [x] Vista de consulta SOAP
- [x] **Lógica Híbrida:**
  - Caso A (Con enfermera): Signos read-only
  - Caso B (Médico solo): Signos editables
- [x] Historia Clínica NOM-004:
  - Ficha de identificación
  - AHF, APNP, APP, AGO
  - Padecimiento actual
  - Interrogatorio por aparatos
- [x] Consulta SOAP:
  - Motivo de la consulta
  - Subjetivo (síntomas)
  - Objetivo (exploración física)
  - Diagnóstico (CIE-10)
  - Plan (tratamiento/receta)
- [x] **Caja Negra Forense:**
  - Grabación de audio completo
  - Transcripción automática
  - Nota editada final
- [x] **Dictado por Voz:**
  - Botón 🎙️ en cada textarea
  - Web Speech API
  - Transcripción en tiempo real
- [x] **PDFs Duales:**
  - Receta para paciente (limpia)
  - Expediente forense (completo)

### Imagenología
- [x] Crear estudio de ultrasonido
- [x] Plantillas pre-cargadas
- [x] Drag & Drop de imágenes
- [x] Interpretación y conclusión
- [x] PDF profesional

## ⚠️ PENDIENTES ANTES DE PRODUCCIÓN

### Funcionalidad Adicional
- [ ] Interoperabilidad HL7 CDA - 4 semanas
- [ ] Telemedicina / Videoconsulta - 6 semanas
- [ ] Receta electrónica certificada (FIEL)
- [ ] App móvil para médicos

## 🧪 ESCENARIOS DE PRUEBA

### Caso A: Flujo CON Enfermera
**Usuarios:** Recepcionista, Enfermera, Médico

#### **Paso 1: Recepción (Recepcionista)**
1. Paciente Juan Pérez llega
2. Hacer check-in de cita 10:00 AM
3. Marcar como "En sala de espera"

**Resultado:** ✅ Cita aparece en lista de enfermería

---

#### **Paso 2: Triage (Enfermera)**
1. Ver lista de pacientes en sala
2. Seleccionar "Juan Pérez"
3. Capturar signos vitales:
   - Peso: 80 kg
   - Talla: 1.80 m
   - IMC: 24.69 (auto-calculado)
   - PA: 120/80 mmHg
   - Temp: 36.5°C
   - FC: 72 lpm
   - FR: 16 rpm
   - SatO2: 98%
4. Guardar
5. Marcar como "En triage"

**Resultado:** ✅ Signos guardados, cita aparece en lista del médico

---

#### **Paso 3: Consulta (Médico)**
1. Ver lista de trabajo
2. Seleccionar "Juan Pérez"
3. **VERIFICAR:** Signos vitales aparecen **BLOQUEADOS** (read-only)
4. Revisar Historia Clínica
5. Hacer clic en "🔴 GRABAR CONSULTA"
6. Realizar consulta (hablar mientras examina):
   - Motivo: "Dolor de cabeza"
   - Subjetivo: "Paciente refiere cefalea frontal de 2 días"
   - Objetivo: "Paciente alerta, Glasgow 15/15..."
   - Diagnóstico: "R51 - Cefalea"
   - Plan: "Paracetamol 500mg cada 8h por 3 días"
7. Hacer clic en botón 🎙️ para dictar la receta
8. Detener grabación
9. Guardar consulta
10. Imprimir receta para paciente
11. Imprimir expediente forense para archivo

**Resultado esperado:**
- ✅ Signos aparecen bloqueados
- ✅ Audio se graba correctamente
- ✅ Transcripción automática funciona
- ✅ Consulta se guarda con transacción atómica
- ✅ PDF receta: Diseño limpio, solo info necesaria
- ✅ PDF forense: Transcripción completa, timestamps, firma digital

---

### Caso B: Flujo SIN Enfermera (Médico Solo)
**Usuario:** Médico

#### **Paso 1: Consulta Directa**
1. Paciente Ana Gómez llega directo a consultorio
2. Médico abre lista de trabajo
3. Seleccionar "Ana Gómez - 11:00 AM"
4. **VERIFICAR:** NO existen signos vitales previos
5. **VERIFICAR:** Campos de signos aparecen **EDITABLES**
6. Capturar signos vitales directamente:
   - Peso: 65 kg
   - Talla: 1.65 m
   - IMC: 23.88 (auto-calculado)
   - PA: 115/75 mmHg
   - Temp: 36.8°C
   - FC: 78 lpm
   - FR: 18 rpm
   - SatO2: 99%
7. Continuar con consulta SOAP
8. Grabar audio
9. Dictar notas
10. Guardar consulta

**Resultado esperado:**
- ✅ Signos aparecen EDITABLES
- ✅ Médico puede capturar todo en una sola vista
- ✅ Transacción atómica guarda Signos + Consulta simultáneamente
- ✅ No hay errores de inconsistencia

---

### Caso C: Ultrasonido
**Usuario:** Médico radiólogo

1. Crear nuevo estudio de ultrasonido
2. Paciente: Luis Miguel
3. Tipo: Ultrasonido Abdominal
4. Seleccionar plantilla: "Hígado Normal"
5. Editar interpretación si es necesario
6. Arrastrar imágenes (Drag & Drop):
   - `higado_corte_longitudinal.jpg`
   - `vesicula_biliar.jpg`
7. Escribir conclusión: "Sin alteraciones ultrasonográficas"
8. Guardar
9. Imprimir reporte en PDF

**Resultado esperado:**
- ✅ Plantilla se carga automáticamente
- ✅ Imágenes se suben correctamente
- ✅ PDF con interpretación profesional

---

# INFRAESTRUCTURA Y SEGURIDAD

## ✅ CONFIGURACIÓN DEL SERVIDOR

### Servidor Web
- [x] Django 5.0 instalado
- [x] Python 3.14 compatible
- [x] Gunicorn configurado
- [x] Nginx reverse proxy
- [x] SSL/HTTPS activo
- [ ] Certificado SSL válido ⚠️ **PENDIENTE PRODUCCIÓN**

### Base de Datos
- [x] PostgreSQL instalado
- [x] Backup diario automático
- [x] Replica de lectura (opcional)
- [ ] Backup offsite configurado ⚠️ **RECOMENDADO**

### Seguridad
- [x] Firewall configurado
- [x] Acceso SSH restringido
- [x] Contraseñas seguras (Argon2)
- [ ] Autenticación 2FA implementada 🔴 **CRÍTICO**
- [ ] WAF (Web Application Firewall) 🟡 **RECOMENDADO**
- [ ] Monitoreo de intrusiones 🟡 **RECOMENDADO**

### Monitoreo
- [ ] Sentry para errores 🟡 **RECOMENDADO**
- [ ] Uptime monitoring 🟡 **RECOMENDADO**
- [ ] Log aggregation (ELK) 🟢 **OPCIONAL**

## 🧪 PRUEBAS DE INFRAESTRUCTURA

### Prueba 1: Carga Simultánea
**Objetivo:** Verificar que el sistema soporta múltiples usuarios
**Herramienta:** Apache JMeter o Locust
**Escenario:**
- 50 usuarios simulados
- 10 órdenes de laboratorio simultáneas
- 5 ventas de farmacia simultáneas
- 3 consultas médicas simultáneas

**Criterio de éxito:** Tiempo de respuesta < 2 segundos

---

### Prueba 2: Backup y Restore
**Objetivo:** Verificar integridad de backups
**Escenario:**
1. Crear datos de prueba (100 registros)
2. Ejecutar backup manual
3. Eliminar datos
4. Restaurar backup
5. Verificar que todos los datos están intactos

**Criterio de éxito:** 100% de datos recuperados

---

### Prueba 3: Seguridad Básica
**Objetivo:** Verificar protecciones básicas
**Herramienta:** OWASP ZAP
**Pruebas:**
- SQL Injection
- XSS (Cross-Site Scripting)
- CSRF tokens
- Clickjacking
- Headers de seguridad

**Criterio de éxito:** 0 vulnerabilidades críticas

---

# CAPACITACIÓN Y DOCUMENTACIÓN

## ✅ MATERIAL DE CAPACITACIÓN

### Manuales de Usuario
- [ ] Manual de Farmacia/POS (20 páginas) ⚠️ **PENDIENTE**
- [ ] Manual de Laboratorio (30 páginas) ⚠️ **PENDIENTE**
- [ ] Manual de Consultorio (40 páginas) ⚠️ **PENDIENTE**
- [ ] Guía rápida de uso (5 páginas) ⚠️ **PENDIENTE**

### Videos de Capacitación
- [ ] Video: Punto de Venta (10 min) ⚠️ **PENDIENTE**
- [ ] Video: Captura de Resultados Lab (15 min) ⚠️ **PENDIENTE**
- [ ] Video: Consulta Médica SOAP (20 min) ⚠️ **PENDIENTE**
- [ ] Video: Caja Negra Forense (5 min) ⚠️ **PENDIENTE**

### Sesiones de Capacitación
- [ ] Capacitación grupal Farmacia (4 horas) ⚠️ **PROGRAMAR**
- [ ] Capacitación grupal Laboratorio (6 horas) ⚠️ **PROGRAMAR**
- [ ] Capacitación grupal Consultorio (8 horas) ⚠️ **PROGRAMAR**
- [ ] Q&A y soporte post-capacitación ⚠️ **PROGRAMAR**

## 🧪 EVALUACIÓN DE CAPACITACIÓN

### Examen de Conocimientos
**Por cada módulo, usuario debe demostrar:**
- ✅ Conocimiento de flujo completo
- ✅ Manejo de casos comunes
- ✅ Resolución de errores básicos
- ✅ ¿Cuándo escalar al soporte?

**Criterio de aprobación:** 80% de aciertos

---

# PLAN DE PRUEBAS

## 📅 CRONOGRAMA DE PRUEBAS

### Semana 1: Pruebas Internas (QA)
**Responsable:** Equipo de desarrollo
- Ejecutar todos los casos de prueba documentados
- Corregir bugs críticos encontrados
- Documentar bugs menores para backlog

---

### Semana 2: Pruebas Alpha (Personal Técnico)
**Responsable:** Personal interno con conocimiento técnico
- 1-2 usuarios por módulo
- Uso real durante 1 semana
- Reporte diario de problemas
- Reunión diaria de 15 min (stand-up)

---

### Semana 3-4: Pruebas Beta (Personal Operativo)
**Responsable:** Personal que usará el sistema en producción
- Operación paralela (sistema viejo + nuevo)
- Capacitación on-the-job
- Reporte de bugs y sugerencias
- Reunión semanal de retroalimentación

---

### Semana 5: Estabilización
**Responsable:** Equipo de desarrollo
- Corrección de bugs reportados
- Ajustes de UX basados en feedback
- Pruebas de regresión
- Preparación para lanzamiento

---

### Semana 6: Lanzamiento Controlado
**Responsable:** Project Manager
- Go-live en sucursal piloto
- Equipo de soporte on-site 24/7
- Monitoreo intensivo de errores
- Plan de rollback preparado

---

## 📋 PLANTILLA DE REPORTE DE BUG

```markdown
## Bug ID: #XXXX

**Módulo:** Farmacia / Laboratorio / Consultorio

**Prioridad:** 🔴 Crítica / 🟡 Alta / 🟢 Media / 🔵 Baja

**Descripción:**
[Descripción clara del problema]

**Pasos para Reproducir:**
1. Paso 1
2. Paso 2
3. Paso 3

**Resultado Esperado:**
[Lo que debería pasar]

**Resultado Actual:**
[Lo que realmente pasa]

**Screenshots/Videos:**
[Adjuntar evidencia]

**Información del Sistema:**
- Navegador: Chrome 120
- SO: Windows 11
- Usuario: medico@prislab.com
- Fecha/Hora: 2026-01-26 14:30

**Impacto:**
[¿Bloquea algún flujo crítico?]

**Workaround:**
[¿Hay forma temporal de evitarlo?]
```

---

## ✅ CRITERIOS DE GO/NO-GO PARA PRODUCCIÓN

### 🔴 BLOQUEANTES (Si falla UNO = NO GO)
- [ ] 0 bugs críticos abiertos
- [ ] Backup automático funcional
- [ ] SSL/HTTPS activo
- [ ] Personal capacitado (80%+ aprobación)
- [ ] Plan de rollback documentado
- [ ] Soporte 24/7 disponible

### 🟡 IMPORTANTES (Si fallan 2+ = NO GO)
- [ ] < 5 bugs de prioridad alta abiertos
- [ ] Monitoreo de errores activo
- [ ] Manuales de usuario entregados
- [ ] Videos de capacitación disponibles
- [ ] Facturación CFDI 4.0 funcional
- [ ] 2FA implementado

### 🟢 DESEABLES (No bloquean go-live)
- [ ] Interoperabilidad HL7
- [ ] Telemedicina
- [ ] App móvil
- [ ] Auditoría externa aprobada

---

## 📞 CONTACTOS DE EMERGENCIA

### Soporte Técnico
**Desarrollador Senior:** Juan Pérez  
**Teléfono:** 555-1234  
**Email:** juan.perez@prislab.com  
**Horario:** 24/7 (primera semana)

### Responsables de Módulo
**Farmacia:** María López - 555-2345  
**Laboratorio:** Carlos García - 555-3456  
**Consultorio:** Dr. Roberto Sánchez - 555-4567

### Escalación
**Project Manager:** Ana Martínez - 555-5678  
**CTO:** Luis Rodríguez - 555-6789

---

## 📊 MÉTRICAS DE ÉXITO

### Durante Pruebas
- **Tasa de bugs críticos:** < 2 por semana
- **Tiempo de resolución:** < 24 horas para críticos
- **Satisfacción de usuarios:** > 80%
- **Tasa de adopción:** > 90% del personal usa el sistema

### Post-Lanzamiento (Primer Mes)
- **Uptime:** > 99.5%
- **Tiempo de respuesta:** < 2 segundos
- **Errores de usuario:** < 5% de operaciones
- **Tickets de soporte:** < 20 por semana

---

## ✅ FIRMA DE APROBACIÓN

### **APROBADO PARA INICIAR PRUEBAS:**

**Farmacia:**  
Nombre: ________________________  
Cargo: _________________________  
Fecha: _________________________  
Firma: _________________________

**Laboratorio:**  
Nombre: ________________________  
Cargo: _________________________  
Fecha: _________________________  
Firma: _________________________

**Consultorio:**  
Nombre: ________________________  
Cargo: _________________________  
Fecha: _________________________  
Firma: _________________________

**Project Manager:**  
Nombre: ________________________  
Fecha: _________________________  
Firma: _________________________

---

**Documento generado por:** Sistema de Calidad PRISLAB  
**Fecha:** 26 de Enero de 2026  
**Versión:** 1.0  
**Próxima revisión:** Semanal durante pruebas

---

**FIN DEL CHECKLIST**
