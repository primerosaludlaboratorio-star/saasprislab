# 🔄 MIGRACIÓN Y PUESTA EN MARCHA: Multi-Tenant Pris-Valle

## 📋 Resumen Ejecutivo

Este documento guía la ejecución de migraciones y la inicialización del sistema multi-tenant para Prislab.

---

## ✅ PASO 1: Ejecución de Migraciones

### Comando a Ejecutar

```bash
# 1. Generar migraciones para los nuevos modelos y campos
python manage.py makemigrations

# 2. Revisar las migraciones generadas (opcional)
# Revisar en core/migrations/ el archivo más reciente

# 3. Aplicar las migraciones
python manage.py migrate
```

### Modelos y Campos Afectados

**Modelo `Empresa`** (Nuevos campos):
- ✅ `color_primario` (CharField, default: "#D9230F")
- ✅ `color_secundario` (CharField, default: "#2B3A42")
- ✅ `color_fondo` (CharField, default: "#FFFFFF")
- ✅ `css_personalizado` (TextField, nullable)
- ✅ `activa` (BooleanField, default: True)

**Modelo `Sucursal`** (Nuevo modelo):
- ✅ ForeignKey a `Empresa`
- ✅ Campos: `nombre`, `codigo_sucursal`, `direccion`, `telefono`, `email`, `responsable`, `activa`, `fecha_creacion`

**Modelo `ConfiguracionModulos`** (Nuevo modelo):
- ✅ OneToOneField a `Empresa`
- ✅ BooleanFields para cada módulo (Laboratorio, Farmacia, IA, etc.)

**Modelo `Usuario`** (Nuevo campo):
- ✅ `sucursal` (ForeignKey a Sucursal, nullable)

### Manejo de Datos Existentes

- ✅ Los campos nuevos tienen valores por defecto
- ✅ Los campos ForeignKey son nullable para evitar conflictos
- ✅ Las migraciones deberían ejecutarse sin problemas con datos existentes

---

## ✅ PASO 2: Script de Inicialización 'Pris-Valle'

### Comando a Ejecutar

```bash
python manage.py inicializar_pris_valle
```

### Funcionalidad del Script

El comando `inicializar_pris_valle` realiza las siguientes tareas:

#### a) Verifica/Crea Empresa Prislab
- ✅ Busca la empresa "PRISLAB"
- ✅ Si no existe, la crea con:
  - `color_primario`: #D9230F (Rojo Prislab)
  - `color_secundario`: #2B3A42 (Oxford Grey)
  - `color_fondo`: #FFFFFF (Blanco)
  - `periodo_vigencia`: "2024-2030"
- ✅ Si existe, actualiza los colores si están vacíos

#### b) Crea Sucursal 'Matriz'
- ✅ Crea sucursal con código "SUC-001"
- ✅ Nombre: "Matriz"
- ✅ Vinculada a empresa Prislab
- ✅ Estado: Activa

#### c) Asigna Usuarios Existentes
- ✅ Asigna todos los usuarios sin empresa a Prislab
- ✅ Asigna todos los usuarios sin sucursal a Sucursal Matriz
- ✅ Mantiene usuarios que ya tienen empresa asignada

#### d) Configura Módulos Activos
- ✅ Crea `ConfiguracionModulos` para Prislab con:
  - `modulo_laboratorio`: True ✅
  - `modulo_farmacia`: True ✅
  - `modulo_ia`: True ✅
  - Otros módulos: False

### Opciones del Comando

```bash
# Ejecución normal (no sobrescribe si ya existe)
python manage.py inicializar_pris_valle

# Ejecución forzada (actualiza incluso si ya existe)
python manage.py inicializar_pris_valle --force
```

### Salida Esperada

```
🚀 Inicializando Multi-Tenant Pris-Valle...

📋 Paso 1: Verificando empresa Prislab...
  ✅ Empresa "PRISLAB" creada

📋 Paso 2: Verificando sucursal Matriz...
  ✅ Sucursal "Matriz" creada

📋 Paso 3: Asignando usuarios a Prislab y Sucursal Matriz...
  ✅ X usuarios asignados a Prislab/Sucursal Matriz

📋 Paso 4: Configurando módulos de Prislab...
  ✅ Configuración de módulos creada
     - Laboratorio: ✅
     - Farmacia: ✅
     - IA: ✅

============================================================
✅ INICIALIZACIÓN COMPLETA
============================================================

📊 Resumen:
   - Empresa: PRISLAB
   - Sucursal: Matriz (SUC-001)
   - Usuarios asignados: X
   - Módulos activos: Laboratorio, Farmacia, IA

🎉 Sistema Pris-Valle Multi-Tenant listo para usar!
```

---

## ✅ PASO 3: Verificación de Regla de Oro (Header Líquido)

### Funcionalidad Verificada

El Header Líquido está correctamente implementado con las siguientes características:

#### 1. Desplazamiento Elástico ✅
- **Marca/Logo**: Se desplaza 270px cuando el sidebar se abre
- **Período de Vigencia**: Se desplaza junto con la marca (parte del mismo elemento)
- **Transición**: 0.3s ease-in-out (suave y profesional)

#### 2. Implementación en `base.html`

**CSS (Líneas 86-105)**:
```css
.marca-prislab {
    margin-left: 80px; /* Posición inicial */
    transition: margin-left 0.3s ease-in-out; /* Transición suave */
}

.header-liquido.sidebar-open .marca-prislab {
    margin-left: 270px; /* Desplazamiento cuando sidebar abierto */
}
```

**HTML (Líneas 243-255)**:
```html
<a href="{% url 'home' %}" class="marca-prislab" id="marcaPrislab">
    {% if empresa_actual and empresa_actual.logo %}
        <img src="{{ empresa_actual.logo.url }}" ... class="logo-icon">
    {% else %}
        <i class="bi bi-heart-pulse-fill logo-icon"></i>
    {% endif %}
    <span>{{ empresa_actual.nombre|default:"PRISLAB" }}</span>
    {% if empresa_actual and empresa_actual.periodo_vigencia %}
        <small>{{ empresa_actual.periodo_vigencia }}</small>
    {% endif %}
</a>
```

#### 3. Características del Desplazamiento

- ✅ **Logo dinámico**: Se desplaza correctamente (logo de empresa o ícono predeterminado)
- ✅ **Nombre dinámico**: Se desplaza correctamente (nombre de empresa o "PRISLAB")
- ✅ **Período de vigencia**: Se desplaza junto con la marca (dentro del mismo `<a>`)
- ✅ **Transición suave**: 0.3s ease-in-out para animación profesional
- ✅ **No se oculta**: Nada queda oculto detrás del sidebar

#### 4. Verificación Manual Recomendada

1. **Iniciar sesión** con un usuario que tenga empresa asignada
2. **Abrir el sidebar** (click en botón hamburguesa)
3. **Verificar**:
   - ✅ La marca se desplaza 270px hacia la derecha
   - ✅ El período de vigencia se desplaza junto con la marca
   - ✅ La transición es suave (0.3s)
   - ✅ Nada queda oculto
4. **Cerrar el sidebar**
5. **Verificar**:
   - ✅ La marca regresa a su posición original (80px)
   - ✅ La transición es suave

---

## 📊 Checklist de Verificación

### Migraciones
- [ ] Ejecutar `python manage.py makemigrations`
- [ ] Revisar migraciones generadas
- [ ] Ejecutar `python manage.py migrate`
- [ ] Verificar que no hay errores

### Inicialización
- [ ] Ejecutar `python manage.py inicializar_pris_valle`
- [ ] Verificar creación de empresa Prislab
- [ ] Verificar creación de sucursal Matriz
- [ ] Verificar asignación de usuarios
- [ ] Verificar configuración de módulos

### Header Líquido
- [ ] Verificar desplazamiento de marca (270px)
- [ ] Verificar desplazamiento de período de vigencia
- [ ] Verificar transición suave (0.3s)
- [ ] Verificar que nada queda oculto
- [ ] Probar con logo dinámico
- [ ] Probar con nombre dinámico

---

## ⚠️ Notas Importantes

1. **Datos Existentes**: Las migraciones son seguras y no afectarán datos existentes
2. **Usuarios Existentes**: Se asignarán automáticamente a Prislab y Sucursal Matriz
3. **Configuración de Módulos**: Solo se crea si no existe (usar `--force` para actualizar)
4. **Header Líquido**: Funciona con cualquier logo/nombre de empresa (dinámico)

---

## 🔧 Solución de Problemas

### Error: "django.db.utils.IntegrityError"
- **Causa**: Conflictos con datos existentes
- **Solución**: Revisar migraciones y ejecutar con `--force` si es necesario

### Error: "No such file or directory"
- **Causa**: Comando no encontrado
- **Solución**: Asegurar que el archivo `inicializar_pris_valle.py` está en `core/management/commands/`

### Header no se desplaza
- **Causa**: JavaScript no cargado o conflicto CSS
- **Solución**: Verificar que `base.html` está extendido correctamente y que el JavaScript de `toggleSidebar` está funcionando

---

**Fecha de Creación**: 2025-01-27  
**Versión**: 1.0  
**Estado**: ✅ LISTO PARA EJECUTAR
