# 🚀 MANUAL DE USUARIO - CONSTRUCTOR LIMS V5

## SISTEMA PRISLAB - MÓDULO DE CONFIGURACIÓN DE ESTUDIOS

**Versión:** 5.0  
**Fecha:** 2026-01-25  
**Usuario Objetivo:** Administradores de Laboratorio

---

## 📋 ÍNDICE

1. [Acceso al Sistema](#acceso-al-sistema)
2. [Lista de Estudios](#lista-de-estudios)
3. [Crear Nuevo Estudio](#crear-nuevo-estudio)
4. [Agregar Parámetros Dinámicamente](#agregar-parametros)
5. [Editar Estudio Existente](#editar-estudio)
6. [Funciones Avanzadas](#funciones-avanzadas)

---

## 🔐 ACCESO AL SISTEMA

### Credenciales de Administrador
```
Usuario: admin
Contraseña: admin123
```

### URL del Sistema
```
http://localhost:8000/lims/estudios/
```

### Navegación Rápida
- **Dashboard:** `/dashboard`
- **Lista de Estudios:** `/lims/estudios/`
- **Nuevo Estudio:** `/lims/estudios/nuevo/`
- **Admin Django:** `/admin`

---

## 📊 LISTA DE ESTUDIOS

### Acceso
Ir a: `http://localhost:8000/lims/estudios/`

### Funciones Disponibles

#### **1. Filtros Inteligentes**
- **Por Sección:** Dropdown con todas las secciones de laboratorio
- **Por Estado:** Activos / Inactivos / Todos
- **Búsqueda:** Código, nombre o abreviatura

#### **2. Estadísticas en Tiempo Real**
La vista muestra 4 cards con:
- Total de Estudios
- Resultados del filtro actual
- Total de Secciones
- Total de Parámetros configurados

#### **3. Tabla de Estudios**
Columnas:
- **Código:** Identificador único (ej: `45`, `QS3`, `PERFCAR`)
- **Nombre:** Descripción completa
- **Sección:** Departamento del laboratorio
- **Parámetros:** Contador de parámetros configurados
- **Precio:** Costo del estudio
- **Entrega:** Tiempo de entrega (días u horas)
- **Estado:** Activo/Inactivo (indicador visual)
- **Acciones:** Botones de Editar, Duplicar, Eliminar

#### **4. Acciones Rápidas**
- **[✏️ Editar]:** Modificar estudio completo
- **[📋 Duplicar]:** Clonar estudio con todos sus parámetros
- **[🗑️ Eliminar]:** Desactivar estudio (confirmación requerida)

---

## ➕ CREAR NUEVO ESTUDIO

### Paso 1: Acceder al Constructor
Click en botón **"Nuevo Estudio"** (esquina superior derecha)

### Paso 2: Información Básica

#### **Campos Obligatorios** (marcados con *)
- **Código:** Identificador único (ej: `PCR001`)
- **Nombre:** Descripción completa (ej: `PCR Multiplex Respiratorio`)
- **Precio:** Costo en pesos mexicanos

#### **Campos Opcionales**
- **Abreviatura:** Código corto para reportes
- **Sección:** Departamento (Hematología, Química Clínica, etc.)
- **Días de Entrega:** Tiempo estándar de procesamiento
- **Tiempo Entrega (horas):** Para estudios urgentes

### Paso 3: Muestras y Logística

#### **Campos Disponibles**
- **Muestra Requerida:** Tipo de muestra (ej: "Sangre EDTA", "Suero")
- **Volumen de Muestra:** Cantidad necesaria (ej: "5 mL")
- **Color de Tubo:** Selector predefinido (ROJO, MORADO, AZUL, etc.)
- **Indicaciones:** Instrucciones para el paciente (ej: "Ayuno 8 horas")

---

## 🧬 AGREGAR PARÁMETROS DINÁMICAMENTE

### El Núcleo del Constructor LIMS

#### **Paso 1: Sección de Parámetros**
Scroll hasta la tarjeta **"Parámetros del Estudio"**

#### **Paso 2: Agregar Parámetros**

**Método 1: Usando el Botón Verde**
1. Click en **"Agregar Parámetro"** (botón verde)
2. Se crea una nueva fila automáticamente
3. El sistema hace scroll al nuevo parámetro
4. Focus automático en el primer campo

**Método 2: Agregar Múltiples**
- Puedes click múltiples veces seguidas
- **SIN LÍMITE de parámetros**
- Ideal para estudios complejos (ej: 50+ parámetros)

#### **Paso 3: Configurar cada Parámetro**

**Campos por Parámetro:**

| Campo | Descripción | Ejemplo |
|-------|-------------|---------|
| **Nombre** | Nombre del analito | "Glucosa" |
| **Unidad** | Unidad de medida | "mg/dL" |
| **Tipo de Dato** | NUMERICO / TEXTO / etc | NUMERICO |
| **Orden** | Posición en el reporte | 1, 2, 3... |
| **Activo** | ☑️ Si está habilitado | ☑️ |
| **Crítico** | ☑️ Si es valor de pánico | ☐ |
| **Eliminar** | ☑️ Para borrar al guardar | ☐ |

#### **Paso 4: Gestión Visual**

**Indicadores de Estado:**
- **Fila normal:** Fondo gris claro
- **Hover:** Borde azul
- **Marcado para eliminar:** Opacidad 40%, tachado

**Contador Dinámico:**
- Badge en el header muestra cantidad activa
- Se actualiza en tiempo real
- No cuenta parámetros marcados para eliminar

---

## ✏️ EDITAR ESTUDIO EXISTENTE

### Acceso
Desde la lista de estudios, click en **[✏️ Editar]**

### Funciones Especiales en Edición

#### **1. Modificar Parámetros Existentes**
- Todos los parámetros guardados aparecen en la tabla
- Edita cualquier campo directamente
- Los cambios se guardan al hacer Submit

#### **2. Agregar Nuevos Parámetros**
- Usa el botón "Agregar Parámetro"
- Se mezclan con los existentes
- El orden se respeta automáticamente

#### **3. Eliminar Parámetros**
- Marca el checkbox **"Eliminar"**
- La fila se tacha visualmente
- Se elimina al guardar (confirmación no requerida)

#### **4. Configurar Rangos de Referencia**
- Si el parámetro YA EXISTE en BD
- Aparece botón **[🎚️]** (Configurar Rangos)
- Abre modal/página para definir:
  - Rangos por sexo (M/F/I)
  - Rangos por edad (0-12, 18-65, etc.)
  - Valores normales (Min-Max)
  - Valores de pánico (Crítico Min-Max)

---

## 🎯 FUNCIONES AVANZADAS

### 1. **Autoguardado de Borradores**

**¿Qué hace?**
- Guarda automáticamente cada 30 segundos
- Usa `localStorage` del navegador
- Solo en modo CREACIÓN (no edición)

**¿Cómo recuperar un borrador?**
1. Si cierras la ventana accidentalmente
2. Vuelve a abrir "Nuevo Estudio"
3. El sistema pregunta: "¿Recuperar borrador?"
4. Click "Aceptar" → Se cargan todos los campos

**Limpiar borrador:**
- Se elimina automáticamente al guardar exitosamente
- Se elimina si cancelas y confirmas

---

### 2. **Duplicar Estudio**

**Flujo:**
1. En la lista, click **[📋 Duplicar]**
2. El sistema crea una copia exacta
3. Modifica el código: `ORIGINAL_COPIA`
4. Modifica el nombre: `Nombre Original (Copia)`
5. Copia TODOS los parámetros
6. Copia TODOS los rangos de referencia

**Uso recomendado:**
- Crear variantes de estudios (ej: BH Normal → BH Pediátrica)
- Duplicar perfiles complejos
- Crear estudios de distintas empresas

---

### 3. **Validación Inteligente**

**Validaciones en Frontend:**
- ✅ Código obligatorio
- ✅ Nombre obligatorio
- ✅ Precio válido (no negativo)
- ⚠️ Alerta si no hay parámetros (permite continuar)

**Validaciones en Backend:**
- ✅ Código único (no duplicados)
- ✅ Transacción atómica (todo o nada)
- ✅ Rollback automático si falla algún parámetro

---

### 4. **Configuración Técnica**

**Campos Avanzados:**
- **Metodología:** Técnica de análisis
- **Equipo Asignado:** Analizador/instrumento
- **Descripción Interna:** Notas para el personal
- **Es Perfil/Paquete:** ☑️ Si agrupa otros estudios
- **Requiere Autorización:** ☑️ Si necesita aprobación especial

---

## 📱 RESPONSIVE DESIGN

### Compatibilidad
- ✅ Desktop (1920x1080+)
- ✅ Laptop (1366x768+)
- ✅ Tablet (768x1024)
- ⚠️ Mobile (básico, optimizar scroll)

### Navegación Touch
- Botones grandes para touch
- Scroll suave automático
- Confirmaciones amigables (SweetAlert2)

---

## ⚡ ATAJOS DE TECLADO

| Acción | Atajo |
|--------|-------|
| Guardar Estudio | `Ctrl + S` (próximamente) |
| Agregar Parámetro | `Ctrl + +` (próximamente) |
| Cancelar | `Esc` |
| Focus en Búsqueda | `Ctrl + K` (próximamente) |

---

## 🐛 RESOLUCIÓN DE PROBLEMAS

### "No se guardó el estudio"
**Causa:** Falta campo obligatorio  
**Solución:** Verifica que tengas Código, Nombre y Precio

### "Error: Código duplicado"
**Causa:** Ya existe un estudio con ese código  
**Solución:** Usa otro código único

### "Los parámetros no aparecen"
**Causa:** Problemas de caché del navegador  
**Solución:** Recarga con `Ctrl + Shift + R`

### "El botón 'Agregar Parámetro' no funciona"
**Causa:** JavaScript deshabilitado o error de consola  
**Solución:** 
1. Abre consola del navegador (F12)
2. Ve a la pestaña "Console"
3. Busca errores en rojo
4. Reporta al equipo técnico

---

## 📞 SOPORTE TÉCNICO

**Equipo:** PRISLAB Engineering Team  
**Email:** soporte@prislab.com  
**Horario:** 24/7 (críticos), 9am-6pm (generales)

**Reportar Bugs:**
1. Captura de pantalla del error
2. Pasos para reproducir
3. Navegador y versión
4. Enviar a: bugs@prislab.com

---

## 📚 EJEMPLOS PRÁCTICOS

### Ejemplo 1: Crear "PCR Multiplex Respiratorio"

```
1. Click "Nuevo Estudio"
2. Código: PCR001
3. Nombre: PCR Multiplex Respiratorio
4. Sección: MICROBIOLOGIA
5. Precio: 2500.00
6. Muestra: Exudado nasofaríngeo
7. Tubo: AMARILLO

Parámetros (agregar 16):
- Influenza A
- Influenza B
- SARS-CoV-2
- Parainfluenza 1
- Parainfluenza 2
- Parainfluenza 3
- Parainfluenza 4
- VSR A
- VSR B
- Adenovirus
- Metapneumovirus
- Rinovirus
- Enterovirus
- Bocavirus
- Coronavirus 229E
- Coronavirus OC43

8. Click "Agregar Parámetro" 16 veces
9. Llenar cada uno
10. Guardar
```

---

**🎉 ¡Sistema listo para operación!**
