/**
 * PRIS VOICE COMMANDER - Cliente JavaScript
 * Control por voz con Web Speech API + WebSocket
 */

class PrisVoiceCommander {
    constructor() {
        this.isListening = false;
        this.recognition = null;
        this.websocket = null;
        this.isWebSocketConnected = false;
        
        // Configuración
        this.config = {
            websocketUrl: this.getWebSocketUrl(),
            restFallbackUrl: '/api/voice/process/',
            useWebSocket: true,
            language: 'es-MX',
            continuous: false,  // Un comando a la vez
            interimResults: false,
        };
        
        // Inicializar
        this.init();
    }
    
    /**
     * Inicializa el Voice Commander
     */
    init() {
        // Verificar soporte de Web Speech API
        if (!('webkitSpeechRecognition' in window) && !('SpeechRecognition' in window)) {
            console.error('PRIS Voice: Web Speech API no soportada en este navegador');
            this.showNotification('Tu navegador no soporta reconocimiento de voz', 'error');
            return;
        }
        
        // Inicializar reconocimiento de voz
        this.initSpeechRecognition();
        
        // Crear botón PTT flotante
        this.createPTTButton();
        
        // Conectar WebSocket
        if (this.config.useWebSocket) {
            this.connectWebSocket();
        }
        
        console.log('PRIS Voice Commander inicializado');
    }
    
    /**
     * Inicializa Web Speech Recognition
     */
    initSpeechRecognition() {
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        this.recognition = new SpeechRecognition();
        
        this.recognition.lang = this.config.language;
        this.recognition.continuous = this.config.continuous;
        this.recognition.interimResults = this.config.interimResults;
        this.recognition.maxAlternatives = 1;
        
        // Eventos
        this.recognition.onstart = () => {
            console.log('PRIS Voice: Escuchando...');
            this.isListening = true;
            this.updatePTTButton('listening');
            this.vibrate([200]); // Haptic feedback
        };
        
        this.recognition.onresult = (event) => {
            const transcript = event.results[0][0].transcript;
            console.log('PRIS Voice: Transcripción:', transcript);
            this.processCommand(transcript);
        };
        
        this.recognition.onerror = (event) => {
            console.error('PRIS Voice: Error:', event.error);
            this.isListening = false;
            this.updatePTTButton('idle');
            
            if (event.error === 'no-speech') {
                this.showNotification('No se detectó voz. Intenta de nuevo.', 'warning');
            } else if (event.error === 'not-allowed') {
                this.showNotification('Permiso de micrófono denegado. Habilítalo en configuración del navegador.', 'error');
            } else {
                this.showNotification('Error en reconocimiento de voz', 'error');
            }
        };
        
        this.recognition.onend = () => {
            console.log('PRIS Voice: Reconocimiento finalizado');
            this.isListening = false;
            this.updatePTTButton('idle');
        };
    }
    
    /**
     * Crea el botón PTT flotante
     */
    createPTTButton() {
        // Verificar si ya existe
        if (document.getElementById('pris-voice-ptt')) {
            return;
        }
        
        // Crear HTML del botón
        const pttHtml = `
            <div id="pris-voice-ptt" class="pris-voice-ptt-container" title="Mantén presionado para hablar">
                <button id="pris-voice-ptt-btn" class="pris-voice-ptt-btn">
                    <i class="bi bi-mic-fill"></i>
                </button>
                <div id="pris-voice-status" class="pris-voice-status"></div>
            </div>
        `;
        
        // Agregar al body
        document.body.insertAdjacentHTML('beforeend', pttHtml);
        
        // Obtener referencias
        const button = document.getElementById('pris-voice-ptt-btn');
        
        // Eventos: Press & Hold para móvil, Click para desktop
        let pressTimer;
        
        // Mouse events (desktop)
        button.addEventListener('mousedown', () => {
            this.startListening();
        });
        
        button.addEventListener('mouseup', () => {
            this.stopListening();
        });
        
        // Touch events (móvil) - Press & Hold
        button.addEventListener('touchstart', (e) => {
            e.preventDefault();
            this.startListening();
        });
        
        button.addEventListener('touchend', (e) => {
            e.preventDefault();
            this.stopListening();
        });
        
        // Click simple (alternativa)
        button.addEventListener('click', (e) => {
            e.preventDefault();
            if (!this.isListening) {
                this.startListening();
                // Auto-stop después de 5 segundos
                setTimeout(() => {
                    if (this.isListening) {
                        this.stopListening();
                    }
                }, 5000);
            }
        });
        
        console.log('PRIS Voice: Botón PTT creado');
    }
    
    /**
     * Inicia el reconocimiento de voz
     */
    startListening() {
        if (this.isListening) {
            return;
        }
        
        try {
            this.recognition.start();
        } catch (e) {
            console.error('PRIS Voice: Error al iniciar reconocimiento:', e);
        }
    }
    
    /**
     * Detiene el reconocimiento de voz
     */
    stopListening() {
        if (!this.isListening) {
            return;
        }
        
        try {
            this.recognition.stop();
        } catch (e) {
            console.error('PRIS Voice: Error al detener reconocimiento:', e);
        }
    }
    
    /**
     * Procesa el comando transcrito
     */
    async processCommand(transcript) {
        console.log('PRIS Voice: Procesando comando:', transcript);
        
        // Mostrar "Pensando..."
        this.updatePTTButton('processing');
        this.showNotification('Pensando...', 'info');
        
        // Obtener contexto actual
        const context = this.getCurrentContext();
        
        // Enviar por WebSocket o REST
        if (this.isWebSocketConnected) {
            this.sendViaWebSocket(transcript, context);
        } else {
            await this.sendViaREST(transcript, context);
        }
    }
    
    /**
     * Envía comando por WebSocket
     */
    sendViaWebSocket(transcript, context) {
        if (!this.websocket || this.websocket.readyState !== WebSocket.OPEN) {
            console.warn('PRIS Voice: WebSocket no conectado, usando fallback REST');
            this.sendViaREST(transcript, context);
            return;
        }
        
        this.websocket.send(JSON.stringify({
            type: 'voice_command',
            transcription: transcript,
            url: context.url,
            context: context.screenData
        }));
    }
    
    /**
     * Envía comando por REST (fallback)
     */
    async sendViaREST(transcript, context) {
        try {
            const response = await fetch(this.config.restFallbackUrl, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCsrfToken()
                },
                credentials: 'same-origin',
                body: JSON.stringify({
                    transcription: transcript,
                    url: context.url,
                    context: context.screenData
                })
            });
            
            const data = await response.json();
            
            if (data.status === 'success') {
                this.handleCommandResult(data);
            } else {
                this.showNotification(data.message || 'Error al procesar comando', 'error');
                this.updatePTTButton('idle');
            }
        } catch (error) {
            console.error('PRIS Voice: Error en REST:', error);
            this.showNotification('Error de conexión', 'error');
            this.updatePTTButton('idle');
        }
    }
    
    /**
     * Maneja el resultado del comando
     */
    handleCommandResult(result) {
        console.log('PRIS Voice: Resultado:', result);
        
        this.updatePTTButton('idle');
        
        // Mostrar respuesta
        this.showNotification(result.response, result.blocked ? 'warning' : 'success');
        
        // Si requiere autenticación biométrica
        if (result.requires_auth) {
            this.requestBiometricAuth(result);
            return;
        }
        
        // Si está bloqueado, no ejecutar acción
        if (result.blocked) {
            return;
        }
        
        // Ejecutar acción si hay
        if (result.action) {
            this.executeAction(result.action, result.parameters);
        }
    }
    
    /**
     * Ejecuta la acción correspondiente
     */
    executeAction(action, parameters) {
        console.log('PRIS Voice: Ejecutando acción:', action, parameters);
        
        if (!action) {
            return;
        }
        
        // Si tiene URL, navegar
        if (action.url) {
            window.location.href = action.url;
        }
        
        // Si tiene acción custom, ejecutar
        if (action.accion) {
            this.executeCustomAction(action.accion, parameters);
        }
    }
    
    /**
     * Ejecuta acciones custom
     */
    executeCustomAction(actionName, parameters) {
        switch (actionName) {
            case 'cargar_receta_en_pdv':
                if (parameters.folio) {
                    // Llamar función de PDV (si existe)
                    if (typeof cargarRecetaEnPDV === 'function') {
                        cargarRecetaEnPDV(parameters.folio);
                    } else {
                        window.location.href = `/farmacia/pdv/?receta=${parameters.folio}`;
                    }
                }
                break;
            
            case 'abrir_buscador_pacientes':
                if (typeof abrirBuscadorPacientes === 'function') {
                    abrirBuscadorPacientes(parameters.nombre);
                } else {
                    window.location.href = `/pacientes/?q=${encodeURIComponent(parameters.nombre || '')}`;
                }
                break;
            
            case 'buscar_producto':
                if (parameters.producto) {
                    window.location.href = `/farmacia/productos/?q=${encodeURIComponent(parameters.producto)}`;
                }
                break;
            
            default:
                console.warn('PRIS Voice: Acción no implementada:', actionName);
        }
    }
    
    /**
     * Solicita autenticación biométrica (WebAuthn)
     */
    async requestBiometricAuth(commandResult) {
        console.log('PRIS Voice: Solicitando autenticación biométrica');
        
        // TODO: Implementar WebAuthn real
        // Por ahora, mostrar confirmación simple
        const confirmed = confirm('⚠️ Comando crítico. ¿Confirmas la acción?');
        
        if (confirmed) {
            this.showNotification('Autenticación exitosa', 'success');
            // Ejecutar acción
            if (commandResult.action) {
                this.executeAction(commandResult.action, commandResult.parameters);
            }
        } else {
            this.showNotification('Comando cancelado', 'info');
        }
    }
    
    /**
     * Conecta WebSocket
     */
    connectWebSocket() {
        try {
            this.websocket = new WebSocket(this.config.websocketUrl);
            
            this.websocket.onopen = () => {
                console.log('PRIS Voice: WebSocket conectado');
                this.isWebSocketConnected = true;
            };
            
            this.websocket.onmessage = (event) => {
                const data = JSON.parse(event.data);
                console.log('PRIS Voice: Mensaje WebSocket:', data);
                
                if (data.type === 'command_result') {
                    this.handleCommandResult(data);
                } else if (data.type === 'connection_established') {
                    this.showNotification(data.message, 'success');
                } else if (data.type === 'error') {
                    this.showNotification(data.message, 'error');
                }
            };
            
            this.websocket.onerror = (error) => {
                console.error('PRIS Voice: Error WebSocket:', error);
                this.isWebSocketConnected = false;
            };
            
            this.websocket.onclose = () => {
                console.log('PRIS Voice: WebSocket desconectado');
                this.isWebSocketConnected = false;
                
                // Reintentar conexión después de 5 segundos
                setTimeout(() => {
                    console.log('PRIS Voice: Reintentando conexión WebSocket...');
                    this.connectWebSocket();
                }, 5000);
            };
        } catch (error) {
            console.error('PRIS Voice: Error al crear WebSocket:', error);
            this.isWebSocketConnected = false;
        }
    }
    
    /**
     * Obtiene la URL del WebSocket
     */
    getWebSocketUrl() {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const host = window.location.host;
        return `${protocol}//${host}/ws/voice/commands/`;
    }
    
    /**
     * Obtiene el contexto actual del usuario
     */
    getCurrentContext() {
        const url = window.location.pathname;
        
        // Intentar extraer datos de pantalla relevantes
        let screenData = '';
        
        // Buscar folios, nombres de paciente, etc.
        const folios = document.querySelectorAll('[data-folio], [data-receta]');
        if (folios.length > 0) {
            screenData += `Folios/Recetas en pantalla: ${Array.from(folios).map(el => el.dataset.folio || el.dataset.receta).join(', ')}. `;
        }
        
        // Buscar nombres de pacientes
        const pacientes = document.querySelectorAll('[data-paciente]');
        if (pacientes.length > 0) {
            screenData += `Pacientes: ${Array.from(pacientes).map(el => el.dataset.paciente).join(', ')}. `;
        }
        
        // Agregar título de página
        screenData += `Página: ${document.title}`;
        
        return {
            url: url,
            screenData: screenData
        };
    }
    
    /**
     * Actualiza el estado visual del botón PTT
     */
    updatePTTButton(state) {
        const button = document.getElementById('pris-voice-ptt-btn');
        const statusDiv = document.getElementById('pris-voice-status');
        
        if (!button) return;
        
        // Limpiar clases
        button.classList.remove('listening', 'processing');
        
        // Agregar clase según estado
        if (state === 'listening') {
            button.classList.add('listening');
            statusDiv.textContent = 'Escuchando...';
        } else if (state === 'processing') {
            button.classList.add('processing');
            statusDiv.textContent = 'Pensando...';
        } else {
            statusDiv.textContent = '';
        }
    }
    
    /**
     * Muestra notificación al usuario
     */
    showNotification(message, type = 'info') {
        // Si existe SweetAlert2, usarlo
        if (typeof Swal !== 'undefined') {
            const iconMap = {
                'success': 'success',
                'error': 'error',
                'warning': 'warning',
                'info': 'info'
            };
            
            Swal.fire({
                icon: iconMap[type] || 'info',
                title: message,
                toast: true,
                position: 'top-end',
                showConfirmButton: false,
                timer: 3000,
                timerProgressBar: true
            });
        } else {
            // Fallback: alert nativo
            console.log(`PRIS Voice [${type}]: ${message}`);
            // Opcionalmente crear notificación custom HTML
        }
    }
    
    /**
     * Vibración háptica (móvil)
     */
    vibrate(pattern) {
        if ('vibrate' in navigator) {
            navigator.vibrate(pattern);
        }
    }
    
    /**
     * Obtiene CSRF token
     */
    getCsrfToken() {
        const meta = document.querySelector('meta[name="csrf-token"]');
        if (meta) return meta.content;
        
        const cookie = document.cookie.match(/csrftoken=([^;]+)/);
        if (cookie) return cookie[1];
        
        return '';
    }
}

// Inicializar automáticamente cuando el DOM esté listo
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        window.prisVoice = new PrisVoiceCommander();
    });
} else {
    window.prisVoice = new PrisVoiceCommander();
}
