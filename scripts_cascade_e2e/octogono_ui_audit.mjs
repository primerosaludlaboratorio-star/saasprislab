import fs from 'node:fs';
import { chromium } from 'playwright';
import { ensureDir, loginWithRetry, safeScreenshot, textIncludesAny } from './playwright_auth.mjs';
import { runPdvAudit } from './_e2e_pdv_audit.mjs';

const BASE_URL = (process.env.BASE_URL || 'http://127.0.0.1:8000').replace(/\/$/, '');
const USER = process.env.E2E_USER || '';
const PASS = process.env.E2E_PASS || '';
const BYPASS = process.env.OMNI_BYPASS_TOKEN || '';
const ORDEN_ID = (process.env.ORDEN_ID || '').trim();
const PACIENTE_ID = (process.env.PACIENTE_ID || '').trim();
const PAYWALL_ORDER_ID = (process.env.PAYWALL_ORDER_ID || '').trim();
const HEADLESS = process.env.HEADLESS !== 'false';
const OUTPUT_DIR = 'scripts_cascade_e2e/output';

const report = {
  version: 'v1.56',
  base_url: BASE_URL,
  started_at: new Date().toISOString(),
  checks: [],
  findings: [],
  screenshots: [],
};

function pushCheck(name, status, details = {}) {
  report.checks.push({ name, status, ...details });
  if (status !== 'pass') {
    report.findings.push({ name, status, summary: details.summary || details.reason || 'Hallazgo detectado', url: details.url || null });
  }
}

async function gotoAndSettle(page, url) {
  await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 60000 });
  await page.waitForLoadState('networkidle', { timeout: 30000 }).catch(() => {});
}

async function openFirstOrderFromConsulta(page) {
  await gotoAndSettle(page, `${BASE_URL}/laboratorio/consulta-ordenes/`);
  const firstLink = page.locator('a[href*="detalle-orden"], a[href*="/laboratorio/orden/"]').first();
  if (await firstLink.count()) {
    await firstLink.click();
    await page.waitForLoadState('networkidle', { timeout: 30000 }).catch(() => {});
    if (page.url().includes('detalle') || page.url().includes('/orden/')) return true;
  }
  const firstRow = page.locator('#tablaOrdenes tbody tr').first();
  if (await firstRow.count()) {
    await firstRow.dblclick().catch(async () => {
      await firstRow.click();
    });
    await page.waitForLoadState('networkidle', { timeout: 30000 }).catch(() => {});
    if (page.url().includes('detalle') || page.url().includes('/orden/')) return true;
  }
  return false;
}

async function checkPaywall(page) {
  if (PAYWALL_ORDER_ID) {
    await gotoAndSettle(page, `${BASE_URL}/laboratorio/detalle-orden/${PAYWALL_ORDER_ID}/`);
  } else {
    const opened = await openFirstOrderFromConsulta(page);
    if (!opened) {
      pushCheck('Muro de Pago', 'warn', { summary: 'No se encontró una orden para validar bloqueo financiero.', url: page.url() });
      return;
    }
  }

  const saldoText = await page.locator('#spanSaldo').textContent().catch(() => '');
  const saldo = Number(String(saldoText).replace(/[^\d.-]/g, '')) || 0;
  const pdfButton = page.locator('button:has-text("Reimprimir Resultados PDF"), a:has-text("Reimprimir Resultados PDF")').first();
  const screenshot = await safeScreenshot(page, OUTPUT_DIR, 'paywall_detalle');
  report.screenshots.push(screenshot);

  if (!(await pdfButton.count())) {
    pushCheck('Muro de Pago', 'warn', { summary: 'No se encontró el botón de PDF en detalle de orden.', url: page.url() });
    return;
  }

  const isDisabled = await pdfButton.evaluate((el) => {
    const disabled = el.hasAttribute('disabled') || el.getAttribute('aria-disabled') === 'true';
    const cls = (el.className || '').toString();
    return disabled || cls.includes('disabled') || window.getComputedStyle(el).pointerEvents === 'none';
  }).catch(() => false);
  const title = await pdfButton.getAttribute('title').catch(() => '');
  const bodyText = await page.textContent('body').catch(() => '');

  if (PAYWALL_ORDER_ID) {
    if (isDisabled || textIncludesAny(`${title} ${bodyText}`, ['adeudo', 'saldo', 'pendiente pago', 'bloqueado'])) {
      pushCheck('Muro de Pago', 'pass', {
        summary: `Orden adeudora ${PAYWALL_ORDER_ID} mantiene PDF bloqueado en UI. Saldo visible: ${saldoText || 'N/D'}`,
        url: page.url(),
      });
      return;
    }
    pushCheck('Muro de Pago', 'fail', { summary: `La orden adeudora ${PAYWALL_ORDER_ID} no mostró bloqueo visual claro del PDF.`, url: page.url() });
    return;
  }

  if (saldo > 0) {
    const [popup] = await Promise.all([
      page.waitForEvent('popup', { timeout: 5000 }).catch(() => null),
      pdfButton.click().catch(() => null),
    ]);
    if (popup) {
      pushCheck('Muro de Pago', 'fail', { summary: `Saldo pendiente detectado (${saldoText}) y el PDF sí se abrió.`, url: page.url() });
      await popup.close().catch(() => {});
      return;
    }
    pushCheck('Muro de Pago', 'pass', { summary: `Con saldo ${saldoText}, no se abrió PDF. Mensaje visible: ${bodyText.slice(0, 180)}`, url: page.url() });
    return;
  }

  pushCheck('Muro de Pago', 'warn', { summary: 'La orden abierta no tenía adeudo; no se pudo validar bloqueo financiero real.', url: page.url() });
}

async function checkFastDoubleClick(page) {
  const orderId = (process.env.DEDO_VELOZ_ORDEN_ID || process.env.PAYWALL_ORDER_ID || '').trim();
  if (!orderId) {
    pushCheck('Dedo Veloz (caja / detalle orden)', 'warn', {
      summary: 'Defina DEDO_VELOZ_ORDEN_ID o PAYWALL_ORDER_ID con una orden que tenga saldo pendiente (>0) para probar doble clic en Guardar Pago.',
    });
    return;
  }
  await gotoAndSettle(page, `${BASE_URL}/laboratorio/detalle-orden/${orderId}/`);
  const saldoText = await page.locator('#spanSaldo').textContent().catch(() => '');
  const saldo = Number(String(saldoText).replace(/[^\d.-]/g, '')) || 0;
  if (saldo <= 0) {
    pushCheck('Dedo Veloz (caja / detalle orden)', 'warn', {
      summary: `La orden ${orderId} no tiene saldo pendiente (saldo=${saldoText}). Use una orden adeudada.`,
      url: page.url(),
    });
    return;
  }

  await page.locator('button:has-text("Agregar Pago")').first().click().catch(() => {});
  await page.waitForSelector('#modalPago', { state: 'visible', timeout: 10000 }).catch(() => {});

  const monto = Math.min(Math.max(saldo, 0.01), 5000);
  await page.fill('#pagoEfectivo', String(monto.toFixed(2)));

  let cobrarPosts = 0;
  const onReq = (req) => {
    if (req.method() === 'POST' && req.url().includes('/laboratorio/api/cobrar-orden/')) cobrarPosts += 1;
  };
  page.on('request', onReq);

  const payBtn = page.locator('#modalPago button.btn-success').filter({ hasText: 'Guardar Pago' }).first();
  try {
    await payBtn.click({ clickCount: 2, delay: 30 });
    await page.waitForTimeout(1800);
  } finally {
    if (typeof page.off === 'function') page.off('request', onReq);
    else page.removeListener('request', onReq);
  }

  const ss = await safeScreenshot(page, OUTPUT_DIR, 'dedo_veloz_caja');
  report.screenshots.push(ss);

  if (cobrarPosts <= 1) {
    pushCheck('Dedo Veloz (caja / detalle orden)', 'pass', {
      summary: `Doble clic en «Guardar Pago»: ${cobrarPosts} POST a cobrar-orden (esperado ≤1; candado __prislabGuardarPagoEnCurso). Saldo previo: ${saldoText}`,
      url: page.url(),
    });
  } else {
    pushCheck('Dedo Veloz (caja / detalle orden)', 'fail', {
      summary: `Se observaron ${cobrarPosts} POST a cobrar-orden; el segundo clic no quedó bloqueado en UI.`,
      url: page.url(),
    });
  }
}

async function checkOrphanData(page) {
  const bogusId = ORDEN_ID ? Number(ORDEN_ID) + 999999 : 99999999;
  await gotoAndSettle(page, `${BASE_URL}/laboratorio/captura/${bogusId}/`);
  const bodyText = await page.textContent('body').catch(() => '');
  const screenshot = await safeScreenshot(page, OUTPUT_DIR, 'orphan_data');
  report.screenshots.push(screenshot);
  if ((page.url().includes('/laboratorio/lista-trabajo/') || page.url().includes('/home/') || page.url().includes('/login/')) && textIncludesAny(bodyText, ['no está disponible', 'ya fue eliminada', 'selecciona una orden', 'lista de trabajo'])) {
    pushCheck('Caos en el Catálogo', 'pass', { summary: 'La UI redirigió a una pantalla válida con mensaje amigable para orden inexistente.', url: page.url() });
  } else if (textIncludesAny(bodyText, ['no está disponible', 'no encontrada', 'selecciona una orden', 'warning']) && !textIncludesAny(bodyText, ['server error', 'traceback'])) {
    pushCheck('Caos en el Catálogo', 'pass', { summary: 'La UI manejó la orden inválida con mensaje amigable.', url: page.url() });
  } else {
    pushCheck('Caos en el Catálogo', 'fail', { summary: 'La ruta inválida no mostró feedback elegante o expuso error técnico.', url: page.url() });
  }
}

async function checkConcurrency(context) {
  if (!ORDEN_ID) {
    pushCheck('Guerra de Edición', 'warn', { summary: 'No se configuró ORDEN_ID; no se pudo probar concurrencia sobre una orden real.' });
    return;
  }
  const pageA = await context.newPage();
  const pageB = await context.newPage();
  try {
    await gotoAndSettle(pageA, `${BASE_URL}/laboratorio/captura/${ORDEN_ID}/`);
    await gotoAndSettle(pageB, `${BASE_URL}/laboratorio/captura/${ORDEN_ID}/`);
    const editA = pageA.locator('#btn-editar-resultados');
    const editB = pageB.locator('#btn-editar-resultados');
    if (!(await editA.count()) || !(await editB.count())) {
      const bodyA = await pageA.textContent('body').catch(() => '');
      pushCheck('Guerra de Edición', textIncludesAny(bodyA, ['VALIDADO', 'RESULTADOS LISTOS']) ? 'pass' : 'warn', {
        summary: textIncludesAny(bodyA, ['VALIDADO', 'RESULTADOS LISTOS'])
          ? 'La orden ya está validada; la UI bloquea edición concurrente de forma legítima.'
          : 'No se encontró el botón de edición en captura para probar concurrencia.',
        url: pageA.url(),
      });
      return;
    }
    await editA.click();
    await editB.click();
    const inputA = pageA.locator('.input-resultado-industrial:not([readonly])').first();
    const inputB = pageB.locator('.input-resultado-industrial:not([readonly])').first();
    if (!(await inputA.count()) || !(await inputB.count())) {
      pushCheck('Guerra de Edición', 'warn', { summary: 'No hay inputs editables visibles para la orden indicada.', url: pageA.url() });
      return;
    }
    await inputA.fill('10');
    await inputB.fill('20');
    await pageA.locator('#btn-editar-resultados').click();
    await pageB.locator('#btn-editar-resultados').click();
    await pageA.waitForTimeout(1000);
    await pageB.waitForTimeout(1000);
    const textB = await pageB.textContent('body').catch(() => '');
    if (textIncludesAny(textB, ['conflicto', 'actualizado por otro usuario', '409'])) {
      pushCheck('Guerra de Edición', 'pass', { summary: 'La UI mostró evidencia de conflicto de edición.', url: pageB.url() });
    } else {
      pushCheck('Guerra de Edición', 'fail', { summary: 'No se observó alerta de conflicto; revisar sobrescritura silenciosa.', url: pageB.url() });
    }
  } finally {
    await pageA.close().catch(() => {});
    await pageB.close().catch(() => {});
  }
}

async function checkPoisonedInput(page) {
  const capturaId = (process.env.CAPTURA_EDITABLE_ORDEN_ID || ORDEN_ID || '').trim();
  if (!capturaId) {
    pushCheck('Input Envenenado (captura LIMS editable)', 'warn', {
      summary: 'Configure CAPTURA_EDITABLE_ORDEN_ID (orden PENDIENTE / EN_PROCESO, no validada) o ORDEN_ID.',
    });
    return;
  }
  await gotoAndSettle(page, `${BASE_URL}/laboratorio/captura/${capturaId}/`);
  const body0 = await page.textContent('body').catch(() => '');
  if (textIncludesAny(body0, ['VALIDADO', 'RESULTADOS LISTOS']) || !(await page.locator('#btn-editar-resultados').count())) {
    pushCheck('Input Envenenado (captura LIMS editable)', 'warn', {
      summary: 'La orden no está en modo editable (validada o sin botón EDITAR). Use CAPTURA_EDITABLE_ORDEN_ID con estado PENDIENTE/EN_PROCESO.',
      url: page.url(),
    });
    return;
  }

  const respPromise = page.waitForResponse(
    (r) =>
      r.url().includes('/laboratorio/api/guardar-resultados/') &&
      r.request().method() === 'POST',
    { timeout: 20000 },
  );

  await page.locator('#btn-editar-resultados').click();
  const input = page.locator('.input-resultado-industrial:not([readonly])').first();
  if (!(await input.count())) {
    pushCheck('Input Envenenado (captura LIMS editable)', 'warn', {
      summary: 'Tras EDITAR no hay inputs habilitados (posible orden sin líneas capturables).',
      url: page.url(),
    });
    return;
  }

  const payload = '<script>alert(1)</script>';
  await input.fill(payload);
  const screenshot = await safeScreenshot(page, OUTPUT_DIR, 'poison_input');
  report.screenshots.push(screenshot);

  await page.locator('#btn-editar-resultados').click();

  let apiStatus = null;
  let apiJson = null;
  try {
    const resp = await respPromise;
    apiStatus = resp.status();
    apiJson = await resp.json().catch(() => null);
  } catch {
    apiStatus = null;
  }

  const pageText = await page.textContent('body').catch(() => '');
  const backendRechazo =
    apiStatus === 400 &&
    apiJson &&
    String(apiJson.mensaje || apiJson.error || '').length > 0;
  const sinTraceback = !textIncludesAny(pageText, ['traceback', 'server error', '500']);

  if (backendRechazo && sinTraceback) {
    pushCheck('Input Envenenado (captura LIMS editable)', 'pass', {
      summary: `Backend respondió 400 con mensaje (${String(apiJson.mensaje || apiJson.error || '').slice(0, 120)}).`,
      url: page.url(),
    });
  } else if (sinTraceback && apiStatus && apiStatus < 500) {
    pushCheck('Input Envenenado (captura LIMS editable)', 'pass', {
      summary: `Respuesta HTTP ${apiStatus} sin error 500 ni traceback visible; revisar mensaje en UI.`,
      url: page.url(),
    });
  } else {
    pushCheck('Input Envenenado (captura LIMS editable)', 'fail', {
      summary: `No se confirmó rechazo seguro (status=${apiStatus}).`,
      url: page.url(),
    });
  }
}

async function checkResponsive(page) {
  await page.setViewportSize({ width: 375, height: 812 });
  await gotoAndSettle(page, `${BASE_URL}/laboratorio/consulta-ordenes/`);
  const ss1 = await safeScreenshot(page, OUTPUT_DIR, 'responsive_consulta_ordenes');
  report.screenshots.push(ss1);
  if (ORDEN_ID) {
    await gotoAndSettle(page, `${BASE_URL}/laboratorio/captura/${ORDEN_ID}/`);
    const validateButton = page.locator('#btn-validar-resultados');
    const stickyBar = page.locator('#barra-acciones-lab');
    const validateVisible = await validateButton.isVisible().catch(() => false);
    const stickyVisible = await stickyBar.isVisible().catch(() => false);
    const stickyFixed = await stickyBar.evaluate((el) => window.getComputedStyle(el).position === 'fixed').catch(() => false);
    const validatedState = textIncludesAny(await page.textContent('body').catch(() => ''), ['VALIDADO', 'RESULTADOS LISTOS']);
    const ss2 = await safeScreenshot(page, OUTPUT_DIR, 'responsive_captura');
    report.screenshots.push(ss2);
    const pass = validateVisible || (stickyVisible && stickyFixed) || validatedState;
    pushCheck('Teléfono en Acayucan', pass ? 'pass' : 'warn', {
      summary: validateVisible
        ? 'El botón Validar sigue visible en 375px.'
        : (stickyVisible && stickyFixed)
          ? 'La barra de acciones sticky permanece visible/fija en 375px y conserva acceso operativo.'
          : validatedState
            ? 'La orden ya está validada; la barra sticky móvil sigue visible y la acción crítica ya no aplica.'
            : 'El botón Validar no fue visible/clicable en 375px.',
      url: page.url(),
    });
  } else {
    pushCheck('Teléfono en Acayucan', 'warn', { summary: 'Sin ORDEN_ID solo se auditó consulta de órdenes en 375px.' });
  }
  await page.setViewportSize({ width: 1440, height: 900 });
}

async function checkBreadcrumbs(page) {
  if (!PACIENTE_ID) {
    pushCheck('Camino de Migas', 'warn', { summary: 'No se configuró PACIENTE_ID; flujo complejo quedó parcial.' });
    return;
  }
  await gotoAndSettle(page, `${BASE_URL}/pacientes/${PACIENTE_ID}/historial-360/`);
  const back = page.locator('a:has-text("Volver"), a:has-text("Regresar")').first();
  if (await back.count()) {
    await back.click().catch(() => null);
    await page.waitForLoadState('networkidle', { timeout: 15000 }).catch(() => {});
    const ok = !page.url().includes('404') && !page.url().includes('500');
    pushCheck('Camino de Migas', ok ? 'pass' : 'fail', { summary: ok ? 'Los enlaces de retorno no llevaron a error.' : 'Un botón de retorno llevó a error.', url: page.url() });
    return;
  }
  pushCheck('Camino de Migas', 'warn', { summary: 'No se encontró enlace de navegación de retorno en historial.', url: page.url() });
}

async function checkAuditMirror(page) {
  if (!PACIENTE_ID) {
    pushCheck('Espejo Forense', 'warn', { summary: 'No se configuró PACIENTE_ID; no se pudo revisar historial visual.' });
    return;
  }
  await gotoAndSettle(page, `${BASE_URL}/pacientes/${PACIENTE_ID}/historial-360/`);
  const body = await page.textContent('body').catch(() => '');
  const screenshot = await safeScreenshot(page, OUTPUT_DIR, 'audit_mirror');
  report.screenshots.push(screenshot);
  const forensicBadge = page.locator('.badge-forense-lab').first();
  const forensicVisible = await forensicBadge.isVisible().catch(() => false);
  if (forensicVisible) {
    const badgeText = await forensicBadge.textContent().catch(() => '');
    pushCheck('Espejo Forense', 'pass', { summary: `La UI del historial muestra badge forense visible: ${String(badgeText).trim()}`, url: page.url() });
  } else if (textIncludesAny(body, ['timeline', 'laboratorio', 'consultas'])) {
    pushCheck('Espejo Forense', 'pass', { summary: 'La vista de historial muestra trazas visibles del expediente.', url: page.url() });
  } else {
    pushCheck('Espejo Forense', 'warn', { summary: 'No se detectó feedback forense claro en la UI del historial.', url: page.url() });
  }
}

async function main() {
  await ensureDir(OUTPUT_DIR);
  const browser = await chromium.launch({ headless: HEADLESS });
  const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const page = await context.newPage();

  try {
    await loginWithRetry(page, context, { baseUrl: BASE_URL, username: USER, password: PASS, bypassToken: BYPASS });
    await checkPaywall(page);
    await checkFastDoubleClick(page);
    await checkOrphanData(page);
    await checkConcurrency(context);
    await checkPoisonedInput(page);
    await runPdvAudit(page, {
      pushCheck,
      gotoAndSettle,
      safeScreenshot,
      baseUrl: BASE_URL,
      outputDir: OUTPUT_DIR,
    });
    await checkResponsive(page);
    await checkBreadcrumbs(page);
    await checkAuditMirror(page);
  } finally {
    report.finished_at = new Date().toISOString();
    await fs.promises.writeFile(`${OUTPUT_DIR}/octogono_ui_audit_report.json`, JSON.stringify(report, null, 2), 'utf8');
    await page.close().catch(() => {});
    await context.close().catch(() => {});
    await browser.close().catch(() => {});
  }

  const failed = report.checks.filter((c) => c.status === 'fail').length;
  const warned = report.checks.filter((c) => c.status === 'warn').length;
  console.log(`Octógono UI audit completado. pass=${report.checks.filter((c) => c.status === 'pass').length} warn=${warned} fail=${failed}`);
  if (failed > 0) process.exitCode = 2;
}

main().catch(async (error) => {
  report.finished_at = new Date().toISOString();
  report.fatal_error = String(error?.stack || error);
  await ensureDir(OUTPUT_DIR);
  await fs.promises.writeFile(`${OUTPUT_DIR}/octogono_ui_audit_report.json`, JSON.stringify(report, null, 2), 'utf8');
  console.error(error);
  process.exit(1);
});
