# 🏗️ ESTÁNDARES DE DISEÑO PRISLAB v5.0
## "Reglas de Varilla de Alta Resistencia" (Basadas en Deltec/Velab)

---

## 📐 PATRÓN DE DISEÑO: MASTER-DETAIL

### Regla 1: Diseño de Doble Panel
**Aplicación:** Módulos de alta rotación (Resultados, Recepción, Farmacia POS)

**Especificaciones:**
- **Panel Izquierdo (Sticky):** Lista de navegación con scroll independiente
  - Ancho fijo: 300px
  - Posición: `position: sticky; top: 0;`
  - Buscador superior para filtrado rápido
  - Items clickeables con estado activo visual
  
- **Panel Derecho (Flexible):** Formulario de edición
  - Ancho: `flex: 1` (resto del espacio)
  - Scroll independiente
  - Contexto persistente durante navegación

**Beneficio:** El usuario NO debe navegar hacia atrás para cambiar de paciente/orden.

**Ejemplo de Implementación:**
```html
<div class="layout-dual">
    <div class="columna-navegacion">...</div>
    <div class="columna-edicion">...</div>
</div>
```

---

## ⌨️ LÓGICA DE CAPTURA: KEYBOARD-FIRST

### Regla 2: Navegación 100% por Teclado
**Aplicación:** Todos los formularios de captura

**Especificaciones:**
- **Enter:** Avanzar al siguiente campo
- **Tab:** Avanzar al siguiente campo (comportamiento estándar mejorado)
- **Shift+Tab:** Retroceder al campo anterior
- **Arrow Down:** Siguiente campo
- **Arrow Up:** Campo anterior
- **Escape:** Cancelar edición / Cerrar modal
- **Ctrl+S:** Guardar (si aplica)

**Máscaras de Entrada:**
- Campos numéricos: Solo aceptan números, punto decimal y signo negativo (si aplica)
- Campos de texto: Sin restricciones (excepto validaciones de negocio)
- Campos de fecha: Formato automático (DD/MM/YYYY)
- Campos de hora: Formato automático (HH:MM)

**Implementación JavaScript:**
```javascript
function manejarTabbing(input, event) {
    if (event.key === 'Enter' || (event.key === 'Tab' && !event.shiftKey)) {
        event.preventDefault();
        // Avanzar al siguiente campo
    }
    // ... más lógica
}
```

---

## 📊 SISTEMA DE DELTA-CHECK

### Regla 3: Validación Histórica Visual
**Aplicación:** Campos de resultados numéricos en Laboratorio

**Especificaciones:**
- **Consulta Automática:** Al cargar un formulario, consultar historial del paciente
- **Columna de Referencia:** Mostrar último resultado previo en columna tenue
- **Cálculo de Delta:** Porcentaje de cambio automático
- **Indicadores Visuales:**
  - Verde: Cambio < 10% (normal)
  - Naranja: Cambio 10-20% (atención)
  - Rojo: Cambio > 20% (crítico)

**Estructura de Datos:**
```python
resultado_anterior = {
    'valor': 110.5,
    'fecha': '2024-01-15',
    'folio': 'ORD-12345',
    'delta_porcentaje': 5.2
}
```

**Visualización:**
```html
<td class="col-delta">
    <div class="delta-check">
        <div class="fw-bold">110.5 (Δ+5.2%)</div>
        <small>15/01/2024 - ORD-12345</small>
    </div>
</td>
```

---

## 🪟 GESTIÓN DE MODALES

### Regla 4: Ediciones Rápidas Asíncronas
**Aplicación:** Catálogos, Configuraciones, Ediciones rápidas

**Especificaciones:**
- **No usar páginas nuevas** para ediciones rápidas
- **Modales Bootstrap/HTML5** con carga AJAX
- **Contexto persistente:** El usuario mantiene su lugar en la operación principal
- **Cierre automático:** Al guardar exitosamente, cerrar modal y actualizar lista

**Estructura:**
```html
<!-- Modal -->
<div class="modal fade" id="modalEditar">
    <div class="modal-dialog">
        <div class="modal-content">
            <!-- Contenido cargado vía AJAX -->
        </div>
    </div>
</div>
```

**Flujo AJAX:**
```javascript
// Abrir modal
function abrirModalEditar(id) {
    fetch(`/api/obtener/${id}/`)
        .then(response => response.json())
        .then(data => {
            document.getElementById('modalEditar').innerHTML = data.html;
            // Mostrar modal
        });
}

// Guardar y cerrar
function guardarModal() {
    fetch('/api/guardar/', { method: 'POST', body: formData })
        .then(() => {
            // Cerrar modal
            // Actualizar lista principal
        });
}
```

---

## 🤖 INTEGRACIÓN DE JARVIS (PRIS)

### Regla 5: Dictado Contextual
**Aplicación:** Todos los campos de entrada

**Especificaciones:**
- **Campo con Foco:** PRIS debe dictar directamente al campo activo
- **Validación Inteligente:**
  - Campo numérico: Validar rango antes de escribir
  - Campo de texto: Sin validación previa
  - Campo de fecha: Convertir formato hablado a fecha
- **Mapeo Inteligente:** Si no hay foco, buscar campo por nombre/código

**Implementación:**
```javascript
function activarDictadoPRIS() {
    const campoActivo = document.activeElement;
    
    if (campoActivo && campoActivo.classList.contains('input-captura')) {
        // Dictado directo al campo activo
        reconocimientoVoz.onresult = function(event) {
            const valor = event.results[0][0].transcript;
            
            // Validar si es campo numérico
            if (campoActivo.type === 'number') {
                const valorNum = parseFloat(valor);
                const min = parseFloat(campoActivo.dataset.min);
                const max = parseFloat(campoActivo.dataset.max);
                
                if (valorNum >= min && valorNum <= max) {
                    campoActivo.value = valorNum;
                } else {
                    alert(`Valor fuera de rango (${min}-${max})`);
                }
            } else {
                campoActivo.value = valor;
            }
        };
    } else {
        // Mapeo inteligente por nombre/código
        procesarDictadoPRIS(transcripcion);
    }
}
```

---

## 📝 AUDITORÍA NATIVA

### Regla 6: Log Automático de Cambios
**Aplicación:** Todos los campos críticos (Resultados, Promociones, Cobranza)

**Especificaciones:**
- **Trigger Automático:** Cada cambio en campo crítico dispara log
- **Datos Registrados:**
  - `ID_Usuario`: Usuario que realizó el cambio
  - `Valor_Anterior`: Valor antes del cambio
  - `Valor_Nuevo`: Valor después del cambio
  - `Marca_Tiempo`: Timestamp del cambio
  - `Campo`: Nombre del campo modificado
  - `Modulo`: Módulo donde ocurrió el cambio
  - `Referencia_ID`: ID del registro principal

**Implementación Backend:**
```python
from core.utils.auditoria_helper import crear_log_auditoria

def guardar_campo(request, campo_id, valor_nuevo):
    campo = Campo.objects.get(id=campo_id)
    valor_anterior = campo.valor
    
    campo.valor = valor_nuevo
    campo.save()
    
    # Auditoría automática
    crear_log_auditoria(
        empresa=request.user.empresa,
        usuario=request.user,
        accion=AuditLog.ACCION_UPDATE,
        modelo='Campo',
        objeto_id=campo_id,
        datos_anterior={'valor': valor_anterior},
        datos_nuevo={'valor': valor_nuevo},
        campo_modificado='valor',
        modulo='LABORATORIO',
        request=request
    )
```

**Implementación Frontend (JavaScript):**
```javascript
// Interceptor de cambios
document.querySelectorAll('.campo-auditable').forEach(campo => {
    campo.addEventListener('change', function() {
        const valorAnterior = this.dataset.valorAnterior;
        const valorNuevo = this.value;
        
        // Enviar a backend para auditoría
        fetch('/api/auditoria/campo/', {
            method: 'POST',
            body: JSON.stringify({
                campo_id: this.id,
                valor_anterior: valorAnterior,
                valor_nuevo: valorNuevo,
                modulo: this.dataset.modulo
            })
        });
        
        // Actualizar valor anterior
        this.dataset.valorAnterior = valorNuevo;
    });
});
```

---

## ✅ CHECKLIST DE IMPLEMENTACIÓN

Para cada nuevo módulo o mejora, verificar:

- [ ] ¿Usa patrón Master-Detail si es de alta rotación?
- [ ] ¿Es 100% operable por teclado?
- [ ] ¿Tiene máscaras de entrada apropiadas?
- [ ] ¿Implementa Delta-Check si aplica?
- [ ] ¿Usa modales para ediciones rápidas?
- [ ] ¿PRIS puede dictar directamente a campos?
- [ ] ¿Cada cambio crítico genera log de auditoría?

---

## 📚 REFERENCIAS

- **Deltec:** Sistema de gestión de laboratorios clínicos
- **Velab:** Sistema de captura de resultados
- **Estándares CLSI:** Clinical and Laboratory Standards Institute

---

**Última actualización:** 2026-01-XX
**Versión:** 1.0
**Autor:** PRISLAB Development Team
