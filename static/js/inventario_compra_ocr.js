/* Lectura documental de compra LAB: propuesta editable, nunca aplicación automática. */
(function () {
  "use strict";
  const open = document.getElementById("abrir-ocr-compra-lab");
  if (!open) return;
  const modal = new bootstrap.Modal(document.getElementById("modalOcrCompraLab"));
  const file = document.getElementById("documento-compra-lab-ocr");
  const analyze = document.getElementById("analizar-compra-lab");
  const confirm = document.getElementById("confirmar-compra-lab");
  const result = document.getElementById("resultado-compra-lab");
  let lecturaId = null;
  let suggestions = [];
  const csrf = document.cookie.split(";").map(x => x.trim()).find(x => x.startsWith("csrftoken="));
  const csrfToken = csrf ? decodeURIComponent(csrf.split("=").slice(1).join("=")) : "";
  open.addEventListener("click", () => modal.show());
  const prefill = document.getElementById("ocr-lab-prefill");
  if (prefill) {
    const data = JSON.parse(prefill.textContent || "{}");
    (data.items || []).forEach(item => {
      const prefix = `recibido_${item.linea_id}_`;
      const set = (suffix, value) => { const el = document.querySelector(`[name="${prefix}${suffix}"]`); if (el && value) el.value = value; };
      set("cantidad", item.cantidad); set("precio_real", item.costo_unitario); set("numero_lote", item.numero_lote);
      set("caducidad", item.fecha_caducidad); set("marca", item.marca); set("fecha_compra", item.fecha_compra);
      set("fecha_apertura", item.fecha_apertura); set("factura_numero", item.factura_numero); set("factura_fecha", item.factura_fecha);
    });
  }
  analyze.addEventListener("click", async () => {
    if (!file.files[0]) { result.innerHTML = '<div class="alert alert-danger">Adjunte una foto.</div>'; return; }
    analyze.disabled = true; result.innerHTML = '<div class="text-muted">Analizando...</div>';
    const data = new FormData(); data.append("documento_compra", file.files[0]);
    try {
      const response = await fetch(open.dataset.analizarUrl, {method: "POST", body: data, headers: {"X-CSRFToken": csrfToken}});
      const body = await response.json();
      if (!response.ok || !body.ok) throw new Error(body.error || "No fue posible leer el documento.");
      lecturaId = body.lectura_id; suggestions = body.sugerencias || [];
      result.innerHTML = '<div class="alert alert-success small">Lectura lista. Revise y edite cada dato antes de preparar la recepción.</div>' +
        suggestions.map((line, i) => {
          const options = (line.candidatos || []).map((c, j) => `<option value="${j}">${c.codigo} - ${c.nombre} (${c.marca || "sin marca"})</option>`).join("");
          return `<div class="card mb-2 p-2 ocr-lab-line" data-index="${i}">
            <div class="fw-semibold">${line.texto}</div>
            <select class="form-select form-select-sm mt-1 ocr-candidate"><option value="">Seleccione catálogo</option>${options}</select>
            <div class="row g-1 mt-1">
              <div class="col"><input class="form-control form-control-sm ocr-qty" type="number" min="0.0001" step="0.0001" value="${line.cantidad || 1}" placeholder="Cantidad"></div>
              <div class="col"><input class="form-control form-control-sm ocr-cost" type="number" min="0" step="0.0001" value="${line.costo_unitario || 0}" placeholder="Costo unitario"></div>
              <div class="col"><input class="form-control form-control-sm ocr-lot" value="${line.numero_lote || ""}" placeholder="Lote"></div>
              <div class="col"><input class="form-control form-control-sm ocr-exp" type="date" value="${line.fecha_caducidad || ""}"></div>
              <div class="col"><input class="form-control form-control-sm ocr-brand" value="${line.marca || ""}" placeholder="Marca"></div>
            </div></div>`;
        }).join("");
      confirm.disabled = !suggestions.length;
    } catch (error) { result.innerHTML = `<div class="alert alert-danger">${error.message}</div>`; }
    analyze.disabled = false;
  });
  confirm.addEventListener("click", async () => {
    const items = [...result.querySelectorAll(".ocr-lab-line")].map((row, i) => {
      const line = suggestions[i] || {}; const candidate = line.candidatos?.[Number(row.querySelector(".ocr-candidate").value)];
      const tableRows = [...document.querySelectorAll('tr[data-silo="LAB"]')];
      return {linea_id: tableRows[i]?.dataset.lineaId, reactivo_id: candidate?.reactivo_id,
        cantidad: row.querySelector(".ocr-qty").value, costo_unitario: row.querySelector(".ocr-cost").value,
        numero_lote: row.querySelector(".ocr-lot").value, fecha_caducidad: row.querySelector(".ocr-exp").value,
        marca: row.querySelector(".ocr-brand").value};
    });
    confirm.disabled = true;
    try {
      const response = await fetch(open.dataset.confirmarUrl, {method: "POST", headers: {"Content-Type": "application/json", "X-CSRFToken": csrfToken},
        body: JSON.stringify({lectura_id: lecturaId, orden_id: open.dataset.ordenId, items})});
      const body = await response.json(); if (!response.ok || !body.ok) throw new Error(body.error || "No fue posible preparar la recepción.");
      window.location.href = body.redirect;
    } catch (error) { result.insertAdjacentHTML("afterbegin", `<div class="alert alert-danger">${error.message}</div>`); confirm.disabled = false; }
  });
})();
