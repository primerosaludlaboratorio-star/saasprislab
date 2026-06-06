/**
 * PRISLAB PDV FARMACIA v3.3 - Motor Principal
 * Carrito, pagos, busqueda, atajos de teclado.
 */
'use strict';

// ESTADO GLOBAL
window.carrito = [];
window.ventaActualId = null;
window.ventaActualFolio = null;
window.cuponAplicado = null;
window.recetaActual = null;
window.precioNetoActivo = false;
window._productoAntibioticoTemp = null;

// ============================================================
// MULTI-TAB: Carritos múltiples en espera (estilo Pulpos)
// ============================================================
var _tabs = {
    activo: 1,
    maxId: 1,
    data: {
        1: { carrito: [], receta: null, cupon: null, paciente: '', pacienteId: null, precioNeto: false }
    }
};

function _guardarTabActual() {
    var t = _tabs.data[_tabs.activo];
    if (!t) return;
    t.carrito = (window.carrito || []).slice();
    t.receta = window.recetaActual;
    t.cupon = window.cuponAplicado;
    t.precioNeto = window.precioNetoActivo;
    var pac = document.getElementById('input-paciente');
    var pacId = document.getElementById('p-paciente-id');
    t.paciente = pac ? pac.value : '';
    t.pacienteId = pacId ? pacId.value : null;
}

function _restaurarTab(id) {
    var t = _tabs.data[id];
    if (!t) return;
    window.carrito = (t.carrito || []).slice();
    window.recetaActual = t.receta || null;
    window.cuponAplicado = t.cupon || null;
    window.precioNetoActivo = !!t.precioNeto;
    var pac = document.getElementById('input-paciente');
    var pacId = document.getElementById('p-paciente-id');
    if (pac) pac.value = t.paciente || '';
    if (pacId) pacId.value = t.pacienteId || '';
}

function _renderTabs() {
    var ul = document.getElementById('ticketTabs');
    if (!ul) return;
    var html = '';
    Object.keys(_tabs.data).forEach(function(id) {
        id = parseInt(id);
        var t = _tabs.data[id];
        var items = (t.carrito || []).reduce(function(s, i) { return s + i.cantidad; }, 0);
        var isActive = id === _tabs.activo;
        html += '<li class="nav-item">' +
            '<a class="nav-link ' + (isActive ? 'active fw-bold bg-white' : 'text-muted') + '" href="#" onclick="switchTicket(' + id + ');return false;" style="padding:.4rem .75rem;">' +
            '<i class="bi bi-receipt"></i> Ticket ' + id +
            (items > 0 ? ' <span class="badge bg-primary rounded-pill ms-1" style="font-size:.7rem;">' + items + '</span>' : '') +
            (Object.keys(_tabs.data).length > 1 && !isActive ? ' <span class="ms-1 text-danger" onclick="cerrarTab(' + id + ');event.stopPropagation();return false;" style="cursor:pointer;font-size:.8rem;" title="Cerrar">×</span>' : '') +
            '</a></li>';
    });
    html += '<li class="nav-item">' +
        '<a class="nav-link text-muted" href="#" onclick="nuevoTicket();return false;" title="Nuevo Ticket en espera">' +
        '<i class="bi bi-plus-lg"></i></a></li>';
    ul.innerHTML = html;
}

window.nuevoTicket = function() {
    if (Object.keys(_tabs.data).length >= 5) {
        _mostrarAlerta('Límite de tickets', 'Máximo 5 tickets simultáneos.', 'warning');
        return;
    }
    _guardarTabActual();
    _tabs.maxId++;
    var nuevoId = _tabs.maxId;
    _tabs.data[nuevoId] = { carrito: [], receta: null, cupon: null, paciente: '', pacienteId: null, precioNeto: false };
    _tabs.activo = nuevoId;
    _restaurarTab(nuevoId);
    renderCarrito();
    _renderTabs();
    var b = document.getElementById('input-buscador');
    if (b) { b.value = ''; b.focus(); }
    _mostrarAlerta('Ticket ' + nuevoId, 'Nuevo ticket abierto. El anterior queda en espera.', 'info');
};

window.switchTicket = function(id) {
    id = parseInt(id);
    if (id === _tabs.activo) return;
    _guardarTabActual();
    _tabs.activo = id;
    _restaurarTab(id);
    renderCarrito();
    _renderTabs();
    var b = document.getElementById('input-buscador');
    if (b) { b.value = ''; b.focus(); }
};

window.cerrarTab = function(id) {
    id = parseInt(id);
    var t = _tabs.data[id];
    if (!t) return;
    if ((t.carrito || []).length > 0 && !confirm('El ticket ' + id + ' tiene productos. ¿Cerrarlo sin cobrar?')) return;
    delete _tabs.data[id];
    if (_tabs.activo === id) {
        var keys = Object.keys(_tabs.data).map(Number);
        _tabs.activo = keys[keys.length - 1] || 1;
        _restaurarTab(_tabs.activo);
        renderCarrito();
    }
    _renderTabs();
};

// Inicializar tabs al cargar
document.addEventListener('DOMContentLoaded', function() {
    _renderTabs();
});

// ============================================================
// LISTA DE PRECIOS — aplica descuento global al carrito
// ============================================================
window._listaPrecioActiva = { id: 0, pct: 0, nombre: 'Precio Público', requiere_auth: false };

window.aplicarListaPrecio = function() {
    var sel = document.getElementById('selector-lista-precio');
    if (!sel) return;
    var opt = sel.options[sel.selectedIndex];
    var pct = parseFloat(opt ? opt.dataset.pct : 0) || 0;
    var nombre = opt ? (opt.dataset.nombre || 'Precio Público') : 'Precio Público';
    var requiere_auth = opt ? opt.dataset.auth === '1' : false;

    if (requiere_auth && pct > 0) {
        if (!confirm('La lista "' + nombre + '" requiere autorización del gerente. ¿Confirmar?')) {
            sel.value = '0';
            return;
        }
    }

    window._listaPrecioActiva = { id: parseInt(sel.value) || 0, pct: pct, nombre: nombre };

    // Actualizar badge
    var badge = document.getElementById('badge-lista-activa');
    var txt = document.getElementById('txt-lista-activa');
    if (badge && txt) {
        if (pct > 0) {
            txt.textContent = nombre + ' -' + pct + '%';
            badge.classList.remove('d-none');
        } else {
            badge.classList.add('d-none');
        }
    }

    // Recalcular precios en el carrito con el descuento de lista
    window.carrito.forEach(function(item) {
        var precioBase = item.precio_base || item.precio_venta;
        if (pct > 0) {
            item.precio_venta = parseFloat((precioBase * (1 - pct / 100)).toFixed(2));
        } else {
            // Restaurar precio original (precio_base es la fuente de verdad)
            item.precio_venta = window.precioNetoActivo ? item.precio_neto : item.precio_base;
        }
    });
    renderCarrito();
    if (pct > 0) _mostrarAlerta('Lista ' + nombre, 'Descuento del ' + pct + '% aplicado a todos los productos.', 'success');
};

// UTILIDADES
function _fmt(n) {
    return '$' + (parseFloat(n) || 0).toFixed(2).replace(/\B(?=(\d{3})+(?!\d))/g, ',');
}
function _csrf() {
    var el = document.querySelector('[name=csrfmiddlewaretoken]') || document.querySelector('meta[name="csrf-token"]');
    return el ? (el.value || el.getAttribute('content') || '') : '';
}
function _getModal(id) {
    var el = document.getElementById(id);
    return el ? bootstrap.Modal.getOrCreateInstance(el) : null;
}
function _mostrarAlerta(titulo, msg, tipo) {
    tipo = tipo || 'info';
    var cont = document.getElementById('_pdv-toast-cont');
    if (!cont) { cont = document.createElement('div'); cont.id = '_pdv-toast-cont'; cont.className = 'toast-container position-fixed top-0 end-0 p-3'; cont.style.zIndex = '10000'; document.body.appendChild(cont); }
    var ic = {success:'check-circle-fill',danger:'x-circle-fill',warning:'exclamation-triangle-fill',info:'info-circle-fill'}[tipo]||'info-circle-fill';
    var div = document.createElement('div');
    div.className = 'toast align-items-center text-bg-' + tipo + ' border-0 mb-2'; div.setAttribute('role','alert');
    div.innerHTML = '<div class="d-flex"><div class="toast-body fw-bold"><i class="bi bi-'+ic+' me-2"></i>'+titulo+': <span class="fw-normal">'+msg+'</span></div><button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button></div>';
    cont.appendChild(div);
    var t = new bootstrap.Toast(div, {delay: 4500}); t.show();
    div.addEventListener('hidden.bs.toast', function() { div.remove(); });
}

// BUSQUEDA
var _buscarTimer = null;
var _pdvBuscarAbort = null;
window.debounceBuscar = function(val) { clearTimeout(_buscarTimer); _buscarTimer = setTimeout(function() { window.buscarAjaxDirecto(val); }, 220); };
function _pdvInyectarHtmlFragmento(html, cont, sp, opts) {
    opts = opts || {};
    if (sp) sp.classList.add('d-none');
    if (!cont) return;
    var h = html || '';
    if (!h.trim()) {
        cont.innerHTML = '<div class="text-center py-4 text-danger px-2">Sin respuesta del servidor.</div>';
        return;
    }
    if (h.indexOf('name="password"') !== -1 && (h.indexOf('/login') !== -1 || h.indexOf('Iniciar') !== -1)) {
        cont.innerHTML = '<div class="text-center py-4 text-warning px-2"><i class="bi bi-shield-lock"></i> Sesión requerida. <a href="/login/?next=' + encodeURIComponent(window.location.pathname) + '">Iniciar sesión</a></div>';
        return;
    }
    try {
        var j = JSON.parse(h);
        if (j && (j.mensaje || j.status === 'error')) {
            cont.innerHTML = '<div class="text-center py-4 text-danger">' + (j.mensaje || 'Error') + '</div>';
            return;
        }
    } catch (e0) {}
    cont.innerHTML = h;
    if (opts.autoUnico) {
        var nodes = cont.querySelectorAll('[data-producto-id]');
        if (nodes.length === 1 && typeof window.intentarAgregar === 'function') {
            var pid = parseInt(nodes[0].getAttribute('data-producto-id'), 10);
            if (pid) setTimeout(function () { window.intentarAgregar(pid); }, 80);
        }
    }
}
window._pdvInyectarHtmlFragmento = _pdvInyectarHtmlFragmento;
window.initPdvBuscador = function() {
    var b = document.getElementById('input-buscador');
    if (!b) return false;
    if (b.dataset.pdvSearchBound === '1') return true;
    b.addEventListener('input', function(){ window.debounceBuscar(b.value); });
    b.addEventListener('paste', function(){ setTimeout(function(){ window.debounceBuscar(b.value); }, 0); });
    b.dataset.pdvSearchBound = '1';
    setTimeout(function(){
        try { b.focus(); } catch (e2) {}
    }, 200);
    return true;
};
window.buscarAjaxDirecto = function(val) {
    val = (val || '').trim();
    var sp = document.getElementById('spinner-busqueda');
    var cont = document.getElementById('search-results-container');
    if (!val || val.length < 2) {
        if (sp) sp.classList.add('d-none');
        if (cont) cont.innerHTML = '<div class="text-center py-5 text-muted"><i class="bi bi-upc-scan display-1 opacity-25"></i><p class="mt-3">Escanee o escriba para buscar.</p></div>';
        return;
    }
    if (sp) sp.classList.remove('d-none');
    var frag = window.PDV_BUSCAR_FRAGMENT_URL || '';
    if (frag) {
        if (_pdvBuscarAbort) {
            try { _pdvBuscarAbort.abort(); } catch (e1) {}
        }
        _pdvBuscarAbort = typeof AbortController !== 'undefined' ? new AbortController() : null;
        var u = frag + (frag.indexOf('?') >= 0 ? '&' : '?') + 'q=' + encodeURIComponent(val);
        console.log('[PDV] Buscando fragmento HTML:', u);
        var fetchOpts = {
            credentials: 'include',
            headers: { 'X-Requested-With': 'XMLHttpRequest', 'Accept': 'text/html', 'Cache-Control': 'no-cache' }
        };
        if (_pdvBuscarAbort) fetchOpts.signal = _pdvBuscarAbort.signal;
        fetch(u, fetchOpts)
            .then(function (r) { return r.text().then(function (t) { return { ok: r.ok, status: r.status, text: t }; }); })
            .then(function (res) {
                if (!res.ok) {
                    if (sp) sp.classList.add('d-none');
                    var msg = res.status === 403 ? 'Sin permisos o sin empresa asignada (403).' : ('Error HTTP ' + res.status + ' al buscar.');
                    console.error('[PDV] buscar-fragmento fallo:', res.status, (res.text || '').slice(0, 200));
                    if (cont) {
                        var snippet = (res.text || '').replace(/</g, '&lt;').slice(0, 180);
                        cont.innerHTML = '<div class="text-center py-4 text-danger px-2"><i class="bi bi-exclamation-triangle"></i> ' + msg + '</div>' +
                            (snippet ? '<div class="small text-muted px-3 py-2 border-top">' + snippet + '</div>' : '');
                    }
                    return;
                }
                _pdvInyectarHtmlFragmento(res.text, cont, sp, { autoUnico: false });
            })
            .catch(function (e) {
                if (sp) sp.classList.add('d-none');
                if (e && (e.name === 'AbortError' || (e + '').indexOf('aborted') !== -1)) return;
                console.error('[PDV] Error busqueda fragmento:', e);
                if (cont) cont.innerHTML = '<div class="text-center py-4 text-danger"><p class="fw-bold">Sin conexión</p><small class="text-muted">' + (e && e.message ? e.message : e) + '</small></div>';
            });
        return;
    }
    var url = (window.PDV_BUSCAR_URL || '/farmacia/api/buscar-producto-pdv/') + '?termino=' + encodeURIComponent(val);
    console.log('[PDV] Buscando JSON:', url);
    fetch(url, { headers: { 'X-Requested-With': 'XMLHttpRequest', 'Accept': 'application/json' }, credentials: 'include' })
        .then(function (r) {
            if (!r.ok) { console.error('[PDV] HTTP error status:', r.status); return Promise.reject('HTTP ' + r.status); }
            return r.json();
        })
        .then(function (data) {
            if (sp) sp.classList.add('d-none');
            console.log('[PDV] Resultados recibidos:', (data.productos || []).length, 'para:', val);
            _renderResultados(data.productos || [], val);
        })
        .catch(function (e) {
            if (sp) sp.classList.add('d-none');
            console.error('[PDV] Error en busqueda:', e);
            if (cont) cont.innerHTML = '<div class="text-center py-4 text-danger"><i class="bi bi-exclamation-triangle-fill display-4 opacity-50"></i><p class="mt-2 fw-bold">Error al buscar productos.</p><small class="text-muted">Verifica la conexion o recarga la pagina. (Cod: ' + e + ')</small></div>';
        });
};
window._pdvBuscarHTML = window.buscarAjaxDirecto;
function _renderResultados(productos, termino) {
    var cont = document.getElementById('search-results-container'); if (!cont) return;
    if (!productos.length) {
        var _msg = termino ? ('No se encontraron productos para <strong>&ldquo;' + termino + '&rdquo;</strong>.') : 'Sin resultados.';
        cont.innerHTML = '<div class="text-center py-5 text-muted"><i class="bi bi-search display-4 opacity-25"></i><p class="mt-2">' + _msg + '</p><small>Intenta con otro nombre, abreviatura o codigo de barras.</small></div>';
        return;
    }
    var html = '<div class="row g-2 p-2">';
    productos.forEach(function(p) {
        var stock = p.stock_total || p.stock || 0; var sinStock = stock <= 0;
        var esVencido = p.sin_stock_vigente || false;
        var alertaPrecio = p.alerta_precio_bajo || false;
        var bloqueado = sinStock || esVencido;
        var bc = p.es_controlado ? 'bg-dark' : (esVencido ? 'bg-danger' : (sinStock ? 'bg-secondary' : (alertaPrecio ? 'bg-warning text-dark' : 'bg-success')));
        var bt = p.es_controlado ? 'CONTROLADO' : (esVencido ? '?? VENCIDO' : (sinStock ? 'SIN STOCK' : (alertaPrecio ? '? PRECIO BAJO' : 'LIBRE')));
        html += '<div class="col-md-4 col-lg-3"><div class="card h-100 shadow-sm ' + (bloqueado?'opacity-50 border-danger':'') + '" style="cursor:' + (bloqueado?'not-allowed':'pointer') + '" ' + (bloqueado ? '' : 'onclick="intentarAgregar('+p.id+')"') + '>';
        html += '<div class="card-body p-3"><span class="badge '+bc+' mb-1">'+bt+'</span><h6 class="fw-bold mb-1 text-truncate" title="'+(p.nombre_comercial||'')+'">'+(p.nombre_comercial||'')+'</h6>';
        html += '<small class="text-muted d-block">'+(p.sustancia_activa||'')+'</small><small class="text-muted d-block">Stock: '+stock+'</small><div class="text-primary fw-bold mt-1">'+_fmt(p.precio_base)+'</div>';
        if (esVencido) html += '<small class="text-danger fw-bold d-block"><i class="bi bi-x-octagon"></i> LOTE VENCIDO â€” No se puede vender</small>';
        if (alertaPrecio) html += '<small class="text-warning fw-bold d-block"><i class="bi bi-exclamation-triangle"></i> Precio < Costo ('+_fmt(p.costo_lote)+')</small>';
        if (p.proxima_caducidad && !esVencido) html += '<small class="text-warning d-block"><i class="bi bi-calendar-x"></i> Cad: '+p.proxima_caducidad+'</small>';
        html += '</div></div></div>';
    });
    cont.innerHTML = html + '</div>';
}

// AGREGAR AL CARRITO
window.intentarAgregar = function(productoId) {
    fetch('/farmacia/api/lotes-producto/' + productoId + '/', {headers:{'X-Requested-With':'XMLHttpRequest'},credentials:'same-origin'})
    .then(function(r){ return r.ok ? r.json() : Promise.reject(r.status); })
    .then(function(data){
        var prod = data.producto || data;
        if (!prod || !prod.nombre_comercial) { alert('Producto no disponible.'); return; }
        if (prod.sin_stock_vigente) { _mostrarAlerta('Lote Vencido', prod.nombre_comercial + ': todos los lotes estÃ¡n VENCIDOS. Retire del Ã¡rea de venta.', 'danger'); return; }
        if (prod.alerta_precio_bajo) {
            if (!confirm('?? ALERTA DE RENTABILIDAD\n\n' + prod.nombre_comercial + '\nPrecio venta: ' + _fmt(prod.precio_base) + '\nCosto lote: ' + _fmt(prod.costo_lote) + '\n\nESTÃ VENDIENDO A PÃ‰RDIDA. Â¿Confirmar de todas formas?')) return;
        }
        if (prod.requiere_receta || prod.es_antibiotico || prod.es_controlado) { window._productoAntibioticoTemp = prod; abrirModalReceta(); return; }
        _agregarAlCarrito(prod);
    })
    .catch(function() {
        var buscador = document.getElementById('input-buscador');
        var term = buscador ? buscador.value : 'a';
        fetch((window.PDV_BUSCAR_URL||'/farmacia/api/buscar-producto-pdv/')+'?termino='+encodeURIComponent(term||'a'),{headers:{'X-Requested-With':'XMLHttpRequest'},credentials:'same-origin'})
        .then(function(r){return r.json();}).then(function(data){ var p=(data.productos||[]).find(function(p){return p.id==productoId;}); if(p)_agregarAlCarrito(p); });
    });
};
function _agregarAlCarrito(prod) {
    var diasRestantes = (prod.dias_restantes !== undefined && prod.dias_restantes !== null) ? prod.dias_restantes : 999;
    if (diasRestantes < 0) { _mostrarAlerta("LOTE VENCIDO", prod.nombre_comercial + " tiene un lote VENCIDO. Baja por MERMA requerida.", "danger"); return; }
    if (diasRestantes >= 0 && diasRestantes <= 7) { if (!confirm("ALERTA: " + prod.nombre_comercial + " caduca en " + diasRestantes + " dia(s). Confirmar venta?")) return; }
    var stock = prod.stock_total || prod.stock || 0;
    if (stock <= 0) { _mostrarAlerta("Sin Stock", prod.nombre_comercial + " no tiene stock.", "warning"); return; }
    var pv = window.precioNetoActivo ? (parseFloat(prod.precio_compra)||parseFloat(prod.precio_base)||0) : (parseFloat(prod.precio_base)||0);
    var costo = parseFloat(prod.precio_compra) || 0;
    if (pv > 0 && costo > 0 && pv < costo) { _mostrarAlerta("Precio bajo costo", prod.nombre_comercial + ": precio=" + _fmt(pv) + " < costo=" + _fmt(costo) + ". Verifique tarifa.", "warning"); }
    var idx = window.carrito.findIndex(function(i){ return i.id===prod.id && i.lote_id===(prod.lote_id||null); });
    if (idx >= 0) {
        if (window.carrito[idx].cantidad < stock) { window.carrito[idx].cantidad++; } else { _mostrarAlerta("Stock maximo","No hay mas unidades.","warning"); return; }
    } else {
        window.carrito.push({id:prod.id,nombre:prod.nombre_comercial||"",sustancia:prod.sustancia_activa||"",precio_base:parseFloat(prod.precio_base)||0,precio_neto:parseFloat(prod.precio_compra)||0,precio_venta:pv,iva_pct:parseFloat(prod.iva_pct)||0,cantidad:1,lote_id:prod.lote_id||null,lote_num:prod.numero_lote_proximo||"",stock:stock,dias_restantes:diasRestantes,es_antibiotico:!!prod.es_antibiotico,es_controlado:!!prod.es_controlado,requiere_receta:!!(prod.requiere_receta||prod.es_antibiotico||prod.es_controlado),costo:costo});
    }
    renderCarrito();
    _renderTabs();
    var b=document.getElementById("input-buscador"); if(b){b.value="";b.focus();}
    var c=document.getElementById("search-results-container"); if(c) c.innerHTML="<div class=\"text-center py-4 text-success\"><i class=\"bi bi-cart-check display-4\"></i><p class=\"mt-2 fw-bold\">Producto agregado.</p></div>";
}

// RENDER CARRITO
window.renderCarrito = function() {
    var tbody=document.getElementById('tabla-carrito-body'); var vacioMsg=document.getElementById('carrito-vacio'); var badge=document.getElementById('contador-items');
    if (!tbody) return;
    if (!window.carrito.length) { tbody.innerHTML=''; if(vacioMsg)vacioMsg.style.display='block'; if(badge)badge.textContent=''; _actualizarTotalesPanel(0,0,0); return; }
    if (vacioMsg) vacioMsg.style.display='none';
    var html = '';
    window.carrito.forEach(function(item,i) {
        var sub = item.precio_venta * item.cantidad;
        html += '<tr><td class="text-muted small">'+(i+1)+'</td><td><div class="fw-bold" style="font-size:.85rem">'+item.nombre+'</div><small class="text-muted">'+item.sustancia+'</small>'+(item.lote_num?'<br><span class="badge bg-light text-dark" style="font-size:.7rem">Lote:'+item.lote_num+'</span>':'')+(item.es_antibiotico?'<span class="badge bg-danger ms-1" style="font-size:.65rem">AB</span>':'')+'</td><td><small class="text-muted">'+(item.lote_num||'&mdash;')+'</small></td><td class="text-center"><div class="input-group input-group-sm" style="max-width:90px;margin:0 auto"><button class="btn btn-outline-secondary btn-sm py-0 px-1" onclick="cambiarCantidad('+i+',-1)">&minus;</button><input type="number" class="form-control text-center py-0" style="font-size:.85rem" value="'+item.cantidad+'" min="1" max="'+item.stock+'" onchange="setCantidad('+i+',this.value)"><button class="btn btn-outline-secondary btn-sm py-0 px-1" onclick="cambiarCantidad('+i+',1)">+</button></div></td><td class="text-end"><small class="text-muted d-block">'+_fmt(item.precio_venta)+'</small></td><td class="text-end fw-bold">'+_fmt(sub)+'</td><td><button class="btn btn-sm btn-outline-danger py-0 px-1" onclick="quitarItem('+i+')"><i class="bi bi-trash3"></i></button></td></tr>';
    });
    tbody.innerHTML = html;
    var t = _calcTotales(); _actualizarTotalesPanel(t.subtotal, t.iva, t.total);
    if (badge) badge.textContent = window.carrito.reduce(function(s,i){return s+i.cantidad;},0);
};
function _calcTotales() {
    var sub=0,iva=0;
    window.carrito.forEach(function(item){var s=item.precio_venta*item.cantidad;sub+=s;iva+=s*(item.iva_pct/100);});
    var sel=document.getElementById('selector-descuento'); var pd=sel?(parseFloat(sel.value)||0):0;
    var desc=sub*pd; if(window.cuponAplicado)desc=sub*(window.cuponAplicado.porcentaje/100);
    return {subtotal:sub,iva:iva,descuento:desc,total:sub-desc+iva};
}
function _actualizarTotalesPanel(sub,iva,total) {
    var s=document.getElementById('res-subtotal');var iv=document.getElementById('res-iva');var t=document.getElementById('res-total');
    if(s)s.textContent=_fmt(sub);if(iv)iv.textContent=_fmt(iva);if(t)t.textContent=_fmt(total);
}

// OPS CARRITO
window.cambiarCantidad = function(idx,delta){if(!window.carrito[idx])return;var n=window.carrito[idx].cantidad+delta;if(n<1){quitarItem(idx);return;}if(n>window.carrito[idx].stock){_mostrarAlerta('Stock maximo','No hay mas unidades.','warning');return;}window.carrito[idx].cantidad=n;renderCarrito();};
window.setCantidad = function(idx, val) {
    var n = parseInt(val);
    if (!window.carrito[idx] || isNaN(n) || n < 1) return;
    var max = window.carrito[idx].stock;
    if (n > max) {
        _mostrarAlerta('Stock insuficiente',
            'Solo hay ' + max + ' unidad(es) de "' + window.carrito[idx].nombre + '". Pedido ajustado.',
            'warning');
        n = max;
    }
    window.carrito[idx].cantidad = n;
    renderCarrito();
};
window.quitarItem = function(idx){window.carrito.splice(idx,1);renderCarrito();};
window.limpiarCarrito = function(){
    if(!window.carrito.length)return;
    if(!confirm('¿Limpiar el ticket actual?'))return;
    window.carrito=[];window.cuponAplicado=null;window.recetaActual=null;window.precioNetoActivo=false;
    if (_tabs.data[_tabs.activo]) {
        _tabs.data[_tabs.activo].carrito = [];
        _tabs.data[_tabs.activo].cupon = null;
        _tabs.data[_tabs.activo].receta = null;
    }
    renderCarrito();
    _renderTabs();
};

// MODAL PAGO
window.abrirModalPago = function(){
    if(!window.carrito.length){_mostrarAlerta('Carrito vacio','Agregue productos antes de cobrar.','info');return;}
    var t=_calcTotales();var disp=document.getElementById('pago-total-display');if(disp)disp.textContent=_fmt(t.total);
    ['p-efectivo-recibido','p-tarjeta','p-transferencia'].forEach(function(id){var el=document.getElementById(id);if(el)el.value='0.00';});
    calcularBalanceMultimodal();
    var m=_getModal('modalPago');if(m)m.show();
    setTimeout(function(){var ef=document.getElementById('p-efectivo-recibido');if(ef){ef.focus();ef.select();}},350);
};
window.recalcularTotal = function(){renderCarrito();var t=_calcTotales();var d=document.getElementById('pago-total-display');if(d)d.textContent=_fmt(t.total);calcularBalanceMultimodal();};
window.calcularBalanceMultimodal = function(){
    var disp=document.getElementById('pago-total-display');var tac=parseFloat((disp?disp.textContent:'0').replace(/[$,]/g,''))||0;
    var ef=parseFloat(document.getElementById('p-efectivo-recibido')?.value)||0;var tc=parseFloat(document.getElementById('p-tarjeta')?.value)||0;var tr=parseFloat(document.getElementById('p-transferencia')?.value)||0;
    var pagado=ef+tc+tr;var dif=pagado-tac;
    var cc=document.getElementById('cambio-container');var fc=document.getElementById('falta-container');var rv=document.getElementById('resumen-vacio');var bf=document.getElementById('btn-finalizar');var ca=document.getElementById('cambio-amount');var fa=document.getElementById('falta-amount');
    if(dif>=0){if(cc)cc.style.display='block';if(fc)fc.style.display='none';if(rv)rv.style.display='none';if(ca)ca.textContent=_fmt(dif);if(bf)bf.disabled=false;}
    else if(pagado>0){if(cc)cc.style.display='none';if(fc)fc.style.display='block';if(rv)rv.style.display='none';if(fa)fa.textContent=_fmt(Math.abs(dif));if(bf)bf.disabled=true;}
    else{if(cc)cc.style.display='none';if(fc)fc.style.display='none';if(rv)rv.style.display='flex';if(bf)bf.disabled=true;}
};

// ENVIAR VENTA
window.enviarVenta = function(){
    if(!window.carrito.length)return;
    var bf=document.getElementById('btn-finalizar');if(bf){bf.disabled=true;bf.innerHTML='<span class="spinner-border spinner-border-sm"></span> Procesando...';}
    var t=_calcTotales();
    var ef=parseFloat(document.getElementById('p-efectivo-recibido')?.value)||0;var tc=parseFloat(document.getElementById('p-tarjeta')?.value)||0;var tr=parseFloat(document.getElementById('p-transferencia')?.value)||0;
    var cambio=Math.max(0,ef+tc+tr-t.total);
    var pagos=[];if(ef>0)pagos.push({metodo:'EFECTIVO',monto:ef});if(tc>0)pagos.push({metodo:'TARJETA',monto:tc});if(tr>0)pagos.push({metodo:'TRANSFERENCIA',monto:tr});
    var ec=document.getElementById('toggle-cortesia')?.checked||false;
    var cl=document.getElementById('p-cliente');var pid=document.getElementById('p-paciente-id');var sel=document.getElementById('selector-descuento');
    var pd=(sel?(parseFloat(sel.value)||0):0)*100;
    var items=window.carrito.map(function(item){return{producto_id:item.id,cantidad:item.cantidad,precio_unitario:item.precio_venta,subtotal:item.precio_venta*item.cantidad,iva_item:(item.precio_venta*item.cantidad)*(item.iva_pct/100),lote_id:item.lote_id||null};});
    var payload={items:items,pagos:pagos,subtotal:t.subtotal.toFixed(2),iva_total:t.iva.toFixed(2),redondeo:'0',total_final:t.total.toFixed(2),descuento_aplicado:t.descuento.toFixed(2),descuento_porcentaje:pd,total_original:t.subtotal.toFixed(2),cliente:(cl?.value?.trim()||'PUBLICO GENERAL'),paciente_id:pid?.value||null,efectivo_recibido:ef.toFixed(2),cambio_entregado:cambio.toFixed(2),es_cortesia:ec,motivo_cortesia:document.getElementById('motivo-cortesia')?.value||'',autorizado_por_cortesia:document.getElementById('autorizado-por-cortesia')?.value||'',codigo_cupon:window.cuponAplicado?.codigo||'',receta_id:window.recetaActual?window.recetaActual.id||null:null,medico_nombre:window.recetaActual?window.recetaActual.medico||'':'',medico_cedula:window.recetaActual?window.recetaActual.cedula||'':'',receta_fecha:window.recetaActual?window.recetaActual.fecha||'':'',numero_receta_externo:window.recetaActual?window.recetaActual.numero_externo||'':'',informacion_adicional:window.recetaActual?window.recetaActual.info_adicional||'':'',es_controlada:window.carrito.some(function(i){return !!(i.requiere_receta||i.es_antibiotico);})};
    fetch('/farmacia/pdv/',{method:'POST',headers:{'Content-Type':'application/json','X-CSRFToken':_csrf(),'X-Requested-With':'XMLHttpRequest'},credentials:'same-origin',body:JSON.stringify(payload)})
    .then(function(r){return r.json();})
    .then(function(data){if(data.status==='success'){window.ventaActualId=data.venta_id;window.ventaActualFolio=data.folio;_onVentaExitosa(data,cambio);}else{throw new Error(data.mensaje||'Error al procesar la venta.');}})
    .catch(function(err){_mostrarAlerta('Error',''+err,'danger');if(bf){bf.disabled=false;bf.innerHTML='FINALIZAR VENTA';}});
};
function _onVentaExitosa(data, cambio) {
    // SPRINT 1.6: Impresion asincrona - carrito limpio en < 10ms
    var mp = _getModal('modalPago'); if (mp) mp.hide();

    // 1. Limpiar carrito INMEDIATAMENTE - cajero puede empezar la siguiente venta ya
    window.carrito = [];
    window.cuponAplicado = null;
    window.recetaActual = null;
    window.precioNetoActivo = false;
    renderCarrito();
    var buscador = document.getElementById('input-buscador');
    if (buscador) { buscador.value = ''; setTimeout(function() { buscador.focus(); }, 60); }

    // 2. Guardar referencia de la venta para impresion
    window.ventaActualId = data.venta_id;
    window.ventaActualFolio = data.folio;

    // 3. Actualizar datos del modal de exito
    var ef = document.getElementById('exito-folio');
    var es = document.getElementById('exito-sello');
    var ecc = document.getElementById('exito-cambio-container');
    var eca = document.getElementById('exito-cambio-amount');
    if (ef) ef.textContent = 'Folio: ' + (data.folio || data.venta_id);
    if (es) es.textContent = 'Sello: ' + (data.sello || 'â€”');
    if (ecc) ecc.style.display = cambio > 0 ? 'block' : 'none';
    if (eca && cambio > 0) eca.textContent = _fmt(cambio);

    // 4. Mostrar modal de exito y disparar impresion en background (setTimeout 0 = async)
    setTimeout(function() {
        var me = _getModal('modalExito'); if (me) me.show();
    }, 0);
    setTimeout(function() {
        if (window.AUTO_PRINT_TICKET && data.venta_id) imprimirTicketVenta();
    }, 0);
}

// NUEVA VENTA — limpia el tab actual y actualiza estado global de tabs
window.startNewSale = function(){
    var me=_getModal('modalExito');if(me)me.hide();
    window.carrito=[];window.cuponAplicado=null;window.recetaActual=null;window.precioNetoActivo=false;
    // Limpiar también el estado del tab activo
    if (_tabs.data[_tabs.activo]) {
        _tabs.data[_tabs.activo] = { carrito: [], receta: null, cupon: null, paciente: '', pacienteId: null, precioNeto: false };
    }
    renderCarrito();
    _renderTabs();
    ['p-efectivo-recibido','p-tarjeta','p-transferencia'].forEach(function(id){var el=document.getElementById(id);if(el)el.value='0.00';});
    var b=document.getElementById('input-buscador');if(b){b.value='';b.focus();}
};

// IMPRESION
window.imprimirTicketVenta = function(){
    if(!window.ventaActualId){alert('No hay venta activa.');return;}
    fetch('/farmacia/pdv/?accion=detalle_venta&id='+window.ventaActualId,{headers:{'X-Requested-With':'XMLHttpRequest'},credentials:'same-origin'})
    .then(function(r){return r.json();}).then(function(v){_imprimirData(v);}).catch(function(){alert('Error al obtener ticket.');});
};
function _imprimirData(v){
    var win=window.open('','_blank','width=320,height=600');if(!win){alert('Permita ventanas emergentes.');return;}
    var rows=(v.items||v.detalles||[]).map(function(i){return '<tr><td>'+(i.producto||i.nombre||'')+'</td><td style="text-align:right">'+i.cantidad+'</td><td style="text-align:right">$'+parseFloat(i.subtotal||0).toFixed(2)+'</td></tr>';}).join('');
    var cfdiHtml='';
    if(v.facturas_cfdi&&v.facturas_cfdi.length){
        cfdiHtml='<div class="d"></div><div style="font-size:10px;line-height:1.3"><strong>CFDI</strong><br>'+
        v.facturas_cfdi.map(function(x){
            var st=x.estado==='TIMBRADO'?'TIMBRADA':(x.estado==='ERROR'?'ERROR':(x.estado==='FACTURANDO'?'EN PAC':'BORRADOR'));
            var line=(x.folio_interno||'')+' - '+st;
            var links='';
            if(x.gestionar_url){links+=' <a href="'+x.gestionar_url+'" target="_blank" rel="noopener">Gestionar</a>';}
            if(x.pdf_url){links+=' <a href="'+x.pdf_url+'" target="_blank" rel="noopener">PDF</a>';}
            if(x.xml_url){links+=' <a href="'+x.xml_url+'" target="_blank" rel="noopener">XML</a>';}
            if(x.ultimo_error_pac){line+='<br><span style="color:#a00">'+String(x.ultimo_error_pac).substring(0,220)+'</span>';}
            return line+links;
        }).join('<br><br>')+'</div>';
    }
    win.document.write('<!DOCTYPE html><html><head><meta charset="UTF-8"><style>body{font-family:monospace;font-size:12px;margin:8px}table{width:100%}th,td{padding:2px 4px}.t{font-size:16px;font-weight:bold;text-align:right}.d{border-top:1px dashed #000;margin:4px 0}@media print{button{display:none}}a{color:#0366d6}</style></head><body><div style="text-align:center"><strong>PRIMERO SALUD LABORATORIO</strong><br><small>Ticket: '+(v.folio||'&mdash;')+'</small><br><small>'+(v.fecha||'')+'</small></div><div class="d"></div><table><tr><th>Producto</th><th>Cant</th><th>Total</th></tr>'+rows+'</table><div class="d"></div><div class="t">TOTAL: $'+parseFloat(v.total||0).toFixed(2)+'</div>'+cfdiHtml+'<div class="d"></div><small>Cajero: '+(v.cajero||'&mdash;')+'</small><br><button onclick="window.print()">Imprimir</button><script>window.onload=function(){window.print();}<\/script></body></html>');
    win.document.close();
}
window.enviarWhatsApp = function(){
    var num=(document.getElementById('whatsapp-numero')?.value||'').replace(/\D/g,'');
    if(num.length<10){alert('Ingrese numero de 10 digitos.');return;}
    var msg=encodeURIComponent('Compra PRISLAB\nFolio: '+(window.ventaActualFolio||'&mdash;')+'\nGracias.');
    window.open('https://wa.me/52'+num+'?text='+msg,'_blank');
};

// ANTIBIOTICOS
window.abrirModalReceta = function(){var m=_getModal('modalReceta');if(m)m.show();};
window.validarReceta = function () {
    var medico   = (document.getElementById('rec-medico') ? document.getElementById('rec-medico').value : '').trim();
    var cedula   = (document.getElementById('rec-cedula') ? document.getElementById('rec-cedula').value : '').trim();
    var fechaEl  = document.getElementById('rec-fecha');
    var fecha    = fechaEl ? fechaEl.value : new Date().toISOString().split('T')[0];
    var numExtEl = document.getElementById('rec-numero-externo');
    var numExt   = numExtEl ? numExtEl.value.trim() : '';
    var infoAdEl = document.getElementById('rec-info-adicional');
    var infoAd   = infoAdEl ? infoAdEl.value.trim() : '';

    if (!medico || !cedula) {
        _mostrarAlerta('Datos incompletos', 'Ingrese nombre del medico y cedula profesional.', 'warning');
        return;
    }

    // Validacion frontend: receta mayor a 30 dias
    if (fecha) {
        var emision = new Date(fecha + 'T00:00:00');
        var diasAntig = Math.floor((Date.now() - emision.getTime()) / 86400000);
        if (diasAntig > 30) {
            _mostrarAlerta('Receta vencida',
                'La receta tiene ' + diasAntig + ' dias de antiguedad (max. 30). No puede ser aceptada.',
                'danger');
            var alertaEl = document.getElementById('rec-fecha-alerta');
            if (alertaEl) alertaEl.style.display = 'block';
            return;
        }
    }
    var alertaEl2 = document.getElementById('rec-fecha-alerta'); if (alertaEl2) alertaEl2.style.display = 'none';

    window.recetaActual = { medico: medico, cedula: cedula, fecha: fecha, numero_externo: numExt, info_adicional: infoAd };
    var m = _getModal('modalReceta'); if (m) m.hide();
    if (window._productoAntibioticoTemp) { _agregarAlCarrito(window._productoAntibioticoTemp); window._productoAntibioticoTemp = null; }
};
window.handleCancelAntibiotic = function(){window._productoAntibioticoTemp=null;var m=_getModal('modalReceta');if(m)m.hide();};

// CORTESIA / PRECIO NETO
window.toggleCortesiaFarmacia = function(){var chk=document.getElementById('toggle-cortesia');var c=document.getElementById('campos-cortesia-farmacia');if(c)c.style.display=chk?.checked?'block':'none';calcularBalanceMultimodal();};
window.solicitarPinStaff = function(){var m=_getModal('modalPinStaff');if(m)m.show();setTimeout(function(){var inp=document.getElementById('input-pin-staff');if(inp){inp.value='';inp.focus();}},300);};
window.confirmarPinStaff = function(){
    var pin=document.getElementById('input-pin-staff')?.value||'';
    fetch('/api/validar-pin-staff/',{method:'POST',headers:{'Content-Type':'application/json','X-CSRFToken':_csrf(),'X-Requested-With':'XMLHttpRequest'},credentials:'same-origin',body:JSON.stringify({pin:pin})})
    .then(function(r){return r.json();})
    .then(function(data){
        var e=document.getElementById('pin-error-msg');
        if(data.valid||data.ok){window.precioNetoActivo=true;window.carrito.forEach(function(item){item.precio_venta=item.precio_neto||item.precio_base;});renderCarrito();var m=_getModal('modalPinStaff');if(m)m.hide();var b=document.getElementById('badge-neto-activo');if(b)b.style.display='block';var bd=document.getElementById('btn-desactivar-neto');if(bd)bd.style.display='inline-block';}
        else{if(e)e.style.display='block';}
    }).catch(function(){var e=document.getElementById('pin-error-msg');if(e)e.style.display='block';});
};
window.desactivarPrecioNeto = function(){window.precioNetoActivo=false;window.carrito.forEach(function(item){item.precio_venta=item.precio_base;});renderCarrito();var b=document.getElementById('badge-neto-activo');if(b)b.style.display='none';var bd=document.getElementById('btn-desactivar-neto');if(bd)bd.style.display='none';};

// CUPON
window.aplicarCupon = function(){
    var codigo=(document.getElementById('p-cupon-codigo')?.value||'').trim();if(!codigo)return;
    fetch('/farmacia/pdv/?accion=validar_cupon&codigo='+encodeURIComponent(codigo),{headers:{'X-Requested-With':'XMLHttpRequest'},credentials:'same-origin'})
    .then(function(r){return r.json();})
    .then(function(data){
        var ic=document.getElementById('info-cupon');var tc=document.getElementById('texto-cupon');
        if(data.valido){window.cuponAplicado={codigo:codigo,porcentaje:data.porcentaje};if(ic){ic.className='alert alert-success py-1 px-2 mt-1 small';ic.style.display='block';}if(tc)tc.textContent=data.porcentaje+'% de descuento aplicado.';}
        else{window.cuponAplicado=null;if(ic){ic.className='alert alert-danger py-1 px-2 mt-1 small';ic.style.display='block';}if(tc)tc.textContent='Cupon invalido o expirado.';}
        recalcularTotal();
    }).catch(function(){window.cuponAplicado=null;});
};

// BUSQUEDA PACIENTE
window.buscarPaciente = function(val){
    if(!val||val.length<3){var r=document.getElementById('resultados-pacientes');if(r)r.style.display='none';return;}
    fetch('/api/buscar-paciente/?q='+encodeURIComponent(val),{headers:{'X-Requested-With':'XMLHttpRequest'},credentials:'same-origin'})
    .then(function(r){return r.json();})
    .then(function(data){
        var c=document.getElementById('resultados-pacientes');if(!c)return;
        if(!data.pacientes?.length){c.style.display='none';return;}
        c.innerHTML=data.pacientes.map(function(p){return '<a href="#" class="list-group-item list-group-item-action py-1" onclick="seleccionarPaciente('+p.id+',\''+p.nombre_completo+'\');return false;">'+p.nombre_completo+'</a>';}).join('');
        c.style.display='block';
    }).catch(function(){});
};
window.seleccionarPaciente = function(id,nombre){var i=document.getElementById('p-cliente');if(i)i.value=nombre;var h=document.getElementById('p-paciente-id');if(h)h.value=id;var c=document.getElementById('resultados-pacientes');if(c)c.style.display='none';};

// GASTO / RETIRO
window.pedirGasto = function(){
    var monto=prompt('Monto del retiro ($):');if(!monto||isNaN(parseFloat(monto)))return;
    var motivo=prompt('Motivo del retiro:')||'Retiro de caja';
    fetch('/farmacia/pdv/',{method:'POST',headers:{'Content-Type':'application/json','X-CSRFToken':_csrf(),'X-Requested-With':'XMLHttpRequest'},credentials:'same-origin',body:JSON.stringify({accion:'registrar_gasto',monto:parseFloat(monto),motivo:motivo})})
    .then(function(r){return r.json();}).then(function(data){if(data.status==='success'){_mostrarAlerta('Retiro registrado',_fmt(monto)+' registrado.','info');}else{_mostrarAlerta('Error',data.mensaje||'Error.','warning');}}).catch(function(){_mostrarAlerta('Sin conexion','No se pudo conectar.','warning');});
};

// CORTE
window.cargarCorte = function(){window.location.href='/farmacia/corte-caja/';};

// TABS MULTIPLES
var _tickets={1:[]};var _ticketActual=1;
window.switchTicket = function(n){_tickets[_ticketActual]=[...window.carrito];_ticketActual=n;window.carrito=_tickets[n]||[];renderCarrito();document.querySelectorAll('#ticketTabs .nav-link').forEach(function(el){el.classList.remove('active','bg-white');});};
window.nuevoTicket = function(){_tickets[_ticketActual]=[...window.carrito];var ids=Object.keys(_tickets).map(Number);var nId=Math.max.apply(null,ids)+1;_tickets[nId]=[];var tabs=document.getElementById('ticketTabs');if(tabs){var li=document.createElement('li');li.className='nav-item';li.innerHTML='<a class="nav-link" href="#" onclick="switchTicket('+nId+')"><i class="bi bi-receipt"></i> Ticket '+nId+'</a>';tabs.insertBefore(li,tabs.lastElementChild);}window.switchTicket(nId);};

// TECLADO VIRTUAL
window.typeKey = function(key){var a=document.activeElement;if(!a||!['INPUT','TEXTAREA'].includes(a.tagName))return;if(key==='BACK'){a.value=a.value.slice(0,-1);}else if(key==='ENTER'){a.dispatchEvent(new KeyboardEvent('keydown',{key:'Enter',bubbles:true}));}else{a.value+=key;}a.dispatchEvent(new Event('input',{bubbles:true}));};
window.toggleVirtualKeyboard = function(){var kb=document.getElementById('virtual-keyboard');if(!kb)return;kb.style.display=(kb.style.display==='none'||kb.style.display==='')?'block':'none';};
window.toggleShortcutsModal = function(){var m=_getModal('modalShortcuts');if(m)m.toggle();};

// ASISTENTE IA
window.enviarConsultaIA = function(){
    var inp=document.getElementById('ia-input');var msg=inp?.value?.trim()||'';if(!msg)return;if(inp)inp.value='';
    var mensajes=document.getElementById('ia-mensajes');if(mensajes)mensajes.innerHTML+='<div class="text-end mb-2"><span class="badge bg-primary">'+msg+'</span></div>';
    fetch('/pris/api/',{method:'POST',headers:{'Content-Type':'application/json','X-CSRFToken':_csrf(),'X-Requested-With':'XMLHttpRequest'},credentials:'same-origin',body:JSON.stringify({mensaje:msg,contexto:'farmacia_pdv'})})
    .then(function(r){return r.json();}).then(function(data){if(mensajes){mensajes.innerHTML+='<div class="mb-2"><div class="alert alert-light py-2">'+(data.respuesta||data.message||'...')+'</div></div>';mensajes.scrollTop=mensajes.scrollHeight;}}).catch(function(){if(mensajes)mensajes.innerHTML+='<div class="alert alert-warning py-1 small">PRIS no disponible.</div>';});
};

// ATAJOS TECLADO
document.addEventListener('keydown',function(e){
    var tag=document.activeElement.tagName;
    if(e.key==='F2'){e.preventDefault();var b=document.getElementById('input-buscador');if(b){b.focus();b.select();}}
    if(e.key==='F4'){e.preventDefault();abrirModalPago();}
    if(e.key==='F8'){e.preventDefault();imprimirTicketVenta();}
    if(e.key==='F10'){e.preventDefault();cargarCorte();}
    if(e.key==='Delete'&&!['INPUT','TEXTAREA'].includes(tag)){limpiarCarrito();}
    if(e.key==='Enter'&&document.getElementById('modalExito')?.classList.contains('show')){startNewSale();}
});


// -- SPRINT 1.4: BARCODE SCANNER GLOBAL BUFFER -----------------------------
// Detecta secuencias rapidas (escaner) aunque el foco NO este en el buscador.
// Patron: >= 5 caracteres en < 80ms seguidos de Enter = codigo de barras.
(function () {
    var _bcBuf = '', _bcLastKey = 0;
    document.addEventListener('keydown', function (e) {
        var tag = document.activeElement ? document.activeElement.tagName : '';
        var eid = document.activeElement ? document.activeElement.id : '';
        // No interceptar si el foco esta en un campo de entrada distinto al buscador
        if (['INPUT', 'TEXTAREA'].includes(tag) && eid !== 'input-buscador') return;

        var now = Date.now();
        if (now - _bcLastKey > 120) _bcBuf = ''; // resetear si pausa > 120ms (tipeo humano vs scanner)
        _bcLastKey = now;

        if (e.key === 'Enter') {
            if (_bcBuf.length >= 4) {
                // Secuencia rapida + Enter = codigo de barras detectado
                e.preventDefault(); e.stopPropagation();
                var codigo = _bcBuf; _bcBuf = '';
                var buscador = document.getElementById('input-buscador');
                if (buscador) buscador.value = codigo;
                console.log('[PDV] Escaner detectado, codigo:', codigo);
                // Busqueda inmediata sin esperar debounce
                var _spScan = document.getElementById('spinner-busqueda');
                if (_spScan) _spScan.classList.remove('d-none');
                var contScan = document.getElementById('search-results-container');
                if (window.PDV_BUSCAR_FRAGMENT_URL) {
                    var _u = window.PDV_BUSCAR_FRAGMENT_URL + (window.PDV_BUSCAR_FRAGMENT_URL.indexOf('?') >= 0 ? '&' : '?') + 'q=' + encodeURIComponent(codigo);
                    fetch(_u, { credentials: 'include', headers: { 'X-Requested-With': 'XMLHttpRequest', 'Accept': 'text/html', 'Cache-Control': 'no-cache' } })
                        .then(function (r) { return r.text().then(function (t) { return { ok: r.ok, status: r.status, text: t }; }); })
                        .then(function (res) {
                            if (!res.ok) {
                                if (_spScan) _spScan.classList.add('d-none');
                                if (contScan) {
                                    contScan.innerHTML = '<div class="text-center py-3 text-danger small">Error ' + res.status + ' al buscar codigo.</div>';
                                }
                                return;
                            }
                            if (typeof _pdvInyectarHtmlFragmento === 'function') {
                                _pdvInyectarHtmlFragmento(res.text, contScan, _spScan, { autoUnico: true });
                            } else if (contScan) { contScan.innerHTML = res.text || ''; }
                        })
                        .catch(function (e) { if (_spScan) _spScan.classList.add('d-none'); console.error('[PDV] Escaner error:', e); });
                } else {
                    var _urlScan = (window.PDV_BUSCAR_URL || '/farmacia/api/buscar-producto-pdv/') + '?termino=' + encodeURIComponent(codigo);
                    fetch(_urlScan, {headers:{'X-Requested-With':'XMLHttpRequest','Accept':'application/json'},credentials:'include'})
                        .then(function(r){ return r.ok ? r.json() : Promise.reject(r.status); })
                        .then(function(data){
                            if (_spScan) _spScan.classList.add('d-none');
                            console.log('[PDV] Escaner resultados:', (data.productos||[]).length);
                            _renderResultados(data.productos || [], codigo);
                            if ((data.productos||[]).length === 1 && typeof window.intentarAgregar === 'function') {
                                setTimeout(function(){ window.intentarAgregar(data.productos[0].id); }, 80);
                            }
                        })
                        .catch(function(e){ if (_spScan) _spScan.classList.add('d-none'); console.error('[PDV] Escaner error:', e); });
                }
                if (buscador) buscador.focus();
            }
            _bcBuf = '';
        } else if (e.key.length === 1 && !e.ctrlKey && !e.altKey && !e.metaKey) {
            _bcBuf += e.key;
        }
    }, true); // capture phase = maxima prioridad
}());

// INIT
window.initPdvFarmacia = function() {
    renderCarrito();
    window.initPdvBuscador();
};
document.addEventListener('DOMContentLoaded', function(){
    window.initPdvFarmacia();
});
window.addEventListener('pageshow', function(){
    window.initPdvFarmacia();
});
if (document.readyState === 'interactive' || document.readyState === 'complete') {
    setTimeout(function(){
        window.initPdvFarmacia();
    }, 0);
}
