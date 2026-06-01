# 🚀 GUÍA DE VERIFICACIÓN - INTERFACES NUEVAS ACTIVAS

**Fecha:** 1 de Febrero de 2026  
**Objetivo:** Probar que las interfaces de Bloques 1-8 estén funcionando correctamente  

---

## 📋 PREREQUISITOS

✅ **Cambios aplicados:**
- Sidebar con RBAC activado
- Consultorio apunta a Gemelo Digital
- Laboratorio apunta a Smart Lab
- Pacientes muestra Timeline
- Archivo `sidebar_clean.html` eliminado

---

## 🔄 PASO 1: REINICIAR EL SERVIDOR

### **Opción A: Usando el script (RECOMENDADO)**

```bash
.\iniciar_servidor.bat
```

### **Opción B: Manual**

```bash
# 1. Detener el servidor actual (si está corriendo)
# Presiona Ctrl + C en la terminal donde corre el servidor

# 2. Activar entorno virtual
cd C:\Users\jonil\Desktop\PRISLAB_SaaS
venv\Scripts\activate

# 3. Iniciar el servidor
python manage.py runserver
```

**Salida esperada:**
```
Starting development server at http://127.0.0.1:8000/
Quit the server with CTRL-BREAK.
```

---

## 🧹 PASO 2: LIMPIAR CACHÉ DEL NAVEGADOR

**IMPORTANTE:** Debes hacer esto en CADA prueba para ver los cambios.

### **Windows:**
```
CTRL + F5
```

### **Mac:**
```
CMD + SHIFT + R
```

### **Alternativa (cualquier navegador):**
1. Abrir DevTools (F12)
2. Clic derecho en el botón de "Recargar"
3. Seleccionar "Vaciar caché y recargar de forma forzada"

---

## ✅ PASO 3: PRUEBAS POR MÓDULO

### **🩺 PRUEBA 1: CONSULTORIO - GEMELO DIGITAL**

**URL:** `http://localhost:8000/consultorio/nueva-consulta/`

**Credenciales:** Usuario con rol `MEDICO` o grupo `MEDICOS`

**Lo que debes ver:**

✅ **Pantalla dividida:**
- **Izquierda (40%):** Formulario de captura (fondo gris claro)
- **Derecha (60%):** Vista previa de receta en "papel" blanco

✅ **Funcionalidad:**
- Al escribir en la izquierda, el texto aparece en la derecha en tiempo real
- Botón "🎙️ GRABAR CONSULTA (IA)" visible
- Secciones SOAP claramente identificadas
- Campos de signos vitales con grid
- IMC se calcula automáticamente al ingresar peso y talla

✅ **Botones de acción (parte inferior):**
- Cancelar
- Guardar y Enviar a Drive
- 🖨️ Imprimir

**Si NO ves esto:**
- ❌ Verifica que reiniciaste el servidor
- ❌ Limpia caché del navegador (CTRL + F5)
- ❌ Revisa que el template sea `nueva_consulta_gemelo.html`

---

### **🔬 PRUEBA 2: LABORATORIO - SMART LAB**

**URL:** `http://localhost:8000/laboratorio/lista-trabajo/`

**Credenciales:** Usuario con rol `QUIMICO` o grupo `LABORATORIO`

**Pasos:**
1. Ir a "Lista de Trabajo"
2. Seleccionar una orden pendiente
3. Clic en "Capturar Resultados"

**Lo que debes ver:**

✅ **Tabla de captura:**
- Columnas: Prueba | Rango | Unidades | **RESULTADO** | Estado
- Inputs grandes y espaciados

✅ **Inputs inteligentes:**
- Abrir DevTools (F12)
- Inspeccionar un input
- **Debe tener atributo:** `data-keywords="..."`
- Ejemplo: `data-keywords="glicada, hemoglobina glicada, a1c"`

✅ **Funcionalidad (opcional, si hay IA configurada):**
- Botón FAB "🎙️ DICTAR" en la esquina inferior derecha
- Al presionar barra espaciadora, se activa el micrófono
- Feedback visual cuando está escuchando

**Si NO ves esto:**
- ❌ Verifica que la vista use `capturar_resultados.html`
- ❌ Revisa que los inputs tengan `data-keywords`
- ❌ Limpia caché (CTRL + F5)

---

### **📊 PRUEBA 3: PACIENTES - TIMELINE**

**URL:** `http://localhost:8000/pacientes/lista/`

**Credenciales:** Cualquier usuario autenticado

**Pasos:**
1. Buscar un paciente con historial (consultas, labs, etc.)
2. Clic en "Ver Expediente" o "Ver Historial"
3. Debe redirigir a `/pacientes/<id>/expediente/`

**Lo que debes ver:**

✅ **Cabecera del paciente:**
- Nombre completo
- Edad, sexo, tipo de sangre
- Información de contacto

✅ **Panel de estadísticas:**
- Total de consultas
- Estudios de laboratorio
- Recetas emitidas
- Alertas críticas (si las hay)

✅ **Timeline vertical:**
- Eventos en orden cronológico (más reciente arriba)
- Cada evento tiene:
  - **Fecha y hora** a la izquierda
  - **Ícono** en el centro (según tipo)
  - **Tarjeta** con título, resumen y botón de acción

✅ **Iconos por tipo:**
- 🩺 **Consulta:** `fa-user-md`
- 🔬 **Laboratorio:** `fa-microscope`
- 📷 **Imagen:** `fa-x-ray`
- 💊 **Receta:** `fa-prescription`

✅ **Botones de acción:**
- "👁️ Ver PDF en Drive" (si el archivo existe)
- Badge "Procesando..." (si no está listo)

**Si NO ves esto:**
- ❌ Verifica que la URL sea `/pacientes/<id>/expediente/`
- ❌ Revisa que use el template `historial_clinico.html`
- ❌ Confirma que el paciente tenga eventos (consultas, labs, etc.)

---

### **🔐 PRUEBA 4: SIDEBAR - RBAC**

**URL:** `http://localhost:8000/` (cualquier página)

**Credenciales:** Probar con diferentes roles

**Caso 1: Usuario MEDICO**

✅ **Debe ver:**
- 🩺 Sección "CONSULTORIO"
  - Consultas
  - Expedientes
  - Mi Agenda
- 🧠 Sección "INTELIGENCIA ARTIFICIAL" (si tiene permisos)

❌ **NO debe ver:**
- Sección "LABORATORIO"
- Sección "FARMACIA"
- Opciones de administración (a menos que sea superuser)

**Caso 2: Usuario LABORATORIO**

✅ **Debe ver:**
- 🔬 Sección "LABORATORIO"
  - Recepción & Cobro
  - Área Técnica
  - Configuración LIMS

❌ **NO debe ver:**
- Sección "CONSULTORIO"
- Sección "FARMACIA" (a menos que también esté en ese grupo)

**Caso 3: Usuario FARMACIA**

✅ **Debe ver:**
- 💊 Sección "FARMACIA"
  - Punto de Venta
  - Inventario
  - Historial de Ventas
  - Libro de Control

❌ **NO debe ver:**
- Sección "CONSULTORIO"
- Sección "LABORATORIO"

**Caso 4: SUPERUSER/ADMIN**

✅ **Debe ver TODO:**
- 🩺 CONSULTORIO
- 🔬 LABORATORIO
- 💊 FARMACIA
- ⚙️ ADMINISTRACIÓN
- 🧠 INTELIGENCIA ARTIFICIAL

**Si NO ves esto:**
- ❌ Verifica que el sidebar use `{% load auth_extras %}`
- ❌ Confirma que use filtros `{% if request.user|has_group:"..." %}`
- ❌ Revisa que los grupos estén creados: `python manage.py crear_grupos_roles`
- ❌ Asigna el usuario al grupo correcto en Django Admin

---

## 🐛 TROUBLESHOOTING

### **Problema: "No veo los cambios"**

**Solución:**
1. ✅ Reiniciar el servidor (Ctrl+C y `python manage.py runserver`)
2. ✅ Limpiar caché del navegador (CTRL + F5)
3. ✅ Probar en modo incógnito
4. ✅ Verificar que no haya errores en la consola de DevTools (F12)

### **Problema: "Template no encontrado"**

**Verificar:**
```bash
# Consultorio
consultorio/templates/consultorio/nueva_consulta_gemelo.html

# Laboratorio
laboratorio/templates/laboratorio/capturar_resultados.html

# Pacientes
core/templates/pacientes/historial_clinico.html

# Sidebar
core/templates/includes/sidebar.html
```

### **Problema: "El sidebar no filtra por rol"**

**Verificar:**
1. ✅ Grupos creados:
   ```bash
   python manage.py crear_grupos_roles
   ```
2. ✅ Usuario asignado al grupo:
   - Ir a Django Admin (`/admin/`)
   - Editar usuario
   - Pestaña "Permisos"
   - Sección "Grupos"
   - Agregar al grupo correspondiente

### **Problema: "Error 500 al acceder a una vista"**

**Revisar:**
1. ✅ Logs del servidor en la terminal
2. ✅ Archivo de logs: `logs/django.log`
3. ✅ Verificar que las migraciones estén aplicadas:
   ```bash
   python manage.py migrate
   ```

---

## 📊 CHECKLIST DE VERIFICACIÓN

- [ ] Servidor reiniciado
- [ ] Caché del navegador limpiado
- [ ] **Consultorio:** Gemelo Digital funciona (split screen)
- [ ] **Laboratorio:** Smart Lab activo (data-keywords en inputs)
- [ ] **Pacientes:** Timeline vertical con iconos
- [ ] **Sidebar:** Solo muestra menús según rol del usuario
- [ ] No hay errores 500 en ninguna vista
- [ ] No hay errores en la consola del navegador (F12)

---

## 🎯 RESULTADO ESPERADO

Al finalizar todas las pruebas, debes confirmar:

✅ **Las 4 interfaces nuevas están ACTIVAS:**
1. Sidebar con RBAC
2. Consultorio con Gemelo Digital
3. Laboratorio con Smart Lab
4. Pacientes con Timeline

✅ **No hay archivos paralelos** (verificado: `sidebar_clean.html` fue borrado)

✅ **Las URLs apuntan a las vistas correctas** (verificado en `config/urls.py`)

✅ **Los cambios son visibles para el usuario final**

---

## 📞 SOPORTE

Si después de seguir esta guía aún no ves los cambios:

1. **Revisar logs del servidor** en la terminal
2. **Abrir DevTools** (F12) y revisar errores en Console
3. **Verificar que los archivos existan** físicamente en el sistema
4. **Confirmar que las vistas apunten a los templates correctos**

---

**FIN DE LA GUÍA**  
**Estado:** ✅ LISTO PARA PRUEBAS

¡Buena suerte con la verificación! 🚀
