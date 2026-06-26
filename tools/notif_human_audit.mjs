// Auditoría por INTERFAZ HUMANA real (Chromium) del Centro de Notificaciones.
// Login como Alice, abre /notificaciones/, valida aislamiento por destinatario,
// badge, y prueba IDOR (marcar la notificación personal de Bob -> 403).
import { chromium } from 'playwright';

const BASE = 'http://127.0.0.1:8000';
const SHOT = '/tmp/claude-0/-home-user-saasprislab/611553c5-050b-528e-971e-e85ad3068344/scratchpad';
const out = [];
const log = (ok, msg) => { out.push(`${ok ? 'PASS' : 'FAIL'} · ${msg}`); };

async function launch() {
  const opts = { headless: true, args: ['--no-sandbox', '--disable-dev-shm-usage'] };
  try { return await chromium.launch(opts); }
  catch { return await chromium.launch({ ...opts, executablePath: '/opt/pw-browsers/chromium' }); }
}

const browser = await launch();
const ctx = await browser.newContext({ ignoreHTTPSErrors: true });
const page = await ctx.newPage();
try {
  // 1) LOGIN (interfaz humana real)
  await page.goto(`${BASE}/login/`, { waitUntil: 'domcontentloaded' });
  await page.fill('input[name="username"]', 'audit_alice');
  await page.fill('input[type="password"]', 'AuditPass123!');
  await Promise.all([
    page.waitForLoadState('networkidle').catch(() => {}),
    page.click('button[type="submit"], input[type="submit"]'),
  ]);
  const afterLogin = page.url();
  log(!afterLogin.endsWith('/login/'), `login redirige fuera de /login/ (url=${afterLogin})`);

  // 2) CENTRO DE NOTIFICACIONES
  const resp = await page.goto(`${BASE}/notificaciones/`, { waitUntil: 'domcontentloaded' });
  log(resp.status() === 200, `/notificaciones/ responde ${resp.status()}`);
  await page.screenshot({ path: `${SHOT}/notif_lista.png`, fullPage: true });
  const body = await page.content();
  log(body.includes('[AUDIT] Global'), 'Alice VE la notificación Global');
  log(body.includes('[AUDIT] Para Alice'), 'Alice VE su notificación personal');
  log(!body.includes('[AUDIT] Para Bob'), 'Alice NO ve la notificación personal de Bob (aislamiento por destinatario)');

  // 3) BADGE (endpoint JSON consumido por la campana)
  const badge = await page.request.get(`${BASE}/notificaciones/badge/`);
  const bj = await badge.json();
  const titulos = (bj.recientes || []).map(r => r.titulo).join(' | ');
  log(badge.status() === 200, `badge responde 200 (no_leidas=${bj.no_leidas})`);
  log(!titulos.includes('Para Bob'), `badge NO incluye notificaciones de Bob (recientes: ${titulos})`);

  // 4) IDOR: marcar la notificación PERSONAL de Bob (id=3) siendo Alice -> 403
  const cookies = await ctx.cookies();
  const csrf = (cookies.find(c => c.name === 'csrftoken') || {}).value || '';
  const idor = await page.request.post(`${BASE}/notificaciones/3/leer/`, {
    headers: { 'X-CSRFToken': csrf, 'Referer': `${BASE}/notificaciones/` },
  });
  log(idor.status() === 403, `marcar notif de Bob (IDOR) -> ${idor.status()} (esperado 403)`);

  // 5) Marcar la propia notificación de Alice (id=2) -> ok
  const own = await page.request.post(`${BASE}/notificaciones/2/leer/`, {
    headers: { 'X-CSRFToken': csrf, 'Referer': `${BASE}/notificaciones/` },
  });
  log(own.status() === 200, `marcar la propia notificación -> ${own.status()} (esperado 200)`);
} catch (e) {
  log(false, `EXCEPCIÓN: ${e.message}`);
} finally {
  await browser.close();
  console.log('\n===== RESULTADO AUDITORÍA HUMANA · NOTIFICACIONES =====');
  console.log(out.join('\n'));
  const fails = out.filter(l => l.startsWith('FAIL')).length;
  console.log(`\n${fails === 0 ? '✅ TODO VERDE' : '❌ ' + fails + ' FALLO(S)'} (${out.length} checks)`);
  process.exit(fails === 0 ? 0 : 1);
}
