/**
 * GRABADORA DE SESIÓN MÉDICA (CAJA NEGRA FORENSE)
 * 
 * Funcionalidad: Graba el audio ambiental de toda la consulta médica
 * para protección legal y trazabilidad forense.
 * 
 * Uso: Se activa al iniciar la consulta y se detiene al finalizar.
 * El audio se adjunta automáticamente al guardar la consulta.
 * 
 * Cumple con: NOM-004-SSA3-2012 (Trazabilidad)
 */

class GrabadoraSesion {
    constructor() {
        this.mediaRecorder = null;
        this.audioChunks = [];
        this.stream = null;
        this.audioBlob = null;
        this.startTime = null;
        this.timerInterval = null;
        
        // Elementos del DOM
        this.btnGrabar = document.getElementById('btnGrabarSesion');
        this.btnDetener = document.getElementById('btnDetenerSesion');
        this.estadoGrabacion = document.getElementById('estadoGrabacion');
        this.tiempoGrabacion = document.getElementById('tiempoGrabacion');
        this.audioPreview = document.getElementById('audioPreview');
        this.audioHiddenInput = document.getElementById('audioSesionInput');
        
        this.inicializar();
    }
    
    inicializar() {
        if (!this.btnGrabar || !this.btnDetener) {
            console.warn('Elementos de grabación no encontrados en el DOM');
            return;
        }
        
        // Event listeners
        this.btnGrabar.addEventListener('click', () => this.iniciarGrabacion());
        this.btnDetener.addEventListener('click', () => this.detenerGrabacion());
        
        // Verificar soporte del navegador
        if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
            this.mostrarError('Tu navegador no soporta grabación de audio');
            this.btnGrabar.disabled = true;
        }
    }
    
    async iniciarGrabacion() {
        try {
            // Solicitar permiso de micrófono
            this.stream = await navigator.mediaDevices.getUserMedia({ 
                audio: {
                    echoCancellation: true,
                    noiseSuppression: true,
                    sampleRate: 44100
                } 
            });
            
            // Configurar MediaRecorder
            const options = { mimeType: 'audio/webm' };
            this.mediaRecorder = new MediaRecorder(this.stream, options);
            
            this.audioChunks = [];
            
            // Evento: datos disponibles
            this.mediaRecorder.addEventListener('dataavailable', event => {
                if (event.data.size > 0) {
                    this.audioChunks.push(event.data);
                }
            });
            
            // Evento: grabación detenida
            this.mediaRecorder.addEventListener('stop', () => {
                this.procesarAudio();
            });
            
            // Iniciar grabación
            this.mediaRecorder.start();
            this.startTime = new Date();
            
            // Actualizar UI
            this.btnGrabar.classList.add('d-none');
            this.btnDetener.classList.remove('d-none');
            this.estadoGrabacion.innerHTML = '<span class="badge bg-danger"><i class="fas fa-circle"></i> GRABANDO</span>';
            
            // Iniciar timer
            this.iniciarTimer();
            
            // Notificación
            this.mostrarNotificacion('Grabación iniciada', 'success');
            
        } catch (error) {
            console.error('Error al iniciar grabación:', error);
            this.mostrarError('No se pudo acceder al micrófono. Verifica los permisos.');
        }
    }
    
    detenerGrabacion() {
        if (this.mediaRecorder && this.mediaRecorder.state !== 'inactive') {
            this.mediaRecorder.stop();
            
            // Detener stream
            if (this.stream) {
                this.stream.getTracks().forEach(track => track.stop());
            }
            
            // Detener timer
            if (this.timerInterval) {
                clearInterval(this.timerInterval);
            }
            
            // Actualizar UI
            this.btnGrabar.classList.remove('d-none');
            this.btnDetener.classList.add('d-none');
            this.estadoGrabacion.innerHTML = '<span class="badge bg-success"><i class="fas fa-check"></i> GRABACIÓN COMPLETADA</span>';
            
            this.mostrarNotificacion('Grabación detenida', 'info');
        }
    }
    
    procesarAudio() {
        // Crear blob de audio
        this.audioBlob = new Blob(this.audioChunks, { type: 'audio/webm' });
        
        // Mostrar preview
        if (this.audioPreview) {
            const audioURL = URL.createObjectURL(this.audioBlob);
            this.audioPreview.src = audioURL;
            this.audioPreview.classList.remove('d-none');
        }
        
        // Preparar para envío
        this.prepararEnvio();
        
        console.log('Audio procesado:', {
            tamaño: this.audioBlob.size,
            tipo: this.audioBlob.type,
            duración: this.calcularDuracion()
        });
    }
    
    prepararEnvio() {
        // Crear DataTransfer para adjuntar al input file
        const dataTransfer = new DataTransfer();
        const file = new File([this.audioBlob], `consulta_${Date.now()}.webm`, { 
            type: 'audio/webm' 
        });
        dataTransfer.items.add(file);
        
        if (this.audioHiddenInput) {
            this.audioHiddenInput.files = dataTransfer.files;
        }
        
        // Agregar metadatos al formulario
        this.agregarMetadatos();
    }
    
    agregarMetadatos() {
        const form = this.btnGrabar.closest('form');
        if (!form) return;
        
        // Crear inputs hidden con metadatos
        const metadatos = [
            { name: 'audio_duracion_segundos', value: this.calcularDuracion() },
            { name: 'audio_timestamp_inicio', value: this.startTime ? this.startTime.toISOString() : '' },
            { name: 'audio_timestamp_fin', value: new Date().toISOString() },
            { name: 'audio_tamano_bytes', value: this.audioBlob.size },
            { name: 'audio_formato', value: 'webm' }
        ];
        
        metadatos.forEach(meta => {
            let input = form.querySelector(`input[name="${meta.name}"]`);
            if (!input) {
                input = document.createElement('input');
                input.type = 'hidden';
                input.name = meta.name;
                form.appendChild(input);
            }
            input.value = meta.value;
        });
    }
    
    iniciarTimer() {
        this.timerInterval = setInterval(() => {
            const elapsed = Math.floor((new Date() - this.startTime) / 1000);
            const minutos = Math.floor(elapsed / 60);
            const segundos = elapsed % 60;
            
            if (this.tiempoGrabacion) {
                this.tiempoGrabacion.textContent = `${minutos.toString().padStart(2, '0')}:${segundos.toString().padStart(2, '0')}`;
            }
        }, 1000);
    }
    
    calcularDuracion() {
        if (!this.startTime) return 0;
        return Math.floor((new Date() - this.startTime) / 1000);
    }
    
    mostrarNotificacion(mensaje, tipo = 'info') {
        // Usar toastr si está disponible
        if (typeof toastr !== 'undefined') {
            toastr[tipo](mensaje);
        } else {
            console.log(`[${tipo.toUpperCase()}] ${mensaje}`);
        }
    }
    
    mostrarError(mensaje) {
        this.mostrarNotificacion(mensaje, 'error');
        if (this.estadoGrabacion) {
            this.estadoGrabacion.innerHTML = `<span class="badge bg-danger"><i class="fas fa-exclamation-triangle"></i> ERROR</span>`;
        }
    }
}

// Inicializar cuando el DOM esté listo
document.addEventListener('DOMContentLoaded', function() {
    // Solo inicializar si estamos en la página de consulta
    if (document.getElementById('btnGrabarSesion')) {
        window.grabadoraSesion = new GrabadoraSesion();
    }
});

// Advertencia si el usuario intenta salir con grabación activa
window.addEventListener('beforeunload', function(e) {
    if (window.grabadoraSesion && 
        window.grabadoraSesion.mediaRecorder && 
        window.grabadoraSesion.mediaRecorder.state === 'recording') {
        e.preventDefault();
        e.returnValue = '¿Estás seguro? Hay una grabación en curso que se perderá.';
        return e.returnValue;
    }
});
