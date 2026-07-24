(function () {
    'use strict';
    var lecturaId = null;
    function csrf() { var el = document.querySelector('[name=csrfmiddlewaretoken]'); return el ? el.value : ''; }
    function esc(value) { return String(value == null ? '' : value).replace(/[&<>"']/g, function (c) { return ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]); }); }
    function setEstado(texto, tipo) { var el = document.getElementById('compra-ocr-estado'); if (el) { el.className = 'small mt-2 text-' + (tipo || 'muted'); el.textContent = texto || ''; } }
    window.abrirLectorCompraFarmacia = function () { var el = document.getElementById('modalLectorCompraFarmacia'); if (el) bootstrap.Modal.getOrCreateInstance(el).show(); };
    function render(data) {
        var d = data.datos || {}, proveedor = d.proveedor || {}, out = document.getElementById('compra-ocr-resultados');
        var html = '<div class="alert alert-secondary"><strong>Proveedor detectado:</strong> ' + esc(proveedor.nombre || 'No identificado') + ' · <strong>RFC:</strong> ' + esc(proveedor.rfc || 'No identificado') + '<br><strong>Folio:</strong> ' + esc(d.folio || '') + ' · <strong>Total leído:</strong> ' + esc(d.total || '') + '</div>';
        html += '<div class="row g-2 mb-3"><div class="col-md-6"><label class="form-label">Proveedor registrado</label><input id="compra-ocr-proveedor" class="form-control" placeholder="Seleccione después en la compra" value="' + esc(proveedor.nombre || '') + '"></div><div class="col-md-3"><label class="form-label">Folio / documento</label><input id="compra-ocr-documento" class="form-control" value="' + esc(d.folio || '') + '"></div><div class="col-md-3"><label class="form-label">Fecha</label><input id="compra-ocr-fecha" type="date" class="form-control" value="' + esc(d.fecha_compra || '') + '"></div></div>';
        (data.sugerencias || []).forEach(function (line, index) {
            html += '<div class="card mb-2"><div class="card-header py-2"><strong>Línea:</strong> ' + esc(line.texto) + '</div><div class="card-body py-2"><div class="list-group mb-2">';
            (line.candidatos || []).forEach(function (c) { html += '<label class="list-group-item"><input type="radio" class="compra-ocr-producto me-2" name="compra-ocr-line-' + index + '" data-line="' + index + '" value="' + c.producto_id + '"> <strong>' + esc(c.nombre) + '</strong> <small>' + esc(c.concentracion || '') + ' · ' + esc(c.presentacion || '') + ' · Marca: ' + esc(c.marca || '') + '</small></label>'; });
            if (!(line.candidatos || []).length) html += '<div class="text-danger small">Sin coincidencia automática; agregue esta línea manualmente.</div>';
            html += '</div><div class="row g-2"><div class="col"><label class="form-label small">Cantidad</label><input class="form-control compra-ocr-cantidad" data-line="' + index + '" type="number" min="1" value="' + esc(line.cantidad || 1) + '"></div><div class="col"><label class="form-label small">Costo unitario</label><input class="form-control compra-ocr-costo" data-line="' + index + '" type="number" min="0.01" step="0.01" value="' + esc(line.costo_unitario || '') + '"></div><div class="col"><label class="form-label small">Lote</label><input class="form-control compra-ocr-lote" data-line="' + index + '" value="' + esc(line.numero_lote || '') + '"></div><div class="col"><label class="form-label small">Caducidad</label><input class="form-control compra-ocr-caducidad" data-line="' + index + '" type="date" value="' + esc(line.fecha_caducidad || '') + '"></div><div class="col"><label class="form-label small">Marca</label><input class="form-control compra-ocr-marca" data-line="' + index + '" value="' + esc(line.marca || '') + '"></div></div></div></div>';
        });
        out.innerHTML = html;
        document.getElementById('btn-confirmar-compra-ocr').disabled = !(data.sugerencias || []).length;
    }
    window.analizarCompraFarmacia = function () {
        var input = document.getElementById('documento-compra-ocr');
        if (!input || !input.files.length) { setEstado('Seleccione o tome una foto.', 'danger'); return; }
        var fd = new FormData(); fd.append('documento_compra', input.files[0]); setEstado('Analizando documento; no se modificará inventario…', 'info');
        document.getElementById('btn-analizar-compra-ocr').disabled = true;
        fetch(window.COMPRA_OCR_ANALIZAR_URL, {method:'POST', body:fd, credentials:'same-origin', headers:{'X-CSRFToken':csrf(), 'X-Requested-With':'XMLHttpRequest'}}).then(function (r) { return r.json().then(function (d) { if (!r.ok) throw new Error(d.error || 'No fue posible analizar.'); return d; }); }).then(function (d) { lecturaId = d.lectura_id; render(d); setEstado('Revise y corrija cada línea antes de confirmar.', 'success'); }).catch(function (e) { setEstado(e.message, 'danger'); }).finally(function () { document.getElementById('btn-analizar-compra-ocr').disabled = false; });
    };
    window.confirmarCompraFarmacia = function () {
        var groups = {}; Array.from(document.querySelectorAll('.compra-ocr-producto:checked')).forEach(function (el) { groups[el.dataset.line] = el.value; });
        var items = Object.keys(groups).map(function (line) { function val(cls) { return document.querySelector('.' + cls + '[data-line="' + line + '"]')?.value || ''; } return {producto_id:Number(groups[line]), cantidad:val('compra-ocr-cantidad'), costo_unitario:val('compra-ocr-costo'), numero_lote:val('compra-ocr-lote'), fecha_caducidad:val('compra-ocr-caducidad'), marca:val('compra-ocr-marca')}; });
        if (!lecturaId || !items.length) { setEstado('Seleccione un producto del catálogo por cada línea que quiera ingresar.', 'danger'); return; }
        var payload = {lectura_id:lecturaId, proveedor:document.getElementById('compra-ocr-proveedor')?.value || '', documento_compra:document.getElementById('compra-ocr-documento')?.value || '', fecha_compra:document.getElementById('compra-ocr-fecha')?.value || '', items:items};
        fetch(window.COMPRA_OCR_CONFIRMAR_URL, {method:'POST', credentials:'same-origin', headers:{'Content-Type':'application/json','X-CSRFToken':csrf(),'X-Requested-With':'XMLHttpRequest'}, body:JSON.stringify(payload)}).then(function (r) { return r.json().then(function (d) { if (!r.ok) throw new Error(d.error || 'No fue posible confirmar.'); return d; }); }).then(function (d) { window.location.href = d.redirect; }).catch(function (e) { setEstado(e.message, 'danger'); });
    };
})();
