/**
 * PRISLAB Main JS — Utilidades globales transversales
 * Módulo: Inicializador de UI, atajos globales, helpers AJAX y toast system.
 */
'use strict';

/* ── 1. CONFIG ──────────────────────────────────────────────────── */
const PRISLAB = window.PRISLAB || {};
PRISLAB.version = '8.3.1';
PRISLAB.debug   = false;

/* ── 2. CSRF HELPER ─────────────────────────────────────────────── */
PRISLAB.getCsrf = function () {
    const meta = document.querySelector('meta[name="csrf-token"]');
    if (meta) return meta.getAttribute('content');
    const cookie = document.cookie.split(';').find(c => c.trim().startsWith('csrftoken='));
    return cookie ? cookie.split('=')[1].trim() : '';
};

/* ── 3. FETCH WRAPPER ───────────────────────────────────────────── */
PRISLAB.post = async function (url, data) {
    const resp = await fetch(url, {
        method : 'POST',
        headers: {
            'Content-Type' : 'application/json',
            'X-CSRFToken'  : PRISLAB.getCsrf(),
        },
        body: JSON.stringify(data),
    });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}: ${url}`);
    return resp.json();
};

/* ── 4. TOAST SYSTEM ────────────────────────────────────────────── */
PRISLAB.toast = function (msg, tipo) {
    tipo = tipo || 'info';
    const colorMap = { success: '#198754', error: '#dc3545', warning: '#fd7e14', info: '#0d6efd' };
    const div = document.createElement('div');
    div.style.cssText = [
        'position:fixed', 'bottom:1.5rem', 'right:1.5rem', 'z-index:9999',
        `background:${colorMap[tipo] || colorMap.info}`, 'color:#fff',
        'padding:.65rem 1.1rem', 'border-radius:.4rem', 'font-size:.85rem',
        'box-shadow:0 4px 12px rgba(0,0,0,.25)', 'max-width:340px',
        'transition:opacity .4s ease',
    ].join(';');
    div.textContent = msg;
    document.body.appendChild(div);
    setTimeout(() => { div.style.opacity = '0'; setTimeout(() => div.remove(), 400); }, 3500);
};

/* ── 5. NÚMERO FORMATEADO (2 decimales, separador local) ─────── */
PRISLAB.fmt = function (n) {
    const num = parseFloat(n);
    if (isNaN(num)) return '—';
    return num.toLocaleString('es-MX', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
};

/* ── 6. DEBOUNCE ────────────────────────────────────────────────── */
PRISLAB.debounce = function (fn, ms) {
    let t;
    return function (...args) {
        clearTimeout(t);
        t = setTimeout(() => fn.apply(this, args), ms || 300);
    };
};

/* ── 7. INICIALIZACIÓN ──────────────────────────────────────────── */
document.addEventListener('DOMContentLoaded', function () {
    // Activar tooltips Bootstrap si existen
    if (typeof bootstrap !== 'undefined' && bootstrap.Tooltip) {
        document.querySelectorAll('[data-bs-toggle="tooltip"]').forEach(el => {
            new bootstrap.Tooltip(el, { trigger: 'hover', placement: el.dataset.bsPlacement || 'top' });
        });
    }

    // Auto-dismiss mensajes Django
    document.querySelectorAll('.alert.auto-dismiss').forEach(el => {
        setTimeout(() => {
            const bsAlert = bootstrap.Alert ? new bootstrap.Alert(el) : null;
            if (bsAlert) bsAlert.close(); else el.remove();
        }, 5000);
    });

    if (PRISLAB.debug) console.log('[PRISLAB] v' + PRISLAB.version + ' inicializado.');
});

window.PRISLAB = PRISLAB;
