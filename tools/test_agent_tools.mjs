/**
 * test_agent_tools.mjs
 * ─────────────────────────────────────────────────────────────────────────────
 * Pruebas de cada herramienta del auditor SIN LLM y SIN tocar producción.
 * Usa un servidor HTML local efímero y una página de prueba controlada.
 *
 * Cómo correr:
 *   node tools/test_agent_tools.mjs
 * ─────────────────────────────────────────────────────────────────────────────
 */

import http from 'node:http';
import path from 'node:path';
import fs from 'node:fs';
import { fileURLToPath } from 'node:url';
import { chromium } from 'playwright';
import { TOOLS, TOOLS_MAP, cleanUrl, hasErrorMarkers } from './ai_agent_tools.mjs';
import { finalizeLoginAttempt } from './run_ai_agent_audit.mjs';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const repoRoot   = path.resolve(__dirname, '..');

// ── HTML de prueba local ───────────────────────────────────────────────────
const TEST_HTML = `<!DOCTYPE html><html lang="es"><head><meta charset="UTF-8"><title>Página de Prueba Auditor</title></head>
<body>
  <h1>Dashboard de Prueba</h1>
  <nav>
    <a href="/modulo-a">Módulo A</a>
    <a href="/modulo-b">Módulo B</a>
    <a href="/modulo-c">Módulo C</a>
  </nav>
  <form id="test-form">
    <input type="text"     name="username"    id="username"    placeholder="Usuario"     value="" />
    <input type="password" name="password"    id="password"    placeholder="Contraseña"  value="" />
    <input type="text"     name="busqueda"    id="busqueda"    placeholder="Buscar..."   value="" />
    <button type="submit" id="btn-submit">Guardar</button>
    <button type="button" id="btn-cancelar">Cancelar</button>
  </form>
  <table id="tabla-datos">
    <tr><th>ID</th><th>Nombre</th><th>Estatus</th></tr>
    <tr><td>1</td><td>Paciente García</td><td>Activo</td></tr>
    <tr><td>2</td><td>Paciente López</td><td>Inactivo</td></tr>
  </table>
  <div id="modal" style="display:none">Modal de Prueba</div>
  <script>
    document.getElementById('btn-cancelar').addEventListener('click', function() {
      document.getElementById('modal').style.display = 'block';
    });
    // Error JS intencional para probar captura de consola
    console.error('TEST_JS_ERROR: error de prueba intencional');
  </script>
</body></html>`;

const ERROR_HTML = `<!DOCTYPE html><html><head><title>Server Error (500)</title></head>
<body><h1>Server Error (500)</h1><p>Internal Server Error — Traceback:</p><pre>Exception Value: test error</pre></body></html>`;

// ── Servidor HTTP local efímero ────────────────────────────────────────────
function startServer() {
  return new Promise((resolve) => {
    const server = http.createServer((req, res) => {
      res.setHeader('Content-Type', 'text/html; charset=utf-8');
      if (req.url === '/error500') {
        res.writeHead(200); // Django lo sirve como 200 con marcadores de error
        res.end(ERROR_HTML);
      } else if (req.url === '/not-found') {
        res.writeHead(404);
        res.end('<h1>404 Not Found</h1>');
      } else {
        res.writeHead(200);
        res.end(TEST_HTML);
      }
    });
    server.listen(0, '127.0.0.1', () => {
      const { port } = server.address();
      resolve({ server, port, base: `http://127.0.0.1:${port}` });
    });
  });
}

// ── Contexto mock para herramientas ───────────────────────────────────────
function makeCtx(screenshotsDir) {
  return {
    findings: [],
    screenshots: [],
    screenshotsDir,
    consoleErrors: [],
    requestFailed: [],
    resource404: [],
    finished: false,
  };
}

// ── Runner de pruebas ─────────────────────────────────────────────────────
let passed = 0;
let failed = 0;
const failures = [];

async function test(name, fn) {
  try {
    await fn();
    console.log(`  ✅  ${name}`);
    passed++;
  } catch (e) {
    console.log(`  ❌  ${name}`);
    console.log(`       → ${e.message}`);
    failures.push({ name, error: e.message });
    failed++;
  }
}

function assert(condition, msg) {
  if (!condition) throw new Error(msg || 'Assertion failed');
}

// ── Main ──────────────────────────────────────────────────────────────────
async function main() {
  console.log('\n═══════════════════════════════════════════════════════');
  console.log('  PRISLAB AI Agent Tools — Suite de Pruebas');
  console.log('═══════════════════════════════════════════════════════\n');

  const { server, port, base } = await startServer();
  console.log(`  Servidor de prueba: ${base}\n`);

  const screenshotsDir = path.join(repoRoot, 'tools', 'test_screenshots');
  fs.mkdirSync(screenshotsDir, { recursive: true });

  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext();
  const page    = await context.newPage();

  // Capturar errores de consola del browser
  const ctx = makeCtx(screenshotsDir);
  page.on('console', (msg) => {
    if (msg.type() === 'error') ctx.consoleErrors.push(msg.text());
  });

  // ── BLOQUE 1: Herramientas de navegación y estado ─────────────────────
  console.log('── 1. navigate ──────────────────────────────────────');

  await test('navigate: carga página normal', async () => {
    const r = await TOOLS_MAP.navigate.handler(page, { url: base }, ctx);
    assert(r.ok, `navigate falló: ${r.error}`);
    assert(r.data.title === 'Página de Prueba Auditor', `title inesperado: ${r.data.title}`);
    assert(!r.data.hasErrorMarkers, 'marcó error en página normal');
  });

  await test('navigate: detecta marcadores de error (500)', async () => {
    const r = await TOOLS_MAP.navigate.handler(page, { url: `${base}/error500` }, ctx);
    assert(!r.ok, 'debería marcar error en página con traceback');
    assert(r.data.hasErrorMarkers, 'hasErrorMarkers debería ser true');
    // Volver a página normal
    await TOOLS_MAP.navigate.handler(page, { url: base }, ctx);
  });

  await test('navigate: URL inválida devuelve ok:false', async () => {
    const r = await TOOLS_MAP.navigate.handler(page, { url: 'http://127.0.0.1:1' }, ctx);
    assert(!r.ok, 'debería fallar con URL de puerto cerrado');
  });

  // ── BLOQUE 2: get_page_state ──────────────────────────────────────────
  console.log('\n── 2. get_page_state ────────────────────────────────');

  // Asegurarse de estar en la página buena antes de los tests de get_page_state
  await TOOLS_MAP.navigate.handler(page, { url: base }, ctx);

  await test('get_page_state: devuelve url, title y visibleText', async () => {
    // Esperar a que la navegación previa haya terminado — no lanzar otra
    await page.waitForLoadState('domcontentloaded').catch(() => {});
    const r = await TOOLS_MAP.get_page_state.handler(page, {}, ctx);
    assert(r.ok, `falló: ${r.error}`);
    assert(r.data.url.includes('127.0.0.1'), `url inesperada: ${r.data.url}`);
    assert(r.data.title === 'Página de Prueba Auditor', `title: ${r.data.title}`);
    assert(r.data.visibleText.length > 0, 'visibleText vacío');
    assert(r.data.visibleText.length <= 1500, `visibleText demasiado largo: ${r.data.visibleText.length}`);
  });

  await test('get_page_state: filtra scripts del visibleText', async () => {
    const r = await TOOLS_MAP.get_page_state.handler(page, {}, ctx);
    assert(!r.data.visibleText.includes('addEventListener'), 'visibleText contiene código JS — filtrado fallido');
  });

  await test('get_page_state: captura errores JS de consola', async () => {
    // El TEST_HTML inyecta un console.error — esperar que lo capture
    await page.waitForTimeout(300);
    const r = await TOOLS_MAP.get_page_state.handler(page, {}, ctx);
    assert(Array.isArray(r.data.jsErrors), 'jsErrors no es array');
    const hasTestError = r.data.jsErrors.some((e) => String(e).includes('TEST_JS_ERROR'));
    assert(hasTestError, `No capturó el error JS de prueba. jsErrors: ${JSON.stringify(r.data.jsErrors)}`);
  });

  await test('get_page_state: include_html_snippet devuelve HTML truncado', async () => {
    const r = await TOOLS_MAP.get_page_state.handler(page, { include_html_snippet: true }, ctx);
    assert(r.data.htmlSnippet && r.data.htmlSnippet.length > 0, 'htmlSnippet vacío');
    assert(r.data.htmlSnippet.length <= 2000, `htmlSnippet demasiado largo: ${r.data.htmlSnippet.length}`);
  });

  // ── BLOQUE 3: find_elements ───────────────────────────────────────────
  console.log('\n── 3. find_elements ─────────────────────────────────');

  await test('find_elements: encuentra botones', async () => {
    const r = await TOOLS_MAP.find_elements.handler(page, { selector: 'button' }, ctx);
    assert(r.ok, `falló: ${r.error}`);
    assert(r.data.count >= 2, `debería haber al menos 2 botones, encontró: ${r.data.count}`);
  });

  await test('find_elements: devuelve name, id, placeholder', async () => {
    const r = await TOOLS_MAP.find_elements.handler(page, { selector: 'input' }, ctx);
    assert(r.ok, `falló: ${r.error}`);
    const inputs = r.data.items;
    const userInput = inputs.find((i) => i.name === 'username');
    assert(userInput, `No encontró input con name="username". Items: ${JSON.stringify(inputs)}`);
    assert(userInput.id === 'username', `id incorrecto: ${userInput.id}`);
    assert(userInput.placeholder === 'Usuario', `placeholder incorrecto: ${userInput.placeholder}`);
  });

  await test('find_elements: filtra elementos invisibles', async () => {
    // El modal está display:none — no debería aparecer
    const r = await TOOLS_MAP.find_elements.handler(page, { selector: '#modal' }, ctx);
    assert(r.ok);
    assert(r.data.visible === 0, `modal invisible debería ser 0 visible, fue: ${r.data.visible}`);
  });

  await test('find_elements: selector inválido devuelve ok:false o count:0', async () => {
    const r = await TOOLS_MAP.find_elements.handler(page, { selector: '#elemento-inexistente' }, ctx);
    assert(r.ok); // no debe explotar
    assert(r.data.count === 0, `count debería ser 0`);
  });

  // ── BLOQUE 4: click ───────────────────────────────────────────────────
  console.log('\n── 4. click ─────────────────────────────────────────');

  await test('click: por texto abre el modal', async () => {
    await TOOLS_MAP.navigate.handler(page, { url: base }, ctx);
    const r = await TOOLS_MAP.click.handler(page, { text: 'Cancelar' }, ctx);
    assert(r.ok, `click falló: ${r.error}`);
    const visible = await page.locator('#modal').isVisible();
    assert(visible, 'El modal debería haberse abierto tras hacer click en Cancelar');
  });

  await test('click: por selector CSS funciona', async () => {
    await TOOLS_MAP.navigate.handler(page, { url: base }, ctx);
    const r = await TOOLS_MAP.click.handler(page, { selector: '#btn-cancelar' }, ctx);
    assert(r.ok, `click por selector falló: ${r.error}`);
  });

  await test('click: texto inexistente devuelve ok:false', async () => {
    const r = await TOOLS_MAP.click.handler(page, { text: 'BotónQueNoExiste_xyz' }, ctx);
    assert(!r.ok, 'debería fallar con texto inexistente');
  });

  await test('click: sin texto ni selector devuelve ok:false', async () => {
    const r = await TOOLS_MAP.click.handler(page, {}, ctx);
    assert(!r.ok);
  });

  // ── BLOQUE 5: fill_input ──────────────────────────────────────────────
  console.log('\n── 5. fill_input ────────────────────────────────────');

  await TOOLS_MAP.navigate.handler(page, { url: base }, ctx);

  await test('fill_input: rellena campo por selector name', async () => {
    const r = await TOOLS_MAP.fill_input.handler(page, { selector: "input[name='username']", value: 'admin' }, ctx);
    assert(r.ok, `falló: ${r.error}`);
    const val = await page.locator("input[name='username']").inputValue();
    assert(val === 'admin', `valor esperado "admin", fue "${val}"`);
  });

  await test('fill_input: rellena campo de contraseña', async () => {
    const r = await TOOLS_MAP.fill_input.handler(page, { selector: "input[type='password']", value: 'secreto123' }, ctx);
    assert(r.ok, `falló: ${r.error}`);
    const val = await page.locator("input[type='password']").inputValue();
    assert(val === 'secreto123', `valor: "${val}"`);
  });

  await test('fill_input: selector inexistente devuelve ok:false', async () => {
    const r = await TOOLS_MAP.fill_input.handler(page, { selector: '#campo-inexistente', value: 'x' }, ctx);
    assert(!r.ok, 'debería fallar con selector inexistente');
  });

  // ── BLOQUE 6: screenshot ──────────────────────────────────────────────
  console.log('\n── 6. screenshot ────────────────────────────────────');

  await TOOLS_MAP.navigate.handler(page, { url: base }, ctx);

  await test('screenshot: crea archivo PNG', async () => {
    const prevCount = ctx.screenshots.length;
    const r = await TOOLS_MAP.screenshot.handler(page, { label: 'test_screenshot_prueba' }, ctx);
    assert(r.ok, `falló: ${r.error}`);
    assert(ctx.screenshots.length > prevCount, 'no se agregó a ctx.screenshots');
    const file = path.join(screenshotsDir, r.data.file);
    assert(fs.existsSync(file), `archivo no existe: ${file}`);
    const size = fs.statSync(file).size;
    assert(size > 1000, `PNG demasiado pequeño (${size} bytes) — posiblemente vacío`);
  });

  await test('screenshot: label especial se sanitiza', async () => {
    const r = await TOOLS_MAP.screenshot.handler(page, { label: 'módulo/raro:2024' }, ctx);
    assert(r.ok);
    assert(!r.data.file.includes('/'), `filename contiene slash: ${r.data.file}`);
  });

  // ── BLOQUE 7: report_finding ──────────────────────────────────────────
  console.log('\n── 7. report_finding ────────────────────────────────');

  await test('report_finding: guarda finding con todos los campos', async () => {
    const prev = ctx.findings.length;
    const r = await TOOLS_MAP.report_finding.handler(page, {
      severity: 'HIGH',
      module: 'TEST',
      title: 'Botón roto de prueba',
      detail: 'El botón no responde al hacer click.',
      recommendation: 'Revisar el event listener en prueba.js:42',
      root_cause: 'apps/test/views.py:88 — la vista no retorna el contexto correcto',
    }, ctx);
    assert(r.ok);
    assert(ctx.findings.length === prev + 1, 'finding no se guardó');
    const f = ctx.findings[ctx.findings.length - 1];
    assert(f.severity === 'HIGH');
    assert(f.rootCause === 'apps/test/views.py:88 — la vista no retorna el contexto correcto', `rootCause: ${f.rootCause}`);
    assert(f.ts, 'falta timestamp');
  });

  await test('report_finding: INFO no requiere root_cause', async () => {
    const r = await TOOLS_MAP.report_finding.handler(page, {
      severity: 'INFO',
      module: 'LOGIN',
      title: 'Login funciona',
      detail: 'El flujo de login completó sin errores.',
    }, ctx);
    assert(r.ok);
  });

  // ── BLOQUE 8: check_network_errors ────────────────────────────────────
  console.log('\n── 8. check_network_errors ──────────────────────────');

  await test('check_network_errors: devuelve arrays aunque estén vacíos', async () => {
    const r = await TOOLS_MAP.check_network_errors.handler(page, {}, ctx);
    assert(r.ok);
    assert(Array.isArray(r.data.requestFailed));
    assert(Array.isArray(r.data.resource404));
  });

  // ── BLOQUE 8b: session_check ──────────────────────────────────────────
  console.log('\n── 8b. session_check ────────────────────────────────');

  await test('session_check: sesión activa en página normal no re-autentica', async () => {
    await page.goto(base, { waitUntil: 'domcontentloaded' });
    ctx.sessionLost = false;
    const r = await TOOLS_MAP.session_check.handler(page, {}, ctx);
    assert(r.ok, `falló: ${r.error}`);
    assert(r.data.sessionActive === true, 'debería reportar sesión activa');
    assert(r.data.url.includes('127.0.0.1'), `url inesperada: ${r.data.url}`);
  });

  await test('session_check: detecta ctx.sessionLost=true y reporta sin credenciales', async () => {
    ctx.sessionLost = true;
    ctx.agentUser = null;
    ctx.agentPass = null;
    const r = await TOOLS_MAP.session_check.handler(page, {}, ctx);
    assert(!r.ok, 'debería fallar si no hay credenciales');
    assert(r.error.includes('credenciales'), `error inesperado: ${r.error}`);
    // Restaurar estado
    ctx.sessionLost = false;
  });

  await test('report_finding: CRITICAL genera auto-screenshot', async () => {
    await page.goto(base, { waitUntil: 'domcontentloaded' });
    const prevShots = ctx.screenshots.length;
    const r = await TOOLS_MAP.report_finding.handler(page, {
      severity: 'CRITICAL',
      module: 'TEST',
      title: 'Error crítico de prueba',
      detail: 'El módulo explotó.',
    }, ctx);
    assert(r.ok);
    assert(r.data.screenshot, 'CRITICAL debería tener screenshot automático');
    assert(ctx.screenshots.length > prevShots, 'screenshot no se agregó a ctx');
  });

  await test('report_finding: INFO NO genera auto-screenshot', async () => {
    const prevShots = ctx.screenshots.length;
    const r = await TOOLS_MAP.report_finding.handler(page, {
      severity: 'INFO',
      module: 'TEST',
      title: 'Todo OK',
      detail: 'El módulo funciona.',
    }, ctx);
    assert(r.ok);
    assert(!r.data.screenshot, 'INFO no debería tener screenshot automático');
    assert(ctx.screenshots.length === prevShots, 'screenshot no debería haberse agregado');
  });

  await test('navigate: detecta sessionLost cuando redirige a /login/', async () => {
    // Simular una URL que redirige a /login/ (el servidor de prueba devuelve el mismo HTML, pero forzamos)
    // Usamos la URL /not-found que devuelve 404 — no es redirección a /login/ así que sessionLost=false
    ctx.sessionLost = false;
    const r = await TOOLS_MAP.navigate.handler(page, { url: `${base}/not-found` }, ctx);
    // /not-found no contiene /login/ en la URL final, así que sessionLost debe ser false
    assert(!r.data.sessionLost, 'no debería marcar sessionLost en una URL normal');
    await page.goto(base, { waitUntil: 'domcontentloaded' });
  });

  // ── BLOQUE 9: inspect_code ────────────────────────────────────────────
  console.log('\n── 9. inspect_code ──────────────────────────────────');

  await test('inspect_code: encuentra "PRISLAB_BASE_URL" en archivos del repo', async () => {
    // Buscar solo en *.mjs para que PowerShell sea rápido (el archivo .env.agent.example lo contiene)
    const r = await TOOLS_MAP.inspect_code.handler(page, { query: 'PRISLAB_BASE_URL', file_pattern: '*.mjs' }, ctx);
    assert(r.ok, `falló: ${r.error}`);
    assert(r.data.results !== 'Sin coincidencias en el código fuente.', 'No encontró PRISLAB_BASE_URL en archivos .mjs');
    assert(r.data.results.includes('PRISLAB_BASE_URL'), `resultado no contiene la query: ${r.data.results.slice(0, 200)}`);
  });

  await test('inspect_code: query sin resultados devuelve mensaje claro', async () => {
    const r = await TOOLS_MAP.inspect_code.handler(page, { query: 'TerminoQueNuncaExisteXYZ_12345' }, ctx);
    assert(r.ok);
    assert(r.data.matches === 0 || r.data.results.includes('Sin coincidencias'), `inesperado: ${r.data.results.slice(0, 100)}`);
  });

  await test('inspect_code: trunca resultados a ≤3000 chars', async () => {
    const r = await TOOLS_MAP.inspect_code.handler(page, { query: 'import', file_pattern: '*.py' }, ctx);
    assert(r.ok);
    assert(r.data.results.length <= 3100, `resultado demasiado largo: ${r.data.results.length}`);
  });

  // ── BLOQUE 10: read_code_file ─────────────────────────────────────────
  console.log('\n── 10. read_code_file ───────────────────────────────');

  await test('read_code_file: lee este mismo archivo de prueba', async () => {
    const r = await TOOLS_MAP.read_code_file.handler(page, {
      file_path: 'tools/test_agent_tools.mjs',
      start_line: 1,
      end_line: 10,
    }, ctx);
    assert(r.ok, `falló: ${r.error}`);
    assert(r.data.lines.includes('test_agent_tools'), `no encontró el contenido esperado: ${r.data.lines.slice(0, 200)}`);
    assert(r.data.totalLines > 50, `totalLines parece bajo: ${r.data.totalLines}`);
  });

  await test('read_code_file: ruta fuera del repo es rechazada', async () => {
    const r = await TOOLS_MAP.read_code_file.handler(page, { file_path: '../../etc/passwd' }, ctx);
    assert(!r.ok, 'debería rechazar rutas fuera del repo');
    assert(r.error.includes('fuera del repositorio') || r.error.includes('No se pudo leer'), `error inesperado: ${r.error}`);
  });

  await test('read_code_file: archivo inexistente devuelve ok:false', async () => {
    const r = await TOOLS_MAP.read_code_file.handler(page, { file_path: 'tools/archivo_que_no_existe_xyz.mjs' }, ctx);
    assert(!r.ok);
    assert(r.error.includes('No se pudo leer'), `error inesperado: ${r.error}`);
  });

  await test('read_code_file: respeta start_line y end_line', async () => {
    const r = await TOOLS_MAP.read_code_file.handler(page, {
      file_path: 'tools/test_agent_tools.mjs',
      start_line: 5,
      end_line: 8,
    }, ctx);
    assert(r.ok, `falló: ${r.error}`);
    // Cada línea tiene formato "5:contenido" — extraer el número antes del primer ":"
    const lines = r.data.lines.split('\n').filter(Boolean);
    assert(lines.length >= 1, 'no devolvió líneas');
    const firstNum = parseInt(lines[0].split(':')[0]);
    const lastNum  = parseInt(lines[lines.length - 1].split(':')[0]);
    assert(firstNum === 5, `primera línea debería ser 5, fue ${firstNum}`);
    assert(lastNum <= 8, `última línea debería ser ≤8, fue ${lastNum}`);
  });

  // ── BLOQUE 11: Helpers ────────────────────────────────────────────────
  console.log('\n── 11. Helpers (cleanUrl, hasErrorMarkers) ──────────');

  await test('cleanUrl: elimina query string', async () => {
    assert(cleanUrl('https://example.com/path?foo=bar') === 'https://example.com/path');
  });

  await test('cleanUrl: maneja undefined y null', async () => {
    assert(cleanUrl(undefined) === '');
    assert(cleanUrl(null) === '');
  });

  await test('hasErrorMarkers: detecta "server error (500)"', async () => {
    assert(hasErrorMarkers('Server Error (500) has occurred'));
  });

  await test('hasErrorMarkers: detecta "traceback"', async () => {
    assert(hasErrorMarkers('some Traceback more text'));
  });

  await test('hasErrorMarkers: no marca páginas normales', async () => {
    assert(!hasErrorMarkers('Bienvenido al sistema PRISLAB'));
  });

  await test('finalizeLoginAttempt: marca CRITICAL si sigue en /login/', async () => {
    const fakeCtx = { findings: [], auditSummary: '', auditStats: { passed: 0, failed: 0, warnings: 0 }, finished: false };
    const fakePage = { url: () => 'https://prislab.labcorecloud.com/login/' };
    const r = finalizeLoginAttempt(fakeCtx, fakePage);
    assert(!r.ok, 'debería devolver ok:false');
    assert(fakeCtx.finished === true, 'debería marcar finished');
    assert(fakeCtx.findings.length === 1, 'debería agregar un finding');
    assert(fakeCtx.findings[0].severity === 'CRITICAL', 'finding debe ser CRITICAL');
    assert(fakeCtx.auditSummary.startsWith('Login fallido'), `summary inesperado: ${fakeCtx.auditSummary}`);
  });

  await test('finalizeLoginAttempt: registra éxito fuera de /login/', async () => {
    const fakeCtx = { findings: [], auditSummary: '', auditStats: { passed: 0, failed: 0, warnings: 0 }, finished: false };
    const fakePage = { url: () => 'https://prislab.labcorecloud.com/home/' };
    const r = finalizeLoginAttempt(fakeCtx, fakePage);
    assert(r.ok, 'debería devolver ok:true');
    assert(fakeCtx.finished === false, 'no debería marcar finished');
    assert(fakeCtx.findings.length === 0, 'no debería agregar findings');
    assert(fakeCtx.auditSummary === 'Login exitoso. Auditoría iniciada.', `summary inesperado: ${fakeCtx.auditSummary}`);
  });

  // ── Limpieza ──────────────────────────────────────────────────────────
  await browser.close();
  server.close();

  // ── Resultado final ───────────────────────────────────────────────────
  console.log('\n═══════════════════════════════════════════════════════');
  console.log(`  Resultado: ${passed} pasaron / ${failed} fallaron`);
  if (failures.length) {
    console.log('\n  Fallos:');
    failures.forEach((f) => console.log(`    ❌ ${f.name}\n       ${f.error}`));
  }
  console.log('═══════════════════════════════════════════════════════\n');

  process.exit(failed > 0 ? 1 : 0);
}

main().catch((err) => {
  console.error('Error fatal en suite de pruebas:', err);
  process.exit(1);
});
