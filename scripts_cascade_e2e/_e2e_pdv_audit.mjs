/**
 * E2E PDV Farmacia: búsqueda → carrito → cobro efectivo → modal éxito / lote en tabla.
 * Requiere: BASE_URL, E2E_USER, E2E_PASS, producto con stock (p. ej. paracetamol en BD).
 */
export async function runPdvAudit(page, { pushCheck, gotoAndSettle, safeScreenshot, baseUrl, outputDir }) {
  const q = (process.env.PDV_SEARCH_TERM || 'paracetamol').trim();
  await gotoAndSettle(page, `${baseUrl}/farmacia/pdv/`);
  const ss0 = await safeScreenshot(page, outputDir, 'pdv_inicio');
  if (!page.url().includes('/farmacia/pdv')) {
    pushCheck('Auditoría PDV Farmacia', 'warn', {
      summary: 'No se cargó /farmacia/pdv/ (permisos o redirección). Verifique rol FARMACIA/CAJERO.',
      url: page.url(),
    });
    return;
  }

  await page.fill('#input-buscador', q);
  await page.waitForTimeout(400);
  await page.evaluate((term) => {
    if (typeof window._pdvBuscarHTML === 'function') window._pdvBuscarHTML(term);
  }, q);
  await page.waitForSelector('#search-results-container .list-group-item', { timeout: 20000 }).catch(() => {});

  const firstHit = page.locator('#search-results-container .list-group-item').first();
  if (!(await firstHit.count())) {
    pushCheck('Auditoría PDV Farmacia', 'warn', {
      summary: `Sin resultados de búsqueda para «${q}». Cargue un producto de prueba con stock.`,
      url: page.url(),
    });
    return;
  }

  await firstHit.click();
  await page.waitForTimeout(800);

  const modalReceta = page.locator('#modalReceta.show, #modalReceta .modal.show');
  if (await modalReceta.count()) {
    await page.fill('#rec-medico', 'E2E Médico');
    await page.fill('#rec-cedula', '12345678');
    const hoy = new Date().toISOString().slice(0, 10);
    await page.fill('#rec-fecha', hoy);
    await page.click('button:has-text("CONFIRMAR DATOS")').catch(() => {});
    await page.waitForTimeout(600);
  }

  const carritoHtml = await page.locator('#tabla-carrito-body').innerHTML().catch(() => '');
  const totalText = await page.locator('#res-total').textContent().catch(() => '$0.00');
  const hasLote = /lote/i.test(carritoHtml) || /Lote:/i.test(carritoHtml);
  if (!carritoHtml || carritoHtml.length < 10) {
    pushCheck('Auditoría PDV Farmacia', 'fail', {
      summary: 'El carrito quedó vacío tras seleccionar producto.',
      url: page.url(),
    });
    return;
  }

  await page.locator('button:has-text("COBRAR")').first().click();
  await page.waitForSelector('#modalPago.show, #modalPago.modal.show', { timeout: 15000 }).catch(() => {});

  const totalNum = Number(String(totalText).replace(/[^\d.]/g, '')) || 0;
  const payAmt = totalNum > 0 ? totalNum.toFixed(2) : '10.00';
  await page.fill('#p-efectivo-recibido', payAmt);
  await page.waitForTimeout(300);
  if (typeof page.evaluate === 'function') {
    await page.evaluate(() => {
      if (typeof window.calcularBalanceMultimodal === 'function') window.calcularBalanceMultimodal();
    });
  }

  const fin = page.locator('#btn-finalizar');
  await fin.waitFor({ state: 'visible', timeout: 10000 }).catch(() => {});
  const disabled = await fin.isDisabled().catch(() => true);
  if (disabled) {
    pushCheck('Auditoría PDV Farmacia', 'warn', {
      summary: 'FINALIZAR VENTA siguió deshabilitado (monto vs total). Revise totales en modal.',
      url: page.url(),
    });
    return;
  }

  await fin.click();
  await page.waitForSelector('#modalExito.show, #modalExito.modal.show', { timeout: 25000 }).catch(() => {});
  const exito = await page.locator('#modalExito').isVisible().catch(() => false);
  const folioTxt = await page.locator('#exito-folio').textContent().catch(() => '');
  const ticketBtn = await page.locator('#btn-imprimir').isVisible().catch(() => false);

  await safeScreenshot(page, outputDir, 'pdv_exito');

  if (exito && (folioTxt || ticketBtn)) {
    pushCheck('Auditoría PDV Farmacia', 'pass', {
      summary: `Venta OK. Folio/UI: ${(folioTxt || '').slice(0, 80)}. Carrito mostró lote: ${hasLote}.`,
      url: page.url(),
    });
  } else {
    pushCheck('Auditoría PDV Farmacia', 'fail', {
      summary: 'No apareció modal de éxito (#modalExito) tras FINALIZAR VENTA.',
      url: page.url(),
    });
  }
}
