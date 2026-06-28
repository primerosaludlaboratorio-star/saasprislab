/**
 * MOTOR DE CÁLCULO (Fórmulas Dinámicas)
 * REGLA: Campos calculados inmutables pero reactivos a cambios en campos base.
 * Validación Jarvis: Bloquear validación si resultado fuera de lógica biológica.
 */

class MotorCalculoFormulas {
    constructor() {
        this.formulas = new Map(); // Almacena fórmulas por campo
        this.dependencias = new Map(); // Mapea: campo_base -> [campos_calculados]
        this.valores = new Map(); // Cache de valores actuales
        this.validacionesBiologicas = new Map(); // Rangos biológicos válidos
    }

    /**
     * Registra una fórmula para un campo calculado.
     * @param {string} campoId - ID del campo calculado
     * @param {string} formula - Fórmula (ej: "GLU * 0.0555" o "HTO / 3")
     * @param {Array<string>} camposBase - IDs de los campos base que alimentan la fórmula
     * @param {Object} validacionBiologica - {min: number, max: number, mensaje: string}
     */
    registrarFormula(campoId, formula, camposBase, validacionBiologica = null) {
        this.formulas.set(campoId, {
            formula: formula,
            camposBase: camposBase,
            validacionBiologica: validacionBiologica
        });

        // Registrar dependencias inversas
        camposBase.forEach(campoBase => {
            if (!this.dependencias.has(campoBase)) {
                this.dependencias.set(campoBase, []);
            }
            this.dependencias.get(campoBase).push(campoId);
        });

        // Marcar campo como calculado (inmutable)
        const campoElement = document.getElementById(campoId);
        if (campoElement) {
            campoElement.readOnly = true;
            campoElement.classList.add('campo-calculado');
            campoElement.style.backgroundColor = '#f0f0f0';
            campoElement.style.cursor = 'not-allowed';
        }
    }

    /**
     * Obtiene el valor actual de un campo.
     * @param {string} campoId - ID del campo
     * @returns {number|null} - Valor numérico o null
     */
    obtenerValor(campoId) {
        const campo = document.getElementById(campoId);
        if (!campo) return null;

        const valor = parseFloat(campo.value);
        return isNaN(valor) ? null : valor;
    }

    /**
     * Reemplaza referencias en la fórmula con valores reales.
     * @param {string} formula - Fórmula con referencias (ej: "GLU * 0.0555")
     * @returns {string} - Fórmula con valores reemplazados
     */
    reemplazarReferencias(formula) {
        let formulaEval = formula;
        
        // Buscar todas las referencias (códigos en mayúsculas)
        const regex = /([A-Z][A-Z0-9_]+)/g;
        const matches = formula.match(regex);
        
        if (matches) {
            matches.forEach(codigo => {
                // Buscar campo por código (data-codigo)
                const campoReferencia = document.querySelector(`[data-codigo="${codigo}"]`);
                if (campoReferencia) {
                    const valor = this.obtenerValor(campoReferencia.id);
                    if (valor !== null) {
                        formulaEval = formulaEval.replace(codigo, valor);
                    } else {
                        // Si falta un valor, la fórmula no se puede calcular
                        throw new Error(`Valor faltante para ${codigo}`);
                    }
                } else {
                    // Intentar buscar por ID que contenga el código
                    const campoPorId = document.getElementById(codigo);
                    if (campoPorId) {
                        const valor = this.obtenerValor(campoPorId.id);
                        if (valor !== null) {
                            formulaEval = formulaEval.replace(codigo, valor);
                        }
                    }
                }
            });
        }
        
        return formulaEval;
    }

    /**
     * Calcula el resultado de una fórmula.
     * @param {string} campoId - ID del campo calculado
     * @returns {number|null} - Resultado calculado o null si hay error
     */
    calcular(campoId) {
        const formulaData = this.formulas.get(campoId);
        if (!formulaData) return null;

        try {
            // Reemplazar referencias con valores
            const formulaEval = this.reemplazarReferencias(formulaData.formula);
            
            // Evaluar fórmula de forma segura
            const resultado = Function('"use strict"; return (' + formulaEval + ')')();
            
            // Validación biológica (Jarvis)
            if (formulaData.validacionBiologica) {
                const validacion = this.validarLogicaBiologica(
                    campoId,
                    resultado,
                    formulaData.validacionBiologica
                );
                
                if (!validacion.valida) {
                    // Bloquear validación y alertar
                    this.bloquearValidacion(campoId, validacion.mensaje);
                    return null;
                }
            }
            
            return resultado;
        } catch (error) {
            console.error(`Error al calcular fórmula para ${campoId}:`, error);
            return null;
        }
    }

    /**
     * Valida si un resultado está dentro de la lógica biológica.
     * @param {string} campoId - ID del campo
     * @param {number} valor - Valor a validar
     * @param {Object} validacionBiologica - {min: number, max: number, mensaje: string}
     * @returns {Object} - {valida: bool, mensaje: string}
     */
    validarLogicaBiologica(campoId, valor, validacionBiologica) {
        const { min, max, mensaje } = validacionBiologica;
        
        if (min !== null && valor < min) {
            return {
                valida: false,
                mensaje: mensaje || `Valor ${valor} por debajo del mínimo biológico (${min})`
            };
        }
        
        if (max !== null && valor > max) {
            return {
                valida: false,
                mensaje: mensaje || `Valor ${valor} por encima del máximo biológico (${max})`
            };
        }
        
        return { valida: true, mensaje: '' };
    }

    /**
     * Bloquea la validación y muestra alerta.
     * @param {string} campoId - ID del campo
     * @param {string} mensaje - Mensaje de alerta
     */
    bloquearValidacion(campoId, mensaje) {
        const campo = document.getElementById(campoId);
        if (!campo) return;

        // Marcar campo con error
        campo.classList.add('error-biologico');
        campo.style.borderColor = '#D9230F';
        campo.style.backgroundColor = '#fff5f5';
        
        // Mostrar alerta
        if (typeof Swal !== 'undefined') {
            Swal.fire({
                icon: 'error',
                title: '⚠️ Validación Bloqueada por PRIS',
                html: `
                    <p><strong>Resultado fuera de lógica biológica:</strong></p>
                    <p>${mensaje}</p>
                    <p class="mt-3"><small>Por favor, revise los valores base antes de validar.</small></p>
                `,
                confirmButtonText: 'Entendido',
                confirmButtonColor: '#D9230F'
            });
        } else {
            alert(`⚠️ PRIS: ${mensaje}`);
        }

        // Deshabilitar botón de validar
        const btnValidar = document.querySelector('[onclick*="validar"]');
        if (btnValidar) {
            btnValidar.disabled = true;
            btnValidar.classList.add('disabled');
        }
    }

    /**
     * Propaga cambios desde un campo base a sus dependientes.
     * @param {string} campoBaseId - ID del campo base que cambió
     */
    propagarCambio(campoBaseId) {
        const dependientes = this.dependencias.get(campoBaseId);
        if (!dependientes) return;

        dependientes.forEach(campoCalculadoId => {
            const resultado = this.calcular(campoCalculadoId);
            if (resultado !== null) {
                const campoCalculado = document.getElementById(campoCalculadoId);
                if (campoCalculado) {
                    campoCalculado.value = resultado.toFixed(2);
                    campoCalculado.dispatchEvent(new Event('input'));
                    
                    // Feedback visual
                    campoCalculado.style.backgroundColor = '#e3f2fd';
                    setTimeout(() => {
                        campoCalculado.style.backgroundColor = '#f0f0f0';
                    }, 500);
                }
            }
        });
    }

    /**
     * Inicializa el motor de cálculo.
     * Configura listeners en todos los campos base.
     */
    inicializar() {
        // Escuchar cambios en campos base
        this.dependencias.forEach((dependientes, campoBaseId) => {
            const campoBase = document.getElementById(campoBaseId);
            if (campoBase) {
                campoBase.addEventListener('input', () => {
                    this.propagarCambio(campoBaseId);
                });
                
                campoBase.addEventListener('blur', () => {
                    this.propagarCambio(campoBaseId);
                });
            }
        });

        // Calcular todos los campos calculados al inicio
        this.formulas.forEach((formulaData, campoId) => {
            const resultado = this.calcular(campoId);
            if (resultado !== null) {
                const campo = document.getElementById(campoId);
                if (campo) {
                    campo.value = resultado.toFixed(2);
                }
            }
        });
    }
}

// Instancia global
window.MotorCalculoFormulas = new MotorCalculoFormulas();

// Auto-inicializar cuando el DOM esté listo
document.addEventListener('DOMContentLoaded', function() {
    if (window.MotorCalculoFormulas) {
        window.MotorCalculoFormulas.inicializar();
    }
});
