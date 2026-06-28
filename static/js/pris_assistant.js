/**
 * PRIS ASSISTANT - El Cerebro del Asistente Virtual
 * Sistema de IA conversacional con comportamiento gimnástico
 * 
 * @author PRISLAB Team
 * @version 1.0.0
 */

class PrisAI {
    constructor() {
        // Estado del asistente
        this.isActive = true;
        this.isDoingAcrobacia = false;
        this.lastMessage = '';
        this.messageHistory = [];
        
        // Elementos del DOM
        this.container = document.getElementById('pris-container');
        this.avatar = document.getElementById('pris-avatar');
        this.bubble = document.getElementById('pris-bubble');
        this.bubbleText = document.getElementById('pris-bubble-text');
        this.closeBtn = document.getElementById('pris-close');
        this.recallBtn = document.getElementById('pris-recall-btn');
        
        // Verificar que los elementos existan
        if (!this.container || !this.avatar || !this.bubble) {
            console.error('❌ Pris Assistant: Elementos del DOM no encontrados');
            return;
        }
        
        // Biblioteca de diálogos
        this.dialogos = {
            bienvenida: [
                "¡Hola! ¿Listo para salvar vidas hoy? 💙",
                "¡Buenos días! Estoy aquí para ayudarte. 🩺",
                "¡Saludos! Soy Pris, tu asistente médica virtual. ✨",
                "¡Hola! Que tengas un excelente día atendiendo pacientes. 💊",
                "¡Bienvenido! ¿En qué puedo asistirte hoy? 🏥"
            ],
            idle: [
                "¿Necesitas ayuda con este módulo? 🤔",
                "Recuerda revisar los signos vitales. 📊",
                "¿Todo bien por aquí? Avísame si necesitas algo. 👋",
                "Estoy monitoreando el sistema. Todo funciona perfecto. ✅",
                "Consejo: Mantén el expediente clínico actualizado. 📋",
                "¿Sabías que puedes usar atajos de teclado? 💡",
                "Mantente hidratado durante tu turno. 💧",
                "La mejor medicina es la prevención. 🛡️"
            ],
            despedida: [
                "Entendido, iré a entrenar un poco. 🤸‍♀️",
                "Te dejo concentrarte. ¡Nos vemos! 👋",
                "Regreso más al rato. ¡Éxito! 💪",
                "Perfecto, me retiro. Estaré por aquí si me necesitas. 😊",
                "¡Nos vemos! Llamame cuando me necesites. 🌟"
            ],
            regreso: [
                "¿Me llamabas? ¡Aquí estoy! 🎉",
                "¡Uf, qué buen entrenamiento! Sigamos. 💪",
                "¡De vuelta! ¿En qué te ayudo? 😄",
                "¡Lista para asistirte nuevamente! 🚀",
                "¡Regresé! ¿Qué necesitas? 💙"
            ],
            postAcrobacia: [
                "¡Me encanta la gimnasia! 🤸‍♀️✨",
                "¡Esa fue una buena pirueta! 🌟",
                "¡Cuerpo sano, mente sana! 💪🧠",
                "¡Ups! Espero no haberte distraído. 😅",
                "La actividad física es importante... ¡incluso para los avatares! 🏃‍♀️",
                "¡10 puntos en la rutina de piso! 🥇",
                "¿Viste eso? ¡Años de entrenamiento! 🎪"
            ],
            consejos: [
                "Tip: Doble clic en el paciente abre su historial completo. 💡",
                "Recuerda: Siempre documenta las alergias. ⚠️",
                "Pro tip: Usa Ctrl+F para buscar rápidamente. 🔍",
                "No olvides: Lavar las manos salva vidas. 🧼",
                "Importante: Verifica la identidad del paciente. 🆔",
                "Consejo: Descansa 5 minutos cada hora. ⏰",
                "Tip de seguridad: No compartas tu contraseña. 🔐"
            ]
        };
        
        // Lista de acrobacias disponibles
        this.acrobacias = [
            'doing-salto-mortal',
            'doing-vuelta-carro',
            'doing-giro-vertical',
            'doing-rondada'
        ];
        
        // Configuración de comportamiento
        this.config = {
            intervaloIdleMessage: 45000, // 45 segundos
            intervaloGimnasia: 60000, // 60 segundos
            probabilidadGimnasia: 0.05, // 5% de probabilidad
            duracionBubble: 8000 // 8 segundos que se muestra el globo
        };
        
        // Inicializar
        this.init();
    }
    
    /**
     * Inicialización del asistente
     */
    init() {
        
        // Mostrar el contenedor
        this.container.classList.add('visible');
        
        // Event listeners
        this.closeBtn.addEventListener('click', () => this.desactivar());
        this.recallBtn.addEventListener('click', () => this.activar());
        this.avatar.addEventListener('click', () => this.onClick());
        
        // Mensaje de bienvenida
        setTimeout(() => {
            this.mostrarMensaje('bienvenida');
        }, 1000);
        
        // Iniciar comportamiento automático
        this.iniciarComportamientoAutomatico();
        
    }
    
    /**
     * Iniciar comportamientos automáticos
     */
    iniciarComportamientoAutomatico() {
        // Mensajes idle aleatorios
        this.idleInterval = setInterval(() => {
            if (this.isActive && !this.isDoingAcrobacia) {
                // 30% de probabilidad de mostrar un mensaje idle
                if (Math.random() < 0.3) {
                    this.mostrarMensaje('idle');
                }
            }
        }, this.config.intervaloIdleMessage);
        
        // Modo gimnasta (acrobacias sorpresa)
        this.gimnasiaInterval = setInterval(() => {
            if (this.isActive && !this.isDoingAcrobacia) {
                if (Math.random() < this.config.probabilidadGimnasia) {
                    this.modoGimnasta();
                }
            }
        }, this.config.intervaloGimnasia);
    }
    
    /**
     * Detener comportamientos automáticos
     */
    detenerComportamientoAutomatico() {
        if (this.idleInterval) clearInterval(this.idleInterval);
        if (this.gimnasiaInterval) clearInterval(this.gimnasiaInterval);
    }
    
    /**
     * Mostrar mensaje en el globo de diálogo
     * @param {string} tipo - Tipo de mensaje (bienvenida, idle, etc.)
     * @param {string} mensajeCustom - Mensaje personalizado (opcional)
     */
    mostrarMensaje(tipo, mensajeCustom = null) {
        let mensaje;
        
        if (mensajeCustom) {
            mensaje = mensajeCustom;
        } else if (this.dialogos[tipo]) {
            mensaje = this.obtenerMensajeAleatorio(this.dialogos[tipo]);
        } else {
            mensaje = "¡Hola! 👋";
        }
        
        // Evitar repetir el mismo mensaje consecutivamente
        if (mensaje === this.lastMessage && !mensajeCustom) {
            mensaje = this.obtenerMensajeAleatorio(this.dialogos[tipo]);
        }
        
        this.lastMessage = mensaje;
        this.messageHistory.push({ tipo, mensaje, timestamp: Date.now() });
        
        // Actualizar texto y mostrar burbuja (null guard por si pris-bubble-text no existe)
        if (this.bubbleText) this.bubbleText.textContent = mensaje;
        this.bubble.classList.add('show');
        this.container.classList.add('pris-hablando');
        
        // Ocultar después de un tiempo
        if (this.bubbleTimeout) clearTimeout(this.bubbleTimeout);
        this.bubbleTimeout = setTimeout(() => {
            this.ocultarMensaje();
        }, this.config.duracionBubble);
    }
    
    /**
     * Ocultar el globo de diálogo
     */
    ocultarMensaje() {
        this.bubble.classList.remove('show');
        this.container.classList.remove('pris-hablando');
    }
    
    /**
     * Obtener mensaje aleatorio de un array
     * @param {Array} mensajes - Array de mensajes
     * @returns {string} Mensaje aleatorio
     */
    obtenerMensajeAleatorio(mensajes) {
        return mensajes[Math.floor(Math.random() * mensajes.length)];
    }
    
    /**
     * Modo Gimnasta - Realizar acrobacia sorpresa
     */
    async modoGimnasta() {
        if (this.isDoingAcrobacia) return;
        
        this.isDoingAcrobacia = true;
        
        // Ocultar globo temporalmente
        this.ocultarMensaje();
        
        // Seleccionar acrobacia aleatoria
        const acrobacia = this.acrobacias[Math.floor(Math.random() * this.acrobacias.length)];
        
        // Aplicar clase de animación
        this.avatar.classList.add(acrobacia);
        
        // Esperar a que termine la animación
        await new Promise(resolve => {
            const onAnimationEnd = () => {
                this.avatar.removeEventListener('animationend', onAnimationEnd);
                resolve();
            };
            this.avatar.addEventListener('animationend', onAnimationEnd);
        });
        
        // Quitar clase de animación
        this.avatar.classList.remove(acrobacia);
        
        // Añadir efecto de aterrizaje
        this.avatar.classList.add('aterrizaje-suave');
        setTimeout(() => {
            this.avatar.classList.remove('aterrizaje-suave');
        }, 600);
        
        // Mostrar mensaje post-acrobacia
        setTimeout(() => {
            this.mostrarMensaje('postAcrobacia');
            this.isDoingAcrobacia = false;
        }, 300);
    }
    
    /**
     * Click en el avatar
     */
    onClick() {
        if (this.isDoingAcrobacia) return;
        
        // Alternar entre consejos y mensajes idle
        const tipo = Math.random() < 0.5 ? 'consejos' : 'idle';
        this.mostrarMensaje(tipo);
    }
    
    /**
     * Desactivar asistente (botón X)
     */
    async desactivar() {
        if (!this.isActive) return;
        
        this.isActive = false;
        
        // Detener comportamientos automáticos
        this.detenerComportamientoAutomatico();
        
        // Mostrar mensaje de despedida
        this.mostrarMensaje('despedida');
        
        // Esperar a que se muestre el mensaje
        await new Promise(resolve => setTimeout(resolve, 2000));
        
        // Fade out del contenedor
        this.container.classList.remove('visible');
        this.container.classList.add('hidden');
        
        // Esperar animación
        await new Promise(resolve => setTimeout(resolve, 500));
        
        // Mostrar botón de recall
        this.recallBtn.classList.add('visible');
        
    }
    
    /**
     * Activar asistente (botón de recall)
     */
    async activar() {
        if (this.isActive) return;
        
        this.isActive = true;
        
        // Ocultar botón de recall
        this.recallBtn.classList.remove('visible');
        
        // Esperar animación
        await new Promise(resolve => setTimeout(resolve, 300));
        
        // Mostrar contenedor
        this.container.classList.remove('hidden');
        this.container.classList.add('visible');
        
        // Esperar a que aparezca
        await new Promise(resolve => setTimeout(resolve, 500));
        
        // Mensaje de regreso
        this.mostrarMensaje('regreso');
        
        // Reiniciar comportamientos automáticos
        this.iniciarComportamientoAutomatico();
        
    }
    
    /**
     * Método público para que otras partes del sistema puedan hacer que Pris hable
     * @param {string} mensaje - Mensaje a mostrar
     */
    decir(mensaje) {
        this.mostrarMensaje(null, mensaje);
    }
    
    /**
     * NUEVO: Consultar al asistente médico con IA (Gemini)
     * @param {string} pregunta - Pregunta del usuario
     * @param {string} contexto - Contexto adicional (opcional)
     * @returns {Promise<string>} Respuesta del asistente
     */
    async consultarAsistenteIA(pregunta, contexto = '') {
        const FETCH_TIMEOUT_MS = 30000;
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), FETCH_TIMEOUT_MS);
        try {
            this.mostrarMensaje(null, '🤔 Déjame consultar eso con mi cerebro IA...');
            
            const response = await fetch('/ia/api/consultar/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken()
                },
                body: JSON.stringify({ pregunta, contexto }),
                signal: controller.signal
            });
            clearTimeout(timeoutId);
            
            const data = await response.json();
            
            if (data.success) {
                this.mostrarMensaje(null, data.respuesta);
                return data.respuesta;
            } else {
                this.mostrarMensaje(null, '❌ Lo siento, no pude procesar esa pregunta.');
                return null;
            }
        } catch (error) {
            clearTimeout(timeoutId);
            if (error.name === 'AbortError') {
                this.mostrarMensaje(null, '❌ La IA tardó demasiado. Intente de nuevo.');
            } else {
                this.mostrarMensaje(null, '❌ Error de conexión con el servidor IA.');
            }
            console.error('Error al consultar asistente IA:', error);
            return null;
        }
    }
    
    /**
     * NUEVO: Analizar síntomas con IA
     * @param {string} sintomas - Descripción de síntomas
     * @param {string} historial - Historial del paciente (opcional)
     * @returns {Promise<Object>} Análisis con diagnósticos probables
     */
    async analizarSintomas(sintomas, historial = '') {
        const FETCH_TIMEOUT_MS = 30000;
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), FETCH_TIMEOUT_MS);
        try {
            this.mostrarMensaje(null, '🔬 Analizando síntomas con IA...');
            
            const response = await fetch('/ia/api/analizar-sintomas/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken()
                },
                body: JSON.stringify({ sintomas, historial }),
                signal: controller.signal
            });
            clearTimeout(timeoutId);
            
            if (response.status === 401 || (response.redirected && response.url && String(response.url).includes('/login'))) {
                this.mostrarMensaje(null, '❌ Sesión expirada. Inicia sesión de nuevo.');
                if (response.redirected) window.location.href = response.url;
                return null;
            }
            
            const data = await response.json();
            
            if (data.success) {
                const analisis = data.analisis;
                const diag = analisis && Array.isArray(analisis.diagnósticos_probables) ? analisis.diagnósticos_probables : [];
                let mensaje = `📋 Análisis completado:\n\n`;
                mensaje += `Diagnósticos probables: ${diag.join(', ') || 'N/A'}\n`;
                mensaje += `Nivel de urgencia: ${(analisis && analisis.nivel_urgencia) || 'N/A'}`;
                
                this.mostrarMensaje(null, mensaje);
                return analisis;
            } else {
                this.mostrarMensaje(null, '❌ No pude analizar los síntomas.');
                return null;
            }
        } catch (error) {
            clearTimeout(timeoutId);
            if (error.name === 'AbortError') {
                this.mostrarMensaje(null, '❌ La IA tardó demasiado. Intente de nuevo.');
            } else {
                this.mostrarMensaje(null, '❌ Error en el análisis de síntomas.');
            }
            console.error('Error al analizar síntomas:', error);
            return null;
        }
    }
    
    /**
     * NUEVO: Verificar interacciones medicamentosas
     * @param {Array<string>} medicamentos - Lista de medicamentos
     * @returns {Promise<Object>} Información sobre interacciones
     */
    async verificarInteracciones(medicamentos) {
        const FETCH_TIMEOUT_MS = 30000;
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), FETCH_TIMEOUT_MS);
        try {
            this.mostrarMensaje(null, '💊 Verificando interacciones medicamentosas...');
            
            const response = await fetch('/ia/api/verificar-interacciones/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken()
                },
                body: JSON.stringify({ medicamentos }),
                signal: controller.signal
            });
            clearTimeout(timeoutId);
            
            const data = await response.json();
            
            if (data.success) {
                const resultado = data.interacciones;
                if (resultado.interacciones_encontradas > 0) {
                    this.mostrarMensaje(null, `⚠️ ${resultado.interacciones_encontradas} interacciones detectadas. Revisa el detalle.`);
                } else {
                    this.mostrarMensaje(null, '✅ No se detectaron interacciones significativas.');
                }
                return resultado;
            } else {
                this.mostrarMensaje(null, '❌ No pude verificar las interacciones.');
                return null;
            }
        } catch (error) {
            clearTimeout(timeoutId);
            if (error.name === 'AbortError') {
                this.mostrarMensaje(null, '❌ La verificación tardó demasiado. Intente de nuevo.');
            } else {
                this.mostrarMensaje(null, '❌ Error en la verificación de interacciones.');
            }
            console.error('Error al verificar interacciones:', error);
            return null;
        }
    }
    
    /**
     * Obtener token CSRF
     * @returns {string} Token CSRF
     */
    getCSRFToken() {
        const name = 'csrftoken';
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }
    
    /**
     * Destruir instancia y limpiar
     */
    destroy() {
        this.detenerComportamientoAutomatico();
    }
}

// Inicializar Pris cuando el DOM esté listo
document.addEventListener('DOMContentLoaded', () => {
    // Verificar que estemos en una página que necesita a Pris
    // (evitar inicializar en login, por ejemplo)
    const body = document.body;
    const isLoginPage = body.classList.contains('login-page') || window.location.pathname.includes('/login');
    
    if (!isLoginPage) {
        // Crear instancia global de Pris
        window.PrisAssistant = new PrisAI();
        
        // Exponer métodos útiles globalmente
        window.pris = {
            // Métodos básicos
            decir: (mensaje) => window.PrisAssistant.decir(mensaje),
            activar: () => window.PrisAssistant.activar(),
            desactivar: () => window.PrisAssistant.desactivar(),
            acrobacia: () => window.PrisAssistant.modoGimnasta(),
            
            // Métodos de IA avanzados
            consultarIA: (pregunta, contexto) => window.PrisAssistant.consultarAsistenteIA(pregunta, contexto),
            analizarSintomas: (sintomas, historial) => window.PrisAssistant.analizarSintomas(sintomas, historial),
            verificarInteracciones: (medicamentos) => window.PrisAssistant.verificarInteracciones(medicamentos)
        };
        
    }
});
