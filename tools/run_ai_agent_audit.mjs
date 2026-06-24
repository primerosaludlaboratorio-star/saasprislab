/**
 * run_ai_agent_audit.mjs — Auditor humano IA de PRISLAB (Gemini + Playwright)
 * ===========================================================================
 * Versión "siguiente nivel": presupuesto por módulo, flujos humanos reales,
 * anti-loop, selector inteligente y severidades correctas (vía audit_human_flows.mjs).
 *
 * Uso:
 *   1) Configura .env.agent (ver claves abajo).
 *   2) node tools/run_ai_agent_audit.mjs            # usa AGENT_TARGET
 *      node tools/run_ai_agent_audit.mjs --target cloud
 *
 * .env.agent (KEY=VALUE):
 *   AGENT_API_KEY=...                 # API key de Gemini (aistudio.google.com)
 *   AGENT_MODEL=gemini-2.5-flash      # opcional
 *   AGENT_TARGET=cloud                # cloud | local
 *   PRISLAB_BASE_URL=https://prislab.labcorecloud.com   # opcional, fija el host
 *   AGENT_USER=admin
 *   AGENT_PASS=...
 *   AGENT_MAX_STEPS=160               # opcional
 *   AGENT_HEADLESS=0                  # 0 = ver el navegador
 */
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';
import { chromium } from 'playwright';
import {
  buildSystemPrompt, MODULE_FLOWS, resolveSelectorVariants, LoopGuard, perModuleBudget,
} from './audit_human_flows.mjs';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(__dirname, '..');

// ── Config ────────────────────────────────────────────────────────────────────
function loadEnvAgent() {
  const p = path.join(ROOT, '.env.agent');
  const env = {};
  if (fs.existsSync(p)) {
    for (const line of fs.readFileSync(p, 'utf8').split(/\r?\n/)) {
      const m = line.match(/^\s*([A-Z0-9_]+)\s*=\s*(.*)\s*$/);
      if (m) env[m[1]] = m[2];
    }
  }
  return { ...env, ...process.env };
}
function arg(name, def) {
  const i = process.argv.indexOf(`--${name}`);
  return i >= 0 && process.argv[i + 1] ? process.argv[i + 1] : def;
}
const E = loadEnvAgent();
const TARGET = arg('target', E.AGENT_TARGET || 'cloud');
const BASE_URL = (E.PRISLAB_BASE_URL || '').trim()
  || (TARGET === 'local' ? 'http://127.0.0.1:8000' : 'https://prislab.labcorecloud.com');
const MODEL = E.AGENT_MODEL || 'gemini-2.5-flash';
const API_KEY = (E.AGENT_API_KEY || E.GEMINI_API_KEY || '').trim();
const USER = E.AGENT_USER || '';
const PASS = E.AGENT_PASS || '';
const MAX_STEPS = parseInt(E.AGENT_MAX_STEPS || '160', 10);
const HEADLESS = (E.AGENT_HEADLESS || '0') === '1';

const runDir = path.join(ROOT, `ai_audit_${new Date().toISOString().replace(/[-:T]/g, '').slice(0, 15)}`);
const shotsDir = path.join(runDir, 'screenshots');
fs.mkdirSync(shotsDir, { recursive: true });

const findings = [];
const report = (f) => { findings.push({ severity: 'INFO', ...f, ts: Date.now() }); };

// ── Launch chromium (robusto: default, si no, binarios preinstalados) ──────────
async function launchBrowser() {
  const opts = { headless: HEADLESS, args: ['--no-sandbox', '--disable-dev-shm-usage'] };
  try { return await chromium.launch(opts); } catch (e1) {
    for (const exe of [
      '/opt/pw-browsers/chromium-1194/chrome-linux/chrome',
      process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH,
    ].filter(Boolean)) {
      try { return await chromium.launch({ ...opts, executablePath: exe }); } catch { /* next */ }
    }
    throw e1;
  }
}

// ── Tools (lo que el LLM puede invocar) ────────────────────────────────────────
function makeTools(page, consoleErrors) {
  return {
    async navigate({ url, wait_for }) {
      const target = url.startsWith('http') ? url : BASE_URL + (url.startsWith('/') ? url : '/' + url);
      const r = await page.goto(target, { waitUntil: wait_for || 'domcontentloaded', timeout: 25000 });
      await page.waitForTimeout(600);
      return { ok: true, status: r ? r.status() : null, url: page.url() };
    },
    async fill_input({ selector, value, role }) {
      const tries = [selector, ...(role ? resolveSelectorVariants({ role }) : [])].filter(Boolean);
      for (const sel of tries) {
        try { await page.fill(sel, value, { timeout: 3500 }); return { ok: true, selector: sel }; }
        catch { /* next variant */ }
      }
      return { ok: false, error: 'selector no encontrado', tried: tries };
    },
    async click({ selector, text }) {
      try {
        if (text) await page.getByText(text, { exact: false }).first().click({ timeout: 4000 });
        else await page.click(selector, { timeout: 4000 });
        await page.waitForTimeout(500);
        return { ok: true };
      } catch (e) { return { ok: false, error: String(e.message || e).slice(0, 120) }; }
    },
    async find_elements({ selector }) {
      try {
        const els = await page.$$eval(selector, (ns) => ns.slice(0, 25).map((n) => ({
          tag: n.tagName.toLowerCase(),
          text: (n.innerText || n.value || n.placeholder || '').trim().slice(0, 60),
          id: n.id || null, name: n.getAttribute('name') || null,
        })));
        return { ok: true, count: els.length, elements: els };
      } catch (e) { return { ok: false, error: String(e.message || e).slice(0, 120) }; }
    },
    async get_page_state() {
      const title = await page.title().catch(() => '');
      const text = (await page.evaluate(() => document.body ? document.body.innerText : '').catch(() => '')).replace(/\s+/g, ' ').slice(0, 1200);
      const errs = consoleErrors.filter((e) => !/localhost:(818[1-9]|82[0-9][0-9]|83[0-9][0-9]|84[0-9][0-9])|qz\.io/.test(e)).slice(-5);
      return { ok: true, url: page.url(), title, text, console_errors: errs };
    },
    async screenshot({ label }) {
      const file = path.join(shotsDir, `${(label || 'shot')}_${Date.now()}.png`);
      try { await page.screenshot({ path: file }); return { ok: true, file: path.basename(file) }; }
      catch (e) { return { ok: false, error: String(e.message || e).slice(0, 80) }; }
    },
    async report_finding(f) { report(f); return { ok: true }; },
    async finish_audit({ summary }) { return { ok: true, done: true, summary }; },
  };
}

// ── Declaración de tools para Gemini (function calling) ────────────────────────
const FN_DECLS = [
  { name: 'navigate', description: 'Ir a una URL (ruta o absoluta).', parameters: { type: 'object', properties: { url: { type: 'string' }, wait_for: { type: 'string' } }, required: ['url'] } },
  { name: 'fill_input', description: 'Escribir en un input. Pasa role ("search"|"submit"|"patient"|"product") para fallback inteligente.', parameters: { type: 'object', properties: { selector: { type: 'string' }, value: { type: 'string' }, role: { type: 'string' } }, required: ['value'] } },
  { name: 'click', description: 'Click por texto visible o selector.', parameters: { type: 'object', properties: { selector: { type: 'string' }, text: { type: 'string' } } } },
  { name: 'find_elements', description: 'Listar elementos que casan un selector.', parameters: { type: 'object', properties: { selector: { type: 'string' } }, required: ['selector'] } },
  { name: 'get_page_state', description: 'Estado de la página (url, título, texto, errores de consola).', parameters: { type: 'object', properties: {} } },
  { name: 'screenshot', description: 'Captura de pantalla.', parameters: { type: 'object', properties: { label: { type: 'string' } } } },
  { name: 'report_finding', description: 'Registrar hallazgo.', parameters: { type: 'object', properties: { module: { type: 'string' }, title: { type: 'string' }, detail: { type: 'string' }, severity: { type: 'string' }, url: { type: 'string' } }, required: ['detail'] } },
  { name: 'finish_audit', description: 'Terminar la auditoría con un resumen.', parameters: { type: 'object', properties: { summary: { type: 'string' } }, required: ['summary'] } },
];

// ── Llamada a Gemini (REST function-calling) ───────────────────────────────────
async function callGemini(systemPrompt, contents) {
  const url = `https://generativelanguage.googleapis.com/v1beta/models/${MODEL}:generateContent?key=${API_KEY}`;
  const body = {
    systemInstruction: { parts: [{ text: systemPrompt }] },
    contents,
    tools: [{ functionDeclarations: FN_DECLS }],
    generationConfig: { temperature: parseFloat(E.AGENT_TEMPERATURE || '0.2') },
  };
  const res = await fetch(url, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
  if (!res.ok) throw new Error(`Gemini ${res.status}: ${(await res.text()).slice(0, 200)}`);
  const data = await res.json();
  const parts = data?.candidates?.[0]?.content?.parts || [];
  const call = parts.find((p) => p.functionCall)?.functionCall;
  const textPart = parts.find((p) => p.text)?.text;
  return { call, text: textPart };
}

// ── Bucle agéntico por módulo (presupuesto repartido) ──────────────────────────
async function run() {
  if (!API_KEY) { console.error('[AGENT] Falta AGENT_API_KEY en .env.agent'); process.exit(1); }
  console.log(`[AGENT] ${MODEL} | ${BASE_URL} | max ${MAX_STEPS} | headless ${HEADLESS}`);
  const { porModulo, reserva } = perModuleBudget(MAX_STEPS);
  const browser = await launchBrowser();
  const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 }, ignoreHTTPSErrors: true });
  const page = await ctx.newPage();
  const consoleErrors = [];
  page.on('console', (m) => { if (m.type() === 'error') consoleErrors.push(m.text().slice(0, 200)); });
  page.on('pageerror', (e) => consoleErrors.push('PAGEERROR: ' + String(e).slice(0, 200)));
  const tools = makeTools(page, consoleErrors);
  const systemPrompt = buildSystemPrompt(BASE_URL, USER, PASS);

  // Cola: login primero, luego un "turno" por módulo con su propio presupuesto.
  const agenda = [{ modulo: 'LOGIN', url: '/login/', budget: reserva, flujo: ['Haz login con las credenciales y confirma que entras al dashboard.'] },
    ...MODULE_FLOWS.map((m) => ({ ...m, budget: porModulo }))];

  let stepsTotal = 0;
  for (const item of agenda) {
    const guard = new LoopGuard();
    const contents = [{ role: 'user', parts: [{ text:
      `MÓDULO: ${item.modulo} (${BASE_URL}${item.url}). Presupuesto: ${item.budget} pasos.\n` +
      `Flujo a ejecutar:\n- ${item.flujo.join('\n- ')}\n` +
      `Empieza con navigate a la URL. Cuando termines este módulo, reporta un finding-resumen y NO sigas con otros (yo te paso al siguiente).` }] }];
    for (let s = 0; s < item.budget && stepsTotal < MAX_STEPS; s++, stepsTotal++) {
      let out;
      try { out = await callGemini(systemPrompt, contents); }
      catch (e) { console.error(`[AGENT] LLM error: ${e.message}`); break; }
      if (!out.call) { // sin acción -> avanzar
        if (out.text) contents.push({ role: 'model', parts: [{ text: out.text }] });
        contents.push({ role: 'user', parts: [{ text: 'Continúa con la siguiente acción concreta o reporta y termina el módulo.' }] });
        continue;
      }
      const { name, args } = { name: out.call.name, args: out.call.args || {} };
      if (guard.isStuck(name, args)) {
        console.log(`[AGENT] anti-loop: ${name} repetido, avanzo de módulo`);
        report({ module: item.modulo, severity: 'MEDIUM', title: 'Posible bloqueo de UI', detail: `El agente repitió ${name} sin progreso en ${item.url}.`, url: BASE_URL + item.url });
        break;
      }
      const fn = tools[name];
      const result = fn ? await fn(args) : { ok: false, error: 'tool desconocida' };
      console.log(`[${item.modulo} ${s + 1}/${item.budget}] ${name} -> ${result.ok ? 'OK' : 'FAIL'}`);
      contents.push({ role: 'model', parts: [{ functionCall: out.call }] });
      contents.push({ role: 'user', parts: [{ functionResponse: { name, response: result } }] });
      if (name === 'finish_audit' || result.done) break;
    }
  }

  await browser.close();
  writeReport();
}

function writeReport() {
  const bySev = (s) => findings.filter((f) => (f.severity || 'INFO').toUpperCase() === s);
  const md = [
    '# PRISLAB AI Agent Audit Report',
    `- Fecha: ${new Date().toISOString()}`,
    `- Target: ${TARGET} | Base: ${BASE_URL} | Modelo: ${MODEL}`,
    `- Hallazgos: ${findings.length} (CRITICAL ${bySev('CRITICAL').length}, HIGH ${bySev('HIGH').length}, MEDIUM ${bySev('MEDIUM').length})`,
    '', '## Hallazgos',
    ...['CRITICAL', 'HIGH', 'MEDIUM', 'INFO'].flatMap((sev) => {
      const fs_ = bySev(sev); if (!fs_.length) return [];
      return [`\n### ${sev} (${fs_.length})`, ...fs_.map((f) => `- **[${f.module || '-'}] ${f.title || ''}** — ${f.detail || ''} ${f.url ? `(${f.url})` : ''}`)];
    }),
  ].join('\n');
  fs.writeFileSync(path.join(runDir, 'report.md'), md);
  fs.writeFileSync(path.join(runDir, 'report.json'), JSON.stringify({ target: TARGET, baseUrl: BASE_URL, model: MODEL, findings }, null, 2));
  console.log(`\n[AGENT] Reporte: ${path.relative(ROOT, path.join(runDir, 'report.md'))} | ${findings.length} hallazgos`);
}

run().catch((e) => { console.error('[AGENT] Fatal:', e); process.exit(1); });
