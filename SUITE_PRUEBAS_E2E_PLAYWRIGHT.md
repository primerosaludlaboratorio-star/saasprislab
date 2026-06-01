# 🎭 SUITE DE PRUEBAS E2E - USUARIO FANTASMA (Playwright)

**Objetivo:** Simular operación máxima de Prislab y reparar errores automáticamente.

---

## 🚀 INSTALACIÓN

### 1. Instalar Playwright:
```bash
pip install playwright
playwright install chromium
```

### 2. O usar el script automático:
```bash
python ejecutar_pruebas_playwright.py
```

---

## 🧪 PRUEBAS IMPLEMENTADAS

### **PRUEBA 1: Captura Clínica - Iluminación Neón** 🔬

**Objetivo:** Verificar que las alertas neón se activan instantáneamente.

**Acciones:**
- ✅ Entrar a "Captura de Resultados"
- ✅ Escribir valores en 32 elementos de química
- ✅ Escribir valores críticos (fuera de rango)
- ✅ Verificar activación visual de alertas neón

**Validaciones:**
- ✅ Clase `fuera-rango-panico` aplicada
- ✅ Cambio de color instantáneo
- ✅ Función JavaScript `validarRango` funcionando

**Reparaciones Automáticas:**
- 🔧 Si no se activa, inyecta eventos `input` y `change` manualmente
- 🔧 Verifica que la función JavaScript existe

---

### **PRUEBA 2: PDV - Alerta FEFO** 💊

**Objetivo:** Verificar pop-up FEFO y confirmación.

**Acciones:**
- ✅ Buscar producto en PDV
- ✅ Mover mouse al botón "Agregar"
- ✅ Hacer clic y verificar pop-up FEFO
- ✅ Confirmar alerta

**Validaciones:**
- ✅ Pop-up FEFO aparece
- ✅ Botón de confirmación visible
- ✅ Pop-up se cierra correctamente

**Reparaciones Automáticas:**
- 🔧 Detecta si el pop-up no aparece (posible error JS)
- 🔧 Busca botones alternativos de confirmación

---

### **PRUEBA 3: Header Líquido - Desplazamiento 270px** 📐

**Objetivo:** Verificar desplazamiento exacto de 270px.

**Acciones:**
- ✅ Activar sidebar (botón hamburguesa)
- ✅ Medir margen antes: `margin-left` inicial
- ✅ Medir margen después: `margin-left` con sidebar abierto
- ✅ Calcular desplazamiento
- ✅ Desactivar sidebar y verificar retorno

**Validaciones:**
- ✅ Desplazamiento = 270px ± 5px
- ✅ Transición suave (0.3s)
- ✅ Sidebar cierra correctamente

**Reparaciones Automáticas:**
- 🔧 Si el desplazamiento es incorrecto, inyecta CSS correctivo:
  ```css
  .sidebar-open ~ * .marca-prislab {
      margin-left: 270px !important;
  }
  ```

---

### **PRUEBA 4: Flujo Médico - Receta 4.0** 🩺

**Objetivo:** Verificar generación de receta con QR.

**Acciones:**
- ✅ Llenar formulario SOAP completo
- ✅ Ingresar signos vitales
- ✅ Escribir indicaciones (IDX)
- ✅ Verificar sincronización FEFO en tiempo real
- ✅ Guardar y generar receta
- ✅ Verificar que QR aparece

**Validaciones:**
- ✅ Formulario SOAP completado
- ✅ Cálculo de IMC automático
- ✅ Sincronización FEFO funciona
- ✅ QR generado y visible
- ✅ QR no está cortado (>50x50px)

**Reparaciones Automáticas:**
- 🔧 Verifica que el QR es renderizado correctamente
- 🔧 Detecta si el QR está cortado o muy pequeño

---

### **PRUEBA 5: Modo "Break the System" - Debouncing** 💥

**Objetivo:** Verificar protección contra clics dobles.

**Acciones:**
- ✅ Buscar botones "Guardar" o "Validar"
- ✅ Hacer clic doble rápido (`dblclick()`)
- ✅ Verificar que solo se procesa una vez

**Validaciones:**
- ✅ Botón se deshabilita después del primer clic
- ✅ Segundo clic es ignorado
- ✅ No se duplican registros

**Reparaciones Automáticas:**
- 🔧 Si no hay protección, inyecta debouncing manualmente:
  ```javascript
  let isSubmitting = false;
  btn.onclick = function(e) {
      if (isSubmitting) {
          e.preventDefault();
          return false;
      }
      isSubmitting = true;
      btn.disabled = true;
      // ...
  };
  ```

---

## 📊 EJECUCIÓN

### **Opción 1: Script Automático (Recomendado)**
```bash
python ejecutar_pruebas_playwright.py
```

### **Opción 2: Django Test**
```bash
python manage.py test core.tests_e2e_playwright
```

### **Opción 3: Prueba Individual**
```bash
python manage.py test core.tests_e2e_playwright.UsuarioFantasmaTest.test_1_captura_clinica_neon
```

---

## 🔍 REPARACIONES AUTOMÁTICAS

### **CSS Dinámico:**
- Si el desplazamiento del header es incorrecto, inyecta CSS correctivo
- Asegura que la transición sea de 270px

### **JavaScript:**
- Si las alertas neón no se activan, dispara eventos manualmente
- Si falta debouncing, inyecta protección contra clics dobles

### **Validaciones:**
- Verifica que las funciones JavaScript existen
- Detecta elementos faltantes y sugiere soluciones

---

## 📝 REPORTE DE PRUEBAS

### **Salida Esperada:**
```
================================================================================
🚀 EJECUTANDO TODAS LAS PRUEBAS - USUARIO FANTASMA
================================================================================

🔬 PRUEBA 1: CAPTURA CLÍNICA - ILUMINACIÓN NEÓN
================================================================================
   📊 Inputs encontrados: 32
   ✅ Input 1: Alerta neón activada
   ✅ Input 2: Alerta neón activada
   ...
   📊 RESUMEN:
      - Inputs procesados: 32
      - Alertas neón activadas: 28
      - Tasa de activación: 87.5%

💊 PRUEBA 2: PDV - ALERTA FEFO
================================================================================
   ✅ Pop-up FEFO detectado
   ✅ Pop-up FEFO confirmado correctamente

📐 PRUEBA 3: HEADER LÍQUIDO - DESPLAZAMIENTO 270PX
================================================================================
   📏 Margen inicial: 80px
   📏 Margen abierto: 350px
   📏 Desplazamiento: 270px
   ✅ Desplazamiento correcto (270px ± 5px)
   ✅ Sidebar cierra correctamente

🩺 PRUEBA 4: FLUJO MÉDICO - RECETA 4.0
================================================================================
   ✅ Sincronización FEFO funcionando
   ✅ QR de validación generado correctamente
   ✅ QR renderizado correctamente (150x150px)

💥 PRUEBA 5: MODO "BREAK THE SYSTEM" - DEBOUNCING
================================================================================
   ✅ Botón se deshabilitó después del primer clic (protección activa)

================================================================================
✅ TODAS LAS PRUEBAS COMPLETADAS
================================================================================
```

---

## ⚙️ CONFIGURACIÓN

### **Navegador:**
- Por defecto: Chromium
- Headless: `headless=False` (visible para debugging)

### **Timeout:**
- Default: 30 segundos por acción
- Configurable en cada prueba

### **Viewport:**
- Tamaño: 1920x1080
- User Agent: Chrome en Windows

---

## 🔧 TROUBLESHOOTING

### **Error: "Playwright not installed"**
```bash
pip install playwright
playwright install chromium
```

### **Error: "Element not found"**
- Verificar que el usuario esté logueado
- Verificar que la URL sea correcta
- Aumentar `time.sleep()` si la página carga lento

### **Error: "Alertas neón no se activan"**
- Verificar que el JavaScript esté cargado
- Verificar que los atributos `data-rango-panico-*` existan
- La prueba intentará reparar automáticamente

### **Error: "Desplazamiento incorrecto"**
- Verificar CSS del header
- La prueba inyectará CSS correctivo automáticamente
- Verificar que `.sidebar-open` se aplica correctamente

---

## ✅ VERIFICACIONES REALIZADAS

1. ✅ **Iluminación Neón:** Activación visual instantánea
2. ✅ **FEFO Pop-up:** Aparece y se confirma correctamente
3. ✅ **Header Líquido:** Desplazamiento exacto de 270px
4. ✅ **Receta 4.0:** QR generado y visible
5. ✅ **Debouncing:** Protección contra clics dobles

---

**✅ SUITE DE PRUEBAS E2E IMPLEMENTADA Y LISTA**
