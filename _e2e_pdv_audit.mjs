/**
 * Auditoría E2E PDV — producción (sin credenciales en repo).
 * Ejecutar: node _e2e_pdv_audit.mjs
 * Opcional: PDV_USER=... PDV_PASS=... para login y prueba completa.
 */
import { chromium } from 'playwright';

const BASE = (process.env.BASE_URL || 'https://prislab-saas-811785477499.us-central1.run.app').replace(/\/$/, '');
const PDV_PATH = process.env.PDV_PATH || '/farmacia/pdv/';
const PDV = `${BASE}${PDV_PATH}`;

const user = process.env.PDV_USER || '';
const pass = process.env.PDV_PASS || '';
const STORAGE = process.env.OMNI_STORAGE_STATE || '';

const networkLog = [];
const consoleLog = [];
const resource404 = [];
const requestFailed = [];

async function main() {
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({
    ignoreHTTPSErrors: true,
    userAgent: 'PRISLAB-E2E-Audit/1.0',
    storageState: STORAGE || undefined,
  });
  const page = await context.newPage();

  page.on('console', (msg) => {
    const t = msg.type();
    const tx = msg.text();
    if (t === 'error' && /favicon\.ico/i.test(tx)) return;
    if (t === 'error' && /net::err_aborted/i.test(tx)) return;
    consoleLog.push({ type: t, text: tx });
  });

  page.on('requestfailed', (req) => {
    try {
      const failureText = req.failure() ? req.failure().errorText : 'unknown';
      if (/net::err_aborted/i.test(failureText)) {
        const u = req.url().split('?')[0];
        if (u.endsWith('/chat/api/conversaciones/')) return;
        if (req.resourceType() === 'fetch') return;
      }
      requestFailed.push({
        url: req.url().split('?')[0],
        method: req.method(),
        failure: failureText,
        resourceType: req.resourceType(),
      });
    } catch {
      // ignore
    }
  });

  page.on('response', async (res) => {
    const u = res.url();
    const ct = (res.headers()['content-type'] || '').toLowerCase();

    if (res.status() === 404) {
      resource404.push({ url: u.split('?')[0], contentType: ct || null });
    }

    const isFarmacia = u.includes('/farmacia/');
    const isBuscarJson = u.includes('buscar-producto-pdv');
    const isBuscarHtml = u.includes('/farmacia/pdv/buscar-fragmento');
    const isFarmaciaApi = u.includes('/farmacia/api/');
    const isPdf = ct.includes('application/pdf') || u.toLowerCase().includes('pdf');

    if (!isFarmacia && !isPdf) return;
    if (!(isBuscarJson || isBuscarHtml || isFarmaciaApi || isPdf)) return;

    let body = null;
    try {
      // Limitar tamaño: solo guardamos JSON/HTML; PDFs se registran sin body.
      if (ct.includes('application/json') || ct.includes('text/html')) {
        body = await res.text();
      }
    } catch (_) {}

    networkLog.push({
      url: u.split('?')[0],
      status: res.status(),
      contentType: ct || null,
      snippet: body && body.length < 2000 ? body : body ? body.slice(0, 500) + '…' : null,
    });
  });

  await page.goto(PDV, { waitUntil: 'networkidle', timeout: 60000 });

  const urlAfter = page.url();
  const htmlSnippet = await page.content();
  const hasInputBuscador = htmlSnippet.includes('id="input-buscador"');
  const hasOninput = htmlSnippet.includes('oninput="_pdvInputHandler') || htmlSnippet.includes('addEventListener(\'input\'');
  const swReg = await page.evaluate(() => !!navigator.serviceWorker?.controller);

  let loginAttempted = false;
  let loginPost429 = false;
  let sessionOk = false;
  let urlAfterLogin = page.url();

  const respHandler = (res) => {
    try {
      const u = res.url().split('?')[0];
      if (u.endsWith('/login/') && res.status() === 429) {
        loginPost429 = true;
      }
    } catch {
      // ignore
    }
  };

  page.on('response', respHandler);

  const preCookies = await context.cookies();
  const preSessionOk = preCookies.some((c) => c && typeof c.name === 'string' && c.name.toLowerCase() === 'sessionid');
  if (!preSessionOk && user && pass && urlAfter.includes('/login')) {
    loginAttempted = true;
    for (const waitMs of [0, 8000, 15000]) {
      if (waitMs) await page.waitForTimeout(waitMs);
      loginPost429 = false;
      await page.setExtraHTTPHeaders({ Referer: `${BASE}/login/` });
      await page.fill('input[name="username"], input#id_username', user);
      await page.fill('input[name="password"], input#id_password', pass);
      await page.click('button[type="submit"], input[type="submit"]');
      await page.waitForLoadState('networkidle', { timeout: 60000 }).catch(() => {});
      urlAfterLogin = page.url();
      const cookies = await context.cookies();
      sessionOk = cookies.some((c) => c && typeof c.name === 'string' && c.name.toLowerCase() === 'sessionid');
      const html = await page.content();
      const hasLoginForm = html.includes('name="password"') && html.includes('name="username"');
      if (sessionOk && !hasLoginForm) break;
      if (!loginPost429 && sessionOk) break;
    }
  }

  page.off('response', respHandler);

  if (preSessionOk) sessionOk = true;
  const loginSucceeded = loginAttempted ? sessionOk : preSessionOk;

  // CustomLoginView redirige por rol e IGNORA `next`.
  // Para auditar PDV, forzamos navegación al PDV tras login.
  if (loginSucceeded) {
    await page.goto(PDV, { waitUntil: 'networkidle', timeout: 60000 }).catch(() => {});
  }

  const urlAfterPdv = page.url();

  // Snapshot REAL del PDV después del goto (el anterior puede ser el HTML de /login)
  const pdvHtml = await page.content();
  const pdvHasInputBuscador = pdvHtml.includes('id="input-buscador"');
  const pdvHasOninput = pdvHtml.includes('oninput="_pdvInputHandler') || pdvHtml.includes('addEventListener(\'input\'');

  const input = page.locator('#input-buscador');
  const inputCount = await input.count();

  // Disparar búsqueda de PDV (si está visible)
  if (inputCount > 0) {
    await input.fill('');
    await input.type(process.env.PDV_QUERY || 'amox', { delay: 50 });
    await page.waitForTimeout(1500);

    // Intentar click en el primer resultado para forzar /farmacia/api/lotes-producto/<id>/
    try {
      const firstItem = page.locator('#search-results-container a.list-group-item').first();
      if ((await firstItem.count()) > 0) {
        await firstItem.click({ timeout: 5000 });
        await page.waitForTimeout(1500);
      }
    } catch (_) {
      // No bloquear auditoría si el click falla
    }
  }

  await browser.close();

  const apiCallsJson = networkLog.filter((n) => n.url.includes('buscar-producto-pdv'));
  const apiCallsHtml = networkLog.filter((n) => n.url.includes('/farmacia/pdv/buscar-fragmento'));
  const apiLotesProducto = networkLog.filter((n) => n.url.includes('/farmacia/api/lotes-producto/'));

  // Placeholder: Auditoría de PDF/Sentinel (se extenderá en el siguiente sprint del Omni-Tester)
  const pdfCalls = networkLog.filter((n) => (n.contentType || '').includes('application/pdf'));

  console.log(JSON.stringify({
    protocol: 'PRISLAB_PDV_E2E_AUDIT',
    timestamp: new Date().toISOString(),
    initialNavigation: PDV,
    finalUrl: urlAfter,
    finalUrlAfterLogin: urlAfterLogin,
    loginSucceeded,
    finalUrlAfterPdv: urlAfterPdv,
    redirectedToLogin: urlAfter.includes('/login'),
    loginEnvProvided: Boolean(user && pass),
    loginAttempted,
    loginPost429: Boolean(loginPost429),
    dom: {
      hasInputBuscador: hasInputBuscador,
      hasOninputOnPage: hasOninput,
      inputBuscadorPresent: inputCount > 0,
      pdvHasInputBuscador,
      pdvHasOninputOnPage: pdvHasOninput,
    },
    serviceWorker: { activeController: swReg },
    network_api_buscar_json: apiCallsJson,
    network_api_buscar_html: apiCallsHtml,
    network_api_lotes_producto: apiLotesProducto,
    network_pdf: pdfCalls,
    all_farmacia_api: networkLog,
    resource_404: resource404,
    request_failed: requestFailed,
    console_errors: consoleLog.filter((c) => c.type === 'error'),
    console_all: consoleLog.slice(0, 40),
  }, null, 2));
}

main().catch((e) => {
  console.error(JSON.stringify({ fatal: String(e), stack: e.stack }));
  process.exit(1);
});
