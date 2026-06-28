/**
 * TRAZABILIDAD LEGAL (Consentimientos)
 * REGLA: Ninguna orden puede pasar a 'Validada' sin el check de firma de consentimiento.
 * Flujo: expediente.firmaconsentimiento.js
 */

class GestorFirmaConsentimiento {
    constructor() {
        this.canvas = null;
        this.ctx = null;
        this.dibujando = false;
        this.firmaBase64 = null;
    }

    /**
     * Inicializa el canvas de firma.
     * @param {string} canvasId - ID del elemento canvas
     */
    inicializarCanvas(canvasId) {
        this.canvas = document.getElementById(canvasId);
        if (!this.canvas) {
            console.error(`Canvas ${canvasId} no encontrado`);
            return;
        }

        this.ctx = this.canvas.getContext('2d');
        this.ctx.strokeStyle = '#000000';
        this.ctx.lineWidth = 2;
        this.ctx.lineCap = 'round';
        this.ctx.lineJoin = 'round';

        // Eventos de mouse
        this.canvas.addEventListener('mousedown', (e) => this.iniciarDibujo(e));
        this.canvas.addEventListener('mousemove', (e) => this.dibujar(e));
        this.canvas.addEventListener('mouseup', () => this.finalizarDibujo());
        this.canvas.addEventListener('mouseout', () => this.finalizarDibujo());

        // Eventos táctiles (móvil)
        this.canvas.addEventListener('touchstart', (e) => {
            e.preventDefault();
            const touch = e.touches[0];
            const mouseEvent = new MouseEvent('mousedown', {
                clientX: touch.clientX,
                clientY: touch.clientY
            });
            this.canvas.dispatchEvent(mouseEvent);
        });

        this.canvas.addEventListener('touchmove', (e) => {
            e.preventDefault();
            const touch = e.touches[0];
            const mouseEvent = new MouseEvent('mousemove', {
                clientX: touch.clientX,
                clientY: touch.clientY
            });
            this.canvas.dispatchEvent(mouseEvent);
        });

        this.canvas.addEventListener('touchend', (e) => {
            e.preventDefault();
            const mouseEvent = new MouseEvent('mouseup', {});
            this.canvas.dispatchEvent(mouseEvent);
        });
    }

    /**
     * Inicia el dibujo de la firma.
     */
    iniciarDibujo(e) {
        this.dibujando = true;
        const rect = this.canvas.getBoundingClientRect();
        this.ctx.beginPath();
        this.ctx.moveTo(e.clientX - rect.left, e.clientY - rect.top);
    }

    /**
     * Dibuja la línea de la firma.
     */
    dibujar(e) {
        if (!this.dibujando) return;

        const rect = this.canvas.getBoundingClientRect();
        this.ctx.lineTo(e.clientX - rect.left, e.clientY - rect.top);
        this.ctx.stroke();
    }

    /**
     * Finaliza el dibujo.
     */
    finalizarDibujo() {
        if (this.dibujando) {
            this.dibujando = false;
            this.ctx.beginPath();
            this.guardarFirmaBase64();
        }
    }

    /**
     * Guarda la firma como Base64.
     */
    guardarFirmaBase64() {
        if (this.canvas) {
            this.firmaBase64 = this.canvas.toDataURL('image/png');
            // Disparar evento personalizado
            this.canvas.dispatchEvent(new CustomEvent('firmaCompletada', {
                detail: { firma: this.firmaBase64 }
            }));
        }
    }

    /**
     * Limpia el canvas.
     */
    limpiar() {
        if (this.ctx && this.canvas) {
            this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
            this.firmaBase64 = null;
        }
    }

    /**
     * Obtiene la firma en Base64.
     * @returns {string|null} - Firma en Base64 o null si no hay firma
     */
    obtenerFirma() {
        return this.firmaBase64;
    }

    /**
     * Verifica si hay una firma válida.
     * @returns {boolean} - True si hay firma, False si no
     */
    tieneFirma() {
        if (!this.firmaBase64) return false;
        
        // Verificar que no sea solo el canvas vacío
        // Crear un canvas temporal para verificar
        const img = new Image();
        img.src = this.firmaBase64;
        
        return new Promise((resolve) => {
            img.onload = () => {
                const tempCanvas = document.createElement('canvas');
                tempCanvas.width = img.width;
                tempCanvas.height = img.height;
                const tempCtx = tempCanvas.getContext('2d');
                tempCtx.drawImage(img, 0, 0);
                
                const imageData = tempCtx.getImageData(0, 0, tempCanvas.width, tempCanvas.height);
                const pixels = imageData.data;
                
                // Verificar que haya píxeles no blancos (firma real)
                let tienePixeles = false;
                for (let i = 0; i < pixels.length; i += 4) {
                    const r = pixels[i];
                    const g = pixels[i + 1];
                    const b = pixels[i + 2];
                    // Si no es blanco (255, 255, 255), hay firma
                    if (r < 250 || g < 250 || b < 250) {
                        tienePixeles = true;
                        break;
                    }
                }
                
                resolve(tienePixeles);
            };
            img.onerror = () => resolve(false);
        });
    }
}

/**
 * Función para guardar consentimiento firmado.
 * @param {number} ordenId - ID de la orden
 * @param {string} firmaBase64 - Firma en Base64
 * @param {string} csrfToken - Token CSRF
 * @returns {Promise} - Promesa con la respuesta del servidor
 */
async function guardarConsentimiento(ordenId, firmaBase64, csrfToken) {
    try {
        const response = await fetch(`/api/consentimiento/guardar/${ordenId}/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrfToken
            },
            body: JSON.stringify({
                firma_digital: firmaBase64,
                acepta_privacidad: document.getElementById('acepta_privacidad')?.checked || false,
                acepta_procesamiento: document.getElementById('acepta_procesamiento')?.checked || false
            })
        });

        const data = await response.json();
        return data;
    } catch (error) {
        console.error('Error al guardar consentimiento:', error);
        return { status: 'error', mensaje: 'Error de conexión' };
    }
}

/**
 * Verifica si una orden tiene consentimiento firmado.
 * @param {number} ordenId - ID de la orden
 * @returns {Promise<boolean>} - True si tiene consentimiento, False si no
 */
async function verificarConsentimiento(ordenId) {
    try {
        const response = await fetch(`/api/consentimiento/verificar/${ordenId}/`);
        const data = await response.json();
        return data.tiene_consentimiento === true;
    } catch (error) {
        console.error('Error al verificar consentimiento:', error);
        return false;
    }
}

// Instancia global
window.GestorFirmaConsentimiento = GestorFirmaConsentimiento;
window.guardarConsentimiento = guardarConsentimiento;
window.verificarConsentimiento = verificarConsentimiento;
