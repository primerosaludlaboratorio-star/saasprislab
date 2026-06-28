/**
 * PRISLAB V5.0 - ASISTENTE DE VOZ CON IA
 * =======================================
 * Fecha: 1 de Febrero de 2026
 * Objetivo: Grabar audio del navegador y enviarlo a Gemini para análisis
 * 
 * CARACTERÍSTICAS:
 * ✅ MediaRecorder API (navegador)
 * ✅ Envío AJAX al servidor
 * ✅ Feedback visual (spinner, animaciones)
 * ✅ Manejo de errores robusto
 * ✅ Reutilizable para múltiples contextos
 */

class VoiceAssistant {
    /**
     * Constructor de la clase VoiceAssistant
     * @param {Object} options - Opciones de configuración
     * @param {string} options.buttonId - ID del botón de grabación
     * @param {string} options.endpoint - URL del endpoint del servidor
     * @param {Function} options.onSuccess - Callback cuando se recibe respuesta exitosa
     * @param {Function} options.onError - Callback cuando hay error
     */
    constructor(options) {
        this.button = document.getElementById(options.buttonId);
        this.endpoint = options.endpoint;
        this.onSuccess = options.onSuccess || this.defaultOnSuccess;
        this.onError = options.onError || this.defaultOnError;
        
        // Estado
        this.isRecording = false;
        this.mediaRecorder = null;
        this.audioChunks = [];
        this.stream = null;
        
        // Elementos de UI
        this.spinner = null;
        this.originalButtonContent = '';
        
        // Inicializar
        this.init();
    }
    
    /**
     * Inicializa el asistente de voz
     */
    init() {
        if (!this.button) {
            console.error('VoiceAssistant: Botón no encontrado');
            return;
        }
        
        // Guardar contenido original del botón
        this.originalButtonContent = this.button.innerHTML;
        
        // Verificar soporte de MediaRecorder
        if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
            console.error('VoiceAssistant: MediaRecorder no soportado en este navegador');
            this.showError('Tu navegador no soporta grabación de audio. Usa Chrome o Edge.');
            this.button.disabled = true;
            return;
        }
        
        // Agregar event listener
        this.button.addEventListener('click', () => this.toggleRecording());
        
        console.log('✓ VoiceAssistant inicializado');
    }
    
    /**
     * Toggle de grabación (iniciar/detener)
     */
    async toggleRecording() {
        if (this.isRecording) {
            this.stopRecording();
        } else {
            await this.startRecording();
        }
    }
    
    /**
     * Inicia la grabación de audio
     */
    async startRecording() {
        try {
            // Solicitar permisos de micrófono
            this.stream = await navigator.mediaDevices.getUserMedia({ 
                audio: {
                    echoCancellation: true,
                    noiseSuppression: true,
                    autoGainControl: true
                } 
            });
            
            // Configurar MediaRecorder
            const options = { mimeType: 'audio/webm' };
            this.mediaRecorder = new MediaRecorder(this.stream, options);
            
            // Limpiar chunks previos
            this.audioChunks = [];
            
            // Event: ondataavailable
            this.mediaRecorder.ondataavailable = (event) => {
                if (event.data.size > 0) {
                    this.audioChunks.push(event.data);
                }
            };
            
            // Event: onstop
            this.mediaRecorder.onstop = () => {
                this.sendAudioToServer();
            };
            
            // Iniciar grabación
            this.mediaRecorder.start();
            this.isRecording = true;
            
            // Actualizar UI
            this.updateUIRecording();
            
            console.log('🎙️ Grabación iniciada');
            
        } catch (error) {
            console.error('Error al iniciar grabación:', error);
            
            if (error.name === 'NotAllowedError') {
                this.showError('Permiso de micrófono denegado. Habilítalo en la configuración del navegador.');
            } else if (error.name === 'NotFoundError') {
                this.showError('No se detectó ningún micrófono. Conecta uno e intenta de nuevo.');
            } else {
                this.showError('Error al acceder al micrófono: ' + error.message);
            }
        }
    }
    
    /**
     * Detiene la grabación de audio
     */
    stopRecording() {
        if (this.mediaRecorder && this.mediaRecorder.state !== 'inactive') {
            this.mediaRecorder.stop();
            this.isRecording = false;
            
            // Detener el stream
            if (this.stream) {
                this.stream.getTracks().forEach(track => track.stop());
            }
            
            console.log('🛑 Grabación detenida');
        }
    }
    
    /**
     * Envía el audio al servidor
     */
    async sendAudioToServer() {
        // Mostrar spinner
        this.updateUIProcessing();
        
        try {
            // Crear blob del audio
            const audioBlob = new Blob(this.audioChunks, { type: 'audio/webm' });
            
            // Validar tamaño
            const sizeInMB = audioBlob.size / (1024 * 1024);
            console.log(`📦 Tamaño del audio: ${sizeInMB.toFixed(2)} MB`);
            
            if (sizeInMB > 10) {
                throw new Error('El audio es demasiado grande (máx. 10 MB). Intenta grabar menos tiempo.');
            }
            
            // Crear FormData
            const formData = new FormData();
            formData.append('audio', audioBlob, 'grabacion.webm');
            
            // Obtener CSRF token
            const csrfToken = this.getCSRFToken();
            
            // Enviar al servidor
            console.log(`📤 Enviando audio a: ${this.endpoint}`);
            
            const response = await fetch(this.endpoint, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': csrfToken
                },
                body: formData
            });
            
            // Verificar respuesta
            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}));
                throw new Error(errorData.error || `Error del servidor: ${response.status}`);
            }
            
            // Parsear JSON
            const data = await response.json();
            
            console.log('✅ Respuesta del servidor:', data);
            
            // Callback de éxito
            this.onSuccess(data);
            
            // Restaurar UI
            this.updateUISuccess();
            
        } catch (error) {
            console.error('❌ Error al enviar audio:', error);
            this.onError(error);
            this.updateUIError();
            this.showError(error.message);
        }
    }
    
    /**
     * Actualiza la UI cuando está grabando
     */
    updateUIRecording() {
        this.button.classList.add('recording-pulse');
        this.button.innerHTML = `
            <i class="fas fa-stop-circle"></i>
            <span class="ms-2">DETENER GRABACIÓN</span>
        `;
        this.button.style.background = 'linear-gradient(135deg, #dc3545 0%, #c82333 100%)';
    }
    
    /**
     * Actualiza la UI cuando está procesando
     */
    updateUIProcessing() {
        this.button.classList.remove('recording-pulse');
        this.button.disabled = true;
        this.button.innerHTML = `
            <div class="spinner-border spinner-border-sm me-2" role="status">
                <span class="visually-hidden">Procesando...</span>
            </div>
            <span>ANALIZANDO CON IA...</span>
        `;
        this.button.style.background = 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)';
    }
    
    /**
     * Actualiza la UI cuando termina con éxito
     */
    updateUISuccess() {
        this.button.innerHTML = `
            <i class="fas fa-check-circle"></i>
            <span class="ms-2">¡LISTO!</span>
        `;
        this.button.style.background = 'linear-gradient(135deg, #28a745 0%, #218838 100%)';
        
        // Restaurar después de 2 segundos
        setTimeout(() => {
            this.resetUI();
        }, 2000);
    }
    
    /**
     * Actualiza la UI cuando hay error
     */
    updateUIError() {
        this.button.innerHTML = `
            <i class="fas fa-exclamation-triangle"></i>
            <span class="ms-2">ERROR</span>
        `;
        this.button.style.background = 'linear-gradient(135deg, #ffc107 0%, #e0a800 100%)';
        
        // Restaurar después de 3 segundos
        setTimeout(() => {
            this.resetUI();
        }, 3000);
    }
    
    /**
     * Restaura la UI al estado original
     */
    resetUI() {
        this.button.disabled = false;
        this.button.innerHTML = this.originalButtonContent;
        this.button.style.background = '';
        this.button.classList.remove('recording-pulse');
    }
    
    /**
     * Obtiene el token CSRF de Django
     */
    getCSRFToken() {
        const cookieValue = document.cookie
            .split('; ')
            .find(row => row.startsWith('csrftoken='))
            ?.split('=')[1];
        
        return cookieValue || '';
    }
    
    /**
     * Muestra un mensaje de error
     */
    showError(message) {
        // Usar el sistema de alertas del sistema si existe
        if (typeof mostrarAlerta === 'function') {
            mostrarAlerta(message, 'danger');
        } else {
            alert(message);
        }
    }
    
    /**
     * Callback por defecto de éxito
     */
    defaultOnSuccess(data) {
        console.log('✅ Audio procesado exitosamente:', data);
    }
    
    /**
     * Callback por defecto de error
     */
    defaultOnError(error) {
        console.error('❌ Error al procesar audio:', error);
    }
}

/**
 * ============================================================================
 * UTILIDADES ADICIONALES
 * ============================================================================
 */

/**
 * Inyecta datos en inputs y dispara eventos
 * @param {string} inputId - ID del input
 * @param {*} value - Valor a inyectar
 * @param {boolean} flashEffect - Aplicar efecto flash
 */
function inyectarValor(inputId, value, flashEffect = true) {
    const input = document.getElementById(inputId);
    
    if (!input) {
        console.warn(`Input no encontrado: ${inputId}`);
        return;
    }
    
    // Inyectar valor
    input.value = value;
    
    // Disparar eventos para que otros scripts lo detecten
    input.dispatchEvent(new Event('input', { bubbles: true }));
    input.dispatchEvent(new Event('change', { bubbles: true }));
    
    // Efecto visual flash
    if (flashEffect) {
        input.classList.add('flash-update');
        setTimeout(() => {
            input.classList.remove('flash-update');
        }, 2000);
    }
    
    console.log(`✓ Valor inyectado en ${inputId}: ${value}`);
}

/**
 * Inyecta múltiples valores desde un objeto
 * @param {Object} dataMap - Mapa de {inputId: valor}
 */
function inyectarMultiplesValores(dataMap) {
    Object.entries(dataMap).forEach(([inputId, value]) => {
        if (value !== null && value !== undefined && value !== '') {
            inyectarValor(inputId, value);
        }
    });
}

/**
 * Busca input por data-keywords y le asigna valor
 * @param {string} keyword - Palabra clave a buscar
 * @param {*} value - Valor a asignar
 */
function inyectarPorKeyword(keyword, value) {
    const inputs = document.querySelectorAll('input[data-keywords]');
    
    for (const input of inputs) {
        const keywords = input.getAttribute('data-keywords').toLowerCase();
        if (keywords.includes(keyword.toLowerCase())) {
            input.value = value;
            input.dispatchEvent(new Event('input', { bubbles: true }));
            input.classList.add('flash-update');
            
            setTimeout(() => {
                input.classList.remove('flash-update');
            }, 2000);
            
            console.log(`✓ Valor inyectado por keyword "${keyword}": ${value}`);
            return true;
        }
    }
    
    console.warn(`No se encontró input con keyword: ${keyword}`);
    return false;
}

/**
 * ============================================================================
 * ESTILOS CSS ADICIONALES (INYECTAR EN HEAD SI NO EXISTEN)
 * ============================================================================
 */

(function inyectarEstilosVoz() {
    const estilos = `
        /* Animación de pulso para botón grabando */
        @keyframes recording-pulse {
            0%, 100% {
                box-shadow: 0 0 0 0 rgba(220, 53, 69, 0.7);
            }
            50% {
                box-shadow: 0 0 0 15px rgba(220, 53, 69, 0);
            }
        }
        
        .recording-pulse {
            animation: recording-pulse 1.5s infinite !important;
        }
        
        /* Efecto flash para inputs actualizados */
        @keyframes flash-update {
            0% {
                background-color: #ffd700;
                transform: scale(1.02);
            }
            100% {
                background-color: white;
                transform: scale(1);
            }
        }
        
        .flash-update {
            animation: flash-update 2s ease-out !important;
        }
    `;
    
    // Verificar si ya existe el estilo
    if (!document.getElementById('voice-assistant-styles')) {
        const styleElement = document.createElement('style');
        styleElement.id = 'voice-assistant-styles';
        styleElement.textContent = estilos;
        document.head.appendChild(styleElement);
    }
})();

/**
 * ============================================================================
 * EXPORT PARA USO EN MÓDULOS
 * ============================================================================
 */

// Si estamos en un entorno de módulos, exportar
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { VoiceAssistant, inyectarValor, inyectarMultiplesValores, inyectarPorKeyword };
}

console.log('📦 VoiceAssistant cargado correctamente');
