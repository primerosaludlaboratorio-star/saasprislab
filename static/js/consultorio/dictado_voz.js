/**
 * DICTADO POR VOZ PUNTUAL
 * 
 * Funcionalidad: Permite dictar texto en campos específicos usando Web Speech API
 * Uso: Botón de micrófono 🎙️ en cada textarea para activar dictado
 * 
 * Compatible con: Chrome, Edge, Safari (iOS 14.5+)
 */

class DictadoVoz {
    constructor() {
        this.recognition = null;
        this.isListening = false;
        this.currentTextarea = null;
        this.currentButton = null;
        
        this.inicializar();
    }
    
    inicializar() {
        // Verificar soporte del navegador
        if (!('webkitSpeechRecognition' in window) && !('SpeechRecognition' in window)) {
            console.warn('Web Speech API no soportada en este navegador');
            this.deshabilitarBotones();
            return;
        }
        
        // Inicializar Speech Recognition
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        this.recognition = new SpeechRecognition();
        
        // Configuración
        this.recognition.lang = 'es-MX';  // Español de México
        this.recognition.continuous = true;  // Dictado continuo
        this.recognition.interimResults = true;  // Resultados mientras habla
        this.recognition.maxAlternatives = 1;
        
        // Event listeners
        this.recognition.addEventListener('result', (e) => this.onResult(e));
        this.recognition.addEventListener('end', () => this.onEnd());
        this.recognition.addEventListener('error', (e) => this.onError(e));
        this.recognition.addEventListener('start', () => this.onStart());
        
        // Configurar botones de dictado
        this.configurarBotones();
    }
    
    configurarBotones() {
        // Buscar todos los botones de dictado
        const botonesDictado = document.querySelectorAll('.btn-dictado');
        
        botonesDictado.forEach(btn => {
            const targetId = btn.dataset.target;
            const textarea = document.getElementById(targetId);
            
            if (!textarea) {
                console.warn(`Textarea con ID ${targetId} no encontrado`);
                return;
            }
            
            btn.addEventListener('click', () => this.toggleDictado(btn, textarea));
        });
    }
    
    toggleDictado(button, textarea) {
        if (this.isListening) {
            this.detenerDictado();
        } else {
            this.iniciarDictado(button, textarea);
        }
    }
    
    iniciarDictado(button, textarea) {
        try {
            this.currentButton = button;
            this.currentTextarea = textarea;
            
            // Actualizar UI del botón
            button.classList.remove('btn-outline-secondary');
            button.classList.add('btn-danger');
            button.innerHTML = '<i class="fas fa-stop-circle"></i> Detener';
            
            // Agregar indicador visual al textarea
            textarea.classList.add('dictando');
            textarea.placeholder = '🎙️ Escuchando... (Habla ahora)';
            
            // Iniciar reconocimiento
            this.recognition.start();
            this.isListening = true;
            
            this.mostrarNotificacion('Micrófono activado. Puedes hablar...', 'info');
            
        } catch (error) {
            console.error('Error al iniciar dictado:', error);
            this.mostrarError('No se pudo iniciar el dictado');
            this.resetearUI();
        }
    }
    
    detenerDictado() {
        if (this.recognition && this.isListening) {
            this.recognition.stop();
            this.isListening = false;
        }
    }
    
    onStart() {
        console.log('Dictado iniciado');
    }
    
    onResult(event) {
        let finalTranscript = '';
        let interimTranscript = '';
        
        // Procesar resultados
        for (let i = event.resultIndex; i < event.results.length; i++) {
            const transcript = event.results[i][0].transcript;
            
            if (event.results[i].isFinal) {
                finalTranscript += transcript + ' ';
            } else {
                interimTranscript += transcript;
            }
        }
        
        // Actualizar textarea
        if (this.currentTextarea) {
            if (finalTranscript) {
                // Agregar texto final
                const cursorPos = this.currentTextarea.selectionStart;
                const textBefore = this.currentTextarea.value.substring(0, cursorPos);
                const textAfter = this.currentTextarea.value.substring(cursorPos);
                
                this.currentTextarea.value = textBefore + finalTranscript + textAfter;
                
                // Mover cursor al final del texto agregado
                const newPos = textBefore.length + finalTranscript.length;
                this.currentTextarea.setSelectionRange(newPos, newPos);
                
                // Trigger change event para frameworks
                this.currentTextarea.dispatchEvent(new Event('input', { bubbles: true }));
            }
            
            // Mostrar texto interim (provisional)
            if (interimTranscript && !finalTranscript) {
                this.mostrarInterim(interimTranscript);
            }
        }
    }
    
    mostrarInterim(texto) {
        // Mostrar preview del texto que está reconociendo
        if (this.currentTextarea) {
            const placeholder = this.currentTextarea.placeholder;
            if (!placeholder.includes('🎙️')) return;
            
            this.currentTextarea.placeholder = `🎙️ "${texto}"`;
        }
    }
    
    onEnd() {
        console.log('Dictado finalizado');
        this.resetearUI();
        
        // Reiniciar automáticamente si sigue escuchando
        if (this.isListening) {
            try {
                setTimeout(() => {
                    if (this.isListening) {
                        this.recognition.start();
                    }
                }, 100);
            } catch (error) {
                console.error('Error al reiniciar reconocimiento:', error);
                this.resetearUI();
            }
        }
    }
    
    onError(event) {
        console.error('Error de reconocimiento:', event.error);
        
        let mensaje = 'Error en el dictado';
        
        switch (event.error) {
            case 'no-speech':
                mensaje = 'No se detectó voz. Intenta de nuevo.';
                break;
            case 'audio-capture':
                mensaje = 'No se pudo acceder al micrófono';
                break;
            case 'not-allowed':
                mensaje = 'Permiso de micrófono denegado';
                break;
            case 'network':
                mensaje = 'Error de red. Verifica tu conexión.';
                break;
        }
        
        this.mostrarError(mensaje);
        this.resetearUI();
    }
    
    resetearUI() {
        if (this.currentButton) {
            this.currentButton.classList.remove('btn-danger');
            this.currentButton.classList.add('btn-outline-secondary');
            this.currentButton.innerHTML = '<i class="fas fa-microphone"></i> Dictar';
        }
        
        if (this.currentTextarea) {
            this.currentTextarea.classList.remove('dictando');
            this.currentTextarea.placeholder = this.currentTextarea.dataset.placeholderOriginal || '';
        }
        
        this.isListening = false;
        this.currentButton = null;
        this.currentTextarea = null;
    }
    
    deshabilitarBotones() {
        const botonesDictado = document.querySelectorAll('.btn-dictado');
        botonesDictado.forEach(btn => {
            btn.disabled = true;
            btn.title = 'Dictado no soportado en este navegador';
            btn.innerHTML = '<i class="fas fa-microphone-slash"></i>';
        });
    }
    
    mostrarNotificacion(mensaje, tipo = 'info') {
        if (typeof toastr !== 'undefined') {
            toastr[tipo](mensaje);
        } else {
            console.log(`[${tipo.toUpperCase()}] ${mensaje}`);
        }
    }
    
    mostrarError(mensaje) {
        this.mostrarNotificacion(mensaje, 'error');
    }
}

// Inicializar cuando el DOM esté listo
document.addEventListener('DOMContentLoaded', function() {
    // Guardar placeholders originales
    document.querySelectorAll('.textarea-dictado').forEach(textarea => {
        textarea.dataset.placeholderOriginal = textarea.placeholder;
    });
    
    // Inicializar dictado
    window.dictadoVoz = new DictadoVoz();
});

// Detener dictado si se cierra la página
window.addEventListener('beforeunload', function() {
    if (window.dictadoVoz && window.dictadoVoz.isListening) {
        window.dictadoVoz.detenerDictado();
    }
});

// Atajos de teclado
document.addEventListener('keydown', function(e) {
    // Ctrl + Shift + D = Activar/Desactivar dictado en campo activo
    if (e.ctrlKey && e.shiftKey && e.key === 'D') {
        e.preventDefault();
        
        const activeElement = document.activeElement;
        if (activeElement && activeElement.tagName === 'TEXTAREA') {
            const btn = document.querySelector(`.btn-dictado[data-target="${activeElement.id}"]`);
            if (btn && window.dictadoVoz) {
                btn.click();
            }
        }
    }
});
