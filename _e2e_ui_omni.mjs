/**
 * Omni-Tester UI E2E (Playwright)
 * Ejecutar:
 *   node _e2e_ui_omni.mjs
 * Requiere:
 *   BASE_URL, E2E_USER, E2E_PASS
 * Opcional:
 *   PDV_QUERY (default: amox)
 */
import { chromium } from 'playwright';

const BASE = (process.env.BASE_URL || 'http://127.0.0.1:8000').replace(/\/$/, '');
const USER = process.env.E2E_USER || '';
const PASS = process.env.E2E_PASS || '';
const PDV_QUERY = process.env.PDV_QUERY || 'amox';
const STORAGE = process.env.OMNI_STORAGE_STATE || '';
const OMNI_BYPASS = process.env.OMNI_BYPASS_TOKEN || '';

const URLS = {
  login: `${BASE}/login/`,
  pdv: `${BASE}/farmacia/pdv/`,
  pdvBuscarHtml: `${BASE}/farmacia/pdv/buscar-fragmento/`,
  pdvBuscarJson: `${BASE}/farmacia/api/buscar-producto-pdv/`,
};

function nowIso() {
  return new Date().toISOString();
}

async function loginOnce(page) {
  await page.goto(URLS.login, { waitUntil: 'networkidle', timeout: 60000 });
  await page.setExtraHTTPHeaders({
    Referer: URLS.login,
    ...(OMNI_BYPASS ? { 'X-Omni-Bypass': OMNI_BYPASS } : {}),
  });
  await page.fill('input[name="username"], input#id_username', USER);
  await page.fill('input[name="password"], input#id_password', PASS);
  await page.click('button[type="submit"], input[type="submit"]');
  await page.waitForLoadState('networkidle', { timeout: 60000 }).catch(() => {});
}

async function loginWithRetry(page, context) {
  let loginPost429 = false;
  let afterLoginUrl = null;
  let sessionOk = false;

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

  for (const waitMs of [0, 8000, 15000]) {
    if (waitMs) await new Promise((r) => setTimeout(r, waitMs));
    loginPost429 = false;
    await loginOnce(page);
    afterLoginUrl = page.url();
    const cookies = await context.cookies();
    sessionOk = cookies.some((c) => c && typeof c.name === 'string' && c.name.toLowerCase() === 'sessionid');
    const html = await page.content();
    const hasLoginForm = html.includes('name="password"') && html.includes('name="username"');
    if (sessionOk && !hasLoginForm) break;
    if (!loginPost429 && sessionOk) break;
  }

  page.off('response', respHandler);
  return { sessionOk, afterLoginUrl, loginPost429 };
}

async function main() {
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({
    ignoreHTTPSErrors: true,
    userAgent: 'PRISLAB-OMNI-UI/1.0',
    storageState: STORAGE || undefined,
  });
  const page = await context.newPage();

  const consoleLog = [];
  const net = [];
  const resource404 = [];
  const requestFailed = [];

  page.on('console', (msg) => consoleLog.push({ type: msg.type(), text: msg.text() }));

  page.on('requestfailed', (req) => {
    try {
      requestFailed.push({
        url: req.url().split('?')[0],
        method: req.method(),
        failure: req.failure() ? req.failure().errorText : 'unknown',
        resourceType: req.resourceType(),
      });
    } catch (_) {}
  });

  page.on('response', async (res) => {
    const u = res.url();
    const ct = (res.headers()['content-type'] || '').toLowerCase();

    if (res.status() === 404) {
      resource404.push({ url: u.split('?')[0], contentType: ct || null });
    }

    if (!u.includes('/farmacia/')) return;
    const isInteresting =
      u.includes('/farmacia/pdv/buscar-fragmento') ||
      u.includes('/farmacia/api/buscar-producto-pdv') ||
      u.includes('/farmacia/api/') ||
      ct.includes('application/pdf');
    if (!isInteresting) return;

    let snippet = null;
    try {
      if (ct.includes('application/json') || ct.includes('text/html')) {
        const t = await res.text();
        snippet = t.length <= 800 ? t : t.slice(0, 800) + '…';
      }
    } catch (_) {}

    net.push({ url: u.split('?')[0], status: res.status(), contentType: ct || null, snippet });
  });

  if (!USER || !PASS) {
    await browser.close();
    console.log(
      JSON.stringify(
        {
          protocol: 'PRISLAB_OMNI_UI_E2E',
          timestamp: nowIso(),
          ok: false,
          fatal: 'Faltan variables de entorno E2E_USER/E2E_PASS.',
        },
        null,
        2,
      ),
    );
    process.exit(2);
  }

  const preCookies = await context.cookies();
  const preSessionOk = preCookies.some((c) => c && typeof c.name === 'string' && c.name.toLowerCase() === 'sessionid');
  const loginResult = preSessionOk ? { sessionOk: true, afterLoginUrl: page.url(), loginPost429: false } : await loginWithRetry(page, context);
  const { sessionOk, afterLoginUrl, loginPost429 } = loginResult;

  // Forzar PDV (CustomLoginView no respeta next)
  await page.goto(URLS.pdv, { waitUntil: 'networkidle', timeout: 60000 });
  const pdvUrl = page.url();

  const hasInput = (await page.locator('#input-buscador').count()) > 0;
  let searchTriggered = false;

  if (hasInput) {
    const input = page.locator('#input-buscador');
    await input.fill('');
    await input.type(PDV_QUERY, { delay: 40 });
    await page.waitForTimeout(1400);
    searchTriggered = true;
  }

  const buscarHtml = net.filter((n) => n.url.includes('/farmacia/pdv/buscar-fragmento'));
  const buscarJson = net.filter((n) => n.url.includes('/farmacia/api/buscar-producto-pdv'));

  await browser.close();

  console.log(
    JSON.stringify(
      {
        protocol: 'PRISLAB_OMNI_UI_E2E',
        timestamp: nowIso(),
        baseUrl: BASE,
        login: { attempted: true, afterLoginUrl, ok: sessionOk, loginPost429: Boolean(loginPost429) },
        pdv: { target: URLS.pdv, finalUrl: pdvUrl, hasInputBuscador: hasInput, searchTriggered, query: PDV_QUERY },
        network: { buscar_html: buscarHtml, buscar_json: buscarJson, all_farmacia: net },
        resource_404: resource404,
        request_failed: requestFailed,
        console_errors: consoleLog.filter((c) => c.type === 'error'),
      },
      null,
      2,
    ),
  );
}

main().catch((e) => {
  console.error(JSON.stringify({ protocol: 'PRISLAB_OMNI_UI_E2E', fatal: String(e), stack: e.stack }));
  process.exit(1);
});
