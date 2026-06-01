# 🚀 PLAN MAESTRO: NÚCLEO PRIS-VALLE 2030
## Plataforma SaaS Multi-Empresa - Sistema Modular

---

## 📋 ÍNDICE

1. [ESTRUCTURA RAÍZ: Motor Camaleónico Multi-Tenant](#estructura-raíz)
2. [BLOQUE 1: Recursos Humanos y Productividad](#bloque-1)
3. [BLOQUE 2: Expediente Clínico y Consulta (ECE)](#bloque-2)
4. [BLOQUE 3: Auditoría y Seguridad](#bloque-3)
5. [BLOQUE 4: Inteligencia Artificial y Automatización](#bloque-4)
6. [BLOQUE 5: Infraestructura y Equipos](#bloque-5)

---

## 🏗️ ESTRUCTURA RAÍZ: Motor Camaleónico Multi-Tenant {#estructura-raíz}

### Objetivo
Crear un sistema que pueda gestionar 2, 5 o 100 empresas de forma independiente con aislamiento total de datos.

### Componentes Clave

#### 1. Modelo `Sucursal` (Nuevo)
- `empresa` (ForeignKey a Empresa)
- `nombre` (CharField)
- `direccion` (TextField)
- `telefono` (CharField)
- `codigo_sucursal` (CharField único)
- `activa` (BooleanField)

#### 2. Aislamiento de Datos
**LLAVE MAESTRA**: Todos los modelos deben incluir:
- `empresa_id` (ForeignKey a Empresa) ✅ **YA EXISTE en la mayoría**
- `sucursal_id` (ForeignKey a Sucursal) ⚠️ **FALTA IMPLEMENTAR**

**Modelos que necesitan `sucursal_id`:**
- `Venta`, `DetalleVenta`, `Pago`
- `Paciente`
- `OrdenDeServicio`, `DetalleOrden`
- `Producto`, `Lote`
- `AjusteInventario`, `GastoCaja`
- `SalesReturn`
- `Gasto`, `DiscountPolicy`

#### 3. Feature Toggles (Interruptores de Módulos)
**Modelo `ConfiguracionModulos`** (Nuevo):
- `empresa` (OneToOneField a Empresa)
- `modulo_laboratorio` (BooleanField, default=True)
- `modulo_farmacia` (BooleanField, default=True)
- `modulo_rrhh` (BooleanField, default=False)
- `modulo_expediente_clinico` (BooleanField, default=False)
- `modulo_hospitalizacion` (BooleanField, default=False)
- `modulo_consulta_externa` (BooleanField, default=False)
- `modulo_citas` (BooleanField, default=False)

#### 4. Identidad Dinámica
**Extensiones al modelo `Empresa`:**
- ✅ `nombre` (ya existe)
- ✅ `logo` (ya existe)
- ✅ `periodo_vigencia` (ya existe)
- ➕ `color_primario` (CharField, default="#D9230F") - Rojo Prislab
- ➕ `color_secundario` (CharField, default="#2B3A42") - Oxford Grey
- ➕ `color_fondo` (CharField, default="#FFFFFF")
- ➕ `css_personalizado` (TextField, blank=True) - Para CSS dinámico

**Middleware de Identidad:**
- Middleware que inyecta datos de la empresa actual en el contexto
- Template context processor para `{{ empresa_actual }}`
- CSS dinámico en `<head>` basado en `empresa_actual.color_primario`

---

## 🛡️ BLOQUE 1: Recursos Humanos y Productividad {#bloque-1}

### Objetivo
Gestionar el talento (Nancy, Gaby, Q.C. Gisell) con blindaje legal.

### Componentes

#### 1.1 Reloj Checador Digital
**Modelo `RegistroAsistencia`:**
- `usuario` (ForeignKey a Usuario)
- `empresa` (ForeignKey a Empresa)
- `sucursal` (ForeignKey a Sucursal)
- `tipo_registro` (CharField: 'ENTRADA', 'SALIDA', 'BREAK_IN', 'BREAK_OUT')
- `fecha_hora` (DateTimeField)
- `metodo_registro` (CharField: 'WEB', 'KIOSCO', 'MOBILE')
- `ip_address` (CharField)
- `ubicacion_gps` (CharField, opcional)

**Vistas:**
- Vista de registro rápido (botón "Entrar" / "Salir")
- Tablero de asistencia en tiempo real
- Historial personal y por empleado
- Reportes de asistencia mensuales

#### 1.2 Bitácora de Evaluación Semanal
**Modelo `EvaluacionEmpleado`:**
- `usuario` (ForeignKey a Usuario)
- `evaluador` (ForeignKey a Usuario)
- `periodo` (CharField: formato "2024-S01" para semana 1)
- `fecha_inicio` (DateField)
- `fecha_fin` (DateField)
- `tipo_periodo` (CharField: 'PERIODO_PRUEBA', 'EVALUACION_SEMANAL', 'EVALUACION_MENSUAL')
- `aptitud_medica` (BooleanField) - Dictamen de aptitud
- `notas_objetivas` (TextField)
- `calificacion_general` (IntegerField, 0-100)
- `recomendacion` (CharField: 'CONTRATAR', 'PRORROGAR', 'NO_CONTRATAR')

#### 1.3 Calculadora de Compensación Variable
**Modelo `BonoEmpleado`:**
- `usuario` (ForeignKey a Usuario)
- `periodo` (CharField)
- `tipo_bono` (CharField: 'CERO_ERRORES', 'VOLUMEN_PACIENTES', 'PUNTUALIDAD', 'ESPECIAL')
- `monto` (DecimalField)
- `criterios_cumplidos` (JSONField)
- `fecha_pago` (DateField)

**Lógica:**
- Bono "Cero Errores": Si `SalesReturn` asociado al usuario = 0 en el período
- Bono Volumen: Por cada 100 pacientes atendidos
- Bono Puntualidad: Si asistencia perfecta en el período

#### 1.4 Tablero de Asistencia
**Vista en tiempo real:**
- Lista de empleados activos (en línea)
- Último registro de cada empleado
- Gráfica de asistencia del día
- Alertas de ausencias no justificadas

---

## 🩺 BLOQUE 2: Expediente Clínico y Consulta (ECE) {#bloque-2}

### Objetivo
Centralizar la salud bajo normativa NOM-024.

### Componentes

#### 2.1 Notas SOAP
**Modelo `NotaClinicaSOAP`:**
- `paciente` (ForeignKey a Paciente)
- `medico` (ForeignKey a Medico)
- `fecha_consulta` (DateTimeField)
- `subjetivo` (TextField) - Lo que el paciente reporta
- `objetivo` (TextField) - Hallazgos físicos/exploración
- `analisis` (TextField) - Diagnóstico o impresión diagnóstica
- `plan` (TextField) - Plan de tratamiento
- `archivos_adjuntos` (JSONField) - IDs de imágenes/documentos

#### 2.2 Receta 4.0
**Extensiones al modelo `Receta`:**
- ✅ Campos básicos (ya existen)
- ➕ `codigo_qr` (CharField, único) - Generado automáticamente
- ➕ `qr_imagen` (ImageField) - QR code generado
- ➕ `fecha_expedicion` (DateTimeField, auto_now_add)
- ➕ `valida_hasta` (DateField)
- ➕ `visibilidad_farmacia` (BooleanField, default=True)

**Funcionalidades:**
- Generación automática de QR con datos de autenticidad
- Visor de existencias en farmacia para el médico
- Validación de receta por QR en el PDV
- Historial de surtido vinculado

#### 2.3 Triage e Ingreso Express
**Modelo `TriagePaciente`:**
- `paciente` (ForeignKey a Paciente)
- `usuario_triage` (ForeignKey a Usuario)
- `fecha_triage` (DateTimeField)
- `nivel_urgencia` (CharField: 'ROJO', 'NARANJA', 'AMARILLO', 'VERDE', 'AZUL')
- `signos_vitales` (JSONField) - TA, FC, FR, Temp, SatO2
- `motivo_consulta` (TextField)
- `observaciones` (TextField)

**Vista de Ingreso Express:**
- Formulario rápido con campos mínimos
- Clasificación automática por algoritmo
- Asignación automática de médico disponible

---

## 👮🏻‍♂️ BLOQUE 3: Auditoría y Seguridad {#bloque-3}

### Objetivo
Control total sin necesidad de presencia física.

### Componentes

#### 3.1 Registro Inalterable (Audit Logs)
**Modelo `AuditLog`:**
- `empresa` (ForeignKey a Empresa)
- `usuario` (ForeignKey a Usuario, nullable)
- `accion` (CharField: 'CREATE', 'UPDATE', 'DELETE', 'VIEW', 'PRINT')
- `modelo_afectado` (CharField) - Nombre del modelo Django
- `objeto_id` (CharField) - ID del objeto afectado
- `datos_anteriores` (JSONField, nullable)
- `datos_nuevos` (JSONField, nullable)
- `fecha_cierta` (DateTimeField, auto_now_add) - Con firma de tiempo
- `ip_address` (CharField)
- `user_agent` (CharField)
- `hash_verificacion` (CharField) - Para prevenir alteraciones

**Middleware de Auditoría:**
- Captura automática de cambios en modelos críticos
- Registro de impresiones (tickets, resultados)
- Registro de cambios de precios
- Registro de eliminaciones

#### 3.2 Botón de Pánico Silencioso
✅ **YA IMPLEMENTADO** en módulo `seguridad`:
- `ConfiguracionSeguridad` (ya existe)
- `AlertaPanico` (ya existe)

**Mejoras necesarias:**
- Botón en header con icono discreto
- Atajo de teclado (Ctrl+Alt+P)
- Integración con WhatsApp/Telegram

#### 3.3 Nube Nocturna (Respaldo Automático)
**Modelo `RespaldoAutomatico`:**
- `empresa` (ForeignKey a Empresa)
- `fecha_respaldo` (DateTimeField)
- `archivo_respaldo` (FileField)
- `tamaño_archivo` (IntegerField)
- `hash_verificacion` (CharField)
- `metodo_respaldo` (CharField: 'LOCAL', 'CLOUD_STORAGE', 'FTP')
- `estado` (CharField: 'COMPLETADO', 'ERROR', 'EN_PROGRESO')

**Tarea Programada (Celery/Cron):**
- Ejecutar diariamente a las 3:00 AM
- Respaldo encriptado de base de datos
- Subida a Cloud Storage (Google Cloud Storage / S3)
- Retención de 30 días de respaldos

---

## 🤖 BLOQUE 4: Inteligencia Artificial y Automatización {#bloque-4}

### Objetivo
Eliminar tareas repetitivas y acelerar ingresos.

### Componentes

#### 4.1 Ojo Biónico (IA Vision)
✅ **YA IMPLEMENTADO** parcialmente en módulo `ia`:
- Modelo `CotizacionOCR` (ya existe)

**Mejoras necesarias:**
- Integración con Google Cloud Vision API
- Procesamiento de imágenes de recetas
- Extracción de medicamentos y dosis
- Generación automática de cotización

#### 4.2 Laboratorio "Manos Libres" (Dictado por Voz)
✅ **YA IMPLEMENTADO** parcialmente en módulo `ia`:
- Modelo `TranscripcionVoz` (ya existe)

**Mejoras necesarias:**
- Integración con Google Speech-to-Text API
- Interfaz de grabación en tiempo real
- Transcripción automática en campo de resultados
- Corrección por contexto (nombres de estudios, valores normales)

#### 4.3 La "Triple Llave" de Envío
**Modelo `ValidacionEnvioResultado`:**
- `orden` (ForeignKey a OrdenDeServicio)
- `fecha_validacion` (DateTimeField)
- `deuda_cero` (BooleanField) - Verificado
- `privacidad_firmada` (BooleanField) - Consentimiento del paciente
- `identidad_validada` (BooleanField) - Verificación de identidad
- `usuario_validador` (ForeignKey a Usuario)
- `metodo_envio` (CharField: 'WHATSAPP', 'EMAIL', 'FISICO')
- `bloqueado_hasta` (DateTimeField, nullable)

**Lógica de Bloqueo:**
- No permitir envío por WhatsApp si falta alguna llave
- Mostrar indicadores visuales en la interfaz
- Registrar intentos de envío bloqueados en `AuditLog`

---

## 🏗️ BLOQUE 5: Infraestructura y Equipos {#bloque-5}

### Objetivo
Continuidad operativa y control técnico.

### Componentes

#### 5.1 Gestión de Equipos
**Modelo `Equipo`:**
- `empresa` (ForeignKey a Empresa)
- `nombre` (CharField) - Ej: "Analizador Fuji 300", "Reactivos Wondfo Lote 12345"
- `tipo` (CharField: 'ANALIZADOR', 'REACTIVO', 'EQUIPO_LAB', 'COMPUTADORA')
- `marca` (CharField)
- `modelo` (CharField)
- `numero_serie` (CharField, único)
- `fecha_adquisicion` (DateField)
- `fecha_caducidad` (DateField, nullable) - Para reactivos
- `estado` (CharField: 'OPERATIVO', 'MANTENIMIENTO', 'FUERA_SERVICIO')
- `ubicacion` (CharField) - Sucursal y área específica

**Modelo `RegistroMantenimiento`:**
- `equipo` (ForeignKey a Equipo)
- `tipo_mantenimiento` (CharField: 'PREVENTIVO', 'CORRECTIVO', 'CALIBRACION')
- `fecha_programada` (DateField)
- `fecha_realizada` (DateField, nullable)
- `proveedor` (CharField)
- `costo` (DecimalField)
- `observaciones` (TextField)

#### 5.2 Modo Offline (LAN)
**Configuración:**
- Cache de datos críticos en LocalStorage/IndexedDB
- Sincronización automática cuando se restablece conexión
- Cola de operaciones pendientes (`QueueOperacion`)
- Indicador visual de estado de conexión

**Modelo `QueueOperacion`:**
- `usuario` (ForeignKey a Usuario)
- `tipo_operacion` (CharField: 'VENTA', 'ORDEN_LAB', 'PACIENTE')
- `datos_json` (JSONField)
- `estado` (CharField: 'PENDIENTE', 'ENVIADA', 'ERROR')
- `fecha_creacion` (DateTimeField)
- `fecha_sincronizacion` (DateTimeField, nullable)

#### 5.3 Mantenimiento Preventivo
**Calendario digital:**
- Vista de calendario con fechas de mantenimiento
- Alertas 7 días antes de mantenimiento programado
- Recordatorios automáticos por email/WhatsApp
- Historial de mantenimientos por equipo

---

## ⚠️ REGLA DE ORO

**"Toda implementación debe respetar el Header Líquido. La marca, el logo y la leyenda de vigencia deben desplazarse elásticamente cuando el sidebar se active. Nada debe quedar oculto."**

✅ **YA IMPLEMENTADO** en `base.html` y `pdv_farmacia.html`

---

## 📊 ORDEN DE IMPLEMENTACIÓN RECOMENDADO

### Fase 1: Fundación (Prioridad Alta)
1. ✅ Estructura Multi-Tenant Base (Empresa ya existe)
2. ⚠️ Modelo Sucursal + sucursal_id en todos los modelos
3. ⚠️ Feature Toggles (ConfiguracionModulos)
4. ⚠️ Identidad Dinámica (CSS personalizado)

### Fase 2: Auditoría y Seguridad (Prioridad Alta)
1. ⚠️ Audit Logs (Registro Inalterable)
2. ✅ Botón de Pánico (ya implementado, mejorar integración)
3. ⚠️ Nube Nocturna (Respaldo Automático)

### Fase 3: RRHH (Prioridad Media)
1. ⚠️ Reloj Checador
2. ⚠️ Bitácora de Evaluación
3. ⚠️ Calculadora de Compensación
4. ⚠️ Tablero de Asistencia

### Fase 4: Expediente Clínico (Prioridad Media)
1. ⚠️ Notas SOAP
2. ⚠️ Receta 4.0 (mejoras al modelo existente)
3. ⚠️ Triage e Ingreso Express

### Fase 5: IA y Automatización (Prioridad Baja)
1. ⚠️ Mejoras a IA Vision (OCR)
2. ⚠️ Mejoras a Dictado por Voz
3. ⚠️ Triple Llave de Envío

### Fase 6: Infraestructura (Prioridad Baja)
1. ⚠️ Gestión de Equipos
2. ⚠️ Modo Offline
3. ⚠️ Mantenimiento Preventivo

---

## 🔧 NOTAS TÉCNICAS

- **Framework**: Django 4.x
- **Base de Datos**: PostgreSQL (Cloud SQL) / SQLite (Desarrollo)
- **Frontend**: Bootstrap 5 + Glassmorphism CSS
- **IA**: Google Cloud Vision API, Google Speech-to-Text API
- **Notificaciones**: WhatsApp Business API, Telegram Bot API
- **Respaldo**: Google Cloud Storage / AWS S3
- **Tareas Programadas**: Celery + Redis (o Django-Q para simplicidad)

---

**Última actualización**: 2025-01-27
**Versión del Plan**: 1.0
