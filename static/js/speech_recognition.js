// Speech Recognition para Dictado por Voz
// Compatible con Chrome/Edge (webkitSpeechRecognition)

class SpeechRecognitionHelper {
    constructor() {
        this.recognition = null;
        this.isListening = false;
        this.currentTarget = null;
        
        if ('webkitSpeechRecognition' in window) {
            this.recognition = new webkitSpeechRecognition();
            this.recognition.continuous = false;
            this.recognition.interimResults = false;
            this.recognition.lang = 'es-MX';
            
            this.recognition.onresult = (event) => {
                const transcript = event.results[0][0].transcript;
                if (this.currentTarget) {
                    const currentValue = this.currentTarget.value || '';
                    this.currentTarget.value = currentValue + ' ' + transcript;
                    // Disparar evento input para que otros scripts detecten el cambio
                    this.currentTarget.dispatchEvent(new Event('input', { bubbles: true }));
                }
            };
            
            this.recognition.onerror = (event) => {
                console.error('Error en reconocimiento de voz:', event.error);
                this.stopListening();
            };
            
            this.recognition.onend = () => {
                this.isListening = false;
                this.updateButtonState();
            };
        }
    }
    
    startListening(targetElement) {
        if (!this.recognition) {
            alert('Tu navegador no soporta reconocimiento de voz. Usa Chrome o Edge.');
            return;
        }
        
        if (this.isListening) {
            this.stopListening();
            return;
        }
        
        this.currentTarget = targetElement;
        this.isListening = true;
        this.recognition.start();
        this.updateButtonState();
    }
    
    stopListening() {
        if (this.recognition && this.isListening) {
            this.recognition.stop();
            this.isListening = false;
            this.updateButtonState();
        }
    }
    
    updateButtonState() {
        // Actualizar estado visual de botones
        document.querySelectorAll('.btn-speech-recognition').forEach(btn => {
            if (this.isListening) {
                btn.classList.add('active');
                btn.innerHTML = '<i class="bi bi-mic-fill"></i> Detener';
            } else {
                btn.classList.remove('active');
                btn.innerHTML = '<i class="bi bi-mic"></i> Dictar';
            }
        });
    }
}

// Instancia global
const speechRecognition = new SpeechRecognitionHelper();

// Función helper para agregar botón de dictado a cualquier textarea/input
function addSpeechButtonToField(fieldId) {
    const field = document.getElementById(fieldId);
    if (!field) return;
    
    // Crear botón si no existe
    let btn = field.parentElement.querySelector('.btn-speech-recognition');
    if (!btn) {
        btn = document.createElement('button');
        btn.type = 'button';
        btn.className = 'btn btn-sm btn-outline-info btn-speech-recognition';
        btn.innerHTML = '<i class="bi bi-mic"></i> Dictar';
        btn.style.marginLeft = '5px';
        btn.onclick = () => speechRecognition.startListening(field);
        field.parentElement.style.position = 'relative';
        field.parentElement.appendChild(btn);
    }
}

// Auto-inicializar en campos comunes
document.addEventListener('DOMContentLoaded', function() {
    // Agregar a todos los textareas de resultados y observaciones
    document.querySelectorAll('textarea[name*="resultado"], textarea[name*="observaciones"], textarea[name*="hallazgos"], textarea[name*="conclusion"]').forEach(textarea => {
        if (!textarea.id) {
            textarea.id = 'speech-field-' + Math.random().toString(36).substr(2, 9);
        }
        addSpeechButtonToField(textarea.id);
    });
});
