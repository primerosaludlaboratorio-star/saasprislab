/**
 * Utilidades JavaScript para Estándares Industriales PRISLAB v5.
 * Reglas de Varilla de Alta Resistencia (Basadas en Deltec/Velab).
 */

// ============================================================================
// REGLA 2: LÓGICA DE CAPTURA (Keyboard-First)
// ============================================================================

/**
 * Configura navegación por teclado para un conjunto de campos.
 * @param {string} selector - Selector CSS de los campos (ej: '.input-captura')
 */
function configurarNavegacionTeclado(selector) {
    const inputs = document.querySelectorAll(selector);
    
    inputs.forEach((input, index) => {
        // Enter: Siguiente campo
        input.addEventListener('keydown', function(e) {
            if (e.key === 'Enter') {
                e.preventDefault();
                const nextIndex = index + 1;
                if (nextIndex < inputs.length) {
                    inputs[nextIndex].focus();
                    inputs[nextIndex].select();
                }
            }
            
            // Arrow Down: Siguiente campo
            if (e.key === 'ArrowDown') {
                e.preventDefault();
                const nextIndex = index + 1;
                if (nextIndex < inputs.length) {
                    inputs[nextIndex].focus();
                    inputs[nextIndex].select();
                }
            }
            
            // Arrow Up: Campo anterior
            if (e.key === 'ArrowUp') {
                e.preventDefault();
                const prevIndex = index - 1;
                if (prevIndex >= 0) {
                    inputs[prevIndex].focus();
                    inputs[prevIndex].select();
                }
            }
            
            // Tab: Siguiente campo (comportamiento mejorado)
            if (e.key === 'Tab' && !e.shiftKey) {
                const nextIndex = index + 1;
                if (nextIndex < inputs.length) {
                    setTimeout(() => {
                        inputs[nextIndex].focus();
                        inputs[nextIndex].select();
                    }, 10);
                }
            }
        });
        
        // Auto-seleccionar texto al enfocar
        input.addEventListener('focus', function() {
            this.select();
        });
    });
}

/**
 * Aplica máscara numérica a un campo de entrada.
 * @param {HTMLElement} input - Campo de entrada
 */
function aplicarMascaraNumerica(input) {
    input.addEventListener('input', function(e) {
        // Permitir solo números y punto decimal
        this.value = this.value.replace(/[^0-9.]/g, '');
        
        // Evitar múltiples puntos decimales
        const partes = this.value.split('.');
        if (partes.length > 2) {
            this.value = partes[0] + '.' + partes.slice(1).join('');
        }
    });
    
    // Validar al perder el foco
    input.addEventListener('blur', function() {
        if (this.value && isNaN(parseFloat(this.value))) {
            this.value = '';
        }
    });
}

/**
 * Configura atajos de teclado globales.
 * @param {Function} guardarBorrador - Función para guardar borrador
 * @param {Function} validarPublicar - Función para validar y publicar
 */
function configurarAtajosGlobales(guardarBorrador, validarPublicar) {
    document.addEventListener('keydown', function(e) {
        // Ctrl+S: Guardar borrador
        if (e.ctrlKey && e.key === 's') {
            e.preventDefault();
            if (guardarBorrador) guardarBorrador();
        }
        
        // Ctrl+Enter: Validar y publicar
        if (e.ctrlKey && e.key === 'Enter') {
            e.preventDefault();
            if (validarPublicar) validarPublicar();
        }
    });
}

// ============================================================================
// REGLA 3: SISTEMA DE DELTA-CHECK
// ============================================================================

/**
 * Calcula y muestra el porcentaje de cambio (Delta Check).
 * @param {HTMLElement} input - Campo de entrada con el valor actual
 * @param {HTMLElement} deltaElement - Elemento donde mostrar el delta
 * @param {number} valorAnterior - Valor anterior para comparación
 */
function actualizarDeltaCheck(input, deltaElement, valorAnterior) {
    if (!deltaElement || !valorAnterior) return;
    
    const valorActual = parseFloat(input.value);
    if (isNaN(valorActual) || isNaN(valorAnterior) || valorAnterior === 0) {
        return;
    }
    
    const delta = valorActual - valorAnterior;
    const porcentaje = ((delta / valorAnterior) * 100).toFixed(1);
    
    // Actualizar visualización
    const textoBase = valorAnterior.toString();
    let claseColor = 'delta-positivo';
    let severidad = 'normal';
    
    if (Math.abs(porcentaje) > 30) {
        claseColor = 'delta-negativo';
        severidad = 'critico';
    } else if (Math.abs(porcentaje) > 20) {
        claseColor = 'delta-negativo';
        severidad = 'advertencia';
    } else if (Math.abs(porcentaje) > 10) {
        claseColor = '';
        deltaElement.style.color = '#ff9800';
        severidad = 'advertencia';
    }
    
    deltaElement.className = `fw-bold ${claseColor}`;
    deltaElement.textContent = `${textoBase} (Δ${porcentaje > 0 ? '+' : ''}${porcentaje}%)`;
    
    // Alertar si es crítico
    if (severidad === 'critico') {
        if (!input.dataset.deltaAlertado) {
            alert(`⚠️ Cambio crítico detectado: ${porcentaje}% respecto al valor anterior. Verifique el valor ingresado.`);
            input.dataset.deltaAlertado = 'true';
        }
    }
}

// ============================================================================
// REGLA 4: GESTIÓN DE MODALES
// ============================================================================

/**
 * Abre un modal asíncrono vía AJAX.
 * @param {string} url - URL para cargar el contenido del modal
 * @param {string} titulo - Título del modal
 * @param {Function} callback - Función a ejecutar después de cerrar el modal
 */
function abrirModalAJAX(url, titulo, callback) {
    fetch(url)
        .then(response => response.text())
        .then(html => {
            // Crear modal
            const modalId = 'modal-' + Date.now();
            const modalHTML = `
                <div class="modal fade" id="${modalId}" tabindex="-1">
                    <div class="modal-dialog">
                        <div class="modal-content">
                            <div class="modal-header">
                                <h5 class="modal-title">${titulo}</h5>
                                <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                            </div>
                            <div class="modal-body">
                                ${html}
                            </div>
                        </div>
                    </div>
                </div>
            `;
            
            // Insertar en el DOM
            const tempDiv = document.createElement('div');
            tempDiv.innerHTML = modalHTML;
            const modal = tempDiv.firstElementChild;
            document.body.appendChild(modal);
            
            // Mostrar modal
            const bsModal = new bootstrap.Modal(modal);
            bsModal.show();
            
            // Ejecutar callback al cerrar
            modal.addEventListener('hidden.bs.modal', function() {
                if (callback) callback();
                modal.remove();
            });
            
            // Cerrar con Escape
            document.addEventListener('keydown', function(e) {
                if (e.key === 'Escape' && document.getElementById(modalId)) {
                    bsModal.hide();
                }
            });
        })
        .catch(error => {
            console.error('Error al cargar modal:', error);
            alert('Error al cargar el formulario. Por favor, intente nuevamente.');
        });
}

// ============================================================================
// REGLA 5: INTEGRACIÓN DE JARVIS (PRIS)
// ============================================================================

/**
 * Configura un campo para ser "escuchable" por PRIS.
 * @param {HTMLElement} input - Campo de entrada
 * @param {Object} config - Configuración {refMin, refMax, codigo, descripcion}
 */
function configurarCampoEscuchablePRIS(input, config) {
    // Agregar atributos de datos
    if (config.refMin !== undefined) input.dataset.refMin = config.refMin;
    if (config.refMax !== undefined) input.dataset.refMax = config.refMax;
    if (config.codigo) input.dataset.codigo = config.codigo;
    if (config.descripcion) input.dataset.descripcion = config.descripcion;
    
    // Marcar como escuchable
    input.dataset.prisEscuchable = 'true';
}

/**
 * Procesa dictado de PRIS y lo aplica al campo correspondiente.
 * @param {string} transcripcion - Texto dictado
 * @param {HTMLElement} campoActual - Campo con foco actual (opcional)
 */
function procesarDictadoPRIS(transcripcion, campoActual) {
    const texto = transcripcion.toUpperCase();
    const numeros = texto.match(/\d+\.?\d*/);
    
    if (!numeros) {
        console.warn('No se detectó número en el dictado:', transcripcion);
        return;
    }
    
    const valor = parseFloat(numeros[0]);
    
    // Si hay un campo con foco, validar y escribir ahí
    if (campoActual && campoActual.dataset.prisEscuchable === 'true') {
        // Validar rango si es numérico
        if (campoActual.type === 'number' || campoActual.dataset.refMin) {
            const refMin = parseFloat(campoActual.dataset.refMin) || null;
            const refMax = parseFloat(campoActual.dataset.refMax) || null;
            
            if (refMin !== null && valor < refMin) {
                if (!confirm(`Valor por debajo del mínimo (${refMin}). ¿Continuar?`)) {
                    return;
                }
            }
            
            if (refMax !== null && valor > refMax) {
                if (!confirm(`Valor por encima del máximo (${refMax}). ¿Continuar?`)) {
                    return;
                }
            }
        }
        
        campoActual.value = valor;
        campoActual.dispatchEvent(new Event('input'));
        campoActual.focus();
        campoActual.select();
        
        // Feedback visual
        campoActual.style.backgroundColor = '#e3f2fd';
        setTimeout(() => {
            campoActual.style.backgroundColor = '';
        }, 1000);
        
        return;
    }
    
    // Si no hay campo con foco, buscar por descripción o código
    const inputs = document.querySelectorAll('[data-pris-escuchable="true"]');
    let mejorCoincidencia = null;
    let mejorScore = 0;
    
    inputs.forEach(input => {
        const descripcion = (input.dataset.descripcion || '').toUpperCase();
        const codigo = (input.dataset.codigo || '').toUpperCase();
        
        let score = 0;
        const palabras = texto.split(' ');
        
        palabras.forEach(palabra => {
            if (descripcion.includes(palabra) && palabra.length > 2) {
                score += palabra.length;
            }
            if (codigo.includes(palabra) && palabra.length > 1) {
                score += palabra.length * 2; // Código tiene más peso
            }
        });
        
        if (score > mejorScore) {
            mejorScore = score;
            mejorCoincidencia = input;
        }
    });
    
    if (mejorCoincidencia) {
        // Validar rango antes de escribir
        const refMin = parseFloat(mejorCoincidencia.dataset.refMin) || null;
        const refMax = parseFloat(mejorCoincidencia.dataset.refMax) || null;
        
        if (refMin !== null && valor < refMin) {
            if (!confirm(`Valor por debajo del mínimo (${refMin}). ¿Continuar?`)) {
                return;
            }
        }
        
        if (refMax !== null && valor > refMax) {
            if (!confirm(`Valor por encima del máximo (${refMax}). ¿Continuar?`)) {
                return;
            }
        }
        
        mejorCoincidencia.value = valor;
        mejorCoincidencia.dispatchEvent(new Event('input'));
        mejorCoincidencia.focus();
        mejorCoincidencia.select();
        
        // Feedback visual
        mejorCoincidencia.style.backgroundColor = '#e3f2fd';
        setTimeout(() => {
            mejorCoincidencia.style.backgroundColor = '';
        }, 1000);
    } else {
        alert('No se encontró un campo que coincida con: ' + transcripcion);
    }
}

// ============================================================================
// REGLA 6: AUDITORÍA NATIVA
// ============================================================================

/**
 * Registra un cambio de campo para auditoría.
 * @param {HTMLElement} input - Campo modificado
 * @param {*} valorAnterior - Valor anterior
 * @param {string} csrfToken - Token CSRF
 */
function auditarCambioCampo(input, valorAnterior, csrfToken) {
    const valorNuevo = input.value;
    
    // No auditar si no hubo cambio real
    if (valorAnterior === valorNuevo) {
        return;
    }
    
    // Preparar datos
    const datos = {
        campo_id: input.id,
        campo_nombre: input.name || input.id,
        valor_anterior: valorAnterior,
        valor_nuevo: valorNuevo,
        timestamp: new Date().toISOString()
    };
    
    // Enviar vía AJAX (sin bloquear UI)
    fetch('/api/auditoria/campo/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrfToken
        },
        body: JSON.stringify(datos)
    }).catch(error => {
        console.error('Error al registrar auditoría:', error);
        // Retry automático después de 1 segundo
        setTimeout(() => {
            auditarCambioCampo(input, valorAnterior, csrfToken);
        }, 1000);
    });
}

/**
 * Configura auditoría automática para un campo.
 * @param {HTMLElement} input - Campo a auditar
 * @param {string} csrfToken - Token CSRF
 */
function configurarAuditoriaCampo(input, csrfToken) {
    let valorAnterior = input.value;
    
    // Guardar valor anterior al enfocar
    input.addEventListener('focus', function() {
        valorAnterior = this.value;
    });
    
    // Auditar al perder el foco
    input.addEventListener('blur', function() {
        if (this.value !== valorAnterior) {
            auditarCambioCampo(this, valorAnterior, csrfToken);
        }
    });
    
    // También auditar en cambios significativos (Enter)
    input.addEventListener('keydown', function(e) {
        if (e.key === 'Enter' && this.value !== valorAnterior) {
            auditarCambioCampo(this, valorAnterior, csrfToken);
            valorAnterior = this.value;
        }
    });
}

// Exportar funciones para uso global
window.EstandaresIndustriales = {
    configurarNavegacionTeclado,
    aplicarMascaraNumerica,
    configurarAtajosGlobales,
    actualizarDeltaCheck,
    abrirModalAJAX,
    configurarCampoEscuchablePRIS,
    procesarDictadoPRIS,
    auditarCambioCampo,
    configurarAuditoriaCampo
};
