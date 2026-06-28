/**
 * PRIS SENTINEL VOICE v1.0 — Asistencia por Voz
 * ===============================================
 * Usa la API SpeechSynthesis del navegador para dar feedback
 * auditivo al personal cuando Sentinel realiza una auto-curacion.
 *
 * Eventos que activan la voz:
 *   - Auto-reparacion exitosa (redireccion por error/permisos)
 *   - Recuperacion de conexion a base de datos
 *   - Optimizacion completada
 *
 * El sistema "habla" para que el personal sienta que alguien
 * los esta cuidando, reduciendo estres ante errores.
 */
(function () {
  'use strict';

  // ══════════════════════════════════════════════════════════════════
  // CONFIG
  // ══════════════════════════════════════════════════════════════════
  const VOICE_CONFIG = {
    enabled: true,
    lang: 'es-MX',         // Español de Mexico
    rate: 0.95,             // Velocidad (0.1 - 10)
    pitch: 1.0,             // Tono (0 - 2)
    volume: 0.7,            // Volumen (0 - 1)
    cooldown_ms: 10000,     // Minimo 10s entre mensajes de voz
  };

  // Messages map
  const VOICE_MESSAGES = {
    'repair_success': 'Optimizacion completada con exito. Puedes continuar trabajando.',
    'permission_fixed': 'Permisos actualizados correctamente. Acceso restaurado.',
    'db_recovery': 'Conexion restaurada. El sistema esta funcionando normalmente.',
    'redirect_safe': 'Te redirigi a una pagina segura. Todo esta bajo control.',
    'form_blocked': 'Detuve un envio duplicado para proteger tus datos.',
    'system_optimized': 'Sistema optimizado. Rendimiento al maximo.',
  };

  let lastVoiceTime = 0;
  let speechSupported = false;

  // ══════════════════════════════════════════════════════════════════
  // INIT: Check SpeechSynthesis support
  // ══════════════════════════════════════════════════════════════════
  if ('speechSynthesis' in window) {
    speechSupported = true;
  }

  // ══════════════════════════════════════════════════════════════════
  // CORE: Speak function
  // ══════════════════════════════════════════════════════════════════
  function sentinelSpeak(messageKey, customText) {
    if (!VOICE_CONFIG.enabled || !speechSupported) return;

    var now = Date.now();
    if ((now - lastVoiceTime) < VOICE_CONFIG.cooldown_ms) return;

    var text = customText || VOICE_MESSAGES[messageKey] || '';
    if (!text) return;

    // Cancel any ongoing speech
    window.speechSynthesis.cancel();

    var utterance = new SpeechSynthesisUtterance(text);
    utterance.lang = VOICE_CONFIG.lang;
    utterance.rate = VOICE_CONFIG.rate;
    utterance.pitch = VOICE_CONFIG.pitch;
    utterance.volume = VOICE_CONFIG.volume;

    // Try to get a Spanish voice
    var voices = window.speechSynthesis.getVoices();
    for (var i = 0; i < voices.length; i++) {
      if (voices[i].lang && voices[i].lang.startsWith('es')) {
        utterance.voice = voices[i];
        break;
      }
    }

    window.speechSynthesis.speak(utterance);
    lastVoiceTime = now;
  }

  // ══════════════════════════════════════════════════════════════════
  // AUTO-DETECT: Check URL params for Sentinel events
  // ══════════════════════════════════════════════════════════════════
  // Sentinel adds ?sentinel_msg=... and ?sentinel_event=... on redirects
  function checkSentinelEvent() {
    var params = new URLSearchParams(window.location.search);
    var sentinelMsg = params.get('sentinel_msg');
    var sentinelEvent = params.get('sentinel_event');

    // Also check Django messages container for Sentinel messages
    var messagesContainer = document.querySelector('.messages, .alert-sentinel, [data-sentinel-msg]');

    if (sentinelEvent) {
      sentinelSpeak(sentinelEvent);
    } else if (sentinelMsg) {
      sentinelSpeak(null, sentinelMsg);
    }

    // Check for sentinel messages in Django message framework
    var alerts = document.querySelectorAll('.alert');
    alerts.forEach(function (alert) {
      var text = (alert.textContent || '').toLowerCase();
      if (text.includes('optimizaci') || text.includes('reparaci') || text.includes('auto-curac')) {
        sentinelSpeak('repair_success');
      } else if (text.includes('permiso') && (text.includes('restaur') || text.includes('actualiz') || text.includes('regener'))) {
        sentinelSpeak('permission_fixed');
      } else if (text.includes('base de datos') || text.includes('conexi') && text.includes('restaur')) {
        sentinelSpeak('db_recovery');
      } else if (text.includes('redirig') || text.includes('pagina segura')) {
        sentinelSpeak('redirect_safe');
      }
    });
  }

  // Voices may load asynchronously
  if (speechSupported) {
    if (window.speechSynthesis.getVoices().length > 0) {
      checkSentinelEvent();
    } else {
      window.speechSynthesis.addEventListener('voiceschanged', function () {
        checkSentinelEvent();
      });
      // Fallback: check after 1s regardless
      setTimeout(checkSentinelEvent, 1000);
    }
  }

  // ══════════════════════════════════════════════════════════════════
  // PUBLIC API: Allow manual triggering from other scripts
  // ══════════════════════════════════════════════════════════════════
  window.SentinelVoice = {
    speak: sentinelSpeak,
    enable: function () { VOICE_CONFIG.enabled = true; },
    disable: function () { VOICE_CONFIG.enabled = false; },
    isSupported: function () { return speechSupported; },
  };

  console.log('%c🔊 PRIS Sentinel Voice v1.0 activo', 'color:#667eea; font-weight:bold;');
})();
