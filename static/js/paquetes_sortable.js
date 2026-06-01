/**
 * UX DE PAQUETES (Ordenamiento)
 * REGLA 4: Listas sortables para creación de paquetes con drag-and-drop.
 * 
 * NOTA: Requiere SortableJS (https://sortablejs.github.io/Sortable/)
 * Incluir en el template: <script src="https://cdn.jsdelivr.net/npm/sortablejs@latest/Sortable.min.js"></script>
 */

class GestorPaquetesSortable {
    constructor() {
        this.sortableInstances = new Map();
    }

    /**
     * Inicializa un contenedor sortable para estudios de un paquete.
     * @param {string} contenedorId - ID del contenedor (ul o div)
     * @param {Function} callbackOrdenCambiado - Función a ejecutar cuando cambia el orden
     */
    inicializar(contenedorId, callbackOrdenCambiado = null) {
        const contenedor = document.getElementById(contenedorId);
        if (!contenedor) {
            console.error(`Contenedor ${contenedorId} no encontrado`);
            return;
        }

        // Verificar que SortableJS esté disponible
        if (typeof Sortable === 'undefined') {
            console.error('SortableJS no está cargado. Incluir: <script src="https://cdn.jsdelivr.net/npm/sortablejs@latest/Sortable.min.js"></script>');
            return;
        }

        const sortable = Sortable.create(contenedor, {
            animation: 150,
            handle: '.handle-drag', // Clase CSS para el handle de arrastre
            ghostClass: 'sortable-ghost',
            chosenClass: 'sortable-chosen',
            dragClass: 'sortable-drag',
            onEnd: (evt) => {
                // Actualizar índices de orden
                this.actualizarIndicesOrden(contenedor);
                
                // Ejecutar callback si existe
                if (callbackOrdenCambiado) {
                    callbackOrdenCambiado(contenedor);
                }
                
                // Guardar orden en servidor
                this.guardarOrdenEnServidor(contenedorId);
            }
        });

        this.sortableInstances.set(contenedorId, sortable);
    }

    /**
     * Actualiza los índices de orden en los elementos.
     * @param {HTMLElement} contenedor - Contenedor sortable
     */
    actualizarIndicesOrden(contenedor) {
        const items = contenedor.querySelectorAll('[data-estudio-id]');
        items.forEach((item, index) => {
            // Actualizar atributo data-orden
            item.dataset.orden = index + 1;
            
            // Actualizar número visible
            const numeroElement = item.querySelector('.numero-orden');
            if (numeroElement) {
                numeroElement.textContent = index + 1;
            }
            
            // Actualizar input hidden si existe
            const inputOrden = item.querySelector('input[name*="orden"]');
            if (inputOrden) {
                inputOrden.value = index + 1;
            }
        });
    }

    /**
     * Guarda el orden en el servidor vía AJAX.
     * @param {string} contenedorId - ID del contenedor
     */
    guardarOrdenEnServidor(contenedorId) {
        const contenedor = document.getElementById(contenedorId);
        if (!contenedor) return;

        const items = contenedor.querySelectorAll('[data-estudio-id]');
        const orden = Array.from(items).map((item, index) => ({
            estudio_id: item.dataset.estudioId,
            orden: index + 1
        }));

        // Obtener ID del paquete desde el contenedor
        const paqueteId = contenedor.dataset.paqueteId;
        if (!paqueteId) {
            console.warn('No se encontró paquete_id en el contenedor');
            return;
        }

        fetch(`/api/paquetes/${paqueteId}/actualizar-orden/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': this.getCsrfToken()
            },
            body: JSON.stringify({ orden: orden })
        })
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                // Feedback visual
                this.mostrarNotificacion('Orden actualizado correctamente', 'success');
            } else {
                console.error('Error al guardar orden:', data.mensaje);
                this.mostrarNotificacion('Error al guardar orden', 'error');
            }
        })
        .catch(error => {
            console.error('Error al guardar orden:', error);
            this.mostrarNotificacion('Error de conexión al guardar orden', 'error');
        });
    }

    /**
     * Obtiene el token CSRF.
     * @returns {string} - Token CSRF
     */
    getCsrfToken() {
        const token = document.querySelector('[name=csrfmiddlewaretoken]');
        return token ? token.value : '';
    }

    /**
     * Muestra una notificación.
     * @param {string} mensaje - Mensaje a mostrar
     * @param {string} tipo - Tipo de notificación ('success' o 'error')
     */
    mostrarNotificacion(mensaje, tipo) {
        // Usar SweetAlert2 si está disponible, sino alert simple
        if (typeof Swal !== 'undefined') {
            Swal.fire({
                icon: tipo === 'success' ? 'success' : 'error',
                title: mensaje,
                timer: 2000,
                showConfirmButton: false
            });
        } else {
            // Crear notificación toast simple
            const toast = document.createElement('div');
            toast.className = `alert alert-${tipo === 'success' ? 'success' : 'danger'}`;
            toast.textContent = mensaje;
            toast.style.position = 'fixed';
            toast.style.top = '20px';
            toast.style.right = '20px';
            toast.style.zIndex = '9999';
            document.body.appendChild(toast);
            
            setTimeout(() => {
                toast.remove();
            }, 2000);
        }
    }
}

// Instancia global
window.GestorPaquetesSortable = new GestorPaquetesSortable();

// Auto-inicializar contenedores con clase 'paquete-sortable'
document.addEventListener('DOMContentLoaded', function() {
    document.querySelectorAll('.paquete-sortable').forEach(contenedor => {
        window.GestorPaquetesSortable.inicializar(contenedor.id);
    });
});
