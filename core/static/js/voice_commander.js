/**
 * PRISLAB Voice Commander (Push-to-Talk)
 * Permite comandos de voz utilizando Web Speech API.
 */

class VoiceCommander {
    constructor(buttonId) {
        this.button = document.getElementById(buttonId);
        this.isRecording = false;
        
        if (!('webkitSpeechRecognition' in window)) {
            console.warn("Speech Recognition API no soportada en este navegador.");
            if(this.button) this.button.style.display = 'none';
            return;
        }

        this.recognition = new webkitSpeechRecognition();
        this.recognition.lang = 'es-MX';
        this.recognition.continuous = false;
        this.recognition.interimResults = false;

        this.initEvents();
    }

    initEvents() {
        if(!this.button) return;

        this.button.addEventListener('mousedown', () => this.startRecording());
        this.button.addEventListener('mouseup', () => this.stopRecording());
        this.button.addEventListener('mouseleave', () => {
            if(this.isRecording) this.stopRecording();
        });

        // Touch support
        this.button.addEventListener('touchstart', (e) => { e.preventDefault(); this.startRecording(); });
        this.button.addEventListener('touchend', (e) => { e.preventDefault(); this.stopRecording(); });

        this.recognition.onresult = (event) => {
            const transcript = event.results[0][0].transcript;
            this.processCommand(transcript);
        };

        this.recognition.onerror = (event) => {
            console.error("Error en reconocimiento de voz:", event.error);
            this.resetButton();
            if(window.prisNotify) window.prisNotify("Error al escuchar el comando.", "warning");
        };
    }

    startRecording() {
        this.isRecording = true;
        this.button.classList.add('recording-active');
        this.button.style.color = '#D9230F';
        this.button.style.transform = 'scale(1.1)';
        try {
            this.recognition.start();
        } catch(e) {} // Evita error si ya estaba escuchando
    }

    stopRecording() {
        this.isRecording = false;
        this.resetButton();
        this.recognition.stop();
    }

    resetButton() {
        this.button.classList.remove('recording-active');
        this.button.style.color = '';
        this.button.style.transform = 'scale(1)';
    }

    processCommand(text) {
        console.log("PRIS IA Comando detectado:", text);
        if(window.prisNotify) {
            window.prisNotify(`Comando detectado: "${text}"`, "info");
        }
        
        // Aquí se enviaría al backend (pris_ai_core/api/voice)
        
        let csrfToken = '';
        const metaCsrf = document.querySelector('meta[name="csrf-token"]');
        if (metaCsrf) {
            csrfToken = metaCsrf.content;
        } else {
            // Fallback para leer cookie csrf si meta no existe
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                if (cookie.startsWith('csrftoken=')) {
                    csrfToken = cookie.substring('csrftoken='.length, cookie.length);
                    break;
                }
            }
        }

        fetch('/ia/api/voice/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrfToken
            },
            body: JSON.stringify({ command: text })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success && data.data && data.data.suggested_action) {
                const action = data.data.suggested_action;
                if (window.prisNotify) {
                    window.prisNotify(`PRIS AI: ${action.message}`, "success");
                }
                
                if (action.type === 'redirect' && action.url_path) {
                    setTimeout(() => {
                        window.location.href = action.url_path;
                    }, 1500);
                }
            } else {
                if (window.prisNotify) window.prisNotify("No entendí el comando. Intenta de nuevo.", "warning");
            }
        })
        .catch(err => {
            console.error(err);
            if (window.prisNotify) window.prisNotify("Error al contactar con la IA.", "danger");
        });
        
    }
}

// Inicializar si existe el botón en la UI
document.addEventListener('DOMContentLoaded', () => {
    // Si queremos inyectar un botón flotante global
    const voiceBtn = document.createElement('button');
    voiceBtn.id = 'prisVoiceBtn';
    voiceBtn.innerHTML = '<i class="bi bi-mic-fill"></i>';
    voiceBtn.style.cssText = 'position:fixed;bottom:30px;right:30px;width:60px;height:60px;border-radius:50%;background:rgba(30,30,30,0.8);backdrop-filter:blur(10px);color:white;border:1px solid rgba(255,255,255,0.2);font-size:24px;box-shadow:0 8px 32px rgba(0,0,0,0.3);z-index:9999;transition:all 0.2s;';
    
    document.body.appendChild(voiceBtn);
    window.prisVoiceCommander = new VoiceCommander('prisVoiceBtn');
});
