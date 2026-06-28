/**
 * ai_agent_tools.mjs
 * ─────────────────────────────────────────────────────────────────────────────
 * Herramientas Playwright que el agente LLM puede invocar.
 * Cada herramienta expone: nombre, descripción, parámetros JSON Schema, y handler.
 *
 * El handler recibe (page, params, context) y retorna { ok, data, error }.
 * context = { findings, screenshots, screenshotsDir, recorder }
 * ─────────────────────────────────────────────────────────────────────────────
 */

import fs from 'node:fs';
import path from 'node:path';

// ── Helpers ────────────────────────────────────────────────────────────────

export function cleanUrl(url) {
  return String(url || '').split('?')[0];
}

export function hasErrorMarkers(text) {
  const lower = String(text || '').toLowerCase();
  const markers = [
    'algo salió mal', 'server error (500)', 'internal server error',
    'traceback', 'exception value:', 'operationalerror at /',
    'fielderror at /', 'permissiondenied', 'page not found (404)',
    'csrf verification failed',
  ];
  return markers.some((m) => lower.includes(m));
}

async function captureScreenshot(page, screenshotsDir, name) {
  const safe = String(name).replace(/[^a-z0-9_\-]/gi, '_').slice(0, 80);
  const file = path.join(screenshotsDir, `${safe}.png`);
  await page.screenshot({ path: file, fullPage: true }).catch(() => {});
  return path.basename(file);
}

// ── Tool definitions ───────────────────────────────────────────────────────

export const TOOLS = [
  {
    name: 'navigate',
    description: 'Navigate the browser to a URL and wait for the page to stabilize. Use the same protocol (http:// or https://) as the base URL provided.',
    parameters: {
      type: 'object',
      properties: {
        url: { type: 'string', description: 'Full URL to navigate to. Use the same protocol as the base URL.' },
        wait_for: {
          type: 'string',
          enum: ['networkidle', 'domcontentloaded', 'load'],
          description: 'Wait condition. Default: networkidle.',
        },
      },
      required: ['url'],
    },
    async handler(page, params, ctx) {
      const waitFor = params.wait_for || 'networkidle';
      try {
        // Usar la URL tal cual viene - no forzar cambios de protocolo
        let targetUrl = params.url;
        await page.goto(targetUrl, { waitUntil: waitFor, timeout: 60000 });
        const currentUrl = page.url();
        const title = await page.title().catch(() => '');
        const bodyText = await page.innerText('body').catch(() => '');
        const hasError = hasErrorMarkers(bodyText) || hasErrorMarkers(title);
        // Sesión expirada: redirigido a /login/ inesperadamente
        const sessionLost = !params.url.includes('/login/') && currentUrl.includes('/login/');
        // Auto-screenshot en error o sesión perdida
        let shot = null;
        if (hasError || sessionLost) {
          shot = await captureScreenshot(page, ctx.screenshotsDir, `error_nav_${Date.now()}`);
          ctx.screenshots.push(shot);
          if (sessionLost) ctx.sessionLost = true;
        }
        return {
          ok: !hasError && !sessionLost,
          data: { url: currentUrl, title, hasErrorMarkers: hasError, sessionLost, screenshot: shot },
          error: sessionLost ? 'SESIÓN EXPIRADA — redirigido a /login/. Llama session_check() para re-autenticar.'
            : hasError ? 'Page contains error markers (500/traceback/etc)' : null,
        };
      } catch (e) {
        return { ok: false, data: {}, error: String(e.message) };
      }
    },
  },

  {
    name: 'get_page_state',
    description: 'Get current page URL, title, visible text summary, and console errors. Use after navigating or after interactions.',
    parameters: {
      type: 'object',
      properties: {
        include_html_snippet: {
          type: 'boolean',
          description: 'If true, include first 3000 chars of simplified HTML for element discovery.',
        },
      },
      required: [],
    },
    async handler(page, params, ctx) {
      const url = page.url();
      const title = await page.title().catch(() => '');
      // Texto visible filtrado: excluye scripts/estilos, max 1500 chars
      const text = await page.evaluate(() => {
        const clone = document.body.cloneNode(true);
        clone.querySelectorAll('script,style,svg,noscript').forEach((el) => el.remove());
        return (clone.innerText || clone.textContent || '').replace(/\s+/g, ' ').trim();
      }).catch(() => '');
      const html = params.include_html_snippet
        ? (await page.content().catch(() => '')).slice(0, 2000)
        : null;
      const hasError = hasErrorMarkers(text) || hasErrorMarkers(title);
      // Recolectar errores JS reales (ignorar QZ Tray 8181/8484)
      const jsErrors = ctx.consoleErrors.slice(-10).filter(
        (e) => !String(e).includes('8181') && !String(e).includes('8484')
      );
      return {
        ok: true,
        data: {
          url: cleanUrl(url),
          title,
          visibleText: text.slice(0, 1500),
          hasErrorMarkers: hasError,
          htmlSnippet: html,
          jsErrors,
        },
        error: null,
      };
    },
  },

  {
    name: 'click',
    description: 'Click an element on the page. Prefer text-based selectors. Falls back to CSS selector.',
    parameters: {
      type: 'object',
      properties: {
        text: { type: 'string', description: 'Visible text of the element to click.' },
        selector: { type: 'string', description: 'CSS selector as fallback.' },
        timeout_ms: { type: 'number', description: 'Max wait time in ms. Default 5000.' },
      },
      required: [],
    },
    async handler(page, params, ctx) {
      const timeout = params.timeout_ms || 5000;
      try {
        if (params.text) {
          const loc = page.getByText(params.text, { exact: false }).first();
          await loc.click({ timeout });
        } else if (params.selector) {
          await page.click(params.selector, { timeout });
        } else {
          return { ok: false, data: {}, error: 'Must provide text or selector.' };
        }
        await page.waitForLoadState('networkidle', { timeout: 10000 }).catch(() => {});
        return { ok: true, data: { url: cleanUrl(page.url()) }, error: null };
      } catch (e) {
        return { ok: false, data: {}, error: String(e.message) };
      }
    },
  },

  {
    name: 'fill_input',
    description: 'Fill a text input or textarea with a value.',
    parameters: {
      type: 'object',
      properties: {
        selector: { type: 'string', description: 'CSS selector or label text of the input.' },
        value: { type: 'string', description: 'Value to type.' },
        submit: { type: 'boolean', description: 'If true, press Enter after filling.' },
      },
      required: ['value'],
    },
    async handler(page, params, ctx) {
      try {
        const sel = params.selector || 'input:visible, textarea:visible';
        const loc = page.locator(sel).first();
        await loc.fill(params.value, { timeout: 5000 });
        if (params.submit) await loc.press('Enter');
        await page.waitForTimeout(800);
        return { ok: true, data: { value: params.value }, error: null };
      } catch (e) {
        return { ok: false, data: {}, error: String(e.message) };
      }
    },
  },

  {
    name: 'find_elements',
    description: 'Find elements matching a selector and return their text and attributes.',
    parameters: {
      type: 'object',
      properties: {
        selector: { type: 'string', description: 'CSS selector.' },
        limit: { type: 'number', description: 'Max elements to return. Default 10.' },
      },
      required: ['selector'],
    },
    async handler(page, params, ctx) {
      try {
        const locs = page.locator(params.selector);
        const count = await locs.count();
        const limit = Math.min(params.limit || 20, count);
        const items = [];
        for (let i = 0; i < limit; i++) {
          const loc = locs.nth(i);
          const text    = await loc.innerText().catch(() => '');
          const href    = await loc.getAttribute('href').catch(() => null);
          const type    = await loc.getAttribute('type').catch(() => null);
          const id      = await loc.getAttribute('id').catch(() => null);
          const name    = await loc.getAttribute('name').catch(() => null);
          const ph      = await loc.getAttribute('placeholder').catch(() => null);
          const ariaL   = await loc.getAttribute('aria-label').catch(() => null);
          const visible = await loc.isVisible().catch(() => false);
          if (!visible) continue;
          items.push({ text: text.trim().slice(0, 150), href, type, id, name, placeholder: ph, ariaLabel: ariaL });
        }
        return { ok: true, data: { count, visible: items.length, items }, error: null };
      } catch (e) {
        return { ok: false, data: {}, error: String(e.message) };
      }
    },
  },

  {
    name: 'screenshot',
    description: 'Take a screenshot of the current page and save it.',
    parameters: {
      type: 'object',
      properties: {
        label: { type: 'string', description: 'Label for the screenshot filename.' },
      },
      required: [],
    },
    async handler(page, params, ctx) {
      const label = params.label || `shot_${Date.now()}`;
      const file = await captureScreenshot(page, ctx.screenshotsDir, label);
      ctx.screenshots.push(file);
      return { ok: true, data: { file }, error: null };
    },
  },

  {
    name: 'check_network_errors',
    description: 'Check for failed network requests and 404 resources since the last call.',
    parameters: { type: 'object', properties: {}, required: [] },
    async handler(page, params, ctx) {
      const failed = ctx.requestFailed.slice(-20);
      const r404 = ctx.resource404.slice(-20);
      return {
        ok: true,
        data: { requestFailed: failed, resource404: r404 },
        error: null,
      };
    },
  },

  {
    name: 'report_finding',
    description: 'Record a finding (bug, warning, or info) from what you observed. CRITICAL/HIGH findings require root_cause from inspect_code.',
    parameters: {
      type: 'object',
      properties: {
        severity: {
          type: 'string',
          enum: ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW', 'INFO'],
          description: 'Severity of the finding. Use INFO for "no data" or "design decision" findings.',
        },
        module: { type: 'string', description: 'PRISLAB module this applies to.' },
        url: { type: 'string', description: 'URL where the finding was observed.' },
        title: { type: 'string', description: 'Short title of the finding.' },
        detail: { type: 'string', description: 'Full description with observed evidence.' },
        recommendation: { type: 'string', description: 'What should be fixed.' },
        root_cause: { type: 'string', description: 'Root cause found in source code after calling inspect_code. REQUIRED for CRITICAL/HIGH. Include file path and line number (e.g. farmacia/views/pdv.py:142).' },
        screenshot: { type: 'string', description: 'Screenshot filename taken as evidence for this finding (from a previous screenshot() call).' },
        finding_type: {
          type: 'string',
          enum: ['REAL_BUG', 'NO_DATA', 'DESIGN_DECISION', 'FALSE_POSITIVE'],
          description: 'Type of finding. REAL_BUG for actual issues, NO_DATA for empty screens, DESIGN_DECISION for intentional redirects, FALSE_POSITIVE for误报.',
        },
      },
      required: ['severity', 'module', 'title', 'detail'],
    },
    async handler(page, params, ctx) {
      // Validación: CRITICAL/HIGH requieren root_cause
      if (['CRITICAL', 'HIGH'].includes(params.severity) && !params.root_cause) {
        console.error(`[AUDITOR] report_finding: severity=${params.severity} REQUIERE root_cause. Hallazgo rechazado: ${params.title}`);
        return { ok: false, data: {}, error: 'CRITICAL/HIGH findings require root_cause from inspect_code' };
      }
      
      // Validación: 404 requiere verificación de código
      if (params.detail.toLowerCase().includes('404') && !params.root_cause) {
        console.error(`[AUDITOR] report_finding: 404 finding REQUIERE root_cause. Usa inspect_code primero. Hallazgo rechazado: ${params.title}`);
        return { ok: false, data: {}, error: '404 findings require root_cause from inspect_code to verify if route/view exists' };
      }
      
      // Auto-screenshot si es HIGH/CRITICAL y no se proporcionó uno
      let shot = params.screenshot || null;
      if (!shot && ['CRITICAL', 'HIGH'].includes(params.severity)) {
        shot = await captureScreenshot(page, ctx.screenshotsDir, `finding_${params.severity.toLowerCase()}_${Date.now()}`);
        ctx.screenshots.push(shot);
      }
      const finding = {
        severity: params.severity,
        module: params.module,
        url: params.url || cleanUrl(page.url()),
        title: params.title,
        detail: params.detail,
        recommendation: params.recommendation || '',
        rootCause: params.root_cause || '',
        screenshot: shot || null,
        findingType: params.finding_type || 'REAL_BUG',
        ts: new Date().toISOString(),
      };
      ctx.findings.push(finding);
      return { ok: true, data: finding, error: null };
    },
  },

  {
    name: 'wait',
    description: 'Wait for a specified number of milliseconds.',
    parameters: {
      type: 'object',
      properties: {
        ms: { type: 'number', description: 'Milliseconds to wait.' },
      },
      required: ['ms'],
    },
    async handler(page, params, ctx) {
      await page.waitForTimeout(Math.min(params.ms || 1000, 10000));
      return { ok: true, data: {}, error: null };
    },
  },

  {
    name: 'inspect_code',
    description: 'Search the repository source code to find the root cause of a UI issue. Use this whenever you find a bug, broken feature, or unexpected behavior — search for the view, template, or URL pattern responsible.',
    parameters: {
      type: 'object',
      properties: {
        query: {
          type: 'string',
          description: 'Text to search in the codebase (e.g. a URL path, function name, template variable, error message, or CSS selector).',
        },
        file_pattern: {
          type: 'string',
          description: 'Optional glob pattern to restrict search (e.g. "*.py", "*.html", "*.js"). Default: search all files.',
        },
        context_lines: {
          type: 'number',
          description: 'Lines of context to return around each match (default 4).',
        },
      },
      required: ['query'],
    },
    async handler(page, params, ctx) {
      const { execSync } = await import('node:child_process');
      const query = String(params.query || '').trim();
      if (!query) return { ok: false, data: {}, error: 'query vacío' };

      const ctxLines = Math.min(Number(params.context_lines) || 4, 10);
      // En Windows, import.meta.url.pathname produce /C:/... — fileURLToPath lo normaliza
      const { fileURLToPath: futp } = await import('node:url');
      const repoRoot = path.resolve(path.dirname(futp(import.meta.url)), '..');

      // Extensiones a buscar según file_pattern o todas las relevantes
      const ext = params.file_pattern || '*.py,*.html,*.js,*.mjs,*.ts';
      const extList = ext.split(',').map((e) => e.trim());

      // Directorios a excluir
      const excludeDirs = [
        'node_modules', '.git', '__pycache__', '.venv', 'venv',
        'staticfiles', 'static', 'media', 'ai_audit_', 'auditoria_',
      ];

      let results = '';
      let hitCount = 0;

      // Usar PowerShell Select-String (compatible Windows)
      try {
        const escaped = query.replace(/'/g, "''");
        const inclPatterns = extList.map((e) => `'${e.replace('*', '*')}'`).join(',');
        const excludePattern = excludeDirs.join('|');
        const psCmd = [
          `Get-ChildItem -Path '${repoRoot}' -Recurse -Include ${inclPatterns} -ErrorAction SilentlyContinue`,
          `| Where-Object { $_.FullName -notmatch '(${excludePattern})' }`,
          `| Select-String -Pattern '${escaped}' -Context ${ctxLines},${ctxLines} -ErrorAction SilentlyContinue`,
          `| Select-Object -First 40`,
          `| Out-String -Width 200`,
        ].join(' ');
        const out = execSync(`powershell -NoProfile -Command "${psCmd}"`, {
          encoding: 'utf8', timeout: 30000, maxBuffer: 1024 * 1024,
        });
        results = out.trim();
        hitCount = (results.match(/^.*:\d+:/gm) || []).length;
      } catch (e) {
        results = String(e.stdout || e.message || '').slice(0, 500);
      }

      if (!results) {
        return { ok: true, data: { matches: 0, results: 'Sin coincidencias en el código fuente.' }, error: null };
      }

      // Truncar a 3000 chars
      const truncated = results.length > 3000
        ? results.slice(0, 3000) + '\n... [truncado]'
        : results;

      return { ok: true, data: { query, matches: hitCount, results: truncated }, error: null };
    },
  },

  {
    name: 'session_check',
    description: 'Check if the session is still active. If the session has expired (redirected to /login/), re-authenticate automatically. Call this at the start of each module or after a navigate() returns sessionLost=true.',
    parameters: {
      type: 'object',
      properties: {
        base_url: { type: 'string', description: 'Base URL of the app (e.g. https://prislab.labcorecloud.com).' },
      },
      required: [],
    },
    async handler(page, params, ctx) {
      const currentUrl = page.url();
      const isOnLogin = currentUrl.includes('/login/');
      if (!isOnLogin && !ctx.sessionLost) {
        return { ok: true, data: { sessionActive: true, url: cleanUrl(currentUrl) }, error: null };
      }
      // Sesión perdida — re-autenticar usando las credenciales guardadas en el contexto
      const user = ctx.agentUser;
      const pass = ctx.agentPass;
      if (!user || !pass) {
        return { ok: false, data: { sessionActive: false }, error: 'No hay credenciales en ctx para re-autenticar.' };
      }
      try {
        const loginUrl = params.base_url
          ? `${params.base_url.replace(/\/$/, '')}/login/`
          : currentUrl.includes('/login/') ? currentUrl : `${new URL(currentUrl).origin}/login/`;
        await page.goto(loginUrl, { waitUntil: 'networkidle', timeout: 30000 });
        await page.locator("input[name='username']").fill(user, { timeout: 5000 });
        await page.locator("input[type='password']").fill(pass, { timeout: 5000 });
        const btn = page.locator("button[type='submit'], input[type='submit']").first();
        await btn.click({ timeout: 5000 });
        await page.waitForLoadState('networkidle', { timeout: 15000 }).catch(() => {});
        const afterUrl = page.url();
        const ok = !afterUrl.includes('/login/');
        ctx.sessionLost = !ok;
        const shot = await captureScreenshot(page, ctx.screenshotsDir, `session_restored_${Date.now()}`);
        ctx.screenshots.push(shot);
        return {
          ok,
          data: { sessionActive: ok, url: cleanUrl(afterUrl), screenshot: shot },
          error: ok ? null : 'Re-autenticación fallida — sigue en /login/',
        };
      } catch (e) {
        return { ok: false, data: { sessionActive: false }, error: String(e.message) };
      }
    },
  },

  {
    name: 'read_code_file',
    description: 'Read a specific source file from the repository to inspect its contents. Use this after inspect_code identifies a file to understand the full context.',
    parameters: {
      type: 'object',
      properties: {
        file_path: {
          type: 'string',
          description: 'Relative path from repo root (e.g. farmacia/views/pdv.py or apps/farmacia/templates/pdv.html).',
        },
        start_line: { type: 'number', description: 'First line to read (1-indexed). Default 1.' },
        end_line: { type: 'number', description: 'Last line to read. Default start_line + 60.' },
      },
      required: ['file_path'],
    },
    async handler(page, params, ctx) {
      const { fileURLToPath: futp } = await import('node:url');
      const repoRoot = path.resolve(path.dirname(futp(import.meta.url)), '..');
      const target = path.resolve(repoRoot, params.file_path.replace(/^[\/\\]/, ''));
      // Seguridad: solo leer dentro del repo
      if (!target.startsWith(repoRoot)) {
        return { ok: false, data: {}, error: 'Ruta fuera del repositorio' };
      }
      try {
        const content = fs.readFileSync(target, 'utf8');
        const allLines = content.split('\n');
        const start = Math.max(0, (params.start_line || 1) - 1);
        const end = Math.min(allLines.length, params.end_line || start + 60);
        const slice = allLines.slice(start, end)
          .map((l, i) => `${start + i + 1}:${l}`)
          .join('\n');
        return {
          ok: true,
          data: { file: params.file_path, totalLines: allLines.length, lines: slice.slice(0, 3000) },
          error: null,
        };
      } catch (e) {
        return { ok: false, data: {}, error: `No se pudo leer: ${e.message}` };
      }
    },
  },

  {
    name: 'finish_audit',
    description: 'Signal that the audit is complete. Provide a final summary.',
    parameters: {
      type: 'object',
      properties: {
        summary: { type: 'string', description: 'Overall audit summary in Spanish.' },
        passed: { type: 'number', description: 'Number of checks that passed.' },
        failed: { type: 'number', description: 'Number of checks that failed.' },
        warnings: { type: 'number', description: 'Number of warnings.' },
      },
      required: ['summary'],
    },
    async handler(page, params, ctx) {
      ctx.finished = true;
      ctx.auditSummary = params.summary;
      ctx.auditStats = {
        passed: params.passed || 0,
        failed: params.failed || 0,
        warnings: params.warnings || 0,
      };
      return { ok: true, data: params, error: null };
    },
  },
];

export const TOOLS_SCHEMA = TOOLS.map((t) => ({
  type: 'function',
  function: {
    name: t.name,
    description: t.description,
    parameters: t.parameters,
  },
}));

export const TOOLS_MAP = Object.fromEntries(TOOLS.map((t) => [t.name, t]));
