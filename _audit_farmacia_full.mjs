/**
 * Auditor Farmacia Full — revisa todas las rutas del módulo de Farmacia.
 * Ejecutar: node _audit_farmacia_full.mjs
 * Requiere: BASE_URL, E2E_USER, E2E_PASS, OMNI_BYPASS_TOKEN (opcional)
 * Opcional: OMNI_STORAGE_STATE
 */
import { chromium } from 'playwright';

const BASE = (process.env.BASE_URL || 'http://127.0.0.1:8000').replace(/\/$/, '');
const USER = process.env.E2E_USER || '';
const PASS = process.env.E2E_PASS || '';
const STORAGE = process.env.OMNI_STORAGE_STATE || '';
const BYPASS = process.env.OMNI_BYPASS_TOKEN || '';

function nowIso() { return new Date().toISOString(); }

// Rutas a auditar: [path, allowedStatuses, description]
const ROUTES = [
  // PDV principal
  ['/farmacia/', [200], 'Dashboard Farmacia'],
  ['/farmacia/pdv/', [200], 'PDV Punto de Venta'],
  ['/farmacia/pdv/buscar-fragmento/?q=amox', [200], 'PDV Buscar Fragmento HTML'],
  ['/farmacia/historial-ventas/', [200], 'Historial de Ventas'],
  ['/farmacia/dashboard/', [200], 'Dashboard Farmacia v2'],
  // Almacén
  ['/farmacia/almacen/entradas/', [200], 'Entrada de Mercancía'],
  ['/farmacia/almacen/ajustes/', [200], 'Ajustes de Inventario'],
  ['/farmacia/estadisticas/', [200], 'Estadísticas de Ventas'],
  // Control
  ['/farmacia/libro-control/', [200], 'Libro Control Antibióticos'],
  ['/farmacia/politicas-descuento/', [200], 'Políticas de Descuento'],
  // Devoluciones (core)
  ['/farmacia/devoluciones/', [200], 'Historial Devoluciones (core)'],
  // APIs JSON
  ['/farmacia/api/buscar-producto-pdv/?termino=amox', [200], 'API Buscar Producto PDV'],
  ['/farmacia/api/kpis/', [200], 'API KPIs Farmacia'],
  ['/farmacia/api/saldo-caja/', [200], 'API Saldo Caja'],
  ['/farmacia/api/buscar-productos-compra/?q=amox', [200], 'API Buscar Productos Compra'],
  ['/farmacia/api/buscar-productos-lectura/?q=amox', [200], 'API Buscar Productos Lectura'],
  // ERP Rutas (bajo /farmacia/erp/)
  ['/farmacia/erp/alertas/', [200], 'ERP Dashboard Alertas'],
  ['/farmacia/erp/kardex/', [200], 'ERP Kardex List'],
  ['/farmacia/erp/kardex/crear-movimiento/', [200], 'ERP Crear Movimiento Kardex'],
  ['/farmacia/erp/compras/registrar/', [200], 'ERP Registrar Compra'],
  ['/farmacia/erp/corte-caja/', [200], 'ERP Corte de Caja'],
  ['/farmacia/erp/generar-etiquetas/', [200], 'ERP Generar Etiquetas'],
  ['/farmacia/erp/reporte/valorizacion/', [200], 'ERP Reporte Valorización'],
  ['/farmacia/erp/devoluciones/', [200], 'ERP Dashboard Devoluciones'],
  ['/farmacia/erp/devoluciones/buscar/', [200], 'ERP Buscar Venta Devolución'],
  ['/farmacia/erp/caja/verificar/', [200], 'ERP Verificar Apertura Caja'],
  ['/farmacia/erp/caja/abrir/', [200], 'ERP Abrir Caja'],
  ['/farmacia/erp/antibioticos/reporte-cofepris/', [200], 'ERP Reporte COFEPRIS'],
  ['/farmacia/erp/semaforo-caducidad/', [200], 'ERP Semáforo Caducidad'],
  ['/farmacia/erp/stock-critico/', [200], 'ERP Stock Crítico'],
  ['/farmacia/erp/api/lotes-producto/1/', [200, 404], 'ERP API Lotes Producto'],
];

async function main() {
  if (!USER || !PASS) {
    console.log(JSON.stringify({
      protocol: 'PRISLAB_FARMACIA_FULL_AUDIT',
      timestamp: nowIso(), ok: false, fatal: 'Faltan E2E_USER/E2E_PASS.',
    }, null, 2));
    process.exit(2);
  }

  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({
    baseURL: BASE,
    ignoreHTTPSErrors: true,
    userAgent: 'PRISLAB-FARMACIA-FULL/1.0',
    storageState: STORAGE || undefined,
  });

  // Pre-login si no hay storage state
  let loginOk = false;
  if (STORAGE) {
    const cookies = await context.cookies();
    loginOk = cookies.some((c) => c && typeof c.name === 'string' && c.name.toLowerCase() === 'sessionid');
  }

  if (!loginOk) {
    const page = await context.newPage();
    const loginUrl = `${BASE}/login/`;
    try {
      for (const waitMs of [0, 8000, 15000]) {
        if (waitMs) await new Promise((r) => setTimeout(r, waitMs));
        await page.goto(loginUrl, { waitUntil: 'domcontentloaded', timeout: 45000 });
        await page.setExtraHTTPHeaders({
          Referer: loginUrl,
          ...(BYPASS ? { 'X-Omni-Bypass': BYPASS } : {}),
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
        if (loginOk) break;
      }
    } catch (e) {
      loginOk = false;
    }
    await page.close().catch(() => {});
  }

  const checks = [];
  const req = context.request;

  for (const [path, allowedStatuses, description] of ROUTES) {
    const url = `${BASE}${path}`;
    const started = Date.now();
    try {
      const resp = await req.get(url, {
        headers: {
          'x-requested-with': 'XMLHttpRequest',
          accept: 'application/json,text/html;q=0.9,*/*;q=0.8',
          ...(BYPASS ? { 'X-Omni-Bypass': BYPASS } : {}),
        },
        timeout: 30000,
      });
      const status = resp.status();
      const ct = (resp.headers()['content-type'] || '').toLowerCase();
      let snippet = null;
      if (ct.includes('application/json') || ct.includes('text/html')) {
        const t = await resp.text();
        snippet = t.length > 600 ? t.slice(0, 600) + '…' : t;
      }

      const ok = allowedStatuses.includes(status);
      checks.push({
        path,
        description,
        status,
        ok,
        allowedStatuses,
        contentType: resp.headers()['content-type'] || null,
        ms: Date.now() - started,
        snippet: ok ? null : snippet,
      });
    } catch (e) {
      checks.push({
        path,
        description,
        status: null,
        ok: false,
        allowedStatuses,
        ms: Date.now() - started,
        error: String(e),
      });
    }
  }

  await context.close().catch(() => {});
  await browser.close().catch(() => {});

  const failed = checks.filter((c) => !c.ok);
  const ok = loginOk && failed.length === 0;

  console.log(JSON.stringify({
    protocol: 'PRISLAB_FARMACIA_FULL_AUDIT',
    timestamp: nowIso(),
    baseUrl: BASE,
    login: { ok: loginOk },
    ok,
    total: checks.length,
    passed: checks.filter((c) => c.ok).length,
    failed: failed.length,
    checks,
    failures: failed,
  }, null, 2));

  if (!ok) process.exit(1);
}

main().catch((e) => {
  console.error(JSON.stringify({ protocol: 'PRISLAB_FARMACIA_FULL_AUDIT', fatal: String(e), stack: e.stack }));
  process.exit(1);
});
