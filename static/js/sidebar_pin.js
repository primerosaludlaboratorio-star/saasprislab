/**
 * Sidebar compatibility shim.
 * El comportamiento real del sidebar vive inline en core/templates/includes/sidebar.html
 * y opera en modo click-to-open persistente.
 */
'use strict';

document.addEventListener('DOMContentLoaded', function () {
    try {
        localStorage.removeItem('sidebarPinned');
    } catch (e) {}
    console.log('[SidebarPIN] Shim activo. Control delegado a sidebar.html (click-to-open).');
});
