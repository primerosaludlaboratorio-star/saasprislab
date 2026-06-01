import fs from 'node:fs';

export async function ensureDir(path) {
  await fs.promises.mkdir(path, { recursive: true });
}

export async function loginWithRetry(page, context, { baseUrl, username, password, bypassToken = '' }) {
  if (!username || !password) {
    throw new Error('Faltan E2E_USER / E2E_PASS para autenticación.');
  }

  const loginUrl = `${baseUrl.replace(/\/$/, '')}/login/`;
  let lastUrl = loginUrl;
  let lastError = null;

  for (let attempt = 1; attempt <= 3; attempt += 1) {
    try {
      await page.goto(loginUrl, { waitUntil: 'domcontentloaded', timeout: 60000 });
      await page.setExtraHTTPHeaders({
        Referer: loginUrl,
        ...(bypassToken ? { 'X-Omni-Bypass': bypassToken } : {}),
      });
      await page.fill('input[name="username"], input#id_username', username, { timeout: 15000 });
      await page.fill('input[name="password"], input#id_password', password, { timeout: 15000 });
      await Promise.all([
        page.waitForLoadState('domcontentloaded', { timeout: 45000 }).catch(() => {}),
        page.click('button[type="submit"], input[type="submit"]', { timeout: 15000 }),
      ]);
      await page.waitForLoadState('networkidle', { timeout: 45000 }).catch(() => {});
      lastUrl = page.url();
      const cookies = await context.cookies();
      const hasSession = cookies.some((c) => (c?.name || '').toLowerCase() === 'sessionid');
      const html = await page.content();
      const hasLoginForm = html.includes('name="password"') && html.includes('name="username"');
      if (hasSession && !hasLoginForm) {
        return { ok: true, url: lastUrl };
      }
      lastError = new Error(`Login no confirmó sesión; URL final: ${lastUrl}`);
    } catch (error) {
      lastError = error;
      lastUrl = page.url();
    }
  }

  throw new Error(`No se pudo autenticar. Última URL: ${lastUrl}. Detalle: ${lastError}`);
}

export async function safeScreenshot(page, outputDir, name) {
  const file = `${outputDir}/${Date.now()}_${name}.png`;
  await page.screenshot({ path: file, fullPage: true }).catch(() => {});
  return file;
}

export function textIncludesAny(text, needles) {
  const haystack = String(text || '').toLowerCase();
  return needles.some((n) => haystack.includes(String(n).toLowerCase()));
}
