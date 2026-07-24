(function () {
    'use strict';
    var lecturaId = null;
    var modal;
    function csrf() {
        var el = document.querySelector('[name=csrfmiddlewaretoken]');
        return el ? el.value : '';
    }
    window.abrirLectorRecetaFarmacia = function () {
        var el = document.getElementById('modalLectorRecetaFarmacia');
        if (!el) return;
        modal = bootstrap.Modal.getOrCreateInstance(el);
        modal.show();
    };
    function estado(texto, tipo) {
        var el = document.getElementById('receta-ocr-farmacia-estado');
        if (el) { el.className = 'small mt-3 text-' + (tipo || 'muted'); el.textContent = texto || ''; }
    }
    function renderSugerencias(sugerencias) {
        var cont = document.getElementById('receta-ocr-farmacia-resultados');
        if (!cont) return;
        if (!sugerencias.length) {
            cont.innerHTML = '<div class="alert alert-danger">No se encontraron coincidencias en el catálogo. Capture el medicamento manualmente.</div>';
            return;
        }
        cont.innerHTML = sugerencias.map(function (s, i) {
            var candidatos = (s.candidatos || []).map(function (c) {
                return '<label class="list-group-item d-flex gap-2 align-items-start">' +
                    '<input class="form-check-input mt-1 receta-candidato" type="radio" name="receta-med-' + i + '" data-producto-id="' + c.producto_id + '" data-cantidad="' + (s.cantidad_sugerida || 1) + '">' +
                    '<span><strong>' + c.nombre + '</strong> <small class="text-muted">' + (c.concentracion || '') + ' · ' + (c.presentacion || '') + '</small><br>' +
                    '<small>Genérico: ' + (c.sustancia_activa || 'no capturado') + ' · Marca: ' + (c.marca || 'no capturada') + ' · Existencia: ' + c.stock + (c.requiere_receta ? ' · <b>requiere receta</b>' : '') + '</small></span></label>';
            }).join('');
            return '<div class="card mb-2"><div class="card-header py-2"><strong>Receta:</strong> ' + s.texto + ' <span class="badge bg-secondary">Cantidad sugerida: ' + (s.cantidad_sugerida || 1) + '</span></div><div class="list-group list-group-flush">' + (candidatos || '<div class="p-3 text-danger">Sin coincidencias; capture manualmente.</div>') + '</div></div>';
        }).join('');
        document.getElementById('btn-confirmar-receta-farmacia').disabled = false;
    }
    window.analizarRecetaFarmacia = function () {
        var input = document.getElementById('foto-receta-farmacia');
        if (!input || !input.files.length) { estado('Seleccione o tome una foto de la receta.', 'danger'); return; }
        var fd = new FormData(); fd.append('imagen_receta', input.files[0]);
        estado('Analizando receta. La venta no se modificará todavía…', 'info');
        document.getElementById('btn-analizar-receta-farmacia').disabled = true;
        fetch(window.PDV_RECETA_ANALIZAR_URL, { method: 'POST', body: fd, credentials: 'same-origin', headers: { 'X-CSRFToken': csrf(), 'X-Requested-With': 'XMLHttpRequest' } })
            .then(function (r) { return r.json().then(function (d) { if (!r.ok) throw new Error(d.error || 'No fue posible analizar la receta.'); return d; }); })
            .then(function (d) { lecturaId = d.lectura_id; estado('Lectura lista. Seleccione una coincidencia por cada medicamento y confirme.', 'success'); renderSugerencias(d.sugerencias || []); })
            .catch(function (e) { estado(e.message, 'danger'); })
            .finally(function () { document.getElementById('btn-analizar-receta-farmacia').disabled = false; });
    };
    window.confirmarRecetaFarmacia = function () {
        var seleccionados = Array.from(document.querySelectorAll('.receta-candidato:checked')).map(function (el) { return { producto_id: Number(el.dataset.productoId), cantidad: Number(el.dataset.cantidad || 1) }; });
        if (!lecturaId || !seleccionados.length) { estado('Seleccione al menos un medicamento antes de confirmar.', 'danger'); return; }
        fetch(window.PDV_RECETA_CONFIRMAR_URL, { method: 'POST', credentials: 'same-origin', headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrf(), 'X-Requested-With': 'XMLHttpRequest' }, body: JSON.stringify({ lectura_id: lecturaId, items: seleccionados }) })
            .then(function (r) { return r.json().then(function (d) { if (!r.ok) throw new Error(d.error || 'No se pudo confirmar.'); return d; }); })
            .then(function (d) { d.items.forEach(function (item) { for (var i = 0; i < item.cantidad; i++) { if (typeof window.intentarAgregar === 'function') window.intentarAgregar(item.producto_id); } }); estado('Selección confirmada. Revise lote, receta y restricciones antes de cobrar.', 'success'); })
            .catch(function (e) { estado(e.message, 'danger'); });
    };
})();
