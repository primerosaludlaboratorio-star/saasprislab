/**
 * Sidebar PIN Fix - Soluciona comportamiento "bailarina" del sidebar
 * Agrega botón para fijar sidebar y reduce sensibilidad al hover
 */
'use strict';

document.addEventListener('DOMContentLoaded', function() {
    const sidebar = document.getElementById('islandSidebar');
    if (!sidebar) return;

    // Crear botón de PIN
    const pinBtn = document.createElement('button');
    pinBtn.id = 'sidebar-pin-btn';
    pinBtn.className = 'sidebar-pin-btn';
    pinBtn.innerHTML = '<i class="fas fa-thumbtack"></i>';
    pinBtn.title = 'Fijar sidebar (Ctrl+Shift+P)';
    sidebar.appendChild(pinBtn);

    // Estado del pin (usar localStorage para persistir)
    let isPinned = localStorage.getItem('sidebarPinned') === 'true';
    let isExpanded = false;
    let mouseLeaveTimer = null;
    const HOVER_DELAY = 800; // ms - tiempo antes de cerrar (menos sensible)

    // Aplicar estado inicial
    updatePinState();

    // Toggle pin al hacer clic
    pinBtn.addEventListener('click', function(e) {
        e.stopPropagation();
        isPinned = !isPinned;
        localStorage.setItem('sidebarPinned', isPinned);
        updatePinState();
    });

    // Atajo de teclado Ctrl+Shift+P
    document.addEventListener('keydown', function(e) {
        if (e.ctrlKey && e.shiftKey && e.key === 'P') {
            e.preventDefault();
            isPinned = !isPinned;
            localStorage.setItem('sidebarPinned', isPinned);
            updatePinState();
        }
    });

    function updatePinState() {
        if (isPinned) {
            sidebar.classList.add('sidebar-pinned');
            pinBtn.classList.add('active');
            pinBtn.innerHTML = '<i class="fas fa-lock"></i>';
            pinBtn.title = 'Desfijar sidebar (Ctrl+Shift+P)';
        } else {
            sidebar.classList.remove('sidebar-pinned');
            pinBtn.classList.remove('active');
            pinBtn.innerHTML = '<i class="fas fa-thumbtack"></i>';
            pinBtn.title = 'Fijar sidebar (Ctrl+Shift+P)';
        }
    }

    // Modificar comportamiento hover para ser menos sensible
    // Solo si no está fijado
    sidebar.addEventListener('mouseenter', function() {
        if (mouseLeaveTimer) {
            clearTimeout(mouseLeaveTimer);
            mouseLeaveTimer = null;
        }
        isExpanded = true;
        sidebar.classList.add('expanded');
    });

    sidebar.addEventListener('mouseleave', function(e) {
        if (isPinned) return; // No cerrar si está fijado
        
        // Delay antes de cerrar (menos sensible)
        mouseLeaveTimer = setTimeout(function() {
            // Verificar si el mouse no volvió al sidebar
            if (!sidebar.matches(':hover')) {
                isExpanded = false;
                sidebar.classList.remove('expanded');
            }
        }, HOVER_DELAY);
    });

    // Mantener abierto cuando se hace clic en un enlace del sidebar
    sidebar.addEventListener('click', function(e) {
        const link = e.target.closest('.prsb-link, .prsb-trigger');
        if (link && isPinned) {
            // Si está fijado, mantener abierto
            e.stopPropagation();
        }
    });

    // Prevenir que se cierre al hacer clic en acordeones
    const triggers = sidebar.querySelectorAll('.prsb-trigger, .prsb-accordion-btn');
    triggers.forEach(function(trigger) {
        trigger.addEventListener('click', function(e) {
            if (isPinned) {
                // No propagar el evento si está fijado
                e.stopPropagation();
            }
        });
    });

    console.log('[SidebarPIN] Inicializado. Estado: ' + (isPinned ? 'FIJADO' : 'hover'));
});
