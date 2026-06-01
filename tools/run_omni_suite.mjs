/**
 * Runner unificado para la suite Omni-Tester.
 *
 * Ejecutar (local):
 *   node tools/run_omni_suite.mjs --target local --base http://127.0.0.1:8000 --user <u> --pass <p>
 * Ejecutar (cloud):
 *   node tools/run_omni_suite.mjs --target cloud --base https://... --user <u> --pass <p>
 * Ejecutar ambos:
 *   node tools/run_omni_suite.mjs --target both --user <u> --pass <p>
 *
 * Notas:
 * - No inicia el servidor local; si --target local, debes tenerlo corriendo.
 * - Guarda artefactos en diagnostico_omni_<timestamp>/ (ignorado por git).
 */

import fs from 'node:fs';
import path from 'node:path';
import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';

function nowStamp() {
  const d = new Date();
  const pad = (n) => String(n).padStart(2, '0');
  return `${d.getFullYear()}${pad(d.getMonth() + 1)}${pad(d.getDate())}_${pad(d.getHours())}${pad(d.getMinutes())}${pad(d.getSeconds())}`;
}

function parseArgs(argv) {
  const out = { target: 'both', base: null, user: null, pass: null };
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    if (a === '--target') out.target = argv[++i] || out.target;
    else if (a === '--base') out.base = argv[++i] || out.base;
    else if (a === '--user') out.user = argv[++i] || out.user;
    else if (a === '--pass') out.pass = argv[++i] || out.pass;
  }
  return out;
}

function substituteEnv(templateMap, vars) {
  const env = {};
  for (const [k, v] of Object.entries(templateMap || {})) {
    env[k] = String(v)
      .replaceAll('${BASE_URL}', vars.baseUrl)
      .replaceAll('${USER}', vars.user)
      .replaceAll('${PASS}', vars.pass);
  }
  return env;
}

function safeJsonParse(txt) {
  try {
    return JSON.parse(txt);
  } catch {
    return null;
  }
}

function collectFindings(obj) {
  // Normaliza hallazgos (muy simple, se puede hacer más rico en el futuro)
  const findings = [];
  if (!obj || typeof obj !== 'object') return findings;

  const proto = obj.protocol || 'UNKNOWN';

  const add = (f) => findings.push({ protocol: proto, ...f });

  // Consola
  if (Array.isArray(obj.console_errors)) {
    for (const e of obj.console_errors) add({ type: 'console_error', message: e.text || String(e) });
  }

  // Recursos 404 (mejor que el console_error genérico)
  if (Array.isArray(obj.resource_404)) {
    for (const r of obj.resource_404) {
      add({ type: 'resource_404', url: r.url || null, contentType: r.contentType || null });
    }
  }

  // Requests fallidos (DNS, aborted, etc.)
  if (Array.isArray(obj.request_failed)) {
    for (const r of obj.request_failed) {
      add({
        type: 'request_failed',
        url: r.url || null,
        method: r.method || null,
        resourceType: r.resourceType || null,
        failure: r.failure || null,
      });
    }
  }

  // Checks (API Smoke)
  if (Array.isArray(obj.checks)) {
    for (const c of obj.checks) {
      if (typeof c.status === 'number' && c.status >= 400) {
        add({ type: 'http_error', url: c.url, status: c.status, name: c.name, snippet: c.snippet || null });
      }
    }
  }

  // Red flags comunes
  // Nota: en algunos auditores, `redirectedToLogin` puede ser true al inicio
  // aunque el flujo termine autenticado. Solo reportar si realmente NO quedó logueado.
  if (obj.redirectedToLogin && obj.loginSucceeded === false) {
    add({ type: 'auth_redirect', url: obj.finalUrl || null });
  }

  // PDV
  if (Array.isArray(obj.network_api_buscar_html) && obj.network_api_buscar_html.length === 0) {
    add({ type: 'pdv_no_search_calls', detail: 'No hubo llamadas a buscar-fragmento.' });
  }

  if (Array.isArray(obj.network_api_lotes_producto)) {
    for (const n of obj.network_api_lotes_producto) {
      if (typeof n.status === 'number' && n.status >= 400) {
        add({ type: 'pdv_lotes_error', url: n.url, status: n.status, snippet: n.snippet || null });
      }
    }
  }

  // Data integrity
  if (Array.isArray(obj.ordenes_listas_sin_pdf) && obj.ordenes_listas_sin_pdf.length > 0) {
    add({ type: 'data_integrity', message: 'Órdenes listas/entregadas sin PDF adjunto', count: obj.ordenes_listas_sin_pdf.length });
  }

  return findings;
}

function dedupeFindings(findings) {
  const seen = new Set();
  const out = [];
  for (const f of findings) {
    const key = [f.protocol, f.type, f.url || '', f.status || '', f.name || '', f.message || ''].join('|');
    if (seen.has(key)) continue;
    seen.add(key);
    out.push(f);
  }
  return out;
}

function runAuditor(repoRoot, auditor, vars) {
  const env = { ...process.env, ...substituteEnv(auditor.env, vars) };
  const cwd = repoRoot;
  const timeoutMs = Number(process.env.OMNI_TIMEOUT_MS || 120000);
  const label = `${auditor.cmd} ${auditor.args.join(' ')}`;
  process.stderr.write(`[omni] start: ${auditor.id} (${label})\n`);
  const started = Date.now();
  const res = spawnSync(auditor.cmd, auditor.args, {
    cwd,
    env,
    encoding: 'utf8',
    timeout: Number.isFinite(timeoutMs) && timeoutMs > 0 ? timeoutMs : undefined,
  });
  process.stderr.write(`[omni] end:   ${auditor.id} (ms=${Date.now() - started}, status=${res.status})\n`);

  const stdout = (res.stdout || '').trim();
  const stderr = (res.stderr || '').trim();
  const json = safeJsonParse(stdout);

  const jsonOk = json && typeof json.ok === 'boolean' ? json.ok : null;
  const exitOk = (typeof res.status === 'number' ? res.status : 1) === 0;
  const ok = exitOk && (jsonOk === null ? true : jsonOk);

  return {
    id: auditor.id,
    cmd: auditor.cmd,
    args: auditor.args,
    exitCode: typeof res.status === 'number' ? res.status : null,
    ok,
    jsonOk,
    stdout,
    stderr,
    json,
  };
}

async function createStorageState(baseUrl, user, pass, outPath) {
  if (!user || !pass) return { ok: false, reason: 'missing-credentials' };
  const { chromium } = await import('playwright');
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({ ignoreHTTPSErrors: true, userAgent: 'PRISLAB-OMNI-LOGIN/1.0' });
  const page = await context.newPage();
  try {
    const loginUrl = `${baseUrl.replace(/\/$/, '')}/login/`;
    await page.goto(loginUrl, { waitUntil: 'domcontentloaded', timeout: 60000 });
    const bypass = process.env.OMNI_BYPASS_TOKEN;
    await page.setExtraHTTPHeaders({
      Referer: loginUrl,
      ...(bypass ? { 'X-Omni-Bypass': bypass } : {}),
    });
    await page.fill('input[name="username"], input#id_username', user);
    await page.fill('input[name="password"], input#id_password', pass);
    await page.click('button[type="submit"], input[type="submit"]');
    await page.waitForLoadState('networkidle', { timeout: 60000 }).catch(() => {});
    const cookies = await context.cookies();
    const sessionOk = cookies.some((c) => c && typeof c.name === 'string' && c.name.toLowerCase() === 'sessionid');
    await context.storageState({ path: outPath });
    return { ok: sessionOk };
  } catch (e) {
    return { ok: false, reason: String(e) };
  } finally {
    await page.close().catch(() => {});
    await context.close().catch(() => {});
    await browser.close().catch(() => {});
  }
}

async function main() {
  const thisFile = fileURLToPath(import.meta.url);
  const repoRoot = path.resolve(path.dirname(thisFile), '..');
  const args = parseArgs(process.argv.slice(2));
  const manifestPath = path.join(repoRoot, 'tools', 'omni_manifest.json');
  const manifest = JSON.parse(fs.readFileSync(manifestPath, 'utf8'));

  const stamp = nowStamp();
  const outDir = path.join(repoRoot, `diagnostico_omni_${stamp}`);
  fs.mkdirSync(outDir, { recursive: true });

  // "Última corrida" por auditor (no gitignored)
  const lastRunsDir = path.join(repoRoot, 'tools', 'last_runs');
  fs.mkdirSync(lastRunsDir, { recursive: true });

  const selectedTargets = args.target === 'both' ? ['local', 'cloud'] : [args.target];

  const suite = { protocol: 'PRISLAB_OMNI_SUITE', timestamp: new Date().toISOString(), targets: {}, findings: [] };

  for (const t of selectedTargets) {
    const tdef = manifest.targets[t];
    if (!tdef) {
      suite.targets[t] = { ok: false, fatal: `Target desconocido: ${t}` };
      continue;
    }

    const baseUrl = args.base || tdef.baseUrlDefault;
    const vars = { baseUrl, user: args.user || process.env.E2E_USER || process.env.PDV_USER || '', pass: args.pass || process.env.E2E_PASS || process.env.PDV_PASS || '' };

    const runs = [];
    const preloginEnabled = process.env.OMNI_PRELOGIN === '1';
    let prelogin = { enabled: preloginEnabled, ok: false, storagePath: null };
    if (preloginEnabled) {
      const storagePath = path.join(repoRoot, 'tools', 'last_runs', `omni_storage_state_${t}.json`);
      prelogin = { ...prelogin, storagePath };
      const pre = await createStorageState(baseUrl, vars.user, vars.pass, storagePath);
      prelogin.ok = Boolean(pre.ok);
      if (pre && pre.reason) {
        prelogin.reason = pre.reason;
      }
      if (prelogin.ok) {
        process.env.OMNI_STORAGE_STATE = storagePath;
      }
    }

    if (preloginEnabled && !prelogin.ok) {
      if (prelogin.reason) {
        process.stderr.write(`[omni] prelogin_failed: ${prelogin.reason}\n`);
      }
      suite.targets[t] = { baseUrl, prelogin, ok: false, fatal: 'prelogin_failed', runs: [] };
      continue;
    }
  const delayMs = Number(process.env.OMNI_BETWEEN_AUDIT_DELAY_MS || 0);
    for (const auditor of tdef.auditors) {
      // Data integrity solo aplica local
      if (t === 'cloud' && auditor.id === 'data_integrity') continue;

      process.stderr.write(`[omni] target=${t} base=${baseUrl}\n`);

    if (delayMs > 0 && runs.length > 0) {
      await new Promise((r) => setTimeout(r, delayMs));
    }

      const r = runAuditor(repoRoot, auditor, vars);
      runs.push(r);

      // Persistencia de artefactos
      const fileBase = `${t}__${auditor.id}`;
      fs.writeFileSync(path.join(outDir, `${fileBase}.stdout.txt`), r.stdout || '', 'utf8');
      fs.writeFileSync(path.join(outDir, `${fileBase}.stderr.txt`), r.stderr || '', 'utf8');
      if (r.json) fs.writeFileSync(path.join(outDir, `${fileBase}.json`), JSON.stringify(r.json, null, 2), 'utf8');

      // Copia NO ignorable para inspección rápida desde IDE/tools
      if (r.json) {
        fs.writeFileSync(path.join(lastRunsDir, `${fileBase}.json`), JSON.stringify(r.json, null, 2), 'utf8');
      } else {
        // Si no hubo JSON, al menos guardamos stderr para diagnosticar
        fs.writeFileSync(path.join(lastRunsDir, `${fileBase}.stderr.txt`), r.stderr || '', 'utf8');
      }

      suite.findings.push(...collectFindings(r.json));
    }

    suite.targets[t] = {
      baseUrl,
      prelogin,
      ok: runs.every((x) => x.ok),
      runs: runs.map((x) => ({ id: x.id, ok: x.ok, jsonOk: x.jsonOk, exitCode: x.exitCode })),
    };
  }

  suite.findings = dedupeFindings(suite.findings);
  suite.summary = {
    ok: Object.values(suite.targets).every((t) => t && t.ok),
    findingsCount: suite.findings.length,
    findingsByType: suite.findings.reduce((acc, f) => {
      acc[f.type] = (acc[f.type] || 0) + 1;
      return acc;
    }, {}),
    outputDir: path.basename(outDir),
  };

  fs.writeFileSync(path.join(outDir, 'suite.json'), JSON.stringify(suite, null, 2), 'utf8');

  // Copias "última corrida" (NO gitignored) para facilitar inspección rápida.
  // Importante: no incluyen credenciales.
  const lastSuitePath = path.join(repoRoot, 'tools', 'last_suite.json');
  const lastSummaryPath = path.join(repoRoot, 'tools', 'last_suite_summary.json');
  fs.writeFileSync(lastSuitePath, JSON.stringify(suite, null, 2), 'utf8');
  fs.writeFileSync(lastSummaryPath, JSON.stringify({
    protocol: suite.protocol,
    timestamp: suite.timestamp,
    targets: suite.targets,
    summary: suite.summary,
    findingsPreview: suite.findings.slice(0, 25),
  }, null, 2), 'utf8');

  // Siempre imprimir resumen corto (para CI/terminal)
  console.log(JSON.stringify({
    protocol: suite.protocol,
    timestamp: suite.timestamp,
    ok: suite.summary.ok,
    findingsCount: suite.summary.findingsCount,
    findingsByType: suite.summary.findingsByType,
    outputDir: suite.summary.outputDir,
    lastSuite: 'tools/last_suite.json',
    lastSummary: 'tools/last_suite_summary.json',
  }, null, 2));
}

main();
