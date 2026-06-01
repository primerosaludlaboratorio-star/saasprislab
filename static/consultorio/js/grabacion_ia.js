/* PRISLAB Motor Grabacion IA — Consultorio Medico */
'use strict';
(function() {
  var _recognition = null; var _grabando = false; var _transcripcion = '';
  function iniciarGrabacion(btnId, contId) {
    var btn = document.getElementById(btnId); var cont = document.getElementById(contId);
    if (!btn) return;
    if (_grabando) { detenerGrabacion(btnId, contId); return; }
    var SR = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (SR) {
      _recognition = new SR(); _recognition.lang = 'es-MX'; _recognition.continuous = true; _recognition.interimResults = true;
      _recognition.onresult = function(e) {
        var final = '';
        for (var i = e.resultIndex; i < e.results.length; i++) { if (e.results[i].isFinal) final += e.results[i][0].transcript + ' '; }
        if (final) {
          _transcripcion += final;
          var ta = document.getElementById('nota_clinica') || document.getElementById('nota_soap') || document.getElementById('diagnostico');
          if (ta) ta.value = (ta.value ? ta.value + ' ' : '') + final.trim();
        }
      };
      _recognition.onerror = function(e) { console.warn('[PRIS] Speech:', e.error); };
      _recognition.start();
    }
    _grabando = true;
    if (btn) { btn.classList.add('grabando'); btn.innerHTML = '<i class="bi bi-stop-circle-fill me-1"></i>Detener'; }
    if (cont) cont.classList.add('activo');
  }
  function detenerGrabacion(btnId, contId) {
    if (_recognition) { try { _recognition.stop(); } catch(e) {} }
    _grabando = false;
    var btn = document.getElementById(btnId); var cont = document.getElementById(contId);
    if (btn) { btn.classList.remove('grabando'); btn.innerHTML = '<i class="bi bi-mic-fill me-1"></i>Dictado IA'; }
    if (cont) cont.classList.remove('activo');
  }
  window.prisGrabacion = { iniciar: iniciarGrabacion, detener: detenerGrabacion, getTranscripcion: function() { return _transcripcion; } };
  console.log('[PRIS] grabacion_ia.js activo');
})();