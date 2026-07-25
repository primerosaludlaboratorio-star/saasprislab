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
    var inputReceta = document.getElementById('foto-receta-farmacia');
    if (inputReceta) inputReceta.addEventListener('change', function () {
        var preview = document.getElementById('receta-ocr-farmacia-preview');
        var image = document.getElementById('receta-ocr-farmacia-preview-img');
        var file = inputReceta.files && inputReceta.files[0];
        if (!preview || !image) return;
        if (!file) { preview.hidden = true; image.removeAttribute('src'); return; }
        if (!file.type || file.type.indexOf('image/') !== 0) {
            preview.hidden = true;
            estado('Seleccione un archivo de imagen válido.', 'danger');
            return;
        }
        var reader = new FileReader();
        reader.onload = function (event) { image.src = event.target.result; preview.hidden = false; };
        reader.readAsDataURL(file);
    });
    function estado(texto, tipo) {
        var el = document.getElementById('receta-ocr-farmacia-estado');
        if (el) { el.className = 'small mt-3 text-' + (tipo || 'muted'); el.textContent = texto || ''; }
    }
    function htmlSeguro(valor) {
        return String(valor == null ? '' : valor).replace(/[&<>"']/g, function (c) {
            return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c];
        });
    }
    function actualizarEstadoConfirmacion() {
        var boton = document.getElementById('btn-confirmar-receta-farmacia');
        if (boton) boton.disabled = !lecturaId || !document.querySelector('.receta-candidato:checked');
    }
    function renderSugerencias(sugerencias, datos, meta) {
        var cont = document.getElementById('receta-ocr-farmacia-resultados');
        if (!cont) return;
        datos = datos || {};
        var medicamentos = Array.isArray(datos.medicamentos) ? datos.medicamentos : [];
        var cabecera = '<div class="card border-primary mb-3"><div class="card-body py-2">' +
            '<div class="d-flex justify-content-between gap-2 flex-wrap"><strong>Texto detectado de la receta</strong>' +
            '<span class="badge bg-info text-dark">' + htmlSeguro(meta && meta.proveedor_vision ? meta.proveedor_vision : 'visión') +
            ' · confianza ' + htmlSeguro(meta && meta.confianza != null ? meta.confianza : '0') + '</span></div>' +
            '<div class="small mt-2"><b>Paciente:</b> ' + htmlSeguro(datos.nombre_paciente || 'No identificado') +
            ' · <b>Fecha:</b> ' + htmlSeguro(datos.fecha_receta || 'No identificada') +
            ' · <b>Médico:</b> ' + htmlSeguro(datos.medico_nombre || 'No identificado') + '</div>' +
            (datos.observaciones ? '<div class="small mt-1"><b>Observaciones:</b> ' + htmlSeguro(datos.observaciones) + '</div>' : '') +
            '</div></div>';
        var lineas = sugerencias.length ? sugerencias : medicamentos.map(function (m) {
            return {texto: m.texto || m.nombre_comercial || m.nombre || '', cantidad_sugerida: m.cantidad || 1,
                indicaciones: m.indicaciones || '', confianza: m.confianza || 0, candidatos: []};
        });
        if (!lineas.length) {
            cont.innerHTML = cabecera + '<div class="alert alert-warning">La imagen se recibió, pero el lector no identificó líneas de medicamento. Capture una foto más cercana y nítida o búsquelo manualmente en el PDV.</div>';
            actualizarEstadoConfirmacion();
            return;
        }
        cont.innerHTML = cabecera + lineas.map(function (s, i) {
            var candidatos = (s.candidatos || []).map(function (c) {
                return '<label class="list-group-item d-flex gap-2 align-items-start">' +
                    '<input class="form-check-input mt-1 receta-candidato" type="radio" name="receta-med-' + i + '" data-producto-id="' + c.producto_id + '" data-cantidad="' + (s.cantidad_sugerida || 1) + '">' +
                    '<span><strong>' + htmlSeguro(c.nombre) + '</strong> <small class="text-muted">' + htmlSeguro(c.concentracion || '') + ' · ' + htmlSeguro(c.presentacion || '') + '</small><br>' +
                    '<small>Genérico: ' + htmlSeguro(c.sustancia_activa || 'no capturado') + ' · Marca: ' + htmlSeguro(c.marca || 'no capturada') + ' · Existencia: ' + htmlSeguro(c.stock) + (c.requiere_receta ? ' · <b>requiere receta</b>' : '') + '</small></span></label>';
            }).join('');
            var indicaciones = s.indicaciones ? '<div class="small text-primary mt-1"><b>Indicaciones:</b> ' + htmlSeguro(s.indicaciones) + '</div>' : '';
            var sinCoincidencia = '<div class="p-3 text-warning">No hay coincidencia automática. Busque este texto en el catálogo para seleccionarlo.</div>' +
                '<div class="p-2 border-top"><div class="input-group input-group-sm"><input class="form-control ocr-busqueda-manual" data-ocr-index="' + i + '" value="' + htmlSeguro(s.texto) + '" aria-label="Buscar medicamento detectado"><button type="button" class="btn btn-outline-primary" data-ocr-buscar="' + i + '">Buscar en catálogo</button></div><div class="mt-2" id="ocr-candidatos-' + i + '"></div></div>';
            return '<div class="card mb-2"><div class="card-header py-2"><strong>Medicamento detectado:</strong> ' + htmlSeguro(s.texto) + ' <span class="badge bg-secondary">Cantidad sugerida: ' + htmlSeguro(s.cantidad_sugerida || 1) + '</span>' + indicaciones + '</div><div class="list-group list-group-flush">' + (candidatos || sinCoincidencia) + '</div></div>';
        }).join('');
        cont.querySelectorAll('.receta-candidato').forEach(function (el) { el.addEventListener('change', actualizarEstadoConfirmacion); });
        cont.querySelectorAll('[data-ocr-buscar]').forEach(function (el) { el.addEventListener('click', function () { buscarCandidatosOCR(Number(el.dataset.ocrBuscar)); }); });
        actualizarEstadoConfirmacion();
    }
    window.buscarCandidatosOCR = function (indice) {
        var input = document.querySelector('.ocr-busqueda-manual[data-ocr-index="' + indice + '"]');
        var destino = document.getElementById('ocr-candidatos-' + indice);
        var termino = input ? input.value.trim() : '';
        if (!termino || !destino) return;
        destino.innerHTML = '<div class="small text-muted">Buscando en catálogo...</div>';
        var url = (window.PDV_BUSCAR_URL || '/farmacia/api/buscar-producto-pdv/') + '?termino=' + encodeURIComponent(termino);
        fetch(url, {credentials: 'same-origin', headers: {'X-Requested-With': 'XMLHttpRequest', 'Accept': 'application/json'}})
            .then(function (r) { return r.json().then(function (d) { if (!r.ok) throw new Error(d.error || 'No fue posible buscar.'); return d; }); })
            .then(function (d) {
                var productos = d.productos || [];
                destino.innerHTML = productos.length ? productos.slice(0, 8).map(function (p) {
                    return '<label class="list-group-item d-flex gap-2 align-items-start"><input class="form-check-input mt-1 receta-candidato" type="radio" name="receta-med-' + indice + '" data-producto-id="' + p.id + '" data-cantidad="1"><span><strong>' + htmlSeguro(p.nombre_comercial || p.nombre) + '</strong><br><small>Genérico: ' + htmlSeguro(p.sustancia_activa || '') + ' · Stock: ' + htmlSeguro(p.stock_total || p.stock || 0) + '</small></span></label>';
                }).join('') : '<div class="small text-danger">Sin resultados. Ajuste el texto y vuelva a buscar.</div>';
                destino.querySelectorAll('.receta-candidato').forEach(function (el) { el.addEventListener('change', actualizarEstadoConfirmacion); });
                actualizarEstadoConfirmacion();
            })
            .catch(function (e) { destino.innerHTML = '<div class="small text-danger">' + htmlSeguro(e.message) + '</div>'; });
    };
    window.analizarRecetaFarmacia = function () {
        var input = document.getElementById('foto-receta-farmacia');
        if (!input || !input.files.length) { estado('Seleccione o tome una foto de la receta.', 'danger'); return; }
        var fd = new FormData(); fd.append('imagen_receta', input.files[0]);
        estado('Analizando receta. La venta no se modificará todavía…', 'info');
        document.getElementById('btn-analizar-receta-farmacia').disabled = true;
        fetch(window.PDV_RECETA_ANALIZAR_URL, { method: 'POST', body: fd, credentials: 'same-origin', headers: { 'X-CSRFToken': csrf(), 'X-Requested-With': 'XMLHttpRequest' } })
            .then(function (r) { return r.json().then(function (d) { if (!r.ok) throw new Error(d.error || 'No fue posible analizar la receta.'); return d; }); })
            .then(function (d) { lecturaId = d.lectura_id; estado('Lectura lista. Revise el texto detectado, seleccione cada medicamento y confirme.', 'success'); renderSugerencias(d.sugerencias || [], d.datos || {}, {proveedor_vision: d.proveedor_vision, confianza: d.confianza}); })
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
