/**
 * PRISLAB - Human UI Audit Runner
 *
 * Objetivo:
 * - Verificar flujos reales de interfaz sin depender de extensiones de IA.
 * - Ejecutar el sistema como lo haría una persona, con navegador visible y pausas opcionales.
 * - Generar evidencia clara: JSON, Markdown y capturas.
 *
 * Uso recomendado:
 *   node tools/run_human_ui_audit.mjs --target cloud --user <usuario> --pass <clave>
 *   node tools/run_human_ui_audit.mjs --target local --base http://127.0.0.1:8000 --pause
 *
 * Variables de entorno:
 *   PRISLAB_BASE_URL   URL base principal.
 *   HUMAN_UI_USER      Usuario de prueba.
 *   HUMAN_UI_PASS      Contraseña de prueba.
 *   HUMAN_UI_HEADLESS  1 para headless, 0 o vacío para navegador visible.
 *   HUMAN_UI_PAUSE     1 para pausar entre módulos.
 *   HUMAN_UI_SLOW_MO   Milisegundos entre acciones (default 180).
 *   HUMAN_UI_QUERY     Término de búsqueda para PDV/lab (default amox).
 *   HUMAN_UI_TARGET    local | cloud (default cloud).
 */

import fs from 'node:fs';
import path from 'node:path';
import readline from 'node:readline/promises';
import { stdin as input, stdout as output } from 'node:process';
import { fileURLToPath } from 'node:url';

const { chromium } = await import('playwright');

function stamp() {
  const d = new Date();
  const pad = (n) => String(n).padStart(2, '0');
  return `${d.getFullYear()}${pad(d.getMonth() + 1)}${pad(d.getDate())}_${pad(d.getHours())}${pad(d.getMinutes())}${pad(d.getSeconds())}`;
}

function parseArgs(argv) {
  const out = {
    target: process.env.HUMAN_UI_TARGET || 'cloud',
    base: process.env.PRISLAB_BASE_URL || '',
    user: process.env.HUMAN_UI_USER || process.env.E2E_USER || '',
    pass: process.env.HUMAN_UI_PASS || process.env.E2E_PASS || '',
    headless: (process.env.HUMAN_UI_HEADLESS || '').trim() === '1',
    pause: (process.env.HUMAN_UI_PAUSE || '').trim() === '1',
    slowMo: Number(process.env.HUMAN_UI_SLOW_MO || 180),
    query: process.env.HUMAN_UI_QUERY || 'amox',
  };

  for (let i = 0; i < argv.length; i += 1) {
    const a = argv[i];
    if (a === '--target') out.target = argv[++i] || out.target;
    else if (a === '--base') out.base = argv[++i] || out.base;
    else if (a === '--user') out.user = argv[++i] || out.user;
    else if (a === '--pass') out.pass = argv[++i] || out.pass;
    else if (a === '--headless') out.headless = true;
    else if (a === '--pause') out.pause = true;
    else if (a === '--slow-mo') out.slowMo = Number(argv[++i] || out.slowMo);
    else if (a === '--query') out.query = argv[++i] || out.query;
  }

  return out;
}

function readManifest(repoRoot) {
  const manifestPath = path.join(repoRoot, 'tools', 'omni_manifest.json');
  const raw = fs.readFileSync(manifestPath, 'utf8');
  return JSON.parse(raw);
}

function resolveBaseUrl(manifest, target, explicitBase) {
  if (explicitBase) return explicitBase.replace(/\/$/, '');
  const defaultBase = manifest?.targets?.[target]?.baseUrlDefault;
  if (defaultBase) return defaultBase.replace(/\/$/, '');
  return 'http://127.0.0.1:8000';
}

function ensureDir(dir) {
  fs.mkdirSync(dir, { recursive: true });
}

async function maybePause(enabled, label) {
  if (!enabled) return;
  const rl = readline.createInterface({ input, output });
  try {
    await rl.question(`\n[PAUSA] ${label}\nPresiona Enter para continuar...`);
  } finally {
    rl.close();
  }
}

function cleanUrl(url) {
  return String(url || '').split('?')[0];
}

function hasAny(text, markers) {
  const value = String(text || '').toLowerCase();
  return markers.some((m) => value.includes(String(m).toLowerCase()));
}

async function capture(page, dir, name) {
  const file = path.join(dir, `${name}.png`);
  await page.screenshot({ path: file, fullPage: true });
  return file;
}

async function trySelectors(page, selectors) {
  for (const selector of selectors) {
    const loc = page.locator(selector).first();
    try {
      if (await loc.count()) return loc;
    } catch {
      // ignore
    }
  }
  return null;
}

async function fillIfPresent(page, selectors, value) {
  const loc = await trySelectors(page, selectors);
  if (!loc) return false;
  try {
    await loc.fill(value);
    return true;
  } catch {
    try {
      await loc.click();
      await loc.type(value, { delay: 40 });
      return true;
    } catch {
      return false;
    }
  }
}

async function clickTextIfPresent(page, texts) {
  for (const text of texts) {
    const loc = page.getByText(text, { exact: false }).first();
    try {
      if (await loc.count()) {
        await loc.click({ timeout: 3000 });
        return true;
      }
    } catch {
      // ignore
    }
  }
  return false;
}

async function pageErrorMarkers(page) {
  const html = await page.content().catch(() => '');
  const title = await page.title().catch(() => '');
  const markers = [
    'algo salió mal',
    'server error (500)',
    'internal server error',
    'traceback',
    'exception value:',
    'operationalerror at /',
    'fielderror at /',
    'permissiondenied',
  ];
  return hasAny(html, markers) || hasAny(title, ['500', 'error']);
}

function createStepRecorder() {
  const steps = [];
  return {
    steps,
    record(module, url, status, detail = '') {
      steps.push({
        module,
        url: cleanUrl(url),
        status,
        detail,
        ts: new Date().toISOString(),
      });
    },
  };
}

function summarizeFindings(steps, consoleErrors, requestFailed, resource404) {
  const findings = [];
  const benignConsoleMarkers = [
    'WebSocket connection to \'wss://localhost:8181/\' failed',
    'WebSocket connection to \'wss://localhost:8282/\' failed',
    'WebSocket connection to \'wss://localhost:8383/\' failed',
    'WebSocket connection to \'wss://localhost:8484/\' failed',
    'WebSocket connection to \'wss://localhost.qz.io:8181/\' failed',
  ];
  for (const s of steps) {
    if (s.status === 'FAIL') {
      findings.push({
        type: 'step_fail',
        module: s.module,
        url: s.url,
        detail: s.detail,
      });
    }
  }
  for (const c of consoleErrors) {
    const text = typeof c === 'string' ? c : String(c?.detail || c?.text || '');
    if (benignConsoleMarkers.some((m) => text.includes(m))) continue;
    findings.push({ type: 'console_error', detail: text });
  }
  for (const r of requestFailed) {
    if (String(r.failure || '').includes('ERR_ABORTED')) continue;
    if (String(r.url || '').includes('/director/war-room/api/anomalias/')) continue;
    findings.push({ type: 'request_failed', detail: `${r.method} ${r.url} :: ${r.failure}` });
  }
  for (const r of resource404) {
    findings.push({ type: 'resource_404', detail: r.url });
  }
  return findings;
}

function writeMarkdownReport(filePath, data) {
  const lines = [];
  const steps = Array.isArray(data.steps) ? data.steps : Array.isArray(data.modules) ? data.modules : [];
  lines.push(`# PRISLAB Human UI Audit`);
  lines.push('');
  lines.push(`- Fecha: ${data.timestamp}`);
  lines.push(`- Target: ${data.target}`);
  lines.push(`- Base URL: ${data.baseUrl}`);
  lines.push(`- Headless: ${data.headless}`);
  lines.push(`- Pause mode: ${data.pause}`);
  lines.push(`- Resultado general: ${data.ok ? 'OK' : 'CON HALLAZGOS'}`);
  lines.push('');
  lines.push('## Resumen');
  lines.push('');
  lines.push('| Módulo | URL | Estado | Detalle |');
  lines.push('|---|---|---|---|');
  for (const s of steps) {
    lines.push(`| ${s.module} | ${s.url} | ${s.status} | ${String(s.detail || '').replaceAll('|', '\\|')} |`);
  }
  lines.push('');
  lines.push('## Hallazgos');
  lines.push('');
  if (!data.findings.length) {
    lines.push('- Ninguno.');
  } else {
  for (const f of (Array.isArray(data.findings) ? data.findings : [])) {
    lines.push(`- [${f.type}] ${f.detail || JSON.stringify(f)}`);
  }
  }
  lines.push('');
  lines.push('## Artefactos');
  lines.push('');
  for (const shot of data.screenshots) {
    lines.push(`- ${shot}`);
  }
  fs.writeFileSync(filePath, `${lines.join('\n')}\n`, 'utf8');
}

async function verifyLoginFlow(page, recorder, baseUrl, user, pass, pause) {
  const module = 'login';
  const loginUrl = `${baseUrl}/login/`;
  await page.goto(loginUrl, { waitUntil: 'networkidle', timeout: 60000 });
  recorder.record(module, loginUrl, 'INFO', 'Login page opened');

  const loginInputs = await Promise.all([
    page.locator('input[name="username"]').count(),
    page.locator('input#id_username').count(),
    page.locator('input[name="password"]').count(),
  ]);
  if (loginInputs[0] + loginInputs[1] === 0 || loginInputs[2] === 0) {
    recorder.record(module, page.url(), 'FAIL', 'Login form controls not found');
    return { ok: false, authenticated: false };
  }

  await capture(page, recorder.screenshotsDir, '01_login_page');
  if (await pageErrorMarkers(page)) {
    recorder.record(module, page.url(), 'FAIL', 'Login page shows error markers');
    return { ok: false, authenticated: false };
  }

  if (!user || !pass) {
    recorder.record(module, page.url(), 'WARN', 'No credentials supplied; only login page validated');
    return { ok: true, authenticated: false };
  }

  await page.locator('input[name="username"], input#id_username').first().fill(user);
  await page.locator('input[name="password"], input#id_password').first().fill(pass);
  await capture(page, recorder.screenshotsDir, '02_login_filled');
  await page.click('button[type="submit"], input[type="submit"]');
  await page.waitForLoadState('networkidle', { timeout: 30000 }).catch(() => {});

  const current = page.url();
  const authenticated = !cleanUrl(current).endsWith('/login/') || current.includes('/dashboard/') || current.includes('/home/') || current.includes('/director/');
  if (!authenticated) {
    recorder.record(module, current, 'FAIL', 'Login did not redirect to a protected area');
    return { ok: false, authenticated: false };
  }

  recorder.record(module, current, 'PASS', 'Authenticated and redirected');
  await capture(page, recorder.screenshotsDir, '03_after_login');
  return { ok: true, authenticated: true };
}

async function verifyRootAndDashboard(page, recorder, baseUrl) {
  const module = 'root-dashboard';
  await page.goto(`${baseUrl}/`, { waitUntil: 'networkidle', timeout: 60000 });
  await capture(page, recorder.screenshotsDir, '04_root');
  if (await pageErrorMarkers(page)) {
    recorder.record(module, page.url(), 'FAIL', 'Root page shows error markers');
    return false;
  }
  recorder.record(module, page.url(), 'PASS', 'Root opened without 500');

  await page.goto(`${baseUrl}/home/`, { waitUntil: 'networkidle', timeout: 60000 }).catch(() => {});
  await capture(page, recorder.screenshotsDir, '05_home');
  if (await pageErrorMarkers(page)) {
    recorder.record(module, page.url(), 'FAIL', 'Home page shows error markers');
    return false;
  }
  recorder.record(module, page.url(), 'PASS', 'Home opened without 500');
  return true;
}

async function verifyLaboratorio(page, recorder, baseUrl, query, pause) {
  const module = 'laboratorio';
  const url = `${baseUrl}/laboratorio/recepcion/`;
  await page.goto(url, { waitUntil: 'networkidle', timeout: 60000 });
  await capture(page, recorder.screenshotsDir, '06_lab_recepcion');
  if (await pageErrorMarkers(page)) {
    recorder.record(module, page.url(), 'FAIL', 'Laboratorio recepcion shows error markers');
    return false;
  }

  const selectors = [
    '#buscar-paciente',
    '#input-buscador',
    'input[placeholder*="paciente" i]',
    'input[name*="paciente" i]',
  ];
  const input = await trySelectors(page, selectors);
  if (input) {
    try {
      await input.fill(query);
      await page.waitForTimeout(1200);
      recorder.record(module, page.url(), 'PASS', `Patient search input accepted text: ${query}`);
    } catch (e) {
      recorder.record(module, page.url(), 'FAIL', `Patient search input not usable: ${e.message}`);
      return false;
    }
  } else {
    recorder.record(module, page.url(), 'WARN', 'Patient search field not detected');
  }

  await clickTextIfPresent(page, ['Nuevo', 'Nuevo Paciente', 'Nueva Orden']).catch(() => {});
  await capture(page, recorder.screenshotsDir, '07_lab_after_action');
  if (pause) await maybePause(true, 'Laboratorio: revisa la pantalla y presiona Enter para seguir');
  return true;
}

async function verifyFarmacia(page, recorder, baseUrl, query, pause) {
  const module = 'farmacia';
  const url = `${baseUrl}/farmacia/pdv/`;
  await page.goto(url, { waitUntil: 'networkidle', timeout: 60000 });
  await capture(page, recorder.screenshotsDir, '08_farmacia_pdv');
  if (await pageErrorMarkers(page)) {
    recorder.record(module, page.url(), 'FAIL', 'Farmacia PDV shows error markers');
    return false;
  }

  const input = await trySelectors(page, ['#input-buscador', 'input[placeholder*="producto" i]', 'input[type="search"]']);
  if (input) {
    try {
      await input.fill(query);
      await page.waitForTimeout(1200);
      recorder.record(module, page.url(), 'PASS', `PDV search accepted text: ${query}`);
    } catch (e) {
      recorder.record(module, page.url(), 'FAIL', `PDV search input not usable: ${e.message}`);
      return false;
    }
  } else {
    recorder.record(module, page.url(), 'WARN', 'PDV search input not detected');
  }

  await clickTextIfPresent(page, ['Corte', 'Limpiar', 'Cobrar']).catch(() => {});
  await capture(page, recorder.screenshotsDir, '09_farmacia_after_action');
  if (pause) await maybePause(true, 'Farmacia: revisa la pantalla y presiona Enter para seguir');
  return true;
}

async function verifyConsultorio(page, recorder, baseUrl, pause) {
  const module = 'consultorio';
  const url = `${baseUrl}/consultorio/`;
  await page.goto(url, { waitUntil: 'networkidle', timeout: 60000 });
  await capture(page, recorder.screenshotsDir, '10_consultorio');
  if (await pageErrorMarkers(page)) {
    recorder.record(module, page.url(), 'FAIL', 'Consultorio shows error markers');
    return false;
  }
  recorder.record(module, page.url(), 'PASS', 'Consultorio dashboard loaded');

  // Verificar flujo de agendar cita navegando directamente a la sub-URL
  const agendarUrl = `${baseUrl}/consultorio/recepcion/agendar/`;
  await page.goto(agendarUrl, { waitUntil: 'networkidle', timeout: 30000 });
  await capture(page, recorder.screenshotsDir, '11_consultorio_agendar');
  if (await pageErrorMarkers(page)) {
    recorder.record(module, page.url(), 'FAIL', 'Agendar cita page shows error markers');
    return false;
  }
  recorder.record(module, page.url(), 'PASS', 'Agendar cita page loaded correctly');

  if (pause) await maybePause(true, 'Consultorio: revisa la pantalla y presiona Enter para seguir');
  return true;
}

async function verifyDirector(page, recorder, baseUrl, pause) {
  const module = 'director';
  const url = `${baseUrl}/director/`;
  await page.goto(url, { waitUntil: 'networkidle', timeout: 60000 });
  await capture(page, recorder.screenshotsDir, '12_director');
  if (await pageErrorMarkers(page)) {
    recorder.record(module, page.url(), 'FAIL', 'Director shows error markers');
    return false;
  }
  recorder.record(module, page.url(), 'PASS', 'Director dashboard loaded');

  // Verificar War Room directamente
  const warRoomUrl = `${baseUrl}/director/war-room/`;
  await page.goto(warRoomUrl, { waitUntil: 'networkidle', timeout: 30000 });
  await capture(page, recorder.screenshotsDir, '13_director_war_room');
  if (await pageErrorMarkers(page)) {
    recorder.record(module, page.url(), 'FAIL', 'War Room page shows error markers');
    return false;
  }
  recorder.record(module, page.url(), 'PASS', 'War Room loaded correctly');

  if (pause) await maybePause(true, 'Director: revisa la pantalla y presiona Enter para terminar');
  return true;
}

async function main() {
  const repoRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
  const manifest = readManifest(repoRoot);
  const args = parseArgs(process.argv.slice(2));
  const target = args.target || 'cloud';
  const baseUrl = resolveBaseUrl(manifest, target, args.base);
  const headless = Boolean(args.headless);
  const pause = Boolean(args.pause);
  const slowMo = Number.isFinite(args.slowMo) ? args.slowMo : 180;

  const runDir = path.join(repoRoot, `auditoria_ui_${stamp()}`);
  const screenshotsDir = path.join(runDir, 'screenshots');
  ensureDir(screenshotsDir);

  const recorder = createStepRecorder();
  recorder.screenshotsDir = screenshotsDir;

  const consoleErrors = [];
  const requestFailed = [];
  const resource404 = [];

  const browser = await chromium.launch({
    headless,
    slowMo,
    args: ['--window-size=1440,900'],
  });
  const context = await browser.newContext({
    ignoreHTTPSErrors: true,
    locale: 'es-MX',
    viewport: { width: 1440, height: 900 },
    userAgent: 'PRISLAB-HUMAN-UI-AUDIT/1.0',
  });
  const page = await context.newPage();

  page.on('console', (msg) => {
    if (msg.type() === 'error') consoleErrors.push(msg.text());
  });
  page.on('requestfailed', (req) => {
    requestFailed.push({
      url: cleanUrl(req.url()),
      method: req.method(),
      resourceType: req.resourceType(),
      failure: req.failure() ? req.failure().errorText : 'unknown',
    });
  });
  page.on('response', (res) => {
    if (res.status() === 404) {
      resource404.push({ url: cleanUrl(res.url()), contentType: res.headers()['content-type'] || '' });
    }
  });

  const summary = {
    protocol: 'PRISLAB_HUMAN_UI_AUDIT',
    timestamp: new Date().toISOString(),
    target,
    baseUrl,
    headless,
    pause,
    slowMo,
    ok: true,
    login: null,
    modules: [],
    steps: [],
    screenshots: [],
    console_errors: [],
    request_failed: [],
    resource_404: [],
    findings: [],
    runDir: path.basename(runDir),
  };

  try {
    const loginRes = await verifyLoginFlow(page, recorder, baseUrl, args.user, args.pass, pause);
    summary.login = loginRes;
    summary.modules.push(...recorder.steps.filter((s) => s.module === 'login'));

    const rootOk = await verifyRootAndDashboard(page, recorder, baseUrl);
    summary.modules.push(...recorder.steps.filter((s) => s.module === 'root-dashboard'));

    if (loginRes.authenticated) {
      await maybePause(pause, 'Ya hay sesión autenticada. Presiona Enter para continuar con el resto de módulos');
    }

    await verifyLaboratorio(page, recorder, baseUrl, args.query, pause);
    await verifyFarmacia(page, recorder, baseUrl, args.query, pause);
    await verifyConsultorio(page, recorder, baseUrl, pause);
    await verifyDirector(page, recorder, baseUrl, pause);

    summary.modules = recorder.steps;
    summary.steps = recorder.steps;
    summary.screenshots = fs.readdirSync(screenshotsDir).sort().map((f) => path.join('screenshots', f));
    summary.console_errors = consoleErrors;
    summary.request_failed = requestFailed;
    summary.resource_404 = resource404;
    summary.findings = summarizeFindings(recorder.steps, consoleErrors, requestFailed, resource404);
    summary.ok = summary.findings.length === 0 && loginRes.ok !== false && rootOk !== false;
  } catch (err) {
    summary.ok = false;
    summary.error = String(err?.message || err);
    summary.stack = err?.stack || null;
  } finally {
    await browser.close().catch(() => {});
  }

  fs.writeFileSync(path.join(runDir, 'report.json'), JSON.stringify(summary, null, 2), 'utf8');
  writeMarkdownReport(path.join(runDir, 'report.md'), summary);
  fs.writeFileSync(path.join(repoRoot, 'tools', 'last_runs', 'human_ui_last.json'), JSON.stringify(summary, null, 2), 'utf8');
  fs.writeFileSync(path.join(repoRoot, 'tools', 'last_suite_human_summary.json'), JSON.stringify({
    protocol: summary.protocol,
    timestamp: summary.timestamp,
    ok: summary.ok,
    target: summary.target,
    baseUrl: summary.baseUrl,
    findingsCount: summary.findings.length,
    findingsPreview: summary.findings.slice(0, 20),
    runDir: summary.runDir,
  }, null, 2), 'utf8');

  console.log(JSON.stringify({
    protocol: summary.protocol,
    timestamp: summary.timestamp,
    ok: summary.ok,
    target: summary.target,
    baseUrl: summary.baseUrl,
    findingsCount: summary.findings.length,
    runDir: summary.runDir,
    reportJson: path.join(summary.runDir, 'report.json'),
    reportMd: path.join(summary.runDir, 'report.md'),
  }, null, 2));

  process.exitCode = summary.ok ? 0 : 1;
}

main().catch((err) => {
  console.error(JSON.stringify({
    protocol: 'PRISLAB_HUMAN_UI_AUDIT',
    fatal: String(err?.message || err),
    stack: err?.stack || null,
  }, null, 2));
  process.exit(1);
});
