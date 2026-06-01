/**
 * Auditoría "System Map Smoke" — cobertura transversal por módulo.
 * Ejecutar:
 *   node _audit_system_map_smoke.mjs
 * Requiere:
 *   BASE_URL, E2E_USER, E2E_PASS
 * Opcional:
 *   ORDEN_ID
 */
import { chromium } from 'playwright';

const BASE = (process.env.BASE_URL || 'http://127.0.0.1:8000').replace(/\/$/, '');
const USER = process.env.E2E_USER || '';
const PASS = process.env.E2E_PASS || '';
const ORDEN_ID = process.env.ORDEN_ID || '';
const STORAGE = process.env.OMNI_STORAGE_STATE || '';
const OMNI_BYPASS = process.env.OMNI_BYPASS_TOKEN || '';

function nowIso() {
  return new Date().toISOString();
}

function stripQuery(u) {
  return String(u || '').split('?')[0];
}

function normalizeOrdenId(raw) {
  const v = String(raw || '').trim();
  if (!v) return '';
  if (v.includes('${')) return '';
  return v;
}

function shouldIgnoreRequestFailed(entry) {
  const url = String(entry?.url || '');
  const failure = String(entry?.failure || '');
  const rt = String(entry?.resourceType || '');

  if (failure.includes('net::ERR_ABORTED')) return true;
  if (rt === 'font') return true;
  if (url.includes('fonts.gstatic.com')) return true;
  if (url.includes('fonts.googleapis.com')) return true;
  if (url.includes('cdn.jsdelivr.net')) return true;
  if (url.includes('cdnjs.cloudflare.com')) return true;
  return false;
}

async function loginOnce(page) {
  await page.goto(`${BASE}/login/`, { waitUntil: 'domcontentloaded', timeout: 60000 });
  await page.setExtraHTTPHeaders({
    Referer: `${BASE}/login/`,
    ...(OMNI_BYPASS ? { 'X-Omni-Bypass': OMNI_BYPASS } : {}),
  });
  await page.fill('input[name="username"], input#id_username', USER, { timeout: 15000 });
  await page.fill('input[name="password"], input#id_password', PASS, { timeout: 15000 });
  await Promise.all([
    page.waitForLoadState('domcontentloaded', { timeout: 60000 }),
    page.click('button[type="submit"], input[type="submit"]', { timeout: 15000 }),
  ]);
}

async function loginWithRetry(page, context) {
  let lastUrl = null;
  let sessionOk = false;
  let loginPost429 = false;

  const respHandler = (res) => {
    try {
      const u = stripQuery(res.url());
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
    lastUrl = page.url();
    const cookies = await context.cookies();
    sessionOk = cookies.some((c) => c && typeof c.name === 'string' && c.name.toLowerCase() === 'sessionid');
    const hasLoginForm = (await page.content()).includes('name="password"') && (await page.content()).includes('name="username"');
    if (sessionOk && !hasLoginForm) break;
    if (!loginPost429 && sessionOk) break;
  }

  page.off('response', respHandler);
  return { sessionOk, lastUrl, loginPost429 };
}

async function checkPage(page, item) {
  const responses = [];
  const handler = (res) => {
    try {
      const u = stripQuery(res.url());
      if (u === stripQuery(item.url)) {
        responses.push({ status: res.status(), url: u, contentType: res.headers()['content-type'] || null });
      }
    } catch {
      // ignore
    }
  };

  page.on('response', handler);

  let finalUrl = null;
  let bodyLen = null;
  let hasLoginForm = false;
  let error = null;

  try {
    await page.goto(item.url, { waitUntil: 'domcontentloaded', timeout: 60000 });
    finalUrl = page.url();
    const html = await page.content();
    bodyLen = html.length;
    hasLoginForm = html.includes('name="password"') && html.includes('name="username"');
  } catch (e) {
    // Navegación a PDF a veces dispara net::ERR_ABORTED aunque el response sea 200.
    // Si tenemos un response con status permitido, no lo consideramos fallo.
    error = String(e);
  }

  page.off('response', handler);

  const status = responses.length ? responses[responses.length - 1].status : null;
  const redirectedToLogin = Boolean((finalUrl || '').includes('/login')) || hasLoginForm;

  const allowed = Array.isArray(item.allowedStatus) && item.allowedStatus.length > 0 ? item.allowedStatus : [200];
  const statusOk = status === null ? false : allowed.includes(status);
  const redirectOk = item.allowRedirectToLogin ? true : !redirectedToLogin;

  // Si Playwright aborta la navegación pero el status es válido (ej. PDF), lo tratamos como ok.
  const isPdfLike = responses.some((r) => String(r.contentType || '').toLowerCase().includes('application/pdf'));
  if (error && statusOk && isPdfLike) {
    error = null;
  }

  return {
    name: item.name,
    module: item.module,
    url: item.url,
    finalUrl,
    status,
    allowedStatus: allowed,
    redirectedToLogin,
    bodyLen,
    statusOk,
    redirectOk,
    ok: !error && statusOk && redirectOk,
    error,
    responses,
  };
}

async function checkApi(ctx, item) {
  let status = null;
  let snippet = null;
  let error = null;

  try {
    const res = await ctx.get(item.url, { maxRedirects: 5 });
    status = res.status();
    try {
      const ct = (res.headers()['content-type'] || '').toLowerCase();
      if (ct.includes('application/json') || ct.includes('text/plain') || ct.includes('text/html')) {
        const t = await res.text();
        snippet = t.length <= 800 ? t : t.slice(0, 800) + '…';
      }
    } catch {
      // ignore
    }
  } catch (e) {
    error = String(e);
  }

  const allowed = Array.isArray(item.allowedStatus) && item.allowedStatus.length > 0 ? item.allowedStatus : [200];
  const statusOk = status === null ? false : allowed.includes(status);

  return {
    name: item.name,
    module: item.module,
    url: item.url,
    status,
    allowedStatus: allowed,
    statusOk,
    ok: !error && statusOk,
    error,
    snippet,
  };
}

function buildTargets() {
  const ordenId = normalizeOrdenId(ORDEN_ID);

  const ui = [
    // Core/Auth
    { module: 'core', name: 'home', url: `${BASE}/home/`, allowedStatus: [200, 302] },
    { module: 'core', name: 'dashboard', url: `${BASE}/dashboard/`, allowedStatus: [200, 302] },

    // Farmacia
    { module: 'farmacia', name: 'farmacia_dashboard', url: `${BASE}/farmacia/`, allowedStatus: [200, 302] },
    { module: 'farmacia', name: 'pdv', url: `${BASE}/farmacia/pdv/`, allowedStatus: [200, 302] },
    { module: 'farmacia', name: 'ventas_historial', url: `${BASE}/farmacia/historial-ventas/`, allowedStatus: [200, 302] },
    { module: 'farmacia', name: 'erp_alertas', url: `${BASE}/farmacia/erp/alertas/`, allowedStatus: [200, 302] },
    { module: 'farmacia', name: 'erp_kardex', url: `${BASE}/farmacia/erp/kardex/`, allowedStatus: [200, 302] },
    { module: 'farmacia', name: 'erp_corte_caja', url: `${BASE}/farmacia/erp/corte-caja/`, allowedStatus: [200, 302] },

    // Laboratorio
    { module: 'laboratorio', name: 'lab_dashboard', url: `${BASE}/laboratorio/`, allowedStatus: [200, 302] },
    { module: 'laboratorio', name: 'lab_worklist', url: `${BASE}/laboratorio/lista-trabajo/`, allowedStatus: [200, 302] },
    { module: 'laboratorio', name: 'lab_registro_resultados', url: `${BASE}/laboratorio/registro-resultados/`, allowedStatus: [200, 302] },

    // LIMS
    { module: 'lims', name: 'lims_estudios', url: `${BASE}/lims/estudios/`, allowedStatus: [200, 302] },
    { module: 'lims', name: 'lims_parametros', url: `${BASE}/lims/parametros/`, allowedStatus: [200, 302] },

    // Inventario
    { module: 'inventario', name: 'inventario_root', url: `${BASE}/inventario/`, allowedStatus: [200, 302] },
    { module: 'inventario', name: 'silo_lab_dashboard', url: `${BASE}/silo-lab/`, allowedStatus: [200, 302] },
    { module: 'inventario', name: 'silo_consultorio_dashboard', url: `${BASE}/silo-lab/consultorio/`, allowedStatus: [200, 302] },
    { module: 'inventario', name: 'silo_generales_dashboard', url: `${BASE}/silo-lab/generales/`, allowedStatus: [200, 302] },

    // Mantenimiento
    { module: 'mantenimiento', name: 'mantenimiento_root', url: `${BASE}/mantenimiento/`, allowedStatus: [200, 302] },
    { module: 'mantenimiento', name: 'cmms_equipos', url: `${BASE}/mantenimiento/equipos/`, allowedStatus: [200, 302] },
    { module: 'mantenimiento', name: 'metrologia_lista', url: `${BASE}/mantenimiento/metrologia/`, allowedStatus: [200, 302] },

    // Consultorio
    { module: 'consultorio', name: 'consultorio_dashboard', url: `${BASE}/consultorio/`, allowedStatus: [200, 302] },
    { module: 'consultorio', name: 'consultorio_agenda', url: `${BASE}/consultorio/agenda/`, allowedStatus: [200, 302] },
    { module: 'consultorio', name: 'consultorio_lista_trabajo_medico', url: `${BASE}/consultorio/medico/lista-trabajo/`, allowedStatus: [200, 302] },

    // Pacientes
    { module: 'pacientes', name: 'pacientes_lista', url: `${BASE}/pacientes/`, allowedStatus: [200, 302] },

    // Bienestar
    { module: 'bienestar', name: 'bienestar_dashboard', url: `${BASE}/bienestar/`, allowedStatus: [200, 302] },

    // Marketing
    { module: 'marketing', name: 'marketing_dashboard', url: `${BASE}/marketing/`, allowedStatus: [200, 302] },

    // Seguridad
    { module: 'seguridad', name: 'seguridad_2fa', url: `${BASE}/seguridad/2fa/`, allowedStatus: [200, 302, 403] },
    { module: 'seguridad', name: 'seguridad_sesiones', url: `${BASE}/seguridad/sesiones/`, allowedStatus: [200, 302, 403] },
    { module: 'seguridad', name: 'seguridad_auditoria', url: `${BASE}/seguridad/auditoria/`, allowedStatus: [200, 302, 403] },

    // Contabilidad
    { module: 'contabilidad', name: 'contabilidad_clientes', url: `${BASE}/contabilidad/clientes/`, allowedStatus: [200, 302] },

    // Chat
    { module: 'chat', name: 'chat_page', url: `${BASE}/chat/`, allowedStatus: [200, 302] },

    // Público
    { module: 'public', name: 'autofactura_publica', url: `${BASE}/facturacion/autofactura/`, allowedStatus: [200, 302], allowRedirectToLogin: true },
  ];

  const api = [
    // Farmacia APIs
    { module: 'farmacia', name: 'pdv_buscar_fragmento', url: `${BASE}/farmacia/pdv/buscar-fragmento/?q=am`, allowedStatus: [200, 302] },
    { module: 'farmacia', name: 'pdv_buscar_json', url: `${BASE}/farmacia/api/buscar-producto-pdv/?termino=am`, allowedStatus: [200, 302] },

    // Push/Sentinel
    { module: 'sentinel', name: 'sentinel_diagnostico', url: `${BASE}/api/sentinel/diagnostico/`, allowedStatus: [200, 302, 403] },

    // Chat APIs (pueden variar por permisos/datos)
    { module: 'chat', name: 'chat_conversaciones', url: `${BASE}/chat/api/conversaciones/`, allowedStatus: [200, 204, 302, 403] },

    // Cron endpoints deben ser 403 sin header
    { module: 'cron', name: 'cron_metrologia_noauth', url: `${BASE}/cron/check-metrologia/`, allowedStatus: [403] },
    { module: 'cron', name: 'cron_stock_noauth', url: `${BASE}/cron/check-stock-critico/`, allowedStatus: [403] },
  ];

  if (ordenId) {
    ui.push({ module: 'laboratorio', name: 'lab_imprimir', url: `${BASE}/laboratorio/imprimir/${ordenId}/`, allowedStatus: [200, 302] });
  }

  return { ui, api };
}

async function main() {
  if (!USER || !PASS) {
    console.log(JSON.stringify({ protocol: 'PRISLAB_SYSTEM_MAP_SMOKE', timestamp: nowIso(), ok: false, fatal: 'Faltan E2E_USER/E2E_PASS.' }, null, 2));
    process.exit(2);
  }

  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({
    ignoreHTTPSErrors: true,
    userAgent: 'PRISLAB-SYSTEM-MAP/1.0',
    storageState: STORAGE || undefined,
  });
  const page = await context.newPage();

  const consoleLog = [];
  const resource404 = [];
  const requestFailed = [];

  page.on('console', (msg) => {
    try {
      consoleLog.push({ type: msg.type(), text: msg.text() });
    } catch {
      // ignore
    }
  });

  page.on('requestfailed', (req) => {
    try {
      const entry = {
        url: stripQuery(req.url()),
        method: req.method(),
        failure: req.failure() ? req.failure().errorText : 'unknown',
        resourceType: req.resourceType(),
      };

      if (!shouldIgnoreRequestFailed(entry)) {
        requestFailed.push(entry);
      }
    } catch {
      // ignore
    }
  });

  page.on('response', (res) => {
    try {
      if (res.status() === 404) {
        resource404.push({ url: stripQuery(res.url()), contentType: res.headers()['content-type'] || null });
      }
    } catch {
      // ignore
    }
  });

  const { sessionOk, lastUrl: afterLoginUrl, loginPost429 } = await loginWithRetry(page, context);

  const targets = buildTargets();

  const uiChecks = [];
  for (const item of targets.ui) {
    uiChecks.push(await checkPage(page, item));
  }

  const apiChecks = [];
  for (const item of targets.api) {
    apiChecks.push(await checkApi(context.request, item));
  }

  await page.close().catch(() => {});
  await context.close().catch(() => {});
  await browser.close().catch(() => {});

  const checks = [...uiChecks, ...apiChecks];
  const ok = sessionOk && checks.every((c) => c.ok);

  console.log(
    JSON.stringify(
      {
        protocol: 'PRISLAB_SYSTEM_MAP_SMOKE',
        timestamp: nowIso(),
        baseUrl: BASE,
        login: { ok: sessionOk, afterLoginUrl, loginPost429: Boolean(loginPost429) },
        ok,
        checks,
        resource_404: resource404,
        request_failed: requestFailed,
        console_errors: consoleLog.filter((c) => c.type === 'error'),
      },
      null,
      2,
    ),
  );

  if (!ok) process.exit(1);
}

main().catch((e) => {
  console.error(JSON.stringify({ protocol: 'PRISLAB_SYSTEM_MAP_SMOKE', fatal: String(e), stack: e.stack }));
  process.exit(1);
});
