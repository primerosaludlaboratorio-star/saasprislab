/**
 * LABORATORIO_AI.JS - CEREBRO INTELIGENTE DE CAPTURA
 * Validación en tiempo real, alertas de pánico, navegación por teclado
 */

/**
 * FUNCIÓN MAESTRA: VALIDAR INPUT EN TIEMPO REAL
 */
function validarInput(input) {
    const valor = parseFloat(input.value);
    
    // Si no hay valor, resetear
    if (!input.value || isNaN(valor)) {
        input.classList.remove('valor-normal', 'valor-alerta', 'valor-critico');
        const iconoId = 'status_' + input.dataset.parametroId;
        const icono = document.getElementById(iconoId) || document.getElementById('icono_' + input.dataset.parametroId);
        if (icono) {
            icono.innerHTML = '<i class="far fa-circle text-muted"></i>';
        }
        return;
    }
    
    // Obtener rangos
    const min = parseFloat(input.dataset.min);
    const max = parseFloat(input.dataset.max);
    const panicoMin = parseFloat(input.dataset.panicoMin);
    const panicoMax = parseFloat(input.dataset.panicoMax);
    const colorAlerta = input.dataset.colorAlerta || '#DC3545';
    const mensajeAlerta = input.dataset.mensajeAlerta || '¡VALOR CRITICO DETECTADO!';
    
    const iconoId = 'status_' + input.dataset.parametroId;
    const icono = document.getElementById(iconoId) || document.getElementById('icono_' + input.dataset.parametroId);
    
    // LÓGICA DE SEMÁFORO
    
    // 1. PÁNICO (Máxima prioridad)
    if ((!isNaN(panicoMin) && valor < panicoMin) || (!isNaN(panicoMax) && valor > panicoMax)) {
        input.classList.remove('valor-normal', 'valor-alerta');
        input.classList.add('valor-critico');
        
        // Cambiar color de borde al color personalizado
        input.style.borderColor = colorAlerta;
        input.style.background = colorAlerta + '22'; // 22 = 13% opacity
        
        // Icono de pánico
        if (icono) {
            icono.innerHTML = '<i class="fas fa-skull-crossbones text-danger"></i>';
        }
        
        // Construir rango de pánico para mostrar
        let rangoPanico = '';
        if (!isNaN(panicoMin) && !isNaN(panicoMax)) {
            rangoPanico = `< ${panicoMin} o > ${panicoMax}`;
        } else if (!isNaN(panicoMin)) {
            rangoPanico = `< ${panicoMin}`;
        } else if (!isNaN(panicoMax)) {
            rangoPanico = `> ${panicoMax}`;
        }
        
        // POPUP DE ALERTA CRÍTICA + MODAL DE NOTIFICACIÓN AUTOMÁTICO
        Swal.fire({
            icon: 'error',
            title: '⚠️ VALOR CRÍTICO DETECTADO',
            html: `<strong>${input.dataset.parametroNombre}:</strong> ${valor}<br>
                   <strong>Rango de Pánico:</strong> ${rangoPanico}<br><br>
                   <div class="alert alert-warning">
                       <strong>ISO 15189:</strong> Este valor requiere notificación inmediata al médico tratante.
                   </div>`,
            confirmButtonText: 'Registrar Notificación Ahora',
            cancelButtonText: 'Recordar Más Tarde',
            showCancelButton: true,
            confirmButtonColor: '#dc3545',
            cancelButtonColor: '#6c757d',
            backdrop: true,
            allowOutsideClick: false
        }).then((result) => {
            if (result.isConfirmed) {
                // Abrir modal de notificación
                abrirModalPanico(
                    input.dataset.parametroId,
                    input.dataset.parametroNombre,
                    valor,
                    rangoPanico
                );
            }
        });
        
        return;
    }
    
    // 2. FUERA DE RANGO NORMAL (pero no crítico)
    if ((!isNaN(min) && valor < min) || (!isNaN(max) && valor > max)) {
        input.classList.remove('valor-normal', 'valor-critico');
        input.classList.add('valor-alerta');
        
        if (icono) {
            icono.innerHTML = '<i class="fas fa-exclamation-triangle text-warning"></i>';
        }
        
        return;
    }
    
    // 3. VALOR NORMAL
    input.classList.remove('valor-alerta', 'valor-critico');
    input.classList.add('valor-normal');
    
    if (icono) {
        icono.innerHTML = '<i class="fas fa-check-circle text-success"></i>';
    }
}

/**
 * NAVEGACIÓN CON TECLADO (ENTER para siguiente)
 */
function navegarSiguiente(inputActual) {
    const inputs = Array.from(document.querySelectorAll('.result-input'));
    const indexActual = inputs.indexOf(inputActual);
    
    if (indexActual >= 0 && indexActual < inputs.length - 1) {
        inputs[indexActual + 1].focus();
        inputs[indexActual + 1].select();
    }
}

/**
 * VALIDAR TODOS LOS INPUTS
 */
function validarTodos() {
    let hayErrores = false;
    let valoresTotales = 0;
    let valoresCriticos = 0;
    
    document.querySelectorAll('.result-input[type="number"]').forEach(input => {
        if (input.value) {
            valoresTotales++;
            validarInput(input);
            
            if (input.classList.contains('valor-critico')) {
                valoresCriticos++;
                hayErrores = true;
            }
        }
    });
    
    if (valoresTotales === 0) {
        Swal.fire({
            icon: 'warning',
            title: 'Sin Resultados',
            text: 'No hay valores capturados para validar.',
            confirmButtonColor: '#3085d6'
        });
        return;
    }
    
    if (hayErrores) {
        Swal.fire({
            icon: 'error',
            title: `${valoresCriticos} Valores Críticos Detectados`,
            text: 'Revisa los valores marcados en rojo. Requieren atención inmediata.',
            confirmButtonColor: '#ef4444'
        });
    } else {
        Swal.fire({
            icon: 'success',
            title: 'Validación Completa',
            text: `${valoresTotales} valores validados correctamente.`,
            confirmButtonColor: '#10b981'
        });
    }
}

/**
 * DETECCIÓN DE CAMBIOS (para modal de confirmación)
 */
document.addEventListener('DOMContentLoaded', function() {
    document.querySelectorAll('.result-input').forEach(input => {
        const valorAnterior = input.dataset.valorAnterior;
        
        if (valorAnterior) {
            input.addEventListener('change', function() {
                const valorNuevo = this.value;
                
                if (valorAnterior !== valorNuevo && valorNuevo) {
                    mostrarModalCambio(input, valorAnterior, valorNuevo);
                }
            });
        }
    });
});

/**
 * MOSTRAR MODAL DE CONFIRMACIÓN DE CAMBIO
 */
function mostrarModalCambio(input, valorAnterior, valorNuevo) {
    const elValorAnterior = document.getElementById('valor-anterior');
    const elValorNuevo = document.getElementById('valor-nuevo');
    const elParametroId = document.getElementById('parametro-id-cambio');
    const elModal = document.getElementById('modalCambioValor');
    if (elValorAnterior) elValorAnterior.textContent = valorAnterior;
    if (elValorNuevo) elValorNuevo.textContent = valorNuevo;
    if (elParametroId) elParametroId.value = input && input.dataset ? input.dataset.parametroId : '';
    if (elModal && typeof bootstrap !== 'undefined') {
        const modal = new bootstrap.Modal(elModal);
        modal.show();
    }
}

/**
 * CONFIRMAR CAMBIO Y AGREGAR RAZÓN AL FORMULARIO
 */
function confirmarCambio() {
    const elParametroId = document.getElementById('parametro-id-cambio');
    const elRazon = document.getElementById('razon-cambio');
    const parametroId = elParametroId ? elParametroId.value : '';
    const razon = elRazon ? elRazon.value : '';
    
    if (!razon.trim()) {
        Swal.fire({
            icon: 'warning',
            title: 'Razón Requerida',
            text: 'Debe proporcionar una razón para el cambio.',
            confirmButtonColor: '#3085d6'
        });
        return;
    }
    
    // Agregar campo oculto con la razón
    const form = document.getElementById('form-captura');
    if (form) {
        const inputRazon = document.createElement('input');
        inputRazon.type = 'hidden';
        inputRazon.name = `razon_${parametroId}`;
        inputRazon.value = razon;
        form.appendChild(inputRazon);
    }
    
    // Cerrar modal
    const modalEl = document.getElementById('modalCambioValor');
    if (modalEl && typeof bootstrap !== 'undefined') {
        const inst = bootstrap.Modal.getInstance(modalEl);
        if (inst) inst.hide();
    }
    
    // Limpiar textarea para próximo uso
    if (elRazon) elRazon.value = '';
    
    Swal.fire({
        icon: 'success',
        title: 'Cambio Registrado',
        text: 'El cambio quedará registrado en el historial.',
        timer: 2000,
        showConfirmButton: false
    });
}

/**
 * ACTIVAR DICTADO POR VOZ (SIMULACIÓN)
 */
function activarDictado() {
    Swal.fire({
        icon: 'info',
        title: 'Dictado por Voz',
        html: `
            <p><strong>Función en desarrollo</strong></p>
            <p>Próximamente podrás dictar:</p>
            <code>"Glucosa 150"</code><br>
            <code>"Hemoglobina 13.5"</code>
            <p class="mt-2"><small>El sistema buscará el parámetro y llenará el valor automáticamente.</small></p>
        `,
        confirmButtonText: 'Entendido',
        confirmButtonColor: '#667eea'
    });
}

/**
 * ACTIVAR OCR (SIMULACIÓN)
 */
function activarOCR() {
    Swal.fire({
        icon: 'info',
        title: 'Escanear Reporte (OCR)',
        html: `
            <p><strong>Función en desarrollo</strong></p>
            <p>Podrás fotografiar un reporte físico y el sistema extraerá los valores automáticamente.</p>
            <p class="mt-2"><small>Tecnología: Tesseract.js + Google Vision API</small></p>
        `,
        confirmButtonText: 'Entendido',
        confirmButtonColor: '#667eea'
    });
}

/**
 * AUTOGUARDADO (opcional, cada 2 minutos)
 */
let autoguardadoInterval = null;

function iniciarAutoguardado() {
    autoguardadoInterval = setInterval(() => {
        const datosCapturados = {};
        let hayDatos = false;
        
        document.querySelectorAll('.result-input').forEach(input => {
            if (input.value) {
                datosCapturados[input.dataset.parametroId] = input.value;
                hayDatos = true;
            }
        });
        
        if (hayDatos) {
            localStorage.setItem('captura_lab_backup', JSON.stringify(datosCapturados));
        }
    }, 120000); // Cada 2 minutos
}

/**
 * RESTAURAR DESDE AUTOGUARDADO
 */
function restaurarAutoguardado() {
    const backup = localStorage.getItem('captura_lab_backup');
    
    if (backup) {
        const datos = JSON.parse(backup);
        let restaurados = 0;
        
        Object.keys(datos).forEach(parametroId => {
            const input = document.querySelector(`input[data-parametro-id="${parametroId}"]`);
            if (input && !input.value) {
                input.value = datos[parametroId];
                validarInput(input);
                restaurados++;
            }
        });
        
        if (restaurados > 0) {
            Swal.fire({
                icon: 'info',
                title: 'Sesión Restaurada',
                text: `Se restauraron ${restaurados} valores de una sesión anterior.`,
                confirmButtonColor: '#3085d6'
            });
        }
    }
}

// Iniciar autoguardado al cargar
document.addEventListener('DOMContentLoaded', function() {
    iniciarAutoguardado();
    restaurarAutoguardado();
});

// Limpiar backup al guardar exitosamente (solo si este template tiene el form)
document.addEventListener('DOMContentLoaded', function() {
    var formCaptura = document.getElementById('form-captura');
    if (formCaptura) {
        formCaptura.addEventListener('submit', function() {
            localStorage.removeItem('captura_lab_backup');
        });
    }
});
