# MANUAL OPERATIVO COMPLETO — PRISLAB V5.0
## Descripción Funcional + Guía de Uso + Recomendaciones de Crecimiento
### Fecha: 9 de Febrero de 2026

---

# TABLA DE CONTENIDO

1. [Visión General del Sistema](#1-vision-general)
2. [Login y Sistema de Roles](#2-login-y-roles)
3. [MÓDULO 1: CONSULTORIO MÉDICO](#3-consultorio-medico)
4. [MÓDULO 2: LABORATORIO CLÍNICO (LIMS)](#4-laboratorio)
5. [MÓDULO 3: FARMACIA Y PUNTO DE VENTA](#5-farmacia)
6. [MÓDULO 4: INTELIGENCIA ARTIFICIAL (Gemini)](#6-inteligencia-artificial)
7. [MÓDULO 5: RECEPCIÓN Y AGENDAMIENTO](#7-recepcion)
8. [MÓDULO 6: ENFERMERÍA Y TRIAGE](#8-enfermeria)
9. [MÓDULO 7: PACIENTES — HISTORIAL 360° Y PORTAL](#9-pacientes)
10. [MÓDULO 8: SEGURIDAD (2FA, SESIONES, AUDITORÍA)](#10-seguridad)
11. [MÓDULO 9: BIENESTAR EMOCIONAL](#11-bienestar)
12. [MÓDULO 10: LOGÍSTICA Y TRANSFERENCIAS](#12-logistica)
13. [MÓDULO 11: MARKETING, CUPONES Y CAMPAÑAS](#13-marketing)
14. [MÓDULO 12: CONTABILIDAD Y FACTURACIÓN CFDI](#14-contabilidad)
15. [MÓDULO 13: FINANZAS SEGREGADAS (Caja Lab + Farmacia)](#15-finanzas)
16. [MÓDULO 14: RECURSOS HUMANOS](#16-rh)
17. [MÓDULO 15: PANEL DEL DIRECTOR](#17-director)
18. [MÓDULO 16: COMUNICACIÓN INTERNA](#18-comunicacion)
19. [MÓDULO 17: IoT Y KIOSCO](#19-iot)
20. [MÓDULO 18: COTIZACIÓN RÁPIDA](#20-cotizacion)
21. [MÓDULO 19: CATÁLOGOS GENERALES](#21-catalogos)
22. [MÓDULO 20: CAPACITACIÓN Y MANUAL](#22-capacitacion)
23. [FUNCIONALIDADES PENDIENTES (Detalladas)](#23-pendientes)
24. [RECOMENDACIONES DE CRECIMIENTO POR MÓDULO](#24-recomendaciones)

---

# 1. VISIÓN GENERAL

## ¿Qué es PRISLAB V5.0?
PRISLAB es un **Sistema de Gestión Integral (ERP Médico-Farmacéutico)** diseñado para clínicas, laboratorios clínicos y farmacias. Es una plataforma **Multi-Tenant** (múltiples empresas/sucursales en una sola instalación), con **Inteligencia Artificial** integrada (Google Gemini), generación de **PDFs profesionales**, y un sistema de **roles dinámicos** que adapta la interfaz según el tipo de usuario.

## Arquitectura
- **Backend:** Django 5 (Python)
- **Frontend:** Templates HTML + JavaScript vanilla + CSS moderno
- **Base de Datos:** PostgreSQL (producción) / SQLite (desarrollo)
- **IA:** Google Gemini API (OCR, Voz, NLP, Asistente Médico)
- **PDF:** ReportLab (tamaño carta US Letter calibrado)
- **Hosting:** Google Cloud Run (serverless, auto-escalable)
- **PWA:** Progressive Web App (funciona offline parcial, instalable en móvil)

## URL de Producción
```
https://prislab-v5-oswjakz55a-uc.a.run.app
```

---

# 2. LOGIN Y SISTEMA DE ROLES

## Cómo funciona el Login
Al ingresar a la URL del sistema, se presenta una pantalla de login personalizada con la identidad de PRISLAB.

**Credenciales de administrador:**
- Usuario: `admin`
- Contraseña: `PrislabV5_2026`

## Redirección Inteligente por Rol
Después del login, el sistema redirige automáticamente según el rol del usuario:

| Rol / Grupo | Pantalla de Inicio |
|---|---|
| **MEDICOS** | Dashboard Médico (Consultorio) |
| **LABORATORIO** | Lista de Trabajo (Lab) |
| **FARMACIA** | Punto de Venta (PDV) |
| **RECEPCION** | Recepción de Laboratorio |
| **ENFERMERIA** | Recepción de Laboratorio |
| **GERENCIA** | Dashboard General (Farmacia) |
| **DIRECTOR** | Dashboard Director |
| **ADMIN / Superusuario** | Dashboard General |

## Roles del Sistema
El sistema soporta estos roles predefinidos:
- **ADMIN** — Acceso total a todos los módulos
- **DIRECTOR** — Panel ejecutivo, métricas, autorizaciones
- **GERENTE** — Dashboard general, reportes financieros
- **MEDICO** — Consultorio, recetas, certificados, expediente clínico
- **QUIMICO** — Captura de resultados de laboratorio
- **RECEPCION** — Registro de pacientes, creación de órdenes
- **CAJERO** — Punto de venta farmacia
- **ENFERMERIA** — Triage y signos vitales

## Sidebar Dinámico (Menú Lateral)
El menú lateral (sidebar) se adapta según el rol del usuario. Solo muestra los módulos a los que tiene acceso. El sidebar incluye:
- Logo de la empresa (dinámico, tomado del perfil de la empresa)
- Menú principal con iconos y acordeones desplegables
- Indicador de usuario activo
- Botón de cerrar sesión

### Cómo se usa:
1. Hacer clic en el icono de hamburguesa para expandir/colapsar
2. Los módulos con sub-menú se abren haciendo clic en el título
3. El módulo activo se resalta visualmente

---

# 3. MÓDULO CONSULTORIO MÉDICO
**Ruta:** `/consultorio/` | **Rol requerido:** MEDICO o ADMIN

## Descripción
El Consultorio Médico es el módulo donde los doctores realizan consultas médicas. Incluye el **"Gemelo Digital"** — una interfaz de doble panel que muestra en tiempo real lo que se escribe en el formulario como una vista previa tipo receta médica.

## Funcionalidades Actuales (Implementadas)

### 3.1 Dashboard del Consultorio
**Ruta:** `/consultorio/`
- Muestra las **citas del día** ordenadas por hora
- **Estadísticas del mes:** total de consultas finalizadas e ingresos
- Acceso rápido a "Nueva Consulta" y "Lista de Trabajo"

### 3.2 Nueva Consulta (Gemelo Digital)
**Ruta:** `/consultorio/medico/nueva-consulta/`

**Cómo se usa:**
1. **Seleccionar paciente:** Se busca por nombre o se crea uno nuevo directamente desde la pantalla
2. **Llenar datos clínicos:** El formulario tiene los campos:
   - Motivo de consulta
   - Exploración física / Hallazgos
   - Diagnóstico
   - Tratamiento
   - Notas internas
3. **Vista previa en tiempo real:** El panel derecho ("Gemelo Digital") refleja en vivo todo lo que se escribe en formato de receta médica profesional
4. **Grabar con IA:** El botón "GRABAR CONSULTA CON IA" activa el micrófono. El médico dicta la consulta verbalmente y Gemini IA transcribe y auto-completa los campos (motivo, diagnóstico, tratamiento)
5. **Generar Receta PDF:** Al finalizar, se genera automáticamente un PDF tamaño carta con membrete de la empresa

### 3.3 Consulta SOAP (Con Cita Previa)
**Ruta:** `/consultorio/medico/consulta/<cita_id>/`

**Cómo se usa:**
1. El médico selecciona una cita de la lista de trabajo
2. Se abre el formulario SOAP completo:
   - **S (Subjetivo):** Lo que el paciente relata
   - **O (Objetivo):** Exploración física, signos vitales
   - **A (Análisis):** Diagnóstico
   - **P (Plan):** Tratamiento, estudios solicitados
3. Se pueden generar **inmediatamente**:
   - Receta médica (PDF)
   - Certificado médico (incapacidad, aptitud, etc.)
   - Orden de laboratorio (que se envía directamente a recepción del lab)

### 3.4 Recepción del Consultorio
**Ruta:** `/consultorio/recepcion/`
- Tablero con las citas del día
- Funciones: Agendar cita, Check-in de paciente
- Al hacer check-in, el paciente pasa a "En Espera"

### 3.5 Triage (Enfermería dentro de Consultorio)
**Ruta:** `/consultorio/enfermeria/triage/`
- Lista de pacientes que necesitan triage
- Captura de signos vitales (peso, talla, presión arterial, temperatura, frecuencia cardíaca, saturación)

### 3.6 Lista de Trabajo Médico
**Ruta:** `/consultorio/medico/lista-trabajo/`
- Muestra las citas del médico pendientes de atender
- Estado: PROGRAMADA → CHECK-IN → EN CURSO → FINALIZADA

### 3.7 Historial Clínico del Paciente
**Ruta:** `/consultorio/paciente/<id>/historial/`
- Muestra todas las consultas previas del paciente en orden cronológico
- Incluye recetas, certificados y estudios solicitados

### 3.8 Certificados Médicos
**Ruta:** `/consultorio/certificado/nuevo/`
- Tipos: Incapacidad, Aptitud, Defunción, Libre
- Se asocian a una consulta o se crean independientemente
- Se generan en PDF profesional

### 3.9 PDFs Profesionales
- **Receta del Paciente:** `/consultorio/pdf/receta/<id>/` — PDF limpio tamaño carta con membrete, datos del médico, cédula profesional, medicamentos, indicaciones
- **Expediente Forense:** `/consultorio/pdf/forense/<id>/` — PDF completo con TODA la información clínica, trazabilidad legal, código QR de verificación

### 3.10 APIs de IA para Consulta
- **Transcripción IA:** El médico graba audio → Gemini transcribe → auto-completa campos SOAP
- **Procesamiento de Audio:** Envía audio grabado al backend, que lo procesa con Gemini
- **Generación Inmediata:** APIs para generar receta, certificado u orden de laboratorio desde la consulta sin recargar la página

## Funcionalidades Pendientes

### 3.A Ultrasonido / Imagenología
- **Qué debe hacer:** Un sub-módulo donde el médico puede crear reportes de ultrasonido con imágenes adjuntas
- **Flujo esperado:** Lista de trabajo USG → Capturar reporte (texto + imágenes) → Generar PDF del estudio
- **Modelos requeridos:** `ReporteUltrasonido`, `ImagenUltrasonido`
- **Estado:** Rutas comentadas, modelos no creados

### 3.B Avatar Live2D (Pris)
- **Qué debe hacer:** Un avatar animado (Hiyori) que aparece en la esquina de la pantalla, respira, parpadea y sigue al cursor con los ojos
- **Para qué:** UX emocional, humanizar la experiencia del médico al usar el sistema
- **Estado:** Integrado en código pero no renderiza en producción (problema de CDN/CORS)

### 3.C Firma Digital en Recetas
- **Qué debe hacer:** El médico firma digitalmente la receta (imagen de firma o firma criptográfica)
- **Estado:** Modelo `FirmaDigital` existe, falta conectar al PDF

## RECOMENDACIONES DE CRECIMIENTO

1. **Voz-a-Nota Continua:** Que el médico pueda dejar el micrófono abierto toda la consulta y el sistema genere automáticamente la nota SOAP completa al terminar
2. **Plantillas de Consulta Rápida:** Plantillas predefinidas para consultas comunes (gripa, chequeo general, diabetes, hipertensión) que auto-llenen los campos SOAP
3. **CIE-10 Autocompletado:** Al escribir el diagnóstico, sugerir automáticamente el código CIE-10 correspondiente
4. **Receta Electrónica Controlada:** Integración con COFEPRIS para recetas de medicamentos controlados
5. **Interconsulta Digital:** Botón para enviar la consulta a otro especialista dentro del sistema
6. **Agenda Drag & Drop:** Calendario visual donde el médico pueda arrastrar citas
7. **Telemedicina:** Videollamada integrada para consultas a distancia
8. **Seguimiento Automatizado:** Alertas automáticas para citas de seguimiento ("Paciente X tiene cita de control en 15 días")
9. **Calculadoras Médicas:** Calculadoras integradas (IMC, Clearance de creatinina, Glasgow, Wells, etc.)
10. **Dictado por Sección:** Poder decir "Diagnóstico:" y que automáticamente salte al campo correcto

---

# 4. MÓDULO LABORATORIO CLÍNICO (LIMS)
**Ruta:** `/laboratorio/` | **Roles:** RECEPCION, QUIMICO, ADMIN

## Descripción
Sistema completo de gestión de laboratorio clínico (LIMS - Laboratory Information Management System). Cubre desde la recepción de muestras hasta la entrega de resultados con PDFs profesionales.

## Funcionalidades Actuales (Implementadas)

### 4.1 Recepción de Laboratorio
**Ruta:** `/laboratorio/recepcion/`

**Cómo se usa:**
1. El recepcionista busca al paciente por nombre o crea uno nuevo
2. Selecciona los estudios que el paciente necesita (búsqueda por nombre o código)
3. Si hay un médico referente, lo selecciona del catálogo
4. Si hay convenio, selecciona el convenio para aplicar precios especiales
5. El sistema calcula el total automáticamente
6. Se crea la **Orden de Servicio** con folio automático (formato: `LAB-XXX-AAAA-XXXXX`)
7. Se cobra la orden (efectivo, tarjeta, transferencia o pagos mixtos)
8. Se imprimen: ticket de cobro + etiquetas de tubos

### 4.2 Lista de Trabajo
**Ruta:** `/laboratorio/lista-trabajo/`

**Cómo se usa:**
1. Muestra TODAS las órdenes del día organizadas por estado:
   - **PENDIENTE** — Cobrada, esperando toma de muestra
   - **EN_PROCESO** — Muestra tomada, pendiente de captura
   - **RESULTADOS_LISTOS** — Resultados capturados, pendiente de validación
   - **ENTREGADO** — Resultados entregados
2. Filtros: por fecha, estado, paciente
3. Se puede imprimir la **Hoja de Trabajo** en PDF (para uso en el área analítica)
4. QR de la hoja de trabajo para acceso rápido desde el celular

### 4.3 Toma de Muestra
**Ruta:** `/laboratorio/toma-muestra/`

**Cómo se usa:**
1. El flebotomista ve las muestras pendientes
2. Registra la toma con hora exacta
3. Se imprimen etiquetas térmicas para los tubos con código de barras/QR
4. Si la muestra es rechazada (hemólisis, cantidad insuficiente), se registra el motivo

### 4.4 Captura de Resultados (Industrial)
**Ruta:** `/laboratorio/captura/<orden_id>/`

**Cómo se usa:**
1. El químico selecciona una orden
2. Ve todos los estudios y parámetros de esa orden
3. Captura los valores uno por uno
4. El sistema automáticamente:
   - Marca valores fuera de rango como **ALTOS** o **BAJOS** con colores
   - Detecta **valores críticos** (pánico) y obliga a notificar al médico
   - Calcula índices eritrocitarios automáticamente (VCM, HCM, CMHC)
5. Se puede usar **IA (Gemini)** para captura por voz: el químico dicta los valores y se llenan automáticamente
6. Al guardar, se actualiza el estado de la orden

### 4.5 Notificación de Valores Críticos (ISO 15189)
**Ruta:** `/laboratorio/notificacion-panico/<orden_id>/`
- Cuando un resultado cae en rango de pánico, el sistema obliga a registrar:
  - Quién fue notificado
  - Hora de notificación
  - Canal (teléfono, presencial)
  - Observaciones

### 4.6 Control de Calidad
**Ruta:** `/laboratorio/control-calidad/`
- Registro de controles internos y externos
- Gráficas de Levey-Jennings (tendencias)

### 4.7 Impresión de Resultados (PDF)
**Ruta:** `/laboratorio/imprimir/<orden_id>/`
- PDF profesional con membrete de la empresa
- Valores fuera de rango resaltados
- Responsable sanitario con cédula y firma
- Código QR de verificación

### 4.8 Etiquetas Térmicas
- Etiquetas de tubo con código de barras
- Etiquetas QR para acceso rápido
- Impresión en lote para múltiples tubos
- Vista previa antes de imprimir

### 4.9 LIMS - Configurador de Estudios (SaaS)
**Ruta:** `/laboratorio/lims/estudios/`

**Cómo se usa:**
1. El administrador puede crear, editar, duplicar o eliminar estudios
2. Cada estudio tiene:
   - Nombre, código, categoría, precio
   - Muestra requerida (suero, sangre completa, orina, etc.)
   - Días de entrega
   - Si es perfil (agrupa varios estudios)
3. Cada estudio tiene **parámetros** configurables:
   - Nombre del parámetro
   - Unidades
   - Método de análisis
   - **Rangos de referencia** por edad y sexo

### 4.10 Escaneo de Receta con IA (OCR)
- El recepcionista toma foto de la receta médica
- Gemini Vision extrae los estudios solicitados
- Se pre-llenan automáticamente en la orden

### 4.11 Escaneo de Identificación con IA
- Se toma foto del INE/pasaporte
- Gemini extrae nombre, fecha de nacimiento, CURP
- Se pre-llenan los datos del paciente

### 4.12 Entrega de Resultados
**Ruta:** `/laboratorio/entrega-resultados/`
- Lista de resultados listos para entregar
- Marcar como entregado (presencial)
- Enviar por email masivo
- Marcar WhatsApp enviado
- Link público para consulta (sin login): `/laboratorio/resultados/publico/<token>/`

### 4.13 Maquila
**Ruta:** `/laboratorio/maquila/`
- Registro de estudios enviados a laboratorios externos
- Seguimiento de status

### 4.14 Carga de Tarifas (Admin)
**Ruta:** `/laboratorio/admin/cargar-tarifas/`
- Subir archivo CSV con catálogo de estudios y precios
- Importación masiva

## Funcionalidades Pendientes

### 4.A Consentimiento Informado Digital
- **Qué debe hacer:** Antes de la toma de muestra, el paciente firma en pantalla (tablet) aceptando el procedimiento
- **Para qué:** Cumplimiento NOM-004-SSA3-2012, protección legal
- **Modelos:** `ConsentimientoInformado`, `RegistroAuditoriaConsentimiento`

### 4.B Interfaz con Equipos de Análisis
- **Qué debe hacer:** Conexión directa con analizadores (hematología, química clínica, uroanálisis) vía protocolo ASTM/HL7
- **Para qué:** Eliminar captura manual, reducir errores humanos
- **Complejidad:** Alta — requiere middleware de comunicación serial/TCP

### 4.C Modelo de Convenios
- **Qué debe hacer:** Catálogo de convenios con médicos/empresas con precios especiales por estudio
- **Estado:** La API existe pero retorna vacío, falta modelo `Convenio`

## RECOMENDACIONES DE CRECIMIENTO

1. **Captura por Código de Barras:** Escanear el código de la etiqueta del tubo para abrir automáticamente la pantalla de captura de esa orden
2. **Auto-validación por Reglas:** Reglas Delta (comparar con resultado anterior del mismo paciente) para detectar errores de captura
3. **Resultados Parciales:** Liberar resultados de un estudio sin esperar a que toda la orden esté completa
4. **Historial de Resultados con Gráficas:** Ya existe parcialmente — expandir para que pacientes vean tendencias de sus valores
5. **Panel de Monitoreo en Tiempo Real:** Pantalla tipo TV para el área analítica mostrando órdenes pendientes, prioridades y tiempos
6. **Integración WhatsApp API:** Enviar resultados PDF automáticamente vía WhatsApp Business API
7. **QR en Ticket:** El paciente escanea el QR del ticket y ve el estado de sus estudios en tiempo real
8. **Gráficas de Productividad:** Métricas de tiempos promedio (recepción → toma → captura → entrega)
9. **Alertas de Caducidad de Reactivos:** Integrar con control de calidad para alertar cuando un reactivo está por vencer
10. **Microbiología:** Módulo específico para antibiogramas y cultivos con temporización

---

# 5. MÓDULO FARMACIA Y PUNTO DE VENTA
**Ruta:** `/farmacia/` | **Roles:** CAJERO, FARMACIA, GERENTE, ADMIN

## Descripción
Sistema integral de farmacia que combina un **Punto de Venta (PDV)** rápido para ventas mostrador con un **ERP Farmacéutico** para gestión de inventario, compras, kardex y control de calidad.

## Funcionalidades Actuales

### 5.1 Dashboard de Farmacia
**Ruta:** `/farmacia/`
- KPIs del día: ventas totales, tickets, promedio por ticket
- Top 5 productos más vendidos
- Alertas: productos próximos a caducar (FEFO), stock bajo mínimo
- Gráfica de ventas de la semana

### 5.2 Punto de Venta (PDV)
**Ruta:** `/farmacia/pdv/`

**Cómo se usa:**
1. **Buscar producto:** Por nombre, sustancia activa o código de barras. Se puede usar lector de código de barras físico
2. **Agregar al carrito:** Clic en el producto → se agrega al carrito con cantidad 1
3. **Verificaciones automáticas:**
   - Si el producto es **antibiótico**, pide la receta médica y datos del médico
   - Si hay **oferta/descuento activo**, se aplica automáticamente
   - Si el stock es **bajo**, muestra alerta amarilla
   - Si está **por caducar** (FEFO), muestra alerta roja
4. **Aplicar cupón:** Se puede ingresar un código de cupón para descuento
5. **Cobrar:** Se selecciona método de pago (efectivo, tarjeta, transferencia) o pagos mixtos
6. **Imprimir ticket:** Automáticamente se genera el ticket de venta
7. **Despacho PEPS:** El sistema automáticamente descuenta del lote más antiguo (PEPS/FIFO)

### 5.3 Historial de Ventas
**Ruta:** `/farmacia/historial-ventas/`
- Lista de todas las ventas con filtros por fecha
- Detalle de cada venta
- Reimpresión de tickets

### 5.4 Devoluciones
**Ruta:** `/farmacia/devoluciones/`

**Cómo se usa:**
1. Buscar la venta original por folio
2. Seleccionar los productos a devolver
3. Indicar motivo y tipo de devolución (reembolso, cambio)
4. Solo gerentes/admin pueden autorizar devoluciones
5. El sistema automáticamente:
   - Reingresa el stock al inventario
   - Registra el movimiento en caja
   - Genera nota de crédito

### 5.5 Entrada de Mercancía (Almacén)
**Ruta:** `/farmacia/almacen/entradas/`

**Cómo se usa:**
1. Se registra la entrada con datos del proveedor
2. Se escanean o agregan los productos recibidos
3. Para cada producto: cantidad, lote, fecha de caducidad, precio de compra
4. El sistema actualiza el stock automáticamente
5. Genera un movimiento de Kardex

### 5.6 Registro de Compras (ERP)
**Ruta:** `/farmacia/erp/compras/registrar/`
- Registro formal de compras a proveedores
- Control de factura, remisión, orden de compra
- Afectación automática de Kardex

### 5.7 Kardex
**Ruta:** `/farmacia/erp/kardex/`
- Historial de TODOS los movimientos de inventario
- Tipos: Entrada, Salida, Ajuste, Merma, Traspaso
- Filtros por producto, fecha, tipo
- Movimientos manuales requieren autorización de gerente

### 5.8 Libro de Control de Antibióticos
**Ruta:** `/farmacia/libro-control/`
- Registro legal obligatorio de venta de antibióticos
- Datos de la receta, médico, paciente
- Cumplimiento NOM-059

### 5.9 Políticas de Descuento
**Ruta:** `/farmacia/politicas-descuento/`
- Creación de políticas de descuento por producto o categoría
- Vigencia temporal (fecha inicio/fin)
- Aplicación automática en PDV

### 5.10 Corte de Caja
**Ruta:** `/finanzas/corte/` y `/farmacia/erp/corte-caja/`
- Corte ciego: el cajero cuenta el efectivo sin ver el total del sistema
- El sistema compara y detecta diferencias
- Registro de gastos operativos del día
- Detalle de pagos por método (efectivo, tarjeta, transferencia)

### 5.11 Etiquetas
- Etiquetas con código de barras para productos
- Generación en lote
- Etiquetas térmicas para precios

### 5.12 Reporte de Valorización
**Ruta:** `/farmacia/erp/reporte/valorizacion/`
- Valor total del inventario a precio de compra y venta
- Desglose por producto y lote

### 5.13 Ajustes de Inventario
**Ruta:** `/farmacia/almacen/ajustes/`
- Ajustes manuales por conteo físico
- Requieren motivo y autorización
- Se registran como movimiento de Kardex

## Funcionalidades Pendientes

### 5.A Merma Inteligente
- Registro de merma con evidencia fotográfica
- Análisis de patrones de merma por producto

### 5.B Predicción de Desabasto
- Algoritmo que analiza ventas históricas y predice cuándo se agotará un producto

## RECOMENDACIONES DE CRECIMIENTO

1. **Punto de Venta Offline:** Que el PDV funcione sin internet y sincronice cuando se recupere la conexión
2. **Lector de Código de Barras Integrado:** Configuración de lectores USB/Bluetooth directamente desde el sistema
3. **Precios por Sucursal:** Diferentes precios para diferentes sucursales
4. **Alertas por WhatsApp:** Notificar al gerente cuando un producto llega a stock mínimo
5. **Receta Electrónica Vinculada:** Si el médico genera receta desde el consultorio, que aparezca automáticamente en el PDV para despacho
6. **Programa de Lealtad:** Puntos por compra, canje de recompensas
7. **Catálogo de Proveedores:** Comparador de precios entre proveedores
8. **Órdenes de Compra Automáticas:** Cuando un producto llega a punto de re-orden, generar automáticamente la orden de compra
9. **Lectura de Factura XML:** Subir el XML de la factura del proveedor y que auto-registre la entrada
10. **Panel de Precios con Cambio de Precios Masivo:** Herramienta para actualizar precios de múltiples productos a la vez (por porcentaje o monto fijo)

---

# 6. MÓDULO INTELIGENCIA ARTIFICIAL (Gemini)
**Ruta:** `/ia/` | **Roles:** Todos (según funcionalidad)

## Descripción
Motor de IA basado en **Google Gemini** que proporciona capacidades de visión por computadora (OCR), procesamiento de voz, análisis clínico y asistencia médica inteligente.

## Funcionalidades Actuales

### 6.1 Dashboard IA
**Ruta:** `/ia/`
- Centro de control de todas las funciones de IA
- Acceso a OCR, Voz y Asistente

### 6.2 OCR de Recetas Médicas
**Ruta:** `/ia/ocr/procesar/`

**Cómo se usa:**
1. Subir foto o imagen de la receta médica
2. Gemini Vision analiza la imagen y extrae:
   - Nombre del médico
   - Cédula profesional
   - Estudios solicitados
   - Medicamentos recetados
3. Los datos se presentan para revisión
4. Con un clic, se puede crear una orden de laboratorio automáticamente desde los datos extraídos

### 6.3 Transcripción de Audio
**Ruta:** `/ia/voz/transcribir/`

**Cómo se usa:**
1. Subir archivo de audio o grabar directamente
2. Gemini transcribe el audio a texto
3. Extrae entidades médicas: síntomas, diagnósticos, medicamentos
4. Se usa para auto-llenar notas clínicas

### 6.4 Asistente Médico (Chat)
**Ruta:** `/ia/asistente/`

**Cómo se usa:**
1. Se escribe una pregunta en lenguaje natural
2. Gemini responde con conocimiento médico
3. Puede resolver consultas sobre:
   - Interacciones medicamentosas
   - Dosis recomendadas
   - Guías clínicas
   - Interpretación de resultados

### 6.5 APIs de IA (Usadas por otros módulos)
- **Análisis de Síntomas:** Recibe lista de síntomas → sugiere diagnósticos diferenciales
- **Verificación de Interacciones:** Recibe lista de medicamentos → detecta interacciones peligrosas
- **Captura por Voz en Laboratorio:** El químico dicta valores → se capturan automáticamente

## Funcionalidades Pendientes

### 6.A Migración a SDK google-genai v1.0+
- Actualmente usa `google-generativeai==0.4.0` (deprecated)
- Debe migrar a `google-genai` con nueva API: `client = genai.Client()`

### 6.B Modelo Fine-Tuned para Laboratorio
- Entrenar un modelo específico para interpretar resultados de laboratorio

## RECOMENDACIONES DE CRECIMIENTO

1. **Análisis Predictivo de Resultados:** "Este paciente tiene tendencia a elevación de glucosa" basado en historial
2. **Resumen Ejecutivo para el Director:** Gemini genera un resumen diario: "Hoy se atendieron 45 pacientes, 3 con valores críticos, ventas de $15,000"
3. **Chatbot para Pacientes:** IA que responda preguntas frecuentes del paciente sobre sus resultados
4. **Correlación de Estudios:** "Paciente con creatinina alta + potasio alto → posible insuficiencia renal"
5. **Lectura Automática de Imágenes de Equipos:** OCR para leer pantallas de analizadores y capturar resultados
6. **Generación Automática de Informes de Calidad:** Gemini analiza datos de control de calidad y genera el informe mensual
7. **Sugerencia de Estudios Adicionales:** Basado en los resultados, sugerir estudios complementarios
8. **Modelo Local (Offline):** Para funcionar sin internet, usar un modelo local más pequeño como fallback

---

# 7. MÓDULO RECEPCIÓN Y AGENDAMIENTO
**Ruta:** `/recepcion/` | **Rol:** RECEPCION, ADMIN

## Descripción
Módulo de recepción general para la clínica. Gestiona el registro de pacientes, agendamiento de citas y flujo de espera.

## Funcionalidades Actuales

### 7.1 Dashboard de Recepción
- Vista general del día: citas programadas, pacientes en espera
- Contadores de estado

### 7.2 Registrar Paciente
**Ruta:** `/recepcion/registrar-paciente/`
- Formulario completo: nombre, apellidos, fecha de nacimiento, sexo, teléfono, email, dirección, CURP

### 7.3 Buscar Paciente
**Ruta:** `/recepcion/buscar-paciente/`
- Búsqueda por nombre, teléfono o CURP
- Resultados instantáneos con AJAX

### 7.4 Agendar Cita
**Ruta:** `/recepcion/agendar-cita/`
- Seleccionar paciente, médico, fecha, hora, motivo
- Duración estimada

### 7.5 Check-in
**Ruta:** `/recepcion/check-in/<cita_id>/`
- Confirmar llegada del paciente
- Cambia estado de PROGRAMADA a EN_ESPERA

### 7.6 Lista de Espera
**Ruta:** `/recepcion/lista-espera/`
- Pacientes que ya hicieron check-in pero no han sido atendidos

### 7.7 Cobro de Consulta
**Ruta:** `/recepcion/cobrar/<cita_id>/`
- Cobro de la consulta médica
- Métodos de pago múltiples

## RECOMENDACIONES DE CRECIMIENTO

1. **Recordatorios Automáticos:** SMS/WhatsApp 24h antes de la cita
2. **Auto Check-in con Kiosco:** El paciente se registra solo en una tablet
3. **Estimación de Tiempo de Espera:** "Tiempo aproximado: 15 minutos"
4. **Calendario Visual:** Agenda tipo Google Calendar para recepción
5. **Confirmación de Cita por WhatsApp:** Botón para confirmar/cancelar desde WhatsApp

---

# 8. MÓDULO ENFERMERÍA Y TRIAGE
**Ruta:** `/enfermeria/` | **Rol:** ENFERMERIA, ADMIN

## Descripción
Módulo dedicado al personal de enfermería para la captura de signos vitales, triage y monitoreo de pacientes.

## Funcionalidades Actuales

### 8.1 Dashboard
- Pacientes pendientes de triage
- Alertas de signos críticos

### 8.2 Lista de Pacientes para Triage
**Ruta:** `/enfermeria/lista-triage/`
- Pacientes con check-in que necesitan toma de signos

### 8.3 Captura de Signos Vitales
**Ruta:** `/enfermeria/capturar-signos/<cita_id>/`
- Peso, talla (auto-calcula IMC)
- Presión arterial (sistólica/diastólica)
- Frecuencia cardíaca
- Temperatura
- Frecuencia respiratoria
- Saturación de oxígeno
- Detección automática de valores fuera de rango

### 8.4 Historial de Signos
**Ruta:** `/enfermeria/historial/<paciente_id>/`
- Historial de signos vitales del paciente en orden cronológico

### 8.5 Gráficas de Tendencias
**Ruta:** `/enfermeria/graficas/<paciente_id>/`
- Gráficas interactivas (peso, presión, glucosa) en el tiempo

### 8.6 Alertas de Signos Críticos
**Ruta:** `/enfermeria/alertas/`
- Lista de pacientes con signos fuera de rango que requieren atención inmediata

## RECOMENDACIONES DE CRECIMIENTO

1. **Escalas de Dolor:** Escala visual analógica (EVA) integrada
2. **Glasgow Coma Scale:** Cálculo automático
3. **Notas de Enfermería:** Registro de intervenciones y observaciones
4. **Control de Líquidos:** Balance hídrico (ingresos/egresos)
5. **Signos Vitales desde Dispositivos:** Conexión con oxímetros, tensiómetros Bluetooth

---

# 9. MÓDULO PACIENTES — HISTORIAL 360° Y PORTAL
**Ruta:** `/pacientes/` | **Roles:** Todos (Staff) + Portal Público (Pacientes)

## Descripción
Centro de información del paciente. Incluye el **Historial 360°** (vista completa de toda la información del paciente) y el **Portal del Paciente** (acceso público para que el paciente vea sus resultados, consultas y recetas).

## Funcionalidades Actuales

### 9.1 Lista de Pacientes
**Ruta:** `/pacientes/`
- Búsqueda por nombre, teléfono, CURP
- Tabla con datos principales

### 9.2 Historial 360°
**Ruta:** `/pacientes/<id>/historial-360/`
- Vista unificada con TODA la información del paciente:
  - Datos demográficos
  - Consultas médicas (todas)
  - Resultados de laboratorio (todos)
  - Recetas
  - Certificados médicos
  - Estudios de imagen
  - Signos vitales
  - Antecedentes
- Ordenado cronológicamente como timeline

### 9.3 Timeline de Consultas
**Ruta:** `/pacientes/<id>/timeline/`
- Vista tipo "línea del tiempo" de las consultas del paciente

### 9.4 Gráficas de Signos Vitales
**Ruta:** `/pacientes/<id>/graficas-signos/`
- Gráficas interactivas de signos vitales en el tiempo
- API JSON para datos dinámicos

### 9.5 Historia Clínica Completa
**Ruta:** `/pacientes/<id>/historia-clinica/`
- Documento formal de historia clínica completa

### 9.6 Expediente Clínico Unificado
**Ruta:** `/pacientes/<id>/expediente/`
- Vista detallada tipo "expediente" con pestañas:
  - Datos generales
  - Historia clínica
  - Consultas
  - Laboratorio
  - Recetas
  - Certificados
  - Estudios de imagen
- Exportable a PDF

### 9.7 Portal del Paciente (Público)
**Ruta:** `/pacientes/portal/`

**Cómo se usa (por el paciente):**
1. El paciente solicita acceso desde `/pacientes/portal/solicitar-acceso/`
2. El administrador aprueba y le envía credenciales
3. El paciente entra con email y contraseña
4. Ve su dashboard con:
   - Últimas consultas
   - Resultados de laboratorio (con descarga PDF)
   - Recetas activas
   - Su perfil
5. Puede cambiar su contraseña
6. Puede descargar resultados en PDF directamente

## RECOMENDACIONES DE CRECIMIENTO

1. **Consentimiento GDPR/LFPDPPP:** Gestión de permisos del paciente sobre sus datos
2. **Foto del Paciente:** Captura de foto desde webcam/celular para el expediente
3. **QR de Paciente:** Tarjeta QR única que al escanearla abre el expediente
4. **Notificaciones al Paciente:** "Tus resultados ya están listos" vía email/SMS
5. **Historial de Medicamentos Activos:** Lista de medicamentos que el paciente está tomando actualmente
6. **Alertas Clínicas Automáticas:** "Paciente diabético + receta de metformina = VERIFICAR función renal"
7. **Compartir con Otro Médico:** El paciente puede compartir su expediente con un médico externo vía link temporal seguro

---

# 10. MÓDULO SEGURIDAD
**Ruta:** `/seguridad/` | **Rol:** ADMIN

## Descripción
Sistema de seguridad con autenticación de dos factores (2FA), gestión de sesiones activas y auditoría de acciones sensibles.

## Funcionalidades Actuales

### 10.1 Autenticación 2FA (TOTP)
- Activar/desactivar autenticación por código temporal (Google Authenticator, Authy)
- Código QR para escanear con la app de autenticación
- Códigos de backup (uso único) en caso de perder el dispositivo

### 10.2 Gestión de Sesiones
- Ver todas las sesiones activas del usuario (dispositivo, IP, ubicación)
- Cerrar sesión remota en cualquier dispositivo
- Cerrar todas las sesiones excepto la actual

### 10.3 Dashboard de Auditoría
- Métricas: intentos de login fallidos, acciones sensibles, sesiones sospechosas
- Gráficas de actividad por hora

### 10.4 Logs de Auditoría
- Registro de TODAS las acciones sensibles (login, cambio de precio, anulación de venta, etc.)
- Filtros por usuario, acción, fecha
- Exportable

## RECOMENDACIONES DE CRECIMIENTO

1. **Login con Biometría:** Huella digital o reconocimiento facial
2. **Geofencing:** Bloquear acceso si el usuario está fuera de la zona geográfica permitida
3. **Rate Limiting:** Bloqueo automático después de X intentos fallidos
4. **Alerta de Login Sospechoso:** Notificación cuando se detecta login desde IP/dispositivo desconocido
5. **Política de Contraseñas:** Forzar cambio cada 90 días, complejidad mínima
6. **Cifrado de Datos Sensibles:** Cifrado AES para datos de pacientes en reposo

---

# 11. MÓDULO BIENESTAR EMOCIONAL
**Ruta:** `/bienestar/` | **Roles:** Todos los empleados

## Descripción
Módulo inspirado en la app **YANA** para el bienestar emocional de los empleados. Incluye diario emocional, chat con IA, recursos de crecimiento y estadísticas de bienestar.

## Funcionalidades Actuales

### 11.1 Dashboard (Estilo YANA)
- Afirmación del día (rota diariamente)
- Última entrada del diario
- Racha de días consecutivos
- Acceso rápido a chat, diario y recursos

### 11.2 Chat con PRIS (IA)
- Chat confidencial donde el empleado puede hablar con la IA
- PRIS responde con empatía y técnicas de apoyo emocional
- Detección de riesgo emocional (si detecta crisis, sugiere ayuda profesional)

### 11.3 Diario Emocional
- Registrar cómo se siente el empleado cada día
- Seleccionar emoción (feliz, tranquilo, ansioso, triste, enojado, etc.)
- Escribir reflexión personal
- Historial de entradas

### 11.4 Estadísticas del Diario
- Gráficas de tendencia emocional
- Distribución de emociones por período
- Identificación de patrones

### 11.5 Recursos de Crecimiento
- Biblioteca de recursos: videos, artículos, ejercicios de mindfulness
- Filtros por categoría
- Detalle de cada recurso

### 11.6 Consultorio de Bienestar
- Agendar cita con psicólogo/counselor
- Integración con agenda

## RECOMENDACIONES DE CRECIMIENTO

1. **Meditación Guiada:** Audio/video de meditaciones integradas
2. **NOM-035 Integrada:** Cuestionarios de riesgo psicosocial directamente desde este módulo
3. **Alertas Anónimas al Director:** Si un empleado reporta riesgo alto, notificar al director sin revelar identidad
4. **Gamificación:** Badges por mantener racha, completar ejercicios
5. **Grupos de Apoyo:** Foro anónimo entre empleados

---

# 12. MÓDULO LOGÍSTICA Y TRANSFERENCIAS
**Ruta:** `/logistica/` | **Roles:** LOGISTICA, GERENTE, ADMIN

## Descripción
Gestión de rutas de recolección, visitas a domicilio y transferencias de inventario entre sucursales.

## Funcionalidades Actuales

### 12.1 Monitor de Rutas
- Vista general de rutas activas
- Estado de cada ruta

### 12.2 Mapa de Rutas
- Visualización geográfica de las rutas
- Puntos de recolección

### 12.3 Asignar Visita
- Asignar un técnico a una visita domiciliaria
- Información del paciente y estudios a recolectar

### 12.4 Transferencias entre Sucursales
- **Crear transferencia:** Seleccionar sucursal origen y destino
- **Agregar productos:** Seleccionar productos y cantidades
- **Enviar:** Marcar la transferencia como "en tránsito"
- **Recibir:** La sucursal destino confirma la recepción
- **Rastreo:** Token UUID para rastreo público
- **Log:** Historial completo de cada movimiento

## RECOMENDACIONES DE CRECIMIENTO

1. **GPS en Tiempo Real:** Tracking del vehículo de recolección
2. **Optimización de Rutas:** Algoritmo que calcule la ruta más eficiente (Google Maps API)
3. **Foto de Evidencia:** El técnico toma foto de la muestra al recolectar
4. **Firma Digital del Paciente:** El paciente firma en el celular del técnico al entregar la muestra
5. **Integración con Fletes:** Para envíos de maquila a laboratorios externos

---

# 13. MÓDULO MARKETING, CUPONES Y CAMPAÑAS
**Ruta:** `/marketing/` | **Roles:** MARKETING, GERENTE, ADMIN

## Descripción
Sistema de crecimiento comercial con campañas de marketing, cupones de descuento, gestión de contactos y entrenamiento de IA.

## Funcionalidades Actuales

### 13.1 Dashboard de Marketing
- Métricas: cupones generados, canjeados, campañas activas

### 13.2 Campañas
- Crear campañas con nombre, descripción, fecha inicio/fin
- Tipos: email, WhatsApp, redes sociales
- Dashboard de seguimiento

### 13.3 Cupones
- Generar cupones con código único
- Descuento porcentual o monto fijo
- Vigencia temporal
- Límite de usos
- Aplicación automática en PDV

### 13.4 Contactos
- Base de datos de contactos (pacientes, médicos, empresas)
- Importación masiva desde archivo

### 13.5 Entrenamiento IA
- Interfaz para entrenar la IA con documentos y conocimiento específico del negocio

## RECOMENDACIONES DE CRECIMIENTO

1. **Email Marketing Automatizado:** Secuencias de emails automáticas
2. **WhatsApp Business API:** Enviar campañas masivas vía WhatsApp
3. **Programa de Referidos:** "Trae un amigo y obtén 10% de descuento"
4. **Encuestas de Satisfacción:** Automatizadas post-consulta/post-estudio
5. **Landing Pages:** Páginas de captura para campañas específicas
6. **A/B Testing:** Probar diferentes mensajes y medir cuál convierte mejor

---

# 14. MÓDULO CONTABILIDAD Y FACTURACIÓN CFDI
**Ruta:** `/contabilidad/` | **Roles:** CONTABILIDAD, ADMIN

## Descripción
Módulo de facturación electrónica CFDI 4.0 y gestión contable. Actualmente tiene la estructura de facturación y los stubs de contabilidad formal.

## Funcionalidades Actuales

### 14.1 Gestión de Clientes de Facturación
- Alta de clientes con datos fiscales (RFC, razón social, régimen fiscal, código postal, uso de CFDI)
- Búsqueda de clientes

### 14.2 Creación de Facturas
- Seleccionar cliente
- Agregar conceptos con clave SAT, cantidad, precio unitario
- Cálculo automático de impuestos (IVA)
- Seleccionar forma de pago y método de pago

### 14.3 Detalle de Factura
- Vista completa con todos los datos fiscales
- Conceptos con desglose de impuestos

### 14.4 Timbrado (Stub)
- La función existe pero NO está conectada a un PAC real
- Cuando se active, enviará el XML al SAT y obtendrá el timbre fiscal

### 14.5 Descarga de PDF
- PDF de la factura con formato profesional

### 14.6 Contabilidad (Stubs - En construcción)
- Dashboard, catálogo de cuentas, pólizas — todas devuelven datos mock por ahora

## Funcionalidades Pendientes

### 14.A Timbrado Real CFDI 4.0
- Conexión con PAC (Finkok, Digifort o SW Sapien)
- Certificado de Sello Digital (CSD)

### 14.B Contabilidad Formal
- Catálogo de cuentas SAT
- Pólizas contables (ingresos, egresos, diario)
- Balanza de comprobación
- Estado de resultados

### 14.C Complemento de Pago
- Para pagos parciales o a crédito

## RECOMENDACIONES DE CRECIMIENTO

1. **Facturación Automática:** Al cobrar una orden de laboratorio o venta de farmacia, generar factura automáticamente si el cliente lo solicita
2. **Conciliación Bancaria:** Importar estados de cuenta y conciliar con movimientos registrados
3. **Cuentas por Cobrar/Pagar:** Control de crédito a clientes y proveedores
4. **Reportes SAT:** Generación de XML para declaraciones mensuales
5. **Nota de Crédito:** Para cancelaciones y devoluciones
6. **Multi-moneda:** Para clínicas en zonas fronterizas (USD/MXN)

---

# 15. MÓDULO FINANZAS SEGREGADAS
**Ruta:** `/finanzas/` | **Roles:** GERENTE, DIRECTOR, ADMIN

## Descripción
Sistema de cajas segregadas por unidad de negocio: Laboratorio y Farmacia tienen cajas independientes, con un dashboard maestro que consolida todo.

## Funcionalidades Actuales

### 15.1 Caja de Laboratorio
**Ruta:** `/finanzas/lab/caja/`
- Ingresos del día por cobro de estudios
- Desglose por método de pago
- Comparativo con días anteriores

### 15.2 Caja de Farmacia
**Ruta:** `/finanzas/farmacia/caja/`
- Ingresos del día por ventas de farmacia
- Desglose por método de pago
- Gastos operativos

### 15.3 Dashboard Master
**Ruta:** `/finanzas/master/`
- Consolidado de ambas cajas
- Totales del día, semana, mes
- Gráficas de tendencia

## RECOMENDACIONES DE CRECIMIENTO

1. **Presupuestos:** Establecer presupuesto mensual y comparar con real
2. **Flujo de Efectivo Proyectado:** Proyección a 30/60/90 días
3. **Alertas Financieras:** Notificar si los ingresos están por debajo de la meta

---

# 16. MÓDULO RECURSOS HUMANOS
**Ruta:** `/rh/` | **Roles:** RH, DIRECTOR, ADMIN

## Descripción
Gestión de recursos humanos con evaluaciones NOM-035, evaluaciones de desempeño 360° y matriz de talento.

## Funcionalidades Actuales

### 16.1 Evaluaciones NOM-035
**Ruta:** `/rh/evaluaciones/`
- Cuestionarios de factores de riesgo psicosocial
- Genera PDF con resultados
- Cumplimiento obligatorio de la norma

### 16.2 Evaluación de Desempeño
**Ruta:** `/rh/desempeno/nueva/`
- Evaluación por competencias
- Calificación numérica por área
- Plan de desarrollo individual

### 16.3 Mis Resultados
**Ruta:** `/rh/mis-resultados/`
- El empleado ve sus propias evaluaciones

### 16.4 Matriz de Talento (9-Box)
**Ruta:** `/rh/matriz-talento/`
- Visualización tipo 9-box para mapear potencial vs desempeño

## Funcionalidades Pendientes

### 16.A Nómina
- Catálogo de conceptos (percepciones, deducciones)
- Periodos de nómina (quincenal, mensual)
- Cálculo automático (ISR, IMSS, INFONAVIT)
- Recibos de nómina
- Timbrado CFDI de nómina

### 16.B Control de Asistencia
- Horarios de trabajo por empleado
- Registro de entrada/salida
- Incidencias (faltas, retardos, permisos)
- Reporte de asistencia mensual
- Integración con reloj checador

## RECOMENDACIONES DE CRECIMIENTO

1. **Expediente Digital del Empleado:** Documentos escaneados (contrato, INE, CURP, acta de nacimiento)
2. **Vacaciones:** Solicitud y aprobación de vacaciones
3. **Capacitación:** Registro de cursos y certificaciones
4. **Organigramas:** Visualización de estructura organizacional
5. **Encuestas de Clima Laboral:** Más allá de NOM-035
6. **Onboarding Digital:** Proceso de ingreso de nuevos empleados automatizado
7. **Calculadora de Liquidación:** Para finiquitos y liquidaciones

---

# 17. MÓDULO PANEL DEL DIRECTOR
**Ruta:** `/director/` | **Roles:** DIRECTOR, GERENTE, ADMIN

## Descripción
Centro de control ejecutivo con métricas en tiempo real, sistema de autorizaciones, buzón de quejas, ranking de desempeño y herramientas de liderazgo.

## Funcionalidades Actuales

### 17.1 Dashboard Ejecutivo
**Ruta:** `/director/`
- **Ventas del día:** Total, efectivo, tarjeta, transferencia
- **Ocupación por sucursal:** Porcentaje de utilización
- **Alertas de laboratorio:** Valores críticos del día
- **Productos con bajo stock:** Lista de alertas FEFO
- **Resumen de autorizaciones pendientes**

### 17.2 Coach Ejecutivo (IA)
**Ruta:** `/director/coach/`
- Chat con IA especializada en liderazgo y gestión empresarial
- Responde preguntas sobre estrategia, manejo de personal, KPIs

### 17.3 Buzón de Quejas y Sugerencias (Kanban)
**Ruta:** `/director/buzon/`
- Tablero Kanban: Pendiente → En Revisión → Resuelto
- Los empleados y clientes envían quejas/sugerencias anónimamente
- El director mueve las tarjetas y registra acciones

### 17.4 Biblioteca de Liderazgo
**Ruta:** `/director/biblioteca/`
- Catálogo de libros recomendados
- Estado: Por leer, Leyendo, Leído
- Agregar nuevos libros

### 17.5 Sistema de Autorizaciones
**Ruta:** `/director/autorizaciones/`
- Solicitudes pendientes de aprobación:
  - Descuentos especiales
  - Anulaciones de venta
  - Ajustes de inventario
  - Devoluciones
- Aprobar/rechazar con un clic
- UUID único por solicitud para validación

### 17.6 Panel de Incidencias
**Ruta:** `/director/auditoria/incidencias/`
- Registro de excepciones a políticas operativas
- Clasificación: leve, moderada, grave
- Seguimiento

### 17.7 Ranking de Desempeño
**Ruta:** `/director/ranking/`
- Ranking de empleados por métricas (ventas, productividad)
- Detalle individual

### 17.8 Reporte de Fricción
**Ruta:** `/reporte-friccion/`
- Análisis de puntos de fricción en la operación

### 17.9 Tu Opinión (Público)
**Ruta:** `/tu-opinion/`
- URL pública para que clientes envíen feedback

## RECOMENDACIONES DE CRECIMIENTO

1. **Dashboard en Pantalla TV:** Modo pantalla completa para monitor en oficina
2. **Reportes Automáticos por Email:** Resumen diario/semanal enviado al director
3. **Metas y OKRs:** Establecer objetivos y key results por departamento
4. **Alertas Inteligentes:** "Las ventas de hoy son 30% menores que el promedio"
5. **Comparativo entre Sucursales:** Benchmark de rendimiento

---

# 18. MÓDULO COMUNICACIÓN INTERNA
**Ruta:** `/chat/` | **Roles:** Todos

## Descripción
Sistema de mensajería interna entre empleados del sistema. Tipo WhatsApp empresarial.

## Funcionalidades Actuales

### 18.1 Enviar Mensaje
- Chat directo entre usuarios del sistema
- Envío de mensajes de texto

### 18.2 Listar Conversaciones
- Ver todas las conversaciones activas

### 18.3 Obtener Mensajes
- Historial de mensajes de una conversación

### 18.4 Listar Usuarios
- Ver usuarios disponibles para chatear

## RECOMENDACIONES DE CRECIMIENTO

1. **Interfaz de Chat Visual:** Tipo WhatsApp con burbujas de mensaje
2. **Notificaciones en Tiempo Real:** WebSockets para mensajes instantáneos
3. **Grupos:** Canales por departamento (Lab, Farmacia, Médicos)
4. **Archivos Adjuntos:** Enviar fotos, PDFs
5. **Mensajes de Voz:** Notas de voz integradas
6. **Menciones:** @usuario para notificar directamente
7. **Bot Pris:** La IA puede participar en las conversaciones para resolver dudas

---

# 19. MÓDULO IoT Y KIOSCO
**App:** `iot/` | **Estado:** Solo modelos creados

## Descripción (Visión a futuro)
Sistema de kioscos de auto-atención donde el paciente puede:
- Hacer check-in solo
- Ver el estado de sus estudios
- Pagar servicios
- Imprimir resultados

## Modelos Existentes
- `Kiosco` — Registro de dispositivos kiosco
- `VerificacionKiosco` — Log de verificaciones realizadas

## Lo que falta
- Vistas web optimizadas para pantalla táctil
- Interfaz tipo ATM para pacientes
- Integración con impresora de tickets
- Integración con lector de QR/código de barras

## RECOMENDACIONES

1. **Modo Kiosco Fullscreen:** PWA en modo pantalla completa
2. **Pago con Terminal:** Integración con terminal bancaria
3. **Reconocimiento Facial:** Identificar al paciente con la cámara
4. **Cola Digital:** El paciente toma turno desde el kiosco

---

# 20. MÓDULO COTIZACIÓN RÁPIDA
**Ruta:** `/cotizacion/` | **Roles:** RECEPCION, ADMIN

## Funcionalidades Actuales

### 20.1 Cotización Rápida
**Ruta:** `/cotizacion/`
- Buscar paciente existente o crear nuevo
- Agregar estudios de laboratorio
- Ver precio total
- Enviar cotización por WhatsApp
- Convertir cotización directamente en orden de servicio

## RECOMENDACIONES

1. **Cotización en PDF:** Generar PDF con membrete para enviar por email
2. **Vigencia:** Que la cotización tenga fecha de vencimiento
3. **Descuentos en Cotización:** Aplicar descuento desde la cotización
4. **Seguimiento:** CRM mini para dar seguimiento a cotizaciones pendientes

---

# 21. MÓDULO CATÁLOGOS GENERALES
**Ruta:** `/catalogos/`

## Funcionalidades Actuales
- **Catálogo de Estudios:** Lista completa con precios, búsqueda
- **Catálogo de Médicos:** Directorio de médicos referentes
- **Catálogo de Convenios:** Convenios con precios especiales (estructura lista, datos pendientes)
- **Precios por Convenio:** Ver precios especiales de un convenio específico

---

# 22. MÓDULO CAPACITACIÓN Y MANUAL
**Ruta:** `/capacitacion/` y `/manual/`

## Funcionalidades Actuales

### 22.1 Capacitación Personal
**Ruta:** `/capacitacion/personal/`
- Material de capacitación para empleados

### 22.2 Capacitación Ejecutiva
**Ruta:** `/capacitacion/ejecutiva/`
- Material para directivos

### 22.3 Manual Operativo
**Ruta:** `/manual/`
- Manual de operación del sistema
- Exportable a PDF

## Funcionalidades Pendientes

### 22.A Capacitación con RAG (IA)
- Subir documentos de capacitación (manuales, SOPs)
- Pris IA los procesa y puede responder preguntas basándose en ellos
- "Tip del Día" automático

## RECOMENDACIONES

1. **Onboarding Interactivo:** Tour guiado para nuevos usuarios
2. **Videos Tutoriales:** Grabaciones cortas de cada función
3. **Quiz de Evaluación:** Después de cada módulo, un quiz para verificar aprendizaje
4. **Certificaciones Internas:** Badges al completar capacitación

---

# 23. FUNCIONALIDADES PENDIENTES (Detalladas)

## PRIORIDAD 1 — IMPACTO ALTO EN NEGOCIO

| # | Funcionalidad | Descripción Detallada | Esfuerzo |
|---|---|---|---|
| 1 | **Nómina** | Crear modelos (ConceptoNomina, PeriodoNomina, Nomina, DetalleNomina). Implementar cálculo de ISR, IMSS, INFONAVIT. Generar recibos PDF. Timbrar CFDI de nómina. | Alto |
| 2 | **Control de Asistencia** | Crear modelos (HorarioTrabajo, IncidenciaAsistencia). Interfaz de registro entrada/salida. Reporte mensual. Integración con reloj checador. | Medio |
| 3 | **Timbrado CFDI Real** | Conectar con PAC (Finkok o SW Sapien). Configurar CSD (Certificado de Sello Digital). Implementar cancelación y notas de crédito. | Medio |
| 4 | **Contabilidad Formal** | Crear modelos (CatalogoCuenta, PolizaContable, MovimientoContable). Implementar catálogo SAT. Balanza de comprobación. | Alto |
| 5 | **Convenios de Laboratorio** | Crear modelo Convenio. Precios especiales por estudio por convenio. Aplicación automática en recepción. | Bajo |

## PRIORIDAD 2 — MEJORA OPERATIVA

| # | Funcionalidad | Descripción | Esfuerzo |
|---|---|---|---|
| 6 | **Ultrasonido** | Modelos + vistas + PDFs para reportes de ultrasonido | Medio |
| 7 | **Consentimiento Informado** | Firma digital del paciente en tablet | Medio |
| 8 | **Migración SDK Gemini** | Actualizar de google-generativeai a google-genai v1.0+ | Bajo |
| 9 | **Sistema de Notificaciones** | Push, email y SMS para alertas del sistema | Medio |
| 10 | **CRM** | Gestión de clientes potenciales, seguimiento, oportunidades | Medio |

## PRIORIDAD 3 — CRECIMIENTO FUTURO

| # | Funcionalidad | Descripción | Esfuerzo |
|---|---|---|---|
| 11 | **Dashboard Unificado KPIs** | Todos los módulos en una pantalla | Medio |
| 12 | **Reportes Financieros** | Ingresos/egresos, balance, flujo de caja | Medio |
| 13 | **Analytics Trazabilidad** | Métricas en tiempo real, análisis de tendencias | Alto |
| 14 | **PRIS Sistema Nervioso** | Dictado inventario, dictado resultado, consulta voz | Alto |
| 15 | **Capacitación RAG** | IA que aprende de documentos internos | Medio |
| 16 | **Interfaz Equipos Lab (ASTM/HL7)** | Conexión directa con analizadores | Muy Alto |
| 17 | **Telemedicina** | Videollamadas integradas | Alto |
| 18 | **App Móvil Nativa** | App para iOS/Android | Muy Alto |

---

# 24. RECOMENDACIONES GLOBALES DE CRECIMIENTO

## Infraestructura
1. **Git con Ramas:** `main` = producción, `develop` = desarrollo, `feature/*` = funcionalidades nuevas
2. **CI/CD Automatizado:** Que al hacer merge a `main` se despliegue automáticamente
3. **Staging Environment:** Ambiente de pruebas antes de producción
4. **Backups Automáticos:** Backup de BD cada 6 horas
5. **Monitoreo:** Google Cloud Monitoring + alertas por email/Slack

## UX/UI
1. **Modo Oscuro:** Toggle global para modo oscuro
2. **Responsive Total:** Optimizar todas las pantallas para móvil
3. **Shortcuts de Teclado:** Atajos para acciones frecuentes
4. **Wizard de Onboarding:** Guía paso a paso para nuevos usuarios
5. **Breadcrumbs:** Indicar siempre dónde está el usuario

## Integraciones
1. **WhatsApp Business API:** Para notificaciones automáticas a pacientes
2. **Google Calendar:** Sincronizar citas del consultorio
3. **SAT Web Services:** Para facturación y validación fiscal
4. **Twilio/SMS:** Para notificaciones por SMS
5. **Stripe/OpenPay:** Pagos en línea desde el portal del paciente

## Seguridad
1. **Penetration Testing:** Auditoría de seguridad externa
2. **HTTPS Everywhere:** Ya implementado en Cloud Run
3. **CSP Headers:** Content Security Policy para prevenir XSS
4. **Data Encryption at Rest:** Cifrado de datos sensibles en BD
5. **Compliance HIPAA/NOM-024:** Documentar cumplimiento normativo

## Escalabilidad
1. **Microservicios:** Separar la IA en su propio servicio
2. **Redis/Celery:** Para tareas asíncronas (envío de emails, generación de PDFs grandes)
3. **CDN para Estáticos:** CloudFront o Cloud CDN para archivos estáticos
4. **WebSockets:** Para chat en tiempo real y actualizaciones instantáneas

---

**FIN DEL MANUAL OPERATIVO COMPLETO**

**Este documento debe actualizarse cada vez que se implemente una nueva funcionalidad.**

**Generado: 9 de Febrero de 2026**
**Equipo: Cursor AI + PRISLAB Dev Team**
