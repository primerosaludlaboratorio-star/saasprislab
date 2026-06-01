/**
 * Auditor API Smoke (sin UI) — robusto.
 *
 * IMPORTANTE:
 * - NO usa fetch manual para login (cookies/CSRF son muy frágiles).
 * - Usa Playwright APIRequestContext para heredar jar de cookies real.
 *
 * Ejecutar:
 *   node _audit_api_smoke.mjs
 * Requiere:
 *   BASE_URL, E2E_USER, E2E_PASS
 * Opcional:
 *   ORDEN_ID
 */

import { chromium } from 'playwright';

const BASE = (process.env.BASE_URL || 'http://127.0.0.1:8000').replace(/\/$/, '');
const USER = process.env.E2E_USER || '';
const PASS = process.env.E2E_PASS || '';
const STORAGE = process.env.OMNI_STORAGE_STATE || '';
const OMNI_BYPASS = process.env.OMNI_BYPASS_TOKEN || '';

function nowIso() {
  return new Date().toISOString();
}

async function probe(ctx, name, url, opts = {}) {
  const started = Date.now();
  try {
    const res = await ctx.get(url, {
      ...opts,
      headers: {
        'x-requested-with': 'XMLHttpRequest',
        accept: 'application/json,text/html;q=0.9,*/*;q=0.8',
        ...(opts.headers || {}),
      },
    });
    const ct = (res.headers()['content-type'] || '').toLowerCase();
    let snippet = null;
    if (ct.includes('application/json') || ct.includes('text/html') || ct.includes('text/plain')) {
      const t = await res.text();
      snippet = t.length > 900 ? t.slice(0, 900) + '…' : t;
    }
    return {
      name,
      url: url.split('?')[0],
      status: res.status(),
      contentType: res.headers()['content-type'] || null,
      ms: Date.now() - started,
      snippet,
    };
  } catch (e) {
    return {
      name,
      url: url.split('?')[0],
      status: null,
      ms: Date.now() - started,
      error: String(e),
    };
  }
}

async function main() {
  if (!USER || !PASS) {
    console.log(JSON.stringify({ protocol: 'PRISLAB_API_SMOKE', timestamp: nowIso(), ok: false, fatal: 'Faltan E2E_USER/E2E_PASS.' }, null, 2));
    process.exit(2);
  }

  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({
    baseURL: BASE,
    ignoreHTTPSErrors: true,
    storageState: STORAGE || undefined,
  });
  const page = await context.newPage();

  const loginUrl = `${BASE}/login/`;
  let loginStatus = null;
  let loginOk = false;
  let loginPost429 = false;
  if (STORAGE) {
    const cookies = await context.cookies();
    loginOk = cookies.some((c) => c && typeof c.name === 'string' && c.name.toLowerCase() === 'sessionid');
  }
  try {
    if (loginOk) {
      loginStatus = 200;
    } else {
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
      const resp = await page.goto(loginUrl, { waitUntil: 'domcontentloaded', timeout: 45000 });
      loginStatus = resp ? resp.status() : null;

      await page.setExtraHTTPHeaders({
        Referer: loginUrl,
        ...(OMNI_BYPASS ? { 'X-Omni-Bypass': OMNI_BYPASS } : {}),
      });
      await page.fill('input[name="username"], input#id_username', USER, { timeout: 15000 });
      await page.fill('input[name="password"], input#id_password', PASS, { timeout: 15000 });

      await Promise.all([
        page.waitForLoadState('domcontentloaded', { timeout: 45000 }),
        page.click('button[type="submit"], input[type="submit"]', { timeout: 15000 }),
      ]);

      const cookies = await context.cookies();
      loginOk = cookies.some((c) => c && typeof c.name === 'string' && c.name.toLowerCase() === 'sessionid');
      const html = await page.content();
      const hasLoginForm = html.includes('name="password"') && html.includes('name="username"');
      if (loginOk && !hasLoginForm) break;
      if (!loginPost429 && loginOk) break;
    }

    page.off('response', respHandler);
    }
  } catch (e) {
    loginOk = false;
  }

  const checks = [];
  const api = context.request;
  checks.push(await probe(api, 'pdv_page', `${BASE}/farmacia/pdv/`, { headers: {} }));
  checks.push(await probe(api, 'pdv_buscar_fragmento', `${BASE}/farmacia/pdv/buscar-fragmento/?q=am`, { headers: {} }));
  checks.push(await probe(api, 'pdv_buscar_json', `${BASE}/farmacia/api/buscar-producto-pdv/?termino=am`, { headers: {} }));

  const ordenId = process.env.ORDEN_ID || '';
  if (ordenId) {
    checks.push(await probe(api, 'lab_imprimir_resultados', `${BASE}/laboratorio/imprimir/${ordenId}/?guardar=1`, { headers: {} }));
    checks.push(await probe(api, 'lab_api_generar_guardar', `${BASE}/laboratorio/api/generar-reporte/${ordenId}/`, { headers: {} }));
  }

  await page.close().catch(() => {});
  await context.close().catch(() => {});
  await browser.close().catch(() => {});

  const ok = loginOk && checks.every((c) => typeof c.status === 'number' && c.status < 400);
  console.log(
    JSON.stringify(
      {
        protocol: 'PRISLAB_API_SMOKE',
        timestamp: nowIso(),
        baseUrl: BASE,
        login: { ok: loginOk, csrfTokenPresent: null, status: loginStatus, loginPost429: Boolean(loginPost429) },
        ok,
        checks,
      },
      null,
      2,
    ),
  );
  if (!ok) process.exit(1);
}

main().catch((e) => {
  console.error(JSON.stringify({ protocol: 'PRISLAB_API_SMOKE', fatal: String(e), stack: e.stack }));
  process.exit(1);
});
