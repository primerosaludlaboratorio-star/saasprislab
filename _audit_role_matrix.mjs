/**
 * Auditoría de Matriz de Roles/Permisos (Playwright)
 * Objetivo: detectar redirects a /login, 403 inesperados y páginas vacías por rol.
 *
 * Ejecutar:
 *   node _audit_role_matrix.mjs
 *
 * Requiere:
 *   BASE_URL, E2E_USER, E2E_PASS
 */
import { chromium } from 'playwright';

const BASE = (process.env.BASE_URL || 'http://127.0.0.1:8000').replace(/\/$/, '');
const USER = process.env.E2E_USER || '';
const PASS = process.env.E2E_PASS || '';

const TARGETS = [
  { name: 'dashboard', url: `${BASE}/dashboard/` },
  { name: 'pdv', url: `${BASE}/farmacia/pdv/` },
  { name: 'pdv_buscar_fragmento', url: `${BASE}/farmacia/pdv/buscar-fragmento/?q=am` },
  { name: 'pdv_buscar_json', url: `${BASE}/farmacia/api/buscar-producto-pdv/?termino=am` },
  { name: 'lab_worklist', url: `${BASE}/laboratorio/lista-trabajo/` },
];

function nowIso() {
  return new Date().toISOString();
}

async function main() {
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({ ignoreHTTPSErrors: true, userAgent: 'PRISLAB-ROLE-MATRIX/1.0' });
  const page = await context.newPage();

  const rows = [];

  if (!USER || !PASS) {
    await browser.close();
    console.log(JSON.stringify({ protocol: 'PRISLAB_ROLE_MATRIX', timestamp: nowIso(), ok: false, fatal: 'Faltan E2E_USER/E2E_PASS.' }, null, 2));
    process.exit(2);
  }

  await page.goto(`${BASE}/login/`, { waitUntil: 'networkidle', timeout: 60000 });
  await page.fill('input[name="username"], input#id_username', USER);
  await page.fill('input[name="password"], input#id_password', PASS);
  await page.click('button[type="submit"], input[type="submit"]');
  await page.waitForLoadState('networkidle', { timeout: 60000 }).catch(() => {});

  for (const t of TARGETS) {
    const responses = [];
    const handler = (res) => {
      if (res.url().split('?')[0] === t.url.split('?')[0]) {
        responses.push({ status: res.status(), url: res.url().split('?')[0], contentType: res.headers()['content-type'] || null });
      }
    };
    page.on('response', handler);

    let finalUrl = null;
    let hasLoginForm = false;
    let bodyLen = null;

    try {
      await page.goto(t.url, { waitUntil: 'networkidle', timeout: 60000 });
      finalUrl = page.url();
      const html = await page.content();
      bodyLen = html.length;
      hasLoginForm = html.includes('name="password"') && html.includes('name="username"');
    } catch (e) {
      rows.push({ target: t.name, url: t.url, error: String(e), responses });
      page.off('response', handler);
      continue;
    }

    const status = responses.length ? responses[responses.length - 1].status : null;
    rows.push({
      target: t.name,
      url: t.url,
      finalUrl,
      status,
      redirectedToLogin: (finalUrl || '').includes('/login') || hasLoginForm,
      bodyLen,
      responses,
    });

    page.off('response', handler);
  }

  await browser.close();

  const ok = rows.every((r) => !r.error);
  console.log(JSON.stringify({ protocol: 'PRISLAB_ROLE_MATRIX', timestamp: nowIso(), baseUrl: BASE, ok, rows }, null, 2));
}

main().catch((e) => {
  console.error(JSON.stringify({ protocol: 'PRISLAB_ROLE_MATRIX', fatal: String(e), stack: e.stack }));
  process.exit(1);
});
