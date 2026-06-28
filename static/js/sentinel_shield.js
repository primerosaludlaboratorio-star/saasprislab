/**
 * PRIS SENTINEL SHIELD v1.0 — Escudo Proactivo del Usuario
 * =========================================================
 * Detecta comportamiento anomalo del usuario ANTES de que genere errores:
 *   1. Rage Clicking: >5 clics/segundo en el mismo elemento
 *   2. Form Abuse: datos absurdos en formularios (ej: nombres con solo numeros)
 *   3. Rapid Resubmit: envio repetido del mismo formulario en <2s
 *
 * Cuando se detecta un problema, muestra un modal amable y previene el error
 * en el servidor, reduciendo la carga y mejorando la experiencia del usuario.
 */
(function () {
  'use strict';

  // ══════════════════════════════════════════════════════════════════
  // CONFIG
  // ══════════════════════════════════════════════════════════════════
  const CONFIG = {
    RAGE_CLICK_THRESHOLD: 8,       // clics maximos (mas tolerante)
    RAGE_CLICK_WINDOW_MS: 1500,    // ventana de deteccion (1.5 seg)
    RAGE_COOLDOWN_MS: 2000,        // espera antes de reactivar elemento (reducido)
    FORM_MIN_NAME_LENGTH: 2,       // longitud minima para nombres
    FORM_RESUBMIT_BLOCK_MS: 2000,  // bloqueo de re-envio rapido
    MODAL_DISPLAY_MS: 2500,        // tiempo que se muestra el modal (reducido)
  };

  // ══════════════════════════════════════════════════════════════════
  // STATE
  // ══════════════════════════════════════════════════════════════════
  const clickTracker = new Map();   // element -> [timestamps]
  const formSubmitTracker = new Map(); // form -> last_submit_time
  let modalVisible = false;
  let shieldModal = null;

  // ══════════════════════════════════════════════════════════════════
  // MODAL UI
  // ══════════════════════════════════════════════════════════════════
  function createShieldModal() {
    if (document.getElementById('sentinel-shield-modal')) return;

    const overlay = document.createElement('div');
    overlay.id = 'sentinel-shield-modal';
    overlay.innerHTML = `
      <div style="
        position:fixed; top:0; left:0; width:100%; height:100%;
        background:rgba(0,0,0,0.45); z-index:99999;
        display:flex; align-items:center; justify-content:center;
        opacity:0; transition:opacity 0.3s ease;
      " id="sentinel-shield-overlay">
        <div style="
          background:#fff; border-radius:16px; padding:32px 28px;
          max-width:420px; width:90%; text-align:center;
          box-shadow:0 20px 60px rgba(0,0,0,0.3);
          transform:scale(0.9); transition:transform 0.3s ease;
        " id="sentinel-shield-card">
          <div style="
            width:64px; height:64px; border-radius:50%;
            background:linear-gradient(135deg,#667eea,#764ba2);
            display:flex; align-items:center; justify-content:center;
            margin:0 auto 16px;
          ">
            <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="2">
              <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>
            </svg>
          </div>
          <h5 style="margin:0 0 8px; color:#333; font-weight:700; font-size:1.15rem;" id="sentinel-shield-title">
            Optimizando tu experiencia...
          </h5>
          <p style="margin:0 0 16px; color:#666; font-size:0.92rem; line-height:1.5;" id="sentinel-shield-msg">
            Parece que algo no va como esperabas. Estoy optimizando la ruta para ti...
          </p>
          <div style="
            height:4px; background:#e9ecef; border-radius:4px; overflow:hidden;
          ">
            <div style="
              height:100%; background:linear-gradient(90deg,#667eea,#764ba2);
              width:0%; transition:width ${CONFIG.MODAL_DISPLAY_MS}ms linear;
            " id="sentinel-shield-progress"></div>
          </div>
        </div>
      </div>
    `;
    document.body.appendChild(overlay);
    shieldModal = overlay;
  }

  function showShieldModal(title, message) {
    if (modalVisible) return;
    modalVisible = true;
    createShieldModal();

    const overlay = document.getElementById('sentinel-shield-overlay');
    const card = document.getElementById('sentinel-shield-card');
    const titleEl = document.getElementById('sentinel-shield-title');
    const msgEl = document.getElementById('sentinel-shield-msg');
    const progress = document.getElementById('sentinel-shield-progress');

    titleEl.textContent = title || 'Optimizando tu experiencia...';
    msgEl.textContent = message || 'Estoy trabajando para resolver esto rapidamente.';

    // Animate in
    requestAnimationFrame(() => {
      overlay.style.opacity = '1';
      card.style.transform = 'scale(1)';
      // Start progress bar
      requestAnimationFrame(() => {
        progress.style.width = '100%';
      });
    });

    // Cerrar al hacer click en el overlay (fuera del card)
    overlay.addEventListener('click', function(ev) {
      if (ev.target === overlay) hideShieldModal();
    });

    // Auto-close
    setTimeout(() => {
      hideShieldModal();
    }, CONFIG.MODAL_DISPLAY_MS);
  }

  function hideShieldModal() {
    const overlay = document.getElementById('sentinel-shield-overlay');
    const card = document.getElementById('sentinel-shield-card');
    if (overlay) {
      overlay.style.opacity = '0';
      card.style.transform = 'scale(0.9)';
      setTimeout(() => {
        if (shieldModal && shieldModal.parentNode) {
          shieldModal.parentNode.removeChild(shieldModal);
          shieldModal = null;
        }
        modalVisible = false;
      }, 300);
    } else {
      modalVisible = false;
    }
  }

  // ══════════════════════════════════════════════════════════════════
  // 1. RAGE CLICK DETECTION
  // ══════════════════════════════════════════════════════════════════
  document.addEventListener('click', function (e) {
    const target = e.target;
    const key = target.tagName + '#' + (target.id || '') + '.' + (target.className || '').toString().substring(0, 30);

    if (!clickTracker.has(key)) {
      clickTracker.set(key, []);
    }

    const clicks = clickTracker.get(key);
    const now = Date.now();
    clicks.push(now);

    // Remove clicks outside the detection window
    while (clicks.length > 0 && (now - clicks[0]) > CONFIG.RAGE_CLICK_WINDOW_MS) {
      clicks.shift();
    }

    if (clicks.length >= CONFIG.RAGE_CLICK_THRESHOLD) {
      e.preventDefault();
      e.stopPropagation();
      clicks.length = 0; // reset

      showShieldModal(
        'Un momento, por favor',
        'Detectamos multiples clics rapidos. Estoy verificando que todo funcione correctamente para ti...'
      );

      // Temporarily disable the element
      if (target.style) {
        target.style.pointerEvents = 'none';
        target.style.opacity = '0.6';
        setTimeout(() => {
          target.style.pointerEvents = '';
          target.style.opacity = '';
        }, CONFIG.RAGE_COOLDOWN_MS);
      }

      // Report to Sentinel (non-blocking)
      _reportToSentinel('rage_click', {
        element: key,
        url: window.location.pathname,
        clicks_in_window: CONFIG.RAGE_CLICK_THRESHOLD,
      });
    }
  }, true); // capture phase to intercept before handlers

  // ══════════════════════════════════════════════════════════════════
  // 2. FORM VALIDATION & RESUBMIT GUARD
  // ══════════════════════════════════════════════════════════════════
  document.addEventListener('submit', function (e) {
    const form = e.target;
    if (!form || form.tagName !== 'FORM') return;

    // ── Rapid resubmit guard ──
    const formKey = form.action || form.id || 'form_' + form.className;
    const now = Date.now();
    const lastSubmit = formSubmitTracker.get(formKey) || 0;

    if ((now - lastSubmit) < CONFIG.FORM_RESUBMIT_BLOCK_MS) {
      e.preventDefault();
      showShieldModal(
        'Procesando tu solicitud',
        'Ya enviaste esta informacion. Espera un momento mientras la procesamos...'
      );
      return;
    }
    formSubmitTracker.set(formKey, now);

    // ── Absurd data detection ──
    const issues = [];
    const inputs = form.querySelectorAll('input[type="text"], input[type="email"], textarea');

    inputs.forEach(function (input) {
      const val = (input.value || '').trim();
      const name = (input.name || input.id || '').toLowerCase();

      // Check name fields for numbers-only
      if ((name.includes('nombre') || name.includes('name') || name.includes('apellido'))
        && val.length > 0 && /^\d+$/.test(val)) {
        issues.push('Un campo de nombre contiene solo numeros');
      }

      // Check email basic format
      if (name.includes('email') || name.includes('correo')) {
        if (val.length > 0 && !val.includes('@')) {
          issues.push('El correo electronico no tiene formato valido');
        }
      }

      // Check for excessively long single words (possible paste attack)
      if (val.length > 500 && !val.includes(' ')) {
        issues.push('Se detecto un texto extremadamente largo sin espacios');
      }

      // Check for SQL injection patterns
      if (/('|--|;|DROP\s|DELETE\s|INSERT\s|UPDATE\s|SELECT\s)/i.test(val) && val.length < 200) {
        issues.push('Se detecto un patron de texto sospechoso');
      }
    });

    if (issues.length > 0) {
      e.preventDefault();
      showShieldModal(
        'Datos por verificar',
        issues[0] + '. Por favor revisa la informacion antes de enviarla.'
      );
      _reportToSentinel('form_validation', {
        issues: issues,
        form_action: form.action,
        url: window.location.pathname,
      });
    }
  }, true);

  // ══════════════════════════════════════════════════════════════════
  // 3. GLOBAL ERROR INTERCEPTOR (fetch + XHR)
  // ══════════════════════════════════════════════════════════════════
  // Intercept fetch errors (5xx)
  const _originalFetch = window.fetch;
  window.fetch = function () {
    return _originalFetch.apply(this, arguments)
      .then(function (response) {
        if (response.status >= 500) {
          showShieldModal(
            'El sistema se esta recuperando',
            'Detectamos un inconveniente temporal. Sentinel ya esta trabajando en solucionarlo automaticamente...'
          );
        }
        return response;
      })
      .catch(function (err) {
        // Network error
        if (err.name === 'TypeError' && err.message.includes('fetch')) {
          showShieldModal(
            'Problema de conexion',
            'Parece que hay un problema con la red. Verifica tu conexion a internet.'
          );
        }
        throw err;
      });
  };

  // ══════════════════════════════════════════════════════════════════
  // TELEMETRY (non-blocking report to server)
  // ══════════════════════════════════════════════════════════════════
  function _reportToSentinel(event_type, data) {
    try {
      var csrfToken = '';
      var csrfMeta = document.querySelector('[name=csrfmiddlewaretoken]');
      if (csrfMeta) csrfToken = csrfMeta.value;
      if (!csrfToken) {
        var cookies = document.cookie.split(';');
        for (var i = 0; i < cookies.length; i++) {
          var c = cookies[i].trim();
          if (c.startsWith('csrftoken=')) {
            csrfToken = c.substring(10);
            break;
          }
        }
      }

      var payload = JSON.stringify({
        event: event_type,
        data: data,
        timestamp: new Date().toISOString(),
        user_agent: navigator.userAgent,
      });

      // Use sendBeacon for fire-and-forget (no blocking)
      if (navigator.sendBeacon) {
        var blob = new Blob([payload], { type: 'application/json' });
        navigator.sendBeacon('/api/sentinel/shield-telemetry/', blob);
      }
    } catch (ex) {
      // Silent — shield telemetry is best-effort
    }
  }

  // ══════════════════════════════════════════════════════════════════
  // CLEANUP: Prevent memory leaks
  // ══════════════════════════════════════════════════════════════════
  setInterval(function () {
    var now = Date.now();
    clickTracker.forEach(function (clicks, key) {
      while (clicks.length > 0 && (now - clicks[0]) > 5000) {
        clicks.shift();
      }
      if (clicks.length === 0) clickTracker.delete(key);
    });
  }, 10000);

  console.log('%c⛊ PRIS Sentinel Shield v1.0 activo', 'color:#764ba2; font-weight:bold;');
})();
