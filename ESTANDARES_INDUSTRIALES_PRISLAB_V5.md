# 🏗️ ESTÁNDARES INDUSTRIALES PRISLAB v5.0
## Reglas de Varilla de Alta Resistencia (Basadas en Deltec/Velab)

**Versión:** 1.0  
**Fecha:** 2026  
**Aplicación:** Todos los módulos de PRISLAB v5.0

---

## 📐 REGLA 1: PATRÓN DE DISEÑO (Master-Detail)

### Especificación
En módulos de alta rotación (Resultados, Recepción, Ventas), **SIEMPRE** usar diseño de doble panel:

- **Panel Izquierdo (300px fijo, sticky):**
  - Lista de navegación con buscador superior
  - Scroll independiente
  - Resaltado del elemento activo
  - Un solo clic para cambiar de contexto

- **Panel Derecho (flexible):**
  - Formulario de edición/captura
  - Ficha demográfica compacta arriba
  - Área de trabajo principal abajo

### Implementación
```html
<div class="layout-dual">
    <div class="columna-navegacion">
        <!-- Lista sticky -->
    </div>
    <div class="columna-captura">
        <!-- Formulario -->
    </div>
</div>
```

### CSS Requerido
```css
.layout-dual {
    display: flex;
    height: calc(100vh - 80px);
    gap: 0;
}
.columna-navegacion {
    width: 300px;
    background: white;
    border-right: 2px solid #dee2e6;
    overflow-y: auto;
    flex-shrink: 0;
}
.columna-captura {
    flex: 1;
    overflow: auto;
}
```

**❌ PROHIBIDO:** Navegación hacia atrás para cambiar de paciente/orden.

---

## ⌨️ REGLA 2: LÓGICA DE CAPTURA (Keyboard-First)

### Especificación
La captura debe ser **100% operable sin mouse**. Implementar:

1. **Listeners de Teclado:**
   - `Enter`: Siguiente campo
   - `Tab`: Siguiente campo
   - `Shift+Tab`: Campo anterior
   - `Arrow Down`: Siguiente campo
   - `Arrow Up`: Campo anterior
   - `Ctrl+S`: Guardar borrador
   - `Ctrl+Enter`: Validar y publicar

2. **Máscaras de Entrada:**
   - Campos numéricos: Solo números y punto decimal
   - Campos de texto: Sin restricciones (excepto validaciones específicas)
   - Auto-selección de texto al enfocar (para reemplazo rápido)

3. **Navegación Inteligente:**
   - El foco NUNCA debe perderse en botones
   - Saltar campos deshabilitados automáticamente
   - Scroll automático al campo siguiente si está fuera de vista

### Implementación JavaScript
```javascript
function manejarTabbing(input, event) {
    if (event.key === 'Enter' || (event.key === 'Tab' && !event.shiftKey)) {
        event.preventDefault();
        const inputs = Array.from(document.querySelectorAll('.input-captura'));
        const currentIndex = inputs.indexOf(input);
        if (currentIndex < inputs.length - 1) {
            inputs[currentIndex + 1].focus();
            inputs[currentIndex + 1].select();
        }
    }
}

// Máscara numérica
function aplicarMascaraNumerica(input) {
    input.addEventListener('input', function(e) {
        this.value = this.value.replace(/[^0-9.]/g, '');
    });
}
```

**❌ PROHIBIDO:** Requerir mouse para navegar entre campos.

---

## 📊 REGLA 3: SISTEMA DE DELTA-CHECK

### Especificación
En cada campo de resultado, **SIEMPRE** consultar el historial del paciente:

1. **Consulta Automática:**
   - Al cargar la orden, buscar resultados previos del mismo paciente
   - Filtrar por código de estudio/parámetro
   - Tomar el resultado más reciente (últimos 6 meses)

2. **Visualización:**
   - Columna "Último Resultado" o "Referencia Histórica"
   - Mostrar: Valor anterior, Fecha, Folio
   - Cálculo automático de porcentaje de cambio (Δ%)
   - Indicadores visuales:
     - Verde: Cambio < 10%
     - Naranja: Cambio 10-20%
     - Rojo: Cambio > 20%

3. **Validación Clínica:**
   - Alertar si el cambio es > 30% (posible error de captura)
   - Permitir confirmación manual del químico

### Implementación Backend
```python
# En la vista de captura
resultados_anteriores = {}
if orden.paciente:
    ordenes_anteriores = OrdenDeServicio.objects.filter(
        empresa=empresa,
        paciente=orden.paciente,
        estado='RESULTADOS_LISTOS',
        fecha_creacion__lt=orden.fecha_creacion
    ).order_by('-fecha_creacion')[:5]
    
    for orden_ant in ordenes_anteriores:
        for detalle_ant in orden_ant.detalles.all():
            if detalle_ant.resultado and detalle_ant.estudio.codigo:
                codigo_estudio = detalle_ant.estudio.codigo
                if codigo_estudio not in resultados_anteriores:
                    resultados_anteriores[codigo_estudio] = {
                        'valor': detalle_ant.resultado,
                        'fecha': orden_ant.fecha_creacion,
                        'folio': orden_ant.folio_orden
                    }
```

**✅ OBLIGATORIO:** Mostrar referencia histórica en TODOS los campos de resultado.

---

## 🪟 REGLA 4: GESTIÓN DE MODALES

### Especificación
Para ediciones rápidas (Antibióticos, Bacterias, Clientes, Estudios), **SIEMPRE** usar modales asíncronos:

1. **Modales AJAX:**
   - No abrir páginas nuevas
   - Mantener contexto de la operación principal
   - Cargar contenido vía AJAX
   - Cerrar con `Escape` o clic fuera

2. **Flujo:**
   - Botón "Agregar" → Abre modal
   - Formulario en modal → Guarda vía AJAX
   - Cierra modal → Actualiza lista sin recargar página

3. **Feedback:**
   - Loading spinner durante guardado
   - Mensaje de éxito/error
   - Actualización automática de la lista

### Implementación
```javascript
function abrirModalEdicion(url, titulo) {
    fetch(url)
        .then(response => response.text())
        .then(html => {
            const modal = document.createElement('div');
            modal.className = 'modal fade';
            modal.innerHTML = html;
            document.body.appendChild(modal);
            const bsModal = new bootstrap.Modal(modal);
            bsModal.show();
        });
}
```

**❌ PROHIBIDO:** Abrir páginas nuevas para ediciones rápidas.

---

## 🎤 REGLA 5: INTEGRACIÓN DE JARVIS (PRIS)

### Especificación
Cada campo de entrada debe ser **"escuchable"** por PRIS:

1. **Dictado Contextual:**
   - Si el foco está en un campo de texto → Dictado directo
   - Si el foco está en un campo numérico → Validar rango antes de escribir
   - Si el foco está en un campo de selección → Buscar coincidencia

2. **Mapeo Inteligente:**
   - "Glucosa 110" → Campo GLU con valor 110
   - "Hemoglobina 14.5" → Campo HGB con valor 14.5
   - Búsqueda por descripción o código

3. **Validación Pre-escritura:**
   - Si el valor dictado está fuera de rango → Alertar antes de escribir
   - Confirmación manual si el cambio es > 30% respecto al anterior

### Implementación
```javascript
function procesarDictadoPRIS(transcripcion, campoActual) {
    const texto = transcripcion.toUpperCase();
    const numeros = texto.match(/\d+\.?\d*/);
    
    if (campoActual.type === 'number') {
        const valor = parseFloat(numeros[0]);
        const refMin = parseFloat(campoActual.dataset.refMin);
        const refMax = parseFloat(campoActual.dataset.refMax);
        
        if (valor < refMin || valor > refMax) {
            if (!confirm(`Valor fuera de rango (${refMin}-${refMax}). ¿Continuar?`)) {
                return;
            }
        }
    }
    
    campoActual.value = numeros ? numeros[0] : texto;
    campoActual.dispatchEvent(new Event('input'));
}
```

**✅ OBLIGATORIO:** Todos los campos de captura deben ser "escuchables".

---

## 📝 REGLA 6: AUDITORÍA NATIVA

### Especificación
Cada cambio en un campo crítico debe disparar un log de auditoría automático:

1. **Campos Auditados:**
   - Resultados de laboratorio
   - Precios y promociones
   - Cobranza y pagos
   - Validaciones y autorizaciones

2. **Datos Registrados:**
   - `ID_Usuario`: Usuario que realizó el cambio
   - `Valor_Anterior`: Valor antes del cambio
   - `Valor_Nuevo`: Valor después del cambio
   - `Marca_Tiempo`: Timestamp del cambio
   - `Campo`: Nombre del campo modificado
   - `IP_Address`: Dirección IP del usuario

3. **Implementación:**
   - Disparar en `onchange` o `onblur` del campo
   - Guardar vía AJAX sin bloquear la UI
   - Retry automático si falla la conexión

### Implementación Backend
```python
from core.utils.trazabilidad import registrar_trazabilidad

def guardar_campo_auditado(campo, valor_anterior, valor_nuevo, request):
    # Guardar cambio en BD
    campo.save()
    
    # Registrar auditoría
    registrar_trazabilidad(
        tipo_operacion='CAMPO_MODIFICADO',
        modulo='LABORATORIO',
        referencia_id=campo.id,
        referencia_tipo='DetalleOrden',
        accion='UPDATE',
        descripcion=f'Campo {campo.nombre} modificado',
        usuario=request.user,
        empresa=request.user.empresa,
        datos_anteriores={'valor': valor_anterior},
        datos_nuevos={'valor': valor_nuevo},
        request=request,
    )
```

### Implementación Frontend
```javascript
function auditarCambio(campo, valorAnterior, valorNuevo) {
    fetch('/api/auditoria/campo/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrfToken
        },
        body: JSON.stringify({
            campo_id: campo.id,
            campo_nombre: campo.name,
            valor_anterior: valorAnterior,
            valor_nuevo: valorNuevo,
            timestamp: new Date().toISOString()
        })
    }).catch(error => {
        console.error('Error al registrar auditoría:', error);
        // Retry automático
        setTimeout(() => auditarCambio(campo, valorAnterior, valorNuevo), 1000);
    });
}
```

**✅ OBLIGATORIO:** Auditoría automática en TODOS los campos críticos.

---

## 📋 CHECKLIST DE IMPLEMENTACIÓN

Al crear un nuevo módulo, verificar:

- [ ] Layout Master-Detail implementado
- [ ] Navegación 100% operable con teclado
- [ ] Máscaras de entrada aplicadas
- [ ] Delta-Check integrado (si aplica)
- [ ] Modales AJAX para ediciones rápidas
- [ ] PRIS integrado en todos los campos
- [ ] Auditoría automática en campos críticos
- [ ] Auto-selección de texto al enfocar
- [ ] Scroll automático al campo siguiente
- [ ] Validación de rangos en tiempo real

---

## 🎯 PRIORIDADES

1. **CRÍTICO:** Reglas 1, 2, 6 (Diseño, Teclado, Auditoría)
2. **ALTO:** Reglas 3, 5 (Delta-Check, PRIS)
3. **MEDIO:** Regla 4 (Modales)

---

**Última actualización:** 2026  
**Mantenedor:** Equipo de Desarrollo PRISLAB v5
