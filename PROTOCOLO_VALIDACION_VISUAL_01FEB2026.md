# ✅ PROTOCOLO DE VALIDACIÓN VISUAL - CHECKLIST EJECUTIVA

**Fecha:** 1 de Febrero de 2026  
**Objetivo:** Verificar que las interfaces de Bloques 1-8 estén visibles  

---

## 🔴 PASO 1: REINICIO DE SISTEMA ✅

**Acción:** Ejecutar el script de inicio

```bash
.\iniciar_servidor.bat
```

**Salida esperada en la terminal:**
```
Starting development server at http://127.0.0.1:8000/
Quit the server with CTRL-BREAK.
```

✅ **COMPLETADO:** Servidor iniciado en `http://localhost:8000`

---

## 🔴 PASO 2: EL GOLPE DE CACHÉ (CRÍTICO) ⚠️

**Acción:** Limpiar caché del navegador

### **Windows:**
```
CTRL + F5
```

### **Mac:**
```
CMD + SHIFT + R
```

### **Alternativa (Cualquier navegador):**
1. Abrir DevTools (`F12`)
2. Clic derecho en botón "Recargar"
3. Seleccionar "Vaciar caché y recargar de forma forzada"

⚠️ **CRÍTICO:** Si no haces esto, verás el "fantasma" de la versión vieja.

---

## 🔴 PASO 3: VALIDACIÓN VISUAL (3 PRUEBAS CRÍTICAS)

---

### **🩺 PRUEBA 1: CONSULTORIO - GEMELO DIGITAL**

**URL:** `http://localhost:8000/consultorio/nueva-consulta/`

**Login:** Usuario con grupo `MEDICOS` o rol `MEDICO`

#### **CHECKLIST VISUAL:**

```
[ ] PANTALLA DIVIDIDA VISIBLE
    └─ Izquierda (40%): Formulario gris claro
    └─ Derecha (60%): "Papel" blanco con preview

[ ] BOTÓN DE VOZ EN LA PARTE SUPERIOR
    └─ "🎙️ GRABAR CONSULTA (IA)"

[ ] SECCIONES SOAP CLARAMENTE IDENTIFICADAS
    └─ [S] Subjetivo (Motivo de consulta)
    └─ [O] Objetivo (Signos vitales)
    └─ [A] Análisis (Diagnóstico)
    └─ [P] Plan (Tratamiento)

[ ] GRID DE SIGNOS VITALES
    └─ Temp, FC, FR, TA, SatO2, Peso, Talla, IMC

[ ] MIRRORING EN TIEMPO REAL
    └─ Escribo en la izquierda → Se ve en la derecha

[ ] PREVIEW DEL "PAPEL" (Derecha)
    └─ Fondo blanco
    └─ Encabezado con logo
    └─ Datos del paciente
    └─ Cuerpo de la receta
    └─ Firma al pie

[ ] BOTONES DE ACCIÓN (Parte inferior)
    └─ Cancelar
    └─ Guardar y Enviar a Drive
    └─ 🖨️ Imprimir
```

#### **SI NO VES ESTO:**
❌ No estás viendo el Gemelo Digital  
❌ Probablemente sigues viendo `nueva_consulta.html` (vieja)  
❌ **SOLUCIÓN:** CTRL + F5 más fuerte, o modo incógnito

---

### **🔬 PRUEBA 2: LABORATORIO - SMART LAB**

**URL:** `http://localhost:8000/laboratorio/lista-trabajo/`

**Login:** Usuario con grupo `LABORATORIO` o rol `QUIMICO`

**Pasos:**
1. Clic en cualquier orden de la lista
2. Clic en "Capturar Resultados"

#### **CHECKLIST VISUAL:**

```
[ ] TABLA ESPACIOSA Y LIMPIA
    └─ Columnas: Prueba | Rango | Unidades | RESULTADO | Estado

[ ] INPUTS GRANDES
    └─ Cada input debe ser visible y espaciado

[ ] ATRIBUTO data-keywords (CRÍTICO)
    └─ Abrir DevTools (F12)
    └─ Inspeccionar un input de resultado
    └─ Buscar: data-keywords="..."
    └─ Ejemplo: data-keywords="glicada, hemoglobina glicada, a1c"

[ ] BOTÓN FAB (Flotante)
    └─ Esquina inferior derecha
    └─ "🎙️ DICTAR (Espacio)"
    └─ Círculo grande y visible

[ ] SEMÁFORO VISUAL (Si aplica)
    └─ Verde: Normal
    └─ Amarillo: Fuera de rango
    └─ Rojo: Crítico
```

#### **VERIFICACIÓN TÉCNICA (DevTools):**

Abrir consola del navegador (F12) y ejecutar:
```javascript
// Debe retornar elementos con data-keywords
document.querySelectorAll('[data-keywords]').length
// Resultado esperado: > 0
```

#### **SI NO VES ESTO:**
❌ Sigues viendo `captura_resultados_completa.html` (vieja)  
❌ **SOLUCIÓN:** CTRL + F5, revisar que la vista use `capturar_resultados.html`

---

### **📊 PRUEBA 3: PACIENTES - TIMELINE**

**URL:** `http://localhost:8000/pacientes/lista/`

**Login:** Cualquier usuario autenticado

**Pasos:**
1. Buscar un paciente con historial
2. Clic en "Ver Expediente" o similar
3. Debe ir a `/pacientes/<id>/expediente/`

#### **CHECKLIST VISUAL:**

```
[ ] CABECERA DEL PACIENTE
    └─ Nombre completo
    └─ Edad, sexo, tipo de sangre
    └─ Foto o avatar

[ ] PANEL DE ESTADÍSTICAS (Parte superior)
    └─ Total de consultas
    └─ Estudios de laboratorio
    └─ Recetas emitidas
    └─ Alertas críticas

[ ] TIMELINE VERTICAL (ELEMENTO CRÍTICO)
    └─ Línea vertical central
    └─ Eventos ordenados cronológicamente
    └─ Más reciente arriba

[ ] CADA EVENTO TIENE:
    └─ Fecha y hora (izquierda)
    └─ Ícono en círculo (centro)
    └─ Tarjeta con información (derecha)

[ ] ICONOS ESPECÍFICOS POR TIPO
    └─ 🩺 Consulta: icono de estetoscopio
    └─ 🔬 Laboratorio: icono de microscopio
    └─ 📷 Imagen: icono de rayos X
    └─ 💊 Receta: icono de pastilla

[ ] BOTONES DE ACCIÓN EN CADA EVENTO
    └─ "👁️ Ver PDF en Drive" (si existe)
    └─ Badge "Procesando..." (si no existe)

[ ] FILTROS INTERACTIVOS (Si aplica)
    └─ Por tipo de evento
    └─ Por rango de fechas
    └─ Por médico
```

#### **SI NO VES ESTO:**
❌ Probablemente estás viendo `detalle.html` o `historial_360.html` (viejos)  
❌ **SOLUCIÓN:** Verificar que la URL sea `/pacientes/<id>/expediente/`

---

### **🔐 PRUEBA 4: SIDEBAR - RBAC (BONUS)**

**URL:** `http://localhost:8000/` (cualquier página)

**Login:** Probar con diferentes roles

#### **CHECKLIST VISUAL:**

**Usuario MEDICO:**
```
[ ] VE: Sección "CONSULTORIO"
[ ] VE: Consultas, Expedientes, Agenda
[ ] NO VE: Sección "LABORATORIO" completa
[ ] NO VE: Sección "FARMACIA" completa
```

**Usuario LABORATORIO:**
```
[ ] VE: Sección "LABORATORIO"
[ ] VE: Recepción, Área Técnica, LIMS
[ ] NO VE: Sección "CONSULTORIO"
[ ] NO VE: Sección "FARMACIA"
```

**Usuario FARMACIA:**
```
[ ] VE: Sección "FARMACIA"
[ ] VE: Punto de Venta, Inventario, Ventas
[ ] NO VE: Sección "CONSULTORIO"
[ ] NO VE: Sección "LABORATORIO"
```

---

## 🎯 CRITERIOS DE ÉXITO TOTAL

Para considerar el sistema un **ÉXITO TOTAL**, se deben cumplir:

### ✅ **ÉXITO 1: Gemelo Digital Visible**
- Pantalla dividida 40/60
- Mirroring funcional
- Preview de receta en "papel"

### ✅ **ÉXITO 2: Smart Lab Activo**
- Inputs con `data-keywords` verificables en DevTools
- Tabla espaciosa
- Botón FAB de voz visible

### ✅ **ÉXITO 3: Timeline Funcional**
- Línea vertical con eventos
- Iconos específicos por tipo
- Ordenamiento cronológico

### ✅ **ÉXITO 4: RBAC Operativo (Bonus)**
- Sidebar muestra solo menús del rol del usuario
- No se ven secciones no autorizadas

---

## ❌ INDICADORES DE FALLO

Si ves cualquiera de esto, **NO ESTÁ FUNCIONANDO:**

### ❌ **FALLO 1: Consultorio**
- No hay pantalla dividida
- Solo ves un formulario simple
- No hay preview del lado derecho

### ❌ **FALLO 2: Laboratorio**
- Los inputs NO tienen `data-keywords` (verificar en DevTools)
- No ves el botón FAB de voz
- La interfaz se ve antigua/genérica

### ❌ **FALLO 3: Pacientes**
- No ves una línea vertical de timeline
- Solo ves una tabla o listado simple
- No hay iconos específicos por tipo

### ❌ **FALLO 4: Sidebar**
- Ves TODAS las secciones sin importar tu rol
- No hay filtrado (todos los usuarios ven lo mismo)

---

## 🚨 PROTOCOLO DE EMERGENCIA

Si después de CTRL + F5 aún no ves los cambios:

### **PASO 1: Modo Incógnito**
```
CTRL + SHIFT + N (Chrome)
CTRL + SHIFT + P (Firefox)
```

### **PASO 2: Verificar Archivos**
```bash
# Verificar que los templates existen
dir consultorio\templates\consultorio\nueva_consulta_gemelo.html
dir laboratorio\templates\laboratorio\capturar_resultados.html
dir core\templates\pacientes\historial_clinico.html
```

### **PASO 3: Verificar Código**
```python
# En consultorio/views.py buscar:
return render(request, 'consultorio/nueva_consulta_gemelo.html', {...})

# En core/views/laboratorio_captura.py buscar:
return render(request, 'laboratorio/capturar_resultados.html', context)
```

### **PASO 4: Logs del Servidor**
Revisar la terminal donde corre el servidor, buscar:
```
TemplateDoesNotExist
o
500 Internal Server Error
```

---

## 📊 HOJA DE RESULTADOS

Completa esta tabla después de las pruebas:

| Prueba | Estado | Notas |
|--------|--------|-------|
| **Gemelo Digital** | [ ] ✅ / [ ] ❌ | _________________ |
| **Smart Lab** | [ ] ✅ / [ ] ❌ | _________________ |
| **Timeline** | [ ] ✅ / [ ] ❌ | _________________ |
| **RBAC Sidebar** | [ ] ✅ / [ ] ❌ | _________________ |

**Resultado Final:**
```
[ ] 4/4 ÉXITO TOTAL 🎉
[ ] 3/4 Casi completo (revisar el fallido)
[ ] 2/4 o menos: Necesita diagnóstico profundo
```

---

## 🏆 MENSAJE FINAL

Si las **3 pruebas críticas** (Gemelo, Smart Lab, Timeline) pasan:

```
🎉 ¡ÉXITO TOTAL! 🎉

Las interfaces de Bloques 1-8 están ACTIVAS.
El sistema está listo para uso en producción.
La unificación forzada fue exitosa.
```

Si alguna falla:

```
⚠️ REVISIÓN NECESARIA

Consulta la sección de Troubleshooting
o avisa para diagnóstico técnico.
```

---

**FIN DEL PROTOCOLO**  
**Estado:** ⏳ ESPERANDO VALIDACIÓN DEL USUARIO
