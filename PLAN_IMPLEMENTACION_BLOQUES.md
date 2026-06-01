# 📋 PLAN DE IMPLEMENTACIÓN: Bloques Pris-Valle

## 🎯 Estado Actual vs. Requerimientos

### ✅ BLOQUE 0: Estructura Camaleónica (Multi-Tenant) - 80% Completo

**Implementado:**
- ✅ Empresa con color_primario, color_secundario, logo
- ✅ Sucursal modelo creado
- ✅ ConfiguracionModulos (Feature Toggles)
- ✅ Middleware de identidad dinámica

**Pendiente:**
- ⚠️ Agregar `sucursal_id` a modelos críticos (Venta, Paciente, OrdenDeServicio, Producto, etc.)
- ⚠️ Campo de vigencia operativa en Empresa (ya existe como `periodo_vigencia`)

---

### 🟡 BLOQUE 1: Parámetros de Laboratorio - 40% Completo

**Implementado:**
- ✅ Estudio modelo básico
- ✅ Rangos de referencia generales (valor_minimo, valor_maximo)
- ✅ Rangos de pánico (rango_panico_min, rango_panico_max)
- ✅ Unidades

**Pendiente:**
- ❌ Valores de referencia dinámicos por sexo (Hombre/Mujer)
- ❌ Valores de referencia dinámicos por edad (Neonato, Infante, Adulto, Adulto Mayor)
- ❌ Índices Eritrocitarios (VGM, HCM, CMHC, RDW)
- ❌ Diferencial Leucocitaria (Neutrófilos, Linfocitos, etc. en % y valor absoluto)
- ❌ Precursores Celulares (Bandas, Mielocitos, Metamielocitos, Blastos)

---

### ✅ BLOQUE 2: Logística de Farmacia - 90% Completo

**Implementado:**
- ✅ SKU/código_barras
- ✅ Sustancia activa
- ✅ Control de lotes (número, fecha caducidad)
- ✅ Costo de compra (precio_compra)
- ✅ Precio de venta (precio_publico)
- ✅ Bandera de antibiótico (es_antibiotico)
- ✅ Validación de receta antes de vender antibióticos

**Pendiente:**
- ✅ Todo está implementado

---

### ❌ BLOQUE 3: Auditoría y RH - 0% Completo

**Pendiente:**
- ❌ Modelo Empleado (Ficha completa)
- ❌ Bitácora 39-A (Evaluación semanal)
- ❌ Reloj Checador (Entrada/Salida con geolocalización/IP)
- ❌ Log de Auditoría Forense (Fecha, Hora, Usuario, Acción, Valor Anterior vs Nuevo)

---

### ❌ BLOQUE 4: Módulo Médico ECE - 0% Completo

**Pendiente:**
- ❌ Nota SOAP (Subjetivo, Objetivo, Análisis, Plan)
- ❌ Antecedentes (Heredofamiliares, Personales Patológicos, No Patológicos)
- ❌ Firma Digital (Imagen de firma, cédula profesional)
- ❌ Vínculo de Resultados (Acceso a PDFs de laboratorio)

---

## 🚀 Orden de Implementación Recomendado

### Fase 1: Completar Bloque 0 (Multi-Tenant) - 2 horas
1. Agregar `sucursal_id` a modelos críticos
2. Verificar que todos tengan `empresa_id`

### Fase 2: Expandir Bloque 1 (Laboratorio) - 4 horas
1. Crear modelo `ValorReferencia` con sexo y edad
2. Crear modelo `IndiceEritrocitario`
3. Crear modelo `DiferencialLeucocitario`
4. Crear modelo `PrecursorCellular`

### Fase 3: Implementar Bloque 3 (RH y Auditoría) - 6 horas
1. Modelo `Empleado`
2. Modelo `Bitacora39A`
3. Modelo `RegistroAsistencia`
4. Modelo `AuditLog`

### Fase 4: Implementar Bloque 4 (ECE) - 4 horas
1. Modelo `NotaClinicaSOAP`
2. Modelo `Antecedente`
3. Modelo `FirmaDigital`
4. Vínculo en Paciente a resultados

---

## 📊 Prioridad de Implementación

**ALTA PRIORIDAD:**
1. Bloque 0: Aislamiento multi-tenant completo
2. Bloque 3: Auditoría forense (seguridad crítica)

**MEDIA PRIORIDAD:**
3. Bloque 1: Valores de referencia dinámicos
4. Bloque 4: ECE (expediente clínico)

**BAJA PRIORIDAD:**
5. Bloque 1: Índices eritrocitarios específicos (puede hacerse después)
