/**
 * PRISLAB — AI Agent Audit Runner
 * ─────────────────────────────────────────────────────────────────────────────
 * Agente LLM autónomo que audita PRISLAB como lo haría un humano.
 * El agente observa, razona y actúa — no sigue un script hardcodeado.
 *
 * Proveedores LLM soportados (vía .env.agent o variables de entorno):
 *   OpenAI     — AGENT_PROVIDER=openai   AGENT_API_KEY=sk-...
 *   Anthropic  — AGENT_PROVIDER=anthropic AGENT_API_KEY=sk-ant-...
 *   Gemini     — AGENT_PROVIDER=gemini   AGENT_API_KEY=AIza...
 *   Ollama     — AGENT_PROVIDER=ollama   AGENT_BASE_URL=http://localhost:11434
 *
 * Uso:
 *   node tools/run_ai_agent_audit.mjs --target local --user admin --pass secret
 *   node tools/run_ai_agent_audit.mjs --target cloud --modules laboratorio,farmacia
 *   node tools/run_ai_agent_audit.mjs --headless --max-steps 40
 *
 * Variables de entorno:
 *   AGENT_PROVIDER         openai | anthropic | gemini | ollama
 *   AGENT_API_KEY          API key del proveedor
 *   AGENT_MODEL            Modelo a usar (default según proveedor)
 *   AGENT_BASE_URL         URL base para Ollama o proxies OpenAI-compatible
 *   AGENT_MAX_STEPS        Máx iteraciones del bucle (default 60)
 *   AGENT_TEMPERATURE      Temperatura del modelo (default 0.2)
 *   PRISLAB_BASE_URL       URL base de PRISLAB
 *   AGENT_USER             Usuario de prueba
 *   AGENT_PASS             Contraseña de prueba
 *   AGENT_HEADLESS         1 para headless
 *   AGENT_SLOW_MO          ms entre acciones Playwright (default 120)
 *   AGENT_MODULES          Módulos a auditar separados por coma
 * ─────────────────────────────────────────────────────────────────────────────
 */

import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { createRequire } from 'node:module';

const ENV = typeof process !== 'undefined' && process?.env ? process.env : {};

// ── Carga .env.agent si existe (sin dependencia externa) ──────────────────
const __dirname = path.dirname(fileURLToPath(import.meta.url));
const repoRoot = path.resolve(__dirname, '..');

function loadEnvFile(filePath) {
  if (!fs.existsSync(filePath)) return;
  const lines = fs.readFileSync(filePath, 'utf8').split('\n');
  for (const line of lines) {
    const trimmed = line.trim();
    if (!trimmed || trimmed.startsWith('#')) continue;
    const eqIdx = trimmed.indexOf('=');
    if (eqIdx < 0) continue;
    const key = trimmed.slice(0, eqIdx).trim();
    const val = trimmed.slice(eqIdx + 1).trim().replace(/^['"]|['"]$/g, '');
    if (key && !(key in ENV)) ENV[key] = val;
  }
}

loadEnvFile(path.join(repoRoot, '.env.agent'));
loadEnvFile(path.join(repoRoot, '.env'));

// ── Playwright ─────────────────────────────────────────────────────────────
const { chromium } = await import('playwright');
import { TOOLS_SCHEMA, TOOLS_MAP, cleanUrl } from './ai_agent_tools.mjs';

// ── Timestamp ─────────────────────────────────────────────────────────────
function stamp() {
  const d = new Date();
  const p = (n) => String(n).padStart(2, '0');
  return `${d.getFullYear()}${p(d.getMonth()+1)}${p(d.getDate())}_${p(d.getHours())}${p(d.getMinutes())}${p(d.getSeconds())}`;
}

// ── Arg parser ────────────────────────────────────────────────────────────
function parseArgs(argv) {
  const cfg = {
    target: ENV.HUMAN_UI_TARGET || ENV.AGENT_TARGET || 'cloud',
    base: ENV.PRISLAB_BASE_URL || '',
    user: ENV.AGENT_USER || ENV.HUMAN_UI_USER || ENV.E2E_USER || '',
    pass: ENV.AGENT_PASS || ENV.HUMAN_UI_PASS || ENV.E2E_PASS || '',
    headless: (ENV.AGENT_HEADLESS || '').trim() === '1',
    slowMo: Number(ENV.AGENT_SLOW_MO || 120),
    maxSteps: Number(ENV.AGENT_MAX_STEPS || 60),
    modules: (ENV.AGENT_MODULES || '').split(',').map((m) => m.trim()).filter(Boolean),
    provider: (ENV.AGENT_PROVIDER || 'openai').toLowerCase(),
    apiKey: ENV.AGENT_API_KEY || '',
    model: ENV.AGENT_MODEL || '',
    baseUrl: ENV.AGENT_BASE_URL || '',
    temperature: Number(ENV.AGENT_TEMPERATURE || 0.2),
  };

  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    if (a === '--target') cfg.target = argv[++i] || cfg.target;
    else if (a === '--base') cfg.base = argv[++i] || cfg.base;
    else if (a === '--user') cfg.user = argv[++i] || cfg.user;
    else if (a === '--pass') cfg.pass = argv[++i] || cfg.pass;
    else if (a === '--headless') cfg.headless = true;
    else if (a === '--slow-mo') cfg.slowMo = Number(argv[++i] || cfg.slowMo);
    else if (a === '--max-steps') cfg.maxSteps = Number(argv[++i] || cfg.maxSteps);
    else if (a === '--modules') cfg.modules = (argv[++i] || '').split(',').map((m) => m.trim()).filter(Boolean);
    else if (a === '--provider') cfg.provider = argv[++i] || cfg.provider;
    else if (a === '--api-key') cfg.apiKey = argv[++i] || cfg.apiKey;
    else if (a === '--model') cfg.model = argv[++i] || cfg.model;
  }

  return cfg;
}

// ── Resolver base URL desde manifest ──────────────────────────────────────
function resolveBaseUrl(manifest, target, explicitBase) {
  if (explicitBase) return explicitBase.replace(/\/$/, '');
  const defaultBase = manifest?.targets?.[target]?.baseUrlDefault;
  if (defaultBase) return defaultBase.replace(/\/$/, '');
  return 'http://127.0.0.1:8000';
}

// ── Proveedores LLM ───────────────────────────────────────────────────────

const PROVIDER_DEFAULTS = {
  openai:    { model: 'gpt-4o',              baseUrl: 'https://api.openai.com/v1' },
  anthropic: { model: 'claude-3-5-sonnet-20241022', baseUrl: 'https://api.anthropic.com' },
  gemini:    { model: 'gemini-1.5-pro',      baseUrl: 'https://generativelanguage.googleapis.com/v1beta' },
  ollama:    { model: 'llama3.1',            baseUrl: 'http://localhost:11434' },
};

/**
 * Llama al LLM con una lista de mensajes y retorna la respuesta (text o tool_call).
 * Normaliza a formato OpenAI tool_calls para simplificar el agente.
 */
async function callLLM(cfg, messages, toolsOverride) {
  const provider = cfg.provider;
  const defaults = PROVIDER_DEFAULTS[provider] || PROVIDER_DEFAULTS.openai;
  const model = cfg.model || defaults.model;
  const baseUrl = cfg.baseUrl || defaults.baseUrl;
  const apiKey = cfg.apiKey;

  const tools = toolsOverride || TOOLS_SCHEMA;
  if (provider === 'anthropic') {
    return await callAnthropic(baseUrl, apiKey, model, cfg.temperature, messages, tools);
  }
  if (provider === 'gemini') {
    return await callGemini(baseUrl, apiKey, model, cfg.temperature, messages, tools);
  }
  // openai + ollama + cualquier compatible OpenAI
  return await callOpenAICompat(baseUrl, apiKey, model, cfg.temperature, messages, provider === 'ollama', tools);
}

async function callOpenAICompat(baseUrl, apiKey, model, temperature, messages, isOllama, tools) {
  const url = `${baseUrl}/chat/completions`;
  const headers = { 'Content-Type': 'application/json' };
  if (apiKey) headers['Authorization'] = `Bearer ${apiKey}`;

  const body = {
    model,
    messages,
    temperature,
    tools: tools || TOOLS_SCHEMA,
    tool_choice: 'auto',
  };

  const res = await fetch(url, {
    method: 'POST',
    headers,
    body: JSON.stringify(body),
  });

  if (!res.ok) {
    const text = await res.text().catch(() => '');
    throw new Error(`LLM API error ${res.status}: ${text.slice(0, 300)}`);
  }

  const data = await res.json();
  const choice = data.choices?.[0];
  if (!choice) throw new Error('No choices in LLM response');

  return normalizeOpenAIChoice(choice);
}

async function callAnthropic(baseUrl, apiKey, model, temperature, messages, tools) {
  const url = `${baseUrl}/v1/messages`;
  const systemMsg = messages.find((m) => m.role === 'system');
  const otherMsgs = messages.filter((m) => m.role !== 'system');
  const toolsToUse = tools || TOOLS_SCHEMA;

  const anthropicTools = toolsToUse.map((t) => ({
    name: t.function.name,
    description: t.function.description,
    input_schema: t.function.parameters,
  }));

  const body = {
    model,
    max_tokens: 4096,
    temperature,
    system: systemMsg?.content || '',
    messages: otherMsgs.map((m) => ({ role: m.role, content: m.content })),
    tools: anthropicTools,
  };

  const res = await fetch(url, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'x-api-key': apiKey,
      'anthropic-version': '2023-06-01',
    },
    body: JSON.stringify(body),
  });

  if (!res.ok) {
    const text = await res.text().catch(() => '');
    throw new Error(`Anthropic API error ${res.status}: ${text.slice(0, 300)}`);
  }

  const data = await res.json();
  // Normalizar a formato OpenAI
  const textBlock = data.content?.find((b) => b.type === 'text');
  const toolBlock = data.content?.find((b) => b.type === 'tool_use');

  if (toolBlock) {
    return {
      type: 'tool_call',
      toolCalls: [{
        id: toolBlock.id || `tc_${Date.now()}`,
        name: toolBlock.name,
        arguments: toolBlock.input || {},
      }],
      text: textBlock?.text || '',
    };
  }
  return { type: 'text', text: textBlock?.text || '', toolCalls: [] };
}

async function callGemini(baseUrl, apiKey, model, temperature, messages, tools) {
  const url = `${baseUrl}/models/${model}:generateContent?key=${apiKey}`;
  const toolsToUse = tools || TOOLS_SCHEMA;

  const geminiTools = [{
    function_declarations: toolsToUse.map((t) => ({
      name: t.function.name,
      description: t.function.description,
      parameters: t.function.parameters,
    })),
  }];

  // Convertir mensajes al formato Gemini
  const contents = [];
  for (const m of messages) {
    if (m.role === 'system') continue; // Se ignora en Gemini (se pone en system_instruction)
    contents.push({
      role: m.role === 'assistant' ? 'model' : 'user',
      parts: [{ text: typeof m.content === 'string' ? m.content : JSON.stringify(m.content) }],
    });
  }

  const systemMsg = messages.find((m) => m.role === 'system');

  const body = {
    contents,
    tools: geminiTools,
    generationConfig: { temperature },
    ...(systemMsg ? { system_instruction: { parts: [{ text: systemMsg.content }] } } : {}),
  };

  const res = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });

  if (!res.ok) {
    const text = await res.text().catch(() => '');
    throw new Error(`Gemini API error ${res.status}: ${text.slice(0, 300)}`);
  }

  const data = await res.json();
  const candidate = data.candidates?.[0]?.content;
  if (!candidate) throw new Error('No candidates in Gemini response');

  const textPart = candidate.parts?.find((p) => p.text);
  const funcPart = candidate.parts?.find((p) => p.functionCall);

  if (funcPart) {
    return {
      type: 'tool_call',
      toolCalls: [{
        id: `gc_${Date.now()}`,
        name: funcPart.functionCall.name,
        arguments: funcPart.functionCall.args || {},
      }],
      text: textPart?.text || '',
    };
  }
  return { type: 'text', text: textPart?.text || '', toolCalls: [] };
}

function normalizeOpenAIChoice(choice) {
  const msg = choice.message;
  if (msg.tool_calls && msg.tool_calls.length > 0) {
    return {
      type: 'tool_call',
      toolCalls: msg.tool_calls.map((tc) => ({
        id: tc.id,
        name: tc.function.name,
        arguments: (() => {
          try { return JSON.parse(tc.function.arguments); } catch { return {}; }
        })(),
      })),
      text: msg.content || '',
    };
  }
  return { type: 'text', text: msg.content || '', toolCalls: [] };
}

// ── Prompt del sistema ─────────────────────────────────────────────────────
function buildSystemPrompt(baseUrl, modules, user, pass, hasCredentials) {
  const authNote = hasCredentials
    ? `Credenciales: usuario="${user}" contraseña="${pass}". Login en ${baseUrl}/login/.`
    : `Sin credenciales — solo páginas públicas.`;

  const protocol = baseUrl.startsWith('https://') ? 'HTTPS' : 'HTTP';
  return `Eres un auditor QA experto en LIMS/HIS. ${authNote} Audita PRISLAB módulo por módulo siguiendo el flujo que recibirás. Reporta hallazgos con evidencia. Ante problemas usa inspect_code+read_code_file para el root cause.

INSTRUCCIÓN CRÍTICA DE PROTOCOLO:
- La URL base es ${baseUrl}, que usa ${protocol}.
- USA ${protocol} para todas las URLs de navegación.
- NUNCA cambies el protocolo de la URL base.
- Si la URL base es https://, usa https:// en todas las URLs.
- Si la URL base es http://, usa http:// en todas las URLs.

REGLAS PARA EVITAR FALSOS POSITIVOS:
1. ANTES DE REPORTAR UN 404 COMO FALLA:
   - Usa inspect_code para buscar la ruta en urls.py del módulo correspondiente
   - Usa read_code_file para verificar si la vista existe en views.py
   - Solo reporta como "FALLA REAL" si la ruta Y la vista no existen
   - Si la ruta existe pero devuelve 404, investiga permisos, middleware o falta de datos

2. DISTINGUIR FALTA DE DATOS VS FUNCIONALIDAD ROTA:
   - Si una pantalla está vacía o muestra "sin datos", NO es una falla funcional
   - Es falta de datos de prueba en el entorno local
   - Reporta como "INFO: Falta de datos de prueba" no como "FALLA CRÍTICA"
   - Solo reporta como falla si la funcionalidad está implementada pero no funciona

3. IDENTIFICAR DECISIONES DE DISEÑO:
   - Si el código tiene comentarios como "La fuente de verdad es X" o "redirige a admin"
   - Es una decisión arquitectónica intencional, no una falla
   - Reporta como "INFO: Decisión de diseño" no como "FALLA"
   - Ejemplo: LIMS redirige al admin de Django por diseño documentado

4. VERIFICACIÓN DE VISTAS EXISTENTES:
   - Antes de reportar "vista no encontrada", busca en:
     - core/views/[modulo].py
     - [modulo]/views.py
     - config/urls.py
   - Si la vista existe con nombre diferente, reporta como "INFO: Nombre diferente"
   - Si la vista existe y funciona, NO reportes nada`;
}

// ── Ejecutor de un módulo con presupuesto propio ──────────────────────────
async function runModuleLoop(cfg, page, ctx, modulePrompt, moduleName, maxSteps) {
  const TOOL_DEFS = Object.values(TOOLS_MAP).map((t) => ({
    type: 'function',
    function: { name: t.name, description: t.description, parameters: t.parameters },
  }));

  // Herramienta virtual finish_module para que el agente señale que terminó
  const finishTool = {
    type: 'function',
    function: {
      name: 'finish_module',
      description: 'Llama esta herramienta cuando hayas completado todos los pasos del módulo actual.',
      parameters: { type: 'object', properties: { summary: { type: 'string' } }, required: ['summary'] },
    },
  };

  const { CODE_INSPECTION_RULE } = await import('./audit_human_flows.mjs');

  const messages = [
    {
      role: 'system',
      content: 'Eres un auditor QA. Ejecuta los pasos en orden usando herramientas. Cuando termines llama finish_module().',
    },
    { role: 'user', content: `${CODE_INSPECTION_RULE}\n\n${modulePrompt}` },
  ];

  // Historial fresco por módulo — evita que contexto acumulado sature Gemini
  let step = 0;
  let moduleFinished = false;
  let lastToolName = null;
  let consecutiveRepeats = 0;
  let textOnlyStreak = 0; // cuántas respuestas seguidas sin tool call

  while (step < maxSteps && !moduleFinished && !ctx.finished) {
    step++;
    ctx.stepsExecuted = (ctx.stepsExecuted || 0) + 1;
    console.error(`[AGENT][${moduleName}] Paso ${step}/${maxSteps}`);

    // Comprimir historial: system[0] + user-prompt[1] + últimos 6 mensajes
    // Gemini-2.5-flash falla con "No candidates" si el contexto supera ~8k tokens
    if (messages.length > 8) {
      const head = messages.slice(0, 2);      // system + módulo-prompt
      const tail = messages.slice(-6);        // últimos 6 intercambios
      messages.splice(0, messages.length, ...head, ...tail);
    }

    let response;
    const waits = [5000, 15000, 30000];
    let lastErr;
    for (let attempt = 0; attempt <= waits.length; attempt++) {
      try {
        response = await callLLM(cfg, messages, [...TOOL_DEFS, finishTool]);
        lastErr = null;
        break;
      } catch (e) {
        lastErr = e;
        if (attempt < waits.length) {
          console.error(`[AGENT][${moduleName}] LLM error (intento ${attempt + 1}): ${e.message} — reintentando en ${waits[attempt] / 1000}s`);
          await new Promise((r) => setTimeout(r, waits[attempt]));
        }
      }
    }
    if (lastErr) {
      console.error(`[AGENT][${moduleName}] LLM error fatal tras ${waits.length + 1} intentos:`, lastErr.message);
      break;
    }

    if (response.type === 'text' || !response.toolCalls.length) {
      textOnlyStreak++;
      messages.push({ role: 'assistant', content: response.text || '...' });
      // Tras 2 respuestas de texto sin acción, ser más directo
      const nudge = textOnlyStreak >= 2
        ? `STOP. No analices más. Ejecuta AHORA el paso ${step} del flujo de ${moduleName} usando una herramienta. Primera herramienta requerida: navigate o get_page_state o find_elements.`
        : `Continúa con el siguiente paso del flujo de ${moduleName}. Usa una herramienta ahora. Cuando termines todos los pasos, llama finish_module().`;
      messages.push({ role: 'user', content: nudge });
      continue;
    }
    textOnlyStreak = 0;

    const assistantMsg = {
      role: 'assistant',
      content: response.text || null,
      tool_calls: response.toolCalls.map((tc) => ({
        id: tc.id,
        type: 'function',
        function: { name: tc.name, arguments: JSON.stringify(tc.arguments) },
      })),
    };
    messages.push(assistantMsg);

    for (const tc of response.toolCalls) {
      // Anti-loop: si repite la misma herramienta 3 veces, empuja a avanzar
      if (tc.name === lastToolName) {
        consecutiveRepeats++;
        if (consecutiveRepeats >= 3) {
          console.error(`[AGENT][${moduleName}] Anti-loop: ${tc.name} repetido ${consecutiveRepeats}x — forzando avance`);
          messages.push({
            role: 'tool',
            tool_call_id: tc.id,
            content: JSON.stringify({ ok: false, error: 'Herramienta repetida demasiadas veces. Avanza al siguiente paso del flujo.' }),
          });
          messages.push({
            role: 'user',
            content: `Deja de repetir '${tc.name}'. Avanza al SIGUIENTE paso del flujo de ${moduleName}.`,
          });
          consecutiveRepeats = 0;
          continue;
        }
      } else {
        lastToolName = tc.name;
        consecutiveRepeats = 1;
      }

      // finish_module virtual
      if (tc.name === 'finish_module') {
        console.error(`[AGENT][${moduleName}] ✓ Módulo completado.`);
        messages.push({
          role: 'tool',
          tool_call_id: tc.id,
          content: JSON.stringify({ ok: true }),
        });
        moduleFinished = true;
        break;
      }

      const tool = TOOLS_MAP[tc.name];
      if (!tool) {
        messages.push({
          role: 'tool',
          tool_call_id: tc.id,
          content: JSON.stringify({ ok: false, error: `Herramienta desconocida: ${tc.name}` }),
        });
        continue;
      }

      console.error(`[AGENT][${moduleName}] → ${tc.name}(${JSON.stringify(tc.arguments).slice(0, 120)})`);

      let result;
      try {
        result = await tool.handler(page, tc.arguments, ctx);
      } catch (e) {
        result = { ok: false, data: {}, error: String(e.message) };
      }

      console.error(`[AGENT][${moduleName}] ← ${tc.name}: ${result.ok ? 'OK' : 'FAIL'} ${result.error ? `(${result.error.slice(0, 100)})` : ''}`);

      // Truncar a 1500 chars — Gemini-2.5-flash tiene límite bajo de salida en tool results
      const rawContent = JSON.stringify(result);
      const toolContent = rawContent.length > 1500
        ? rawContent.slice(0, 1500) + '... [truncado]'
        : rawContent;

      messages.push({
        role: 'tool',
        tool_call_id: tc.id,
        content: toolContent,
      });

      if (ctx.finished) break;
    }
  }

  if (!moduleFinished) {
    console.error(`[AGENT][${moduleName}] Presupuesto de pasos agotado (${maxSteps}).`);
  }

  // Check automático de errores de red al finalizar el módulo (mejora #5)
  const netFailed = ctx.requestFailed.slice(-20).filter(
    (r) => !String(r.url).includes('8181') && !String(r.url).includes('8484')
  );
  const net404 = ctx.resource404.slice(-20).filter(
    (r) => !String(r.url).includes('favicon') && !String(r.url).includes('8181')
  );
  if (netFailed.length > 0 || net404.length > 0) {
    const detail = [
      netFailed.length ? `Solicitudes fallidas (${netFailed.length}): ${netFailed.map((r) => r.url).join(', ')}` : null,
      net404.length   ? `Recursos 404 (${net404.length}): ${net404.map((r) => r.url).join(', ')}` : null,
    ].filter(Boolean).join('\n');
    ctx.findings.push({
      severity: netFailed.length > 2 ? 'HIGH' : 'MEDIUM',
      module: moduleName,
      url: cleanUrl(page.url()),
      title: `Errores de red detectados en ${moduleName}`,
      detail,
      recommendation: 'Verificar URLs en urls.py, archivos estáticos y endpoints de API.',
      rootCause: '',
      screenshot: null,
      ts: new Date().toISOString(),
    });
    // Limpiar para el siguiente módulo
    ctx.requestFailed.splice(0);
    ctx.resource404.splice(0);
  }
}

export function finalizeLoginAttempt(ctx, page, cleanUrlFn = cleanUrl) {
  const url = cleanUrlFn(page?.url?.() || '');
  if (url.includes('/login/')) {
    ctx.findings.push({
      severity: 'CRITICAL',
      module: 'login',
      url,
      title: 'Login fallido',
      detail: 'El auditor permaneció en /login/ después del intento de autenticación. Las credenciales son inválidas, la sesión no se creó o el servidor respondió con un flujo de login persistente.',
      recommendation: 'Verificar credenciales de producción, estado del servidor y lógica de autenticación antes de continuar con la auditoría.',
      ts: new Date().toISOString(),
    });
    ctx.auditSummary = 'Login fallido — credenciales incorrectas o servidor no responde. Auditoría abortada.';
    ctx.auditStats = { passed: 0, failed: 1, warnings: 0 };
    ctx.finished = true;
    return { ok: false, url };
  }

  ctx.auditSummary = 'Login exitoso. Auditoría iniciada.';
  return { ok: true, url };
}

// ── Bucle principal del agente — por módulo ────────────────────────────────
async function runAgentLoop(cfg, page, ctx, baseUrl) {
  const { MODULE_FLOWS } = await import('./audit_human_flows.mjs');

  const targetModules = cfg.modules.length > 0 ? cfg.modules : null;
  const flows = targetModules
    ? MODULE_FLOWS.filter((m) => targetModules.includes(m.id))
    : MODULE_FLOWS;

  ctx.stepsExecuted = 0;

  // Fase 1: Login obligatorio primero
  const loginFlow = flows.find((m) => m.id === 'login');
  if (loginFlow) {
    console.error(`\n[AGENT] ══ MÓDULO: ${loginFlow.name} ══`);
    const prompt = loginFlow.prompt(baseUrl, cfg.user, cfg.pass);
    await runModuleLoop(cfg, page, ctx, prompt, loginFlow.name, loginFlow.steps + 8);
    // Si después del login seguimos en /login/, todo falló
    const loginState = finalizeLoginAttempt(ctx, page);
    if (!loginState.ok) {
      return;
    }
  }

  // Fase 2: Resto de módulos en orden
  for (const flow of flows.filter((m) => m.id !== 'login')) {
    if (ctx.finished) break;
    console.error(`\n[AGENT] ══ MÓDULO: ${flow.name} ══`);
    const prompt = typeof flow.prompt === 'function'
      ? flow.prompt(baseUrl, cfg.user, cfg.pass)
      : flow.prompt;
    await runModuleLoop(cfg, page, ctx, prompt, flow.name, flow.steps + 8);
  }

  if (!ctx.finished) {
    ctx.auditSummary = `Auditoría completa. ${flows.length} módulos procesados. ${ctx.findings.length} hallazgos totales.`;
    ctx.auditStats = {
      passed: ctx.findings.filter((f) => f.severity === 'INFO').length,
      failed: ctx.findings.filter((f) => ['CRITICAL','HIGH'].includes(f.severity)).length,
      warnings: ctx.findings.filter((f) => ['MEDIUM','LOW'].includes(f.severity)).length,
    };
    ctx.finished = true;
  }
}

// ── Reporte Markdown ──────────────────────────────────────────────────────
function writeMarkdownReport(filePath, data) {
  const SEV_ICON = { CRITICAL: '🔴', HIGH: '🟠', MEDIUM: '🟡', LOW: '🔵', INFO: '✅' };
  const SEV_LABEL = { CRITICAL: 'CRÍTICO', HIGH: 'ALTO', MEDIUM: 'MEDIO', LOW: 'BAJO', INFO: 'INFO' };
  const critical = data.findings.filter((f) => f.severity === 'CRITICAL').length;
  const high     = data.findings.filter((f) => f.severity === 'HIGH').length;
  const medium   = data.findings.filter((f) => f.severity === 'MEDIUM').length;
  const low      = data.findings.filter((f) => f.severity === 'LOW').length;
  const info     = data.findings.filter((f) => f.severity === 'INFO').length;

  const dur = data.durationMs ? `${(data.durationMs / 60000).toFixed(1)} min` : '—';
  const overallBadge = critical > 0 ? '🔴 CRÍTICO'
    : high > 0 ? '🟠 CON PROBLEMAS'
    : medium > 0 ? '🟡 ADVERTENCIAS'
    : '✅ APROBADO';

  const lines = [];

  // ── Encabezado ────────────────────────────────────────────────────────────
  lines.push('# PRISLAB — Reporte de Auditoría IA');
  lines.push('');
  lines.push(`> **Resultado general: ${overallBadge}**`);
  lines.push('');

  // ── Metadata ──────────────────────────────────────────────────────────────
  lines.push('## Metadata de la ejecución');
  lines.push('');
  lines.push('| Campo | Valor |');
  lines.push('|-------|-------|');
  lines.push(`| Fecha | ${data.timestamp} |`);
  lines.push(`| Entorno | ${data.target} — ${data.baseUrl} |`);
  lines.push(`| LLM | ${data.provider} / ${data.model} |`);
  lines.push(`| Pasos ejecutados | ${data.stepsExecuted} |`);
  lines.push(`| Duración | ${dur} |`);
  lines.push(`| Módulos auditados | ${[...new Set(data.findings.map((f) => f.module).filter(Boolean))].join(', ') || '—'} |`);
  lines.push('');

  // ── Tabla resumen por módulo (mejora #8) ───────────────────────────────────────
  const allModules = [...new Set(data.findings.map((f) => f.module).filter(Boolean))];
  if (allModules.length) {
    lines.push('## Resumen por módulo');
    lines.push('');
    lines.push('| Módulo | 🔴 CRÍTICO | 🔴 ALTO | 🟡 MEDIO | 🔵 BAJO | ✅ INFO | Estado |');
    lines.push('|--------|---------|------|-------|------|------|--------|');
    for (const mod of allModules) {
      const mf = data.findings.filter((f) => f.module === mod);
      const mc = mf.filter((f) => f.severity === 'CRITICAL').length;
      const mh = mf.filter((f) => f.severity === 'HIGH').length;
      const mm = mf.filter((f) => f.severity === 'MEDIUM').length;
      const ml = mf.filter((f) => f.severity === 'LOW').length;
      const mi = mf.filter((f) => f.severity === 'INFO').length;
      const badge = mc > 0 ? '🔴 CRÍTICO' : mh > 0 ? '🟠 PROBLEMA' : mm > 0 ? '🟡 ADVERTENCIA' : '✅ OK';
      lines.push(`| ${mod} | ${mc || '—'} | ${mh || '—'} | ${mm || '—'} | ${ml || '—'} | ${mi || '—'} | ${badge} |`);
    }
    lines.push('');
  }

  // ── Tablero de hallazgos ──────────────────────────────────────────────────
  lines.push('## Tablero de hallazgos');
  lines.push('');
  
  // Filtrar por tipo de hallazgo
  const realBugs = data.findings.filter(f => f.findingType === 'REAL_BUG');
  const noData = data.findings.filter(f => f.findingType === 'NO_DATA');
  const designDecisions = data.findings.filter(f => f.findingType === 'DESIGN_DECISION');
  const falsePositives = data.findings.filter(f => f.findingType === 'FALSE_POSITIVE');
  
  lines.push('| Tipo de hallazgo | Cantidad |');
  lines.push('|------------------|---------|');
  lines.push(`| � Fallas Reales (REAL_BUG) | ${realBugs.length} |`);
  lines.push(`| 📊 Falta de datos (NO_DATA) | ${noData.length} |`);
  lines.push(`| 🏗️ Decisión de diseño (DESIGN_DECISION) | ${designDecisions.length} |`);
  lines.push(`| ❌ Falsos positivos (FALSE_POSITIVE) | ${falsePositives.length} |`);
  lines.push(`| **TOTAL**  | **${data.findings.length}** |`);
  lines.push('');
  
  // Solo mostrar severidad para fallas reales
  if (realBugs.length > 0) {
    lines.push('### Severidad de fallas reales');
    lines.push('');
    lines.push('| Severidad | Cantidad |');
    lines.push('|-----------|---------|');
    const realCritical = realBugs.filter(f => f.severity === 'CRITICAL').length;
    const realHigh = realBugs.filter(f => f.severity === 'HIGH').length;
    const realMedium = realBugs.filter(f => f.severity === 'MEDIUM').length;
    const realLow = realBugs.filter(f => f.severity === 'LOW').length;
    lines.push(`| 🔴 CRÍTICO | ${realCritical} |`);
    lines.push(`| � ALTO    | ${realHigh} |`);
    lines.push(`| 🟡 MEDIO   | ${realMedium} |`);
    lines.push(`| 🔵 BAJO    | ${realLow} |`);
    lines.push('');
  }

  // ── Resumen ejecutivo del agente ──────────────────────────────────────────
  lines.push('## Resumen ejecutivo');
  lines.push('');
  lines.push(data.agentSummary || '_El agente no generó resumen — ver hallazgos detallados._');
  lines.push('');

  // ── Hallazgos detallados ──────────────────────────────────────────────────
  lines.push('## Hallazgos detallados');
  lines.push('');

  if (!data.findings.length) {
    lines.push('_Sin hallazgos registrados._');
  } else {
    // Primero mostrar fallas reales, luego otros tipos
    const realBugs = data.findings.filter(f => f.findingType === 'REAL_BUG');
    const otherFindings = data.findings.filter(f => f.findingType !== 'REAL_BUG');
    
    const TYPE_LABEL = {
      'REAL_BUG': '🐛 Falla Real',
      'NO_DATA': '📊 Falta de Datos',
      'DESIGN_DECISION': '🏗️ Decisión de Diseño',
      'FALSE_POSITIVE': '❌ Falso Positivo',
    };
    
    // Función para renderizar hallazgos
    const renderFindings = (items, title) => {
      if (!items.length) return;
      lines.push(`### ${title} (${items.length})`);
      lines.push('');
      const bySeverity = ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW', 'INFO'];
      let idx = 0;
      for (const sev of bySeverity) {
        const sevItems = items.filter((f) => f.severity === sev);
        if (!sevItems.length) continue;
        for (const f of sevItems) {
          idx++;
          lines.push(`#### ${idx}. ${f.title}`);
          lines.push('');
          lines.push(`| Campo | Valor |`);
          lines.push(`|-------|-------|`);
          lines.push(`| Tipo | ${TYPE_LABEL[f.findingType] || f.findingType} |`);
          lines.push(`| Severidad | ${SEV_ICON[f.severity]} ${SEV_LABEL[f.severity]} |`);
          lines.push(`| Módulo | ${f.module || '—'} |`);
          lines.push(`| URL | ${f.url || '—'} |`);
          lines.push(`| Timestamp | ${f.ts || '—'} |`);
          lines.push('');
          lines.push(`**Síntoma observado:**`);
          lines.push('');
          lines.push(`${f.detail}`);
          lines.push('');
          if (f.rootCause) {
            lines.push(`**Root cause en código:**`);
            lines.push('');
            lines.push('```');
            lines.push(f.rootCause);
            lines.push('```');
            lines.push('');
          }
          if (f.recommendation) {
            lines.push(`**Recomendación:**`);
            lines.push('');
            lines.push(`> ${f.recommendation}`);
            lines.push('');
          }
          // Screenshot vinculado al finding como imagen inline (mejora #1+7)
          if (f.screenshot) {
            lines.push(`**Evidencia:**`);
            lines.push('');
            lines.push(`![${f.title}](./screenshots/${f.screenshot})`);
            lines.push('');
          }
          lines.push('---');
          lines.push('');
        }
      }
    };
    
    // Renderizar fallas reales primero
    renderFindings(realBugs, '🐛 Fallas Reales (requieren corrección)');
    
    // Renderizar otros hallazgos
    if (noData.length > 0) renderFindings(noData, '📊 Falta de Datos (requieren datos de prueba)');
    if (designDecisions.length > 0) renderFindings(designDecisions, '🏗️ Decisiones de Diseño (arquitectura intencional)');
    if (falsePositives.length > 0) renderFindings(falsePositives, '❌ Falsos Positivos (errores del auditor)');
  }

  // ── Screenshots (mejora #7: imágenes inline) ─────────────────────────────
  if (data.screenshots && data.screenshots.length) {
    lines.push('## Galería de evidencia fotográfica');
    lines.push('');
    lines.push('> Imágenes capturadas durante la auditoría. Carpeta: `screenshots/`');
    lines.push('');
    data.screenshots.forEach((s, i) => {
      lines.push(`### ${i + 1}. \`${s}\``);
      lines.push('');
      lines.push(`![screenshot ${i + 1}](./screenshots/${s})`);
      lines.push('');
    });
  }

  // ── Errores de consola JS ─────────────────────────────────────────────────
  const jsErrors = (data.consoleErrors || []).filter((e) =>
    // Ignorar el WebSocket de QZ Tray (impresora local) — no es un bug de la app
    !String(e.text || e).includes('8181') && !String(e.text || e).includes('8484')
  );
  if (jsErrors.length) {
    lines.push('## Errores de consola JavaScript');
    lines.push('');
    lines.push('> Estos errores se capturaron en el navegador durante la auditoría.');
    lines.push('');
    for (const e of jsErrors.slice(0, 30)) {
      const msg = typeof e === 'string' ? e : (e.text || JSON.stringify(e));
      lines.push(`- \`${msg.slice(0, 200)}\``);
    }
    lines.push('');
  }

  // ── Errores de red ────────────────────────────────────────────────────────
  const netFailed = (data.requestFailed || []).filter((r) =>
    !String(r.url).includes('8181') && !String(r.url).includes('8484')
  );
  const net404 = (data.resource404 || []).filter((r) =>
    !String(r.url).includes('favicon') && !String(r.url).includes('8181')
  );

  if (netFailed.length || net404.length) {
    lines.push('## Errores de red');
    lines.push('');
    if (netFailed.length) {
      lines.push('### Solicitudes fallidas');
      lines.push('');
      lines.push('| Método | URL | Error |');
      lines.push('|--------|-----|-------|');
      for (const r of netFailed.slice(0, 25)) {
        lines.push(`| ${r.method || 'GET'} | ${r.url} | ${r.failure || '—'} |`);
      }
      lines.push('');
    }
    if (net404.length) {
      lines.push('### Recursos 404');
      lines.push('');
      for (const r of net404.slice(0, 25)) {
        lines.push(`- \`${r.url}\``);
      }
      lines.push('');
    }
  } else {
    lines.push('## Errores de red');
    lines.push('');
    lines.push('_Ninguno significativo detectado._');
    lines.push('');
  }

  // ── Pie ───────────────────────────────────────────────────────────────────
  lines.push('---');
  lines.push('');
  lines.push(`_Reporte generado automáticamente por PRISLAB AI Agent Audit · ${data.timestamp}_`);

  fs.writeFileSync(filePath, `${lines.join('\n')}\n`, 'utf8');
}

// ── Main ──────────────────────────────────────────────────────────────────
async function main() {
  const manifest = JSON.parse(
    fs.readFileSync(path.join(repoRoot, 'tools', 'omni_manifest.json'), 'utf8')
  );
  const cfg = parseArgs(process.argv.slice(2));
  const baseUrl = resolveBaseUrl(manifest, cfg.target, cfg.base);

  // Validar que hay proveedor LLM configurado
  if (!cfg.apiKey && cfg.provider !== 'ollama') {
    console.error(JSON.stringify({
      fatal: `AGENT_API_KEY no configurado. Exporta la variable o crea .env.agent con AGENT_API_KEY=<tu_clave>`,
      provider: cfg.provider,
    }, null, 2));
    process.exit(1);
  }

  const defaults = PROVIDER_DEFAULTS[cfg.provider] || PROVIDER_DEFAULTS.openai;
  const modelName = cfg.model || defaults.model;

  console.error(`[AGENT] Provider: ${cfg.provider} | Model: ${modelName} | Target: ${baseUrl}`);
  console.error(`[AGENT] Max steps: ${cfg.maxSteps} | Headless: ${cfg.headless}`);

  // Crear directorio de run
  const runDir = path.join(repoRoot, `ai_audit_${stamp()}`);
  const screenshotsDir = path.join(runDir, 'screenshots');
  fs.mkdirSync(screenshotsDir, { recursive: true });

  // Contexto compartido entre herramientas y agente
  const ctx = {
    findings: [],
    screenshots: [],
    screenshotsDir,
    consoleErrors: [],
    requestFailed: [],
    resource404: [],
    finished: false,
    auditSummary: '',
    auditStats: { passed: 0, failed: 0, warnings: 0 },
    stepsExecuted: 0,
  };

  // Lanzar browser con directorio temporal para evitar HSTS cacheado
  const browser = await chromium.launch({
    headless: cfg.headless,
    slowMo: cfg.slowMo,
    args: [
      '--window-size=1440,900',
      '--disable-web-security',
      '--disable-features=IsolateOrigins,site-per-process',
      '--ignore-certificate-errors',
      '--ignore-certificate-errors-spki-list',
      '--ignore-ssl-errors',
      '--disable-hsts',
      '--disable-features=VizDisplayCompositor',
    ],
  });
  const context = await browser.newContext({
    ignoreHTTPSErrors: true,
    locale: 'es-MX',
    viewport: { width: 1440, height: 900 },
    userAgent: 'PRISLAB-AI-AGENT-AUDIT/1.0',
    // Desactivar HSTS en el contexto
    extraHTTPHeaders: {
      'Upgrade-Insecure-Requests': '0',
    },
    // Forzar uso de HTTP
    serviceWorkers: 'block',
    // Usar storage temporal para evitar HSTS cacheado
    storageState: undefined,
  });
  const page = await context.newPage();

  // Listeners pasivos
  page.on('console', (msg) => {
    if (msg.type() === 'error') ctx.consoleErrors.push(msg.text());
  });
  page.on('requestfailed', (req) => {
    ctx.requestFailed.push({
      url: cleanUrl(req.url()),
      method: req.method(),
      failure: req.failure()?.errorText || 'unknown',
    });
  });
  page.on('response', (res) => {
    if (res.status() === 404) {
      ctx.resource404.push({ url: cleanUrl(res.url()) });
    }
  });

  // Inyectar credenciales en ctx para que session_check pueda re-autenticar
  if (cfg.user && cfg.pass) {
    ctx.agentUser = cfg.user;
    ctx.agentPass = cfg.pass;
  }

  let stepsExecuted = 0;
  const startTs = Date.now();

  try {
    // Contar pasos ejecutados anulando el bucle después
    await runAgentLoop(cfg, page, ctx, baseUrl);
  } catch (err) {
    ctx.findings.push({
      severity: 'CRITICAL',
      module: 'agent',
      url: cleanUrl(page.url()),
      title: 'Error fatal del agente',
      detail: String(err?.message || err),
      recommendation: 'Revisar configuración del agente y del LLM.',
      ts: new Date().toISOString(),
    });
  } finally {
    await browser.close().catch(() => {});
  }

  const durationMs = Date.now() - startTs;
  const criticalCount = ctx.findings.filter((f) => f.severity === 'CRITICAL').length;
  const highCount = ctx.findings.filter((f) => f.severity === 'HIGH').length;
  const ok = criticalCount === 0 && highCount === 0;

  const summary = {
    protocol: 'PRISLAB_AI_AGENT_AUDIT',
    timestamp: new Date().toISOString(),
    target: cfg.target,
    baseUrl,
    provider: cfg.provider,
    model: modelName,
    headless: cfg.headless,
    maxSteps: cfg.maxSteps,
    stepsExecuted: ctx.stepsExecuted || stepsExecuted,
    durationMs,
    ok,
    agentSummary: ctx.auditSummary,
    stats: ctx.auditStats,
    findings: ctx.findings,
    screenshots: ctx.screenshots,
    requestFailed: ctx.requestFailed,
    resource404: ctx.resource404,
    consoleErrors: ctx.consoleErrors,
    runDir: path.basename(runDir),
  };

  // Guardar artefactos
  const reportJsonPath = path.join(runDir, 'report.json');
  const reportMdPath = path.join(runDir, 'report.md');
  fs.writeFileSync(reportJsonPath, JSON.stringify(summary, null, 2), 'utf8');
  writeMarkdownReport(reportMdPath, summary);

  // last_runs
  const lastRunsDir = path.join(repoRoot, 'tools', 'last_runs');
  fs.mkdirSync(lastRunsDir, { recursive: true });
  fs.writeFileSync(
    path.join(lastRunsDir, 'ai_agent_last.json'),
    JSON.stringify(summary, null, 2),
    'utf8',
  );

  // Salida estándar (JSON resumen para CI)
  console.log(JSON.stringify({
    protocol: summary.protocol,
    timestamp: summary.timestamp,
    ok: summary.ok,
    target: summary.target,
    baseUrl: summary.baseUrl,
    provider: summary.provider,
    model: summary.model,
    findingsCount: summary.findings.length,
    critical: criticalCount,
    high: highCount,
    durationMs,
    runDir: summary.runDir,
    reportJson: path.join(summary.runDir, 'report.json'),
    reportMd: path.join(summary.runDir, 'report.md'),
  }, null, 2));

  process.exitCode = ok ? 0 : 1;
}

const isMainModule = (() => {
  try {
    if (typeof process === 'undefined' || !process.argv?.[1]) return false;
    return import.meta.url === pathToFileURL(process.argv[1]).href;
  } catch {
    return false;
  }
})();

if (isMainModule) {
  main().catch((err) => {
    console.error(JSON.stringify({
      protocol: 'PRISLAB_AI_AGENT_AUDIT',
      fatal: String(err?.message || err),
      stack: err?.stack || null,
    }, null, 2));
    process.exit(1);
  });
}
