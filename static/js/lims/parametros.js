/**
 * PRISLAB LIMS v6.0 — Módulo de Parámetros
 * Gestión AJAX de Rangos de Referencia con Candado de Inmutabilidad
 *
 * Variables globales esperadas (inyectadas desde el template):
 *   PARAMETRO_ID  — id del parámetro actual
 *   URL_RANGOS    — endpoint base /lims/api/parametros/{id}/rangos/
 *   URL_SOFT_DEL  — endpoint soft-delete /lims/api/parametros/{id}/eliminar/
 *   CSRF_TOKEN    — token CSRF de Django
 */

'use strict';

function _headers() {
  return { 'Content-Type': 'application/json', 'X-CSRFToken': CSRF_TOKEN };
}
function _val(id) { const el = document.getElementById(id); return el ? el.value.trim() : ''; }
function _set(id, v) { const el = document.getElementById(id); if (el) el.value = (v !== null && v !== undefined) ? v : ''; }
function _sexoLabel(s) { return s === 'M' ? 'Masculino' : s === 'F' ? 'Femenino' : 'Indistinto'; }

/* ── CARGAR RANGOS ── */
async function cargarRangos() {
  const tbody = document.getElementById('tbody-rangos');
  if (!tbody) return;
  try {
    const resp = await fetch(URL_RANGOS, { credentials: 'same-origin' });
    const data = await resp.json();
    if (!resp.ok) throw new Error(data.error || 'Error al cargar rangos');
    const rangos = data.rangos || [];
    tbody.innerHTML = rangos.length === 0
      ? '<tr><td colspan="9" class="text-center text-muted py-3"><i class="bi bi-inbox me-1"></i>Sin rangos configurados.</td></tr>'
      : rangos.map(_renderFilaRango).join('');
  } catch (err) {
    tbody.innerHTML = '<tr><td colspan="9" class="text-danger text-center py-2"><i class="bi bi-exclamation-triangle-fill me-1"></i>' + err.message + '</td></tr>';
  }
}

function _renderFilaRango(r) {
  const edadStr = (r.edad_minima !== null || r.edad_maxima !== null)
    ? (r.edad_minima ?? '0') + ' - ' + (r.edad_maxima ?? 'inf')
    : '<em class="text-muted">Todas</em>';
  const rangoJSON = JSON.stringify(r).replace(/'/g, "\\'").replace(/"/g, '&quot;');
  return '<tr id="rango-row-' + r.id + '">'
    + '<td>' + _sexoLabel(r.sexo) + '</td>'
    + '<td class="text-center">' + edadStr + '</td>'
    + '<td class="text-center">' + (r.valor_minimo ?? '—') + '</td>'
    + '<td class="text-center">' + (r.valor_maximo ?? '—') + '</td>'
    + '<td class="text-center text-danger fw-bold">' + (r.panico_minimo ?? '—') + '</td>'
    + '<td class="text-center text-danger fw-bold">' + (r.panico_maximo ?? '—') + '</td>'
    + '<td>' + (r.texto_referencia || '—') + '</td>'
    + '<td class="text-center"><span class="badge bg-secondary badge-version">v' + r.version + '</span></td>'
    + '<td class="text-center">'
    + '<button class="btn btn-accion-rango btn-outline-primary me-1" onclick="abrirModalEditarRango(' + rangoJSON + ')" title="Editar (crea nueva version)"><i class="bi bi-pencil-fill"></i></button>'
    + '<button class="btn btn-accion-rango btn-outline-danger" onclick="confirmarEliminarRango(' + r.id + ')" title="Soft Delete"><i class="bi bi-trash-fill"></i></button>'
    + '</td></tr>';
}

/* ── MODAL NUEVO RANGO ── */
function abrirModalNuevoRango() {
  _set('rango-id-editando', '');
  ['rng-sexo','rng-edad-min','rng-edad-max','rng-val-min','rng-val-max','rng-panic-min','rng-panic-max','rng-texto-ref'].forEach(id => _set(id, ''));
  _set('rng-sexo', 'I');
  document.getElementById('modal-rango-titulo').textContent = 'Nuevo Rango de Referencia';
  document.getElementById('aviso-edicion-rango').style.display = 'none';
  new bootstrap.Modal(document.getElementById('modalRango')).show();
}

/* ── MODAL EDITAR RANGO ── */
function abrirModalEditarRango(rango) {
  _set('rango-id-editando', rango.id);
  _set('rng-sexo', rango.sexo);
  _set('rng-edad-min', rango.edad_minima);
  _set('rng-edad-max', rango.edad_maxima);
  _set('rng-val-min', rango.valor_minimo);
  _set('rng-val-max', rango.valor_maximo);
  _set('rng-panic-min', rango.panico_minimo);
  _set('rng-panic-max', rango.panico_maximo);
  _set('rng-texto-ref', rango.texto_referencia);
  document.getElementById('modal-rango-titulo').textContent = 'Editar Rango — v' + rango.version + ' (creará v' + (rango.version + 1) + ')';
  document.getElementById('aviso-edicion-rango').style.display = '';
  new bootstrap.Modal(document.getElementById('modalRango')).show();
}

/* ── GUARDAR RANGO ── */
async function guardarRango() {
  const rangoId = _val('rango-id-editando');
  const payload = {
    sexo: _val('rng-sexo') || 'I',
    edad_minima: _val('rng-edad-min') !== '' ? parseInt(_val('rng-edad-min')) : null,
    edad_maxima: _val('rng-edad-max') !== '' ? parseInt(_val('rng-edad-max')) : null,
    valor_minimo: _val('rng-val-min') !== '' ? _val('rng-val-min') : null,
    valor_maximo: _val('rng-val-max') !== '' ? _val('rng-val-max') : null,
    panico_minimo: _val('rng-panic-min') !== '' ? _val('rng-panic-min') : null,
    panico_maximo: _val('rng-panic-max') !== '' ? _val('rng-panic-max') : null,
    texto_referencia: _val('rng-texto-ref') || null,
  };
  const url = rangoId ? URL_RANGOS + rangoId + '/' : URL_RANGOS;
  const method = rangoId ? 'PUT' : 'POST';
  try {
    const resp = await fetch(url, { method: method, headers: _headers(), body: JSON.stringify(payload), credentials: 'same-origin' });
    const data = await resp.json();
    if (!resp.ok) throw new Error(data.error || 'Error al guardar');
    bootstrap.Modal.getInstance(document.getElementById('modalRango'))?.hide();
    await cargarRangos();
    _toastOk(rangoId ? 'Rango actualizado (nueva version creada)' : 'Rango agregado');
  } catch (err) { alert('Error: ' + err.message); }
}

/* ── ELIMINAR RANGO ── */
async function confirmarEliminarRango(rangoId) {
  if (!confirm('Eliminar este rango?\nSe cerrara su vigencia (Soft Delete).\nLos resultados historicos quedan intactos.')) return;
  try {
    const resp = await fetch(URL_RANGOS + rangoId + '/', { method: 'DELETE', headers: _headers(), credentials: 'same-origin' });
    const data = await resp.json();
    if (!resp.ok) throw new Error(data.error || 'Error al eliminar');
    await cargarRangos();
    _toastOk('Rango eliminado (historial protegido)');
  } catch (err) { alert('Error: ' + err.message); }
}

/* ── SOFT DELETE PARAMETRO ── */
function confirmarSoftDelete(paramId, paramNombre) {
  document.getElementById('sd-param-id').value = paramId;
  document.getElementById('sd-param-nombre').textContent = paramNombre;
  document.getElementById('sd-motivo').value = '';
  new bootstrap.Modal(document.getElementById('modalSoftDelete')).show();
}

async function ejecutarSoftDelete() {
  const motivo = document.getElementById('sd-motivo').value.trim();
  if (!motivo) { document.getElementById('sd-motivo').classList.add('is-invalid'); return; }
  try {
    const resp = await fetch(URL_SOFT_DEL, { method: 'POST', headers: _headers(), body: JSON.stringify({ motivo: motivo }), credentials: 'same-origin' });
    const data = await resp.json();
    if (!resp.ok) throw new Error(data.error || 'Error al desactivar');
    bootstrap.Modal.getInstance(document.getElementById('modalSoftDelete'))?.hide();
    _toastOk(data.mensaje || 'Parametro desactivado');
    setTimeout(function() { window.location.href = '/lims/parametros/'; }, 1200);
  } catch (err) { alert('Error: ' + err.message); }
}

/* ── TOAST ── */
function _toastOk(msg) {
  let c = document.getElementById('toast-container');
  if (!c) { c = document.createElement('div'); c.id = 'toast-container'; c.style.cssText = 'position:fixed;bottom:1rem;right:1rem;z-index:9999;'; document.body.appendChild(c); }
  const id = 'toast-' + Date.now();
  c.insertAdjacentHTML('beforeend', '<div id="' + id + '" class="toast align-items-center text-bg-success border-0 show" role="alert" style="font-size:12px;"><div class="d-flex"><div class="toast-body"><i class="bi bi-check-circle-fill me-1"></i>' + msg + '</div><button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button></div></div>');
  setTimeout(function() { document.getElementById(id)?.remove(); }, 3500);
}
