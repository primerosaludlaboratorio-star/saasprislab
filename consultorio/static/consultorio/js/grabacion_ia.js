/**
 * PRISLAB V5 - MOTOR DE DICTADO CLÍNICO INTELIGENTE (SOAP)
 * ==========================================================
 * Sistema de grabación de voz con:
 * - Web Speech API para transcripción en tiempo real
 * - Envío a Gemini para clasificación SOAP automática
 * - Auto-llenado inteligente del formulario
 * - Botón único: el médico habla, la IA clasifica
 *
 * Autor: PRISLAB Team
 * Fecha: 09 de Febrero 2026
 */

class GrabadorConsultaMedica {
    constructor() {
        this.recognition = null;
        this.isRecording = false;
        this.transcripcionCompleta = '';
        this.transcripcionTemporal = '';
        
        // Elementos del DOM
        this.btnGrabar = document.querySelector('.btn-grabar-voz');
        
        // URLs de la API
        this.urlAnalizarTranscripcion = '/consultorio/api/analizar-transcripcion/';
        
        // Inicializar
        this.init();
    }
    
    init() {
        if (!this.btnGrabar) {
            console.warn('[PRISLAB IA] Boton de grabacion no encontrado');
            return;
        }
        
        // Verificar soporte Web Speech API
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        if (!SpeechRecognition) {
            console.warn('[PRISLAB IA] Web Speech API no soportada, usando fallback MediaRecorder');
            this.usarFallbackMediaRecorder();
            return;
        }
        
        // Configurar Web Speech API
        this.recognition = new SpeechRecognition();
        this.recognition.continuous = true;
        this.recognition.interimResults = true;
        this.recognition.lang = 'es-MX';
        this.recognition.maxAlternatives = 1;
        
        // Eventos de reconocimiento
        this.recognition.onresult = (event) => this.onResult(event);
        this.recognition.onerror = (event) => this.onError(event);
        this.recognition.onend = () => this.onEnd();
        
        // Event listener del boton
        this.btnGrabar.addEventListener('click', () => this.toggleGrabacion());
        
    }
    
    /**
     * Fallback: usar MediaRecorder si Web Speech API no esta disponible
     */
    usarFallbackMediaRecorder() {
        this.mediaRecorder = null;
        this.audioChunks = [];
        
        this.btnGrabar.addEventListener('click', () => {
            if (this.isRecording) {
                this.detenerMediaRecorder();
            } else {
                this.iniciarMediaRecorder();
            }
        });
    }
    
    async iniciarMediaRecorder() {
        try {
            const stream = await navigator.mediaDevices.getUserMedia({
                audio: { echoCancellation: true, noiseSuppression: true }
            });
            
            this.audioChunks = [];
            this.mediaRecorder = new MediaRecorder(stream);
            
            this.mediaRecorder.addEventListener('dataavailable', (e) => {
                if (e.data.size > 0) this.audioChunks.push(e.data);
            });
            
            this.mediaRecorder.addEventListener('stop', () => {
                stream.getTracks().forEach(t => t.stop());
                // MediaRecorder no da transcripcion directa
                // Mostramos un campo para que el medico pegue/escriba la transcripcion
                this.mostrarCampoTranscripcionManual();
            });
            
            this.mediaRecorder.start();
            this.isRecording = true;
            this.actualizarUIGrabando();
            this.mostrarNotificacion('Grabando audio... (hable claramente)', 'info');
        } catch (err) {
            this.mostrarError('Error al acceder al microfono: ' + err.message);
        }
    }
    
    detenerMediaRecorder() {
        if (this.mediaRecorder) {
            this.mediaRecorder.stop();
            this.isRecording = false;
            this.actualizarUIDetenido();
        }
    }
    
    mostrarCampoTranscripcionManual() {
        // Si no hay Web Speech, pedimos la transcripcion manual o de otro servicio
        const existente = document.getElementById('modal-transcripcion-manual');
        if (existente) existente.remove();
        
        const modal = document.createElement('div');
        modal.id = 'modal-transcripcion-manual';
        modal.style.cssText = 'position:fixed;top:0;left:0;right:0;bottom:0;background:rgba(0,0,0,0.7);z-index:10000;display:flex;align-items:center;justify-content:center;';
        modal.innerHTML = `
            <div style="background:white;border-radius:12px;padding:2rem;max-width:600px;width:90%;">
                <h5 style="margin-bottom:1rem;"><i class="fas fa-keyboard"></i> Transcripcion de la Consulta</h5>
                <p class="text-muted" style="font-size:0.9rem;">Tu navegador no soporta dictado por voz automatico. 
                Escribe o pega la transcripcion de la consulta y la IA la clasificara automaticamente.</p>
                <textarea id="textarea-transcripcion-manual" class="form-control" rows="8" 
                    placeholder="Escriba aqui lo que el paciente y usted dijeron durante la consulta...&#10;&#10;Ejemplo: Paciente refiere dolor de cabeza desde hace 3 dias, con fiebre de 38.5. A la exploracion se encuentra faringe hiperémica..."></textarea>
                <div class="d-flex gap-2 mt-3">
                    <button type="button" class="btn btn-primary flex-fill" id="btn-enviar-transcripcion">
                        <i class="fas fa-robot me-2"></i>Analizar con IA
                    </button>
                    <button type="button" class="btn btn-secondary" id="btn-cerrar-modal-transcripcion">
                        Cancelar
                    </button>
                </div>
            </div>
        `;
        document.body.appendChild(modal);
        
        const btnCerrar = document.getElementById('btn-cerrar-modal-transcripcion');
        const btnEnviar = document.getElementById('btn-enviar-transcripcion');
        const textareaTrans = document.getElementById('textarea-transcripcion-manual');
        if (btnCerrar) btnCerrar.addEventListener('click', () => modal.remove());
        if (btnEnviar && textareaTrans) btnEnviar.addEventListener('click', () => {
            const texto = textareaTrans.value.trim();
            if (texto) {
                modal.remove();
                this.enviarTranscripcionAGemini(texto);
            }
        });
    }
    
    // =========================================================================
    // WEB SPEECH API: Transcripcion en tiempo real
    // =========================================================================
    
    toggleGrabacion() {
        if (this.isRecording) {
            this.detenerGrabacion();
        } else {
            this.iniciarGrabacion();
        }
    }
    
    iniciarGrabacion() {
        try {
            this.transcripcionCompleta = '';
            this.transcripcionTemporal = '';
            this.recognition.start();
            this.isRecording = true;
            this.actualizarUIGrabando();
            this.mostrarVisorTranscripcion();
            this.mostrarNotificacion('Escuchando... Hable con normalidad', 'info');
        } catch (err) {
            console.error('[PRISLAB IA] Error al iniciar:', err);
            this.mostrarError('Error al iniciar el microfono: ' + err.message);
        }
    }
    
    detenerGrabacion() {
        if (this.recognition && this.isRecording) {
            this.isRecording = false;
            this.recognition.stop();
            this.actualizarUIDetenido();
            
            // Procesar la transcripcion completa
            const textoFinal = this.transcripcionCompleta.trim();
            if (textoFinal.length > 10) {
                this.mostrarNotificacion('Analizando con IA...', 'info', true);
                this.enviarTranscripcionAGemini(textoFinal);
            } else {
                this.mostrarError('La transcripcion es muy corta. Intente de nuevo hablando mas.');
                this.ocultarVisorTranscripcion();
            }
        }
    }
    
    onResult(event) {
        let interimTranscript = '';
        let finalTranscript = '';
        
        for (let i = event.resultIndex; i < event.results.length; i++) {
            const transcript = event.results[i][0].transcript;
            if (event.results[i].isFinal) {
                finalTranscript += transcript + ' ';
            } else {
                interimTranscript += transcript;
            }
        }
        
        if (finalTranscript) {
            this.transcripcionCompleta += finalTranscript;
        }
        
        // Actualizar visor en tiempo real
        this.actualizarVisorTranscripcion(
            this.transcripcionCompleta + interimTranscript
        );
    }
    
    onError(event) {
        console.error('[PRISLAB IA] Error de reconocimiento:', event.error);
        
        if (event.error === 'no-speech') {
            // Silencio, reintentar
            if (this.isRecording) {
                try { this.recognition.start(); } catch(e) {}
            }
            return;
        }
        
        if (event.error === 'not-allowed') {
            this.mostrarError('Permiso de microfono denegado. Active el microfono en la configuracion del navegador.');
        } else if (event.error === 'network') {
            this.mostrarError('Error de red. Verifique su conexion a internet.');
        }
    }
    
    onEnd() {
        // Si aun estamos grabando, reiniciar (Web Speech se detiene cada ~60s)
        if (this.isRecording) {
            try {
                this.recognition.start();
            } catch (e) {
                console.warn('[PRISLAB IA] No se pudo reiniciar:', e);
            }
        }
    }
    
    // =========================================================================
    // VISOR DE TRANSCRIPCION EN TIEMPO REAL
    // =========================================================================
    
    mostrarVisorTranscripcion() {
        let visor = document.getElementById('visor-transcripcion');
        if (!visor) {
            visor = document.createElement('div');
            visor.id = 'visor-transcripcion';
            visor.style.cssText = `
                position: fixed; bottom: 80px; left: 20px; right: 20px;
                max-height: 200px; overflow-y: auto;
                background: rgba(0,0,0,0.85); color: #00ff88;
                padding: 1rem 1.5rem; border-radius: 12px;
                font-family: 'Courier New', monospace; font-size: 0.95rem;
                z-index: 9999; box-shadow: 0 8px 32px rgba(0,0,0,0.3);
                border: 1px solid rgba(0,255,136,0.3);
            `;
            visor.innerHTML = '<div class="d-flex align-items-center"><span class="spinner-grow spinner-grow-sm text-success me-2"></span><span>Escuchando...</span></div>';
            document.body.appendChild(visor);
        }
    }
    
    actualizarVisorTranscripcion(texto) {
        const visor = document.getElementById('visor-transcripcion');
        if (visor && texto) {
            visor.innerHTML = `<small class="text-white-50 d-block mb-1">TRANSCRIPCION EN VIVO:</small>${texto}`;
            visor.scrollTop = visor.scrollHeight;
        }
    }
    
    ocultarVisorTranscripcion() {
        const visor = document.getElementById('visor-transcripcion');
        if (visor) {
            visor.style.transition = 'opacity 0.5s';
            visor.style.opacity = '0';
            setTimeout(() => visor.remove(), 500);
        }
    }
    
    // =========================================================================
    // ENVIO A GEMINI PARA CLASIFICACION SOAP
    // =========================================================================
    
    async enviarTranscripcionAGemini(transcripcion) {
        const FETCH_TIMEOUT_MS = 30000; // 30s — modo supervivencia
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), FETCH_TIMEOUT_MS);
        try {
            this.mostrarNotificacion('La IA esta clasificando los campos SOAP...', 'info', true);
            
            const csrfToken = this.getCSRFToken();
            const response = await fetch(this.urlAnalizarTranscripcion, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrfToken,
                },
                body: JSON.stringify({
                    transcripcion_completa: transcripcion,
                }),
                signal: controller.signal,
            });
            clearTimeout(timeoutId);
            
            if (response.status === 401 || (response.redirected && response.url && String(response.url).includes('/login'))) {
                this.mostrarError('Sesión expirada. Por favor, inicia sesión de nuevo.');
                if (response.redirected) window.location.href = response.url;
                return;
            }
            if (!response.ok) {
                const errText = await response.text();
                try {
                    const errJson = JSON.parse(errText);
                    throw new Error(errJson.error || errJson.mensaje || `Error ${response.status}`);
                } catch (parseErr) {
                    if (parseErr instanceof SyntaxError) throw new Error(`Error del servidor: ${response.status}`);
                    throw parseErr;
                }
            }
            const data = await response.json();
            
            if (data.ok && data.campos_soap) {
                this.autocompletarFormularioSOAP(data.campos_soap);
                this.ocultarVisorTranscripcion();
                this.mostrarNotificacion('Consulta analizada y formulario completado', 'success');
            } else {
                throw new Error(data.error || 'Error al analizar transcripcion');
            }
            
        } catch (error) {
            clearTimeout(timeoutId);
            if (error.name === 'AbortError') {
                this.mostrarError('La IA tardó demasiado en responder. Intente de nuevo o complete los campos manualmente.');
            } else {
                this.mostrarError('Error al procesar con IA: ' + (error.message || 'Sin conexión. Intente más tarde.'));
            }
            console.error('[PRISLAB IA] Error:', error);
            this.ocultarVisorTranscripcion();
        }
    }
    
    // =========================================================================
    // AUTO-LLENADO INTELIGENTE DE FORMULARIO SOAP
    // =========================================================================
    
    autocompletarFormularioSOAP(campos) {
        
        // S - Subjetivo: Motivo de consulta + Padecimiento actual
        const motivoTexto = [
            campos.motivo_consulta || '',
            campos.padecimiento_actual ? '\n\nPadecimiento Actual:\n' + campos.padecimiento_actual : ''
        ].join('').trim();
        
        if (motivoTexto) {
            this.llenarCampo('motivo-consulta', motivoTexto);
        }
        
        // O - Objetivo: Signos vitales detectados
        if (campos.signos_vitales_detectados) {
            const sv = campos.signos_vitales_detectados;
            if (sv.temperatura) this.llenarCampo('temperatura', sv.temperatura);
            if (sv.frecuencia_cardiaca) this.llenarCampo('frecuencia-cardiaca', sv.frecuencia_cardiaca);
            if (sv.presion_arterial) this.llenarCampo('presion-arterial', sv.presion_arterial);
            if (sv.peso) this.llenarCampo('peso', sv.peso);
            if (sv.talla) this.llenarCampo('talla', sv.talla);
            if (sv.saturacion) this.llenarCampo('saturacion', sv.saturacion);
        }
        
        // A - Analisis: Exploracion fisica + Diagnostico
        if (campos.exploracion_fisica) {
            this.llenarCampo('exploracion-fisica', campos.exploracion_fisica);
        }
        
        const diagnosticoTexto = [
            campos.diagnostico_principal || '',
            campos.diagnostico_cie10 ? ` (${campos.diagnostico_cie10})` : '',
            campos.diagnosticos_secundarios ? '\nSecundarios: ' + campos.diagnosticos_secundarios : '',
        ].join('').trim();
        
        if (diagnosticoTexto) {
            this.llenarCampo('diagnostico', diagnosticoTexto);
        }
        
        // P - Plan: Tratamiento + Estudios
        const planTexto = [
            campos.plan_tratamiento || '',
            campos.estudios_solicitados ? '\n\nEstudios Solicitados:\n' + campos.estudios_solicitados : '',
        ].join('').trim();
        
        if (planTexto) {
            this.llenarCampo('tratamiento', planTexto);
        }
        
        // Medicamentos detectados (formato legible para el tratamiento)
        if (campos.medicamentos_detectados && campos.medicamentos_detectados.length > 0) {
            const medTexto = campos.medicamentos_detectados.map((m, i) => {
                return `${i + 1}. ${m.nombre || ''} ${m.dosis || ''}, ${m.via || 'VO'}, ${m.frecuencia || ''} x ${m.duracion || ''}`;
            }).join('\n');
            
            // Agregar al tratamiento existente
            const tratamientoInput = document.getElementById('tratamiento');
            if (tratamientoInput && medTexto) {
                const actual = tratamientoInput.value.trim();
                if (actual && !actual.includes(medTexto.substring(0, 20))) {
                    tratamientoInput.value = actual + '\n\nMedicamentos:\n' + medTexto;
                } else if (!actual) {
                    tratamientoInput.value = medTexto;
                }
                tratamientoInput.dispatchEvent(new Event('input', { bubbles: true }));
            }
        }
        
    }
    
    llenarCampo(id, valor) {
        const campo = document.getElementById(id);
        if (campo && valor) {
            const valorStr = String(valor);
            
            // Si es textarea y ya tiene contenido, no sobreescribir
            if (campo.tagName === 'TEXTAREA' && campo.value.trim()) {
                campo.value = campo.value.trim() + '\n\n[IA] ' + valorStr;
            } else {
                campo.value = valorStr;
            }
            
            // Disparar evento para sincronizar el Gemelo Digital
            campo.dispatchEvent(new Event('input', { bubbles: true }));
            
            // Animacion visual
            campo.classList.add('campo-ia-llenado');
            campo.style.transition = 'background-color 0.5s, border-color 0.5s';
            campo.style.backgroundColor = '#e8f5e9';
            campo.style.borderColor = '#4caf50';
            
            setTimeout(() => {
                campo.style.backgroundColor = '';
                campo.style.borderColor = '';
                campo.classList.remove('campo-ia-llenado');
            }, 3000);
        }
    }
    
    // =========================================================================
    // UI
    // =========================================================================
    
    actualizarUIGrabando() {
        if (!this.btnGrabar) return;
        this.btnGrabar.classList.add('grabando');
        this.btnGrabar.innerHTML = `
            <i class="fas fa-stop-circle me-2" style="animation: pulse 1s infinite;"></i>
            GRABANDO... (Clic para detener y analizar)
            <i class="fas fa-stop-circle ms-2" style="animation: pulse 1s infinite;"></i>
        `;
        this.btnGrabar.style.background = 'linear-gradient(135deg, #e74c3c 0%, #c0392b 100%)';
        this.btnGrabar.style.animation = 'pulse 2s infinite';
    }
    
    actualizarUIDetenido() {
        if (!this.btnGrabar) return;
        this.btnGrabar.classList.remove('grabando');
        this.btnGrabar.innerHTML = `
            <i class="fas fa-microphone me-2"></i>
            GRABAR CONSULTA CON IA
            <i class="fas fa-microphone ms-2"></i>
        `;
        this.btnGrabar.style.background = 'linear-gradient(135deg, #dc3545 0%, #c82333 100%)';
        this.btnGrabar.style.animation = '';
    }
    
    getCSRFToken() {
        const token = document.querySelector('[name=csrfmiddlewaretoken]');
        if (token) return token.value;
        // Fallback: leer de cookie
        const cookies = document.cookie.split(';');
        for (let c of cookies) {
            c = c.trim();
            if (c.startsWith('csrftoken=')) {
                return c.substring('csrftoken='.length);
            }
        }
        return '';
    }
    
    mostrarNotificacion(mensaje, tipo = 'info', loading = false) {
        const notifAnterior = document.querySelector('.notif-grabacion');
        if (notifAnterior) notifAnterior.remove();
        
        const colores = {
            info: '#3498db',
            success: '#27ae60',
            error: '#e74c3c',
        };
        
        const notif = document.createElement('div');
        notif.className = 'notif-grabacion';
        notif.style.cssText = `
            position: fixed; top: 20px; right: 20px;
            padding: 1rem 1.5rem; border-radius: 10px;
            background: ${colores[tipo] || colores.info}; color: white;
            font-weight: 600; font-size: 0.95rem;
            z-index: 10001; box-shadow: 0 4px 20px rgba(0,0,0,0.3);
            display: flex; align-items: center; gap: 0.5rem;
            max-width: 400px; animation: slideIn 0.3s ease;
        `;
        
        if (loading) {
            notif.innerHTML = `<div class="spinner-border spinner-border-sm" role="status"></div> ${mensaje}`;
        } else {
            const icono = tipo === 'success' ? 'check-circle' : tipo === 'error' ? 'exclamation-triangle' : 'info-circle';
            notif.innerHTML = `<i class="fas fa-${icono}"></i> ${mensaje}`;
        }
        
        document.body.appendChild(notif);
        
        if (!loading) {
            setTimeout(() => {
                notif.style.opacity = '0';
                notif.style.transition = 'opacity 0.3s';
                setTimeout(() => notif.remove(), 300);
            }, 4000);
        }
    }
    
    mostrarError(mensaje) {
        this.mostrarNotificacion(mensaje, 'error');
        console.error('[PRISLAB IA]', mensaje);
    }
}

// Inicializar cuando el DOM este listo
document.addEventListener('DOMContentLoaded', function() {
    window.grabadorConsulta = new GrabadorConsultaMedica();
});
