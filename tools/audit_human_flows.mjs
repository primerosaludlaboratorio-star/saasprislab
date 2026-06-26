/**
 * audit_human_flows.mjs — "Cerebro" de auditoría humana para el agente PRISLAB
 * ============================================================================
 * Drop-in para tools/run_ai_agent_audit.mjs. Resuelve los 3 problemas reales
 * de la corrida anterior:
 *   1) Se queda sin pasos -> presupuesto POR MÓDULO (no compartido).
 *   2) Superficial ("lee títulos") -> flujos humanos concretos por módulo.
 *   3) Loops de find_elements / "null reasoning" -> anti-loop + selector inteligente.
 *
 * Uso en el runner:
 *   import { buildSystemPrompt, MODULE_FLOWS, resolveSelectorVariants,
 *            LoopGuard, perModuleBudget } from './audit_human_flows.mjs';
 *   const systemPrompt = buildSystemPrompt(baseUrl, user, pass);
 *   // en cada tool fill_input/click: si el selector exacto falla, iterar
 *   //   resolveSelectorVariants(intent) antes de reportar "no encontrado".
 *   // en el loop: const guard = new LoopGuard(); if (guard.isStuck(tool,args)) -> forzar avance.
 */

// ── Flujos humanos por módulo (URL + pasos concretos + qué verificar) ─────────
export const MODULE_FLOWS = [
  {
    modulo: 'Laboratorio · Recepción',
    url: '/laboratorio/recepcion/',
    flujo: [
      'Buscar un paciente existente (escribe en el buscador y espera resultados AJAX).',
      'Si no hay resultados, crear paciente express (nombre, edad, sexo).',
      'Agregar 1-2 estudios al carrito (buscar estudio -> click resultado).',
      'Verificar que el total se actualiza y que aparece el botón de cobro/crear orden.',
      'Crear la orden y confirmar que devuelve folio (no 500).',
    ],
    verificar: 'folio generado, total > 0, sin 500, búsqueda AJAX responde',
  },
  {
    modulo: 'Laboratorio · Monitor/Validación',
    url: '/laboratorio/monitor/',
    flujo: [
      'Abrir una orden en estado capturado.',
      'Intentar "Aprobar Resultados" (transición VALIDADO_PARCIAL->COMPLETO).',
      'Confirmar que NO da 500 y que la orden pasa a RESULTADOS_LISTOS con PDF.',
    ],
    verificar: 'transición sin 500, estado RESULTADOS_LISTOS, PDF adjunto (fix LAB-A)',
  },
  {
    modulo: 'Farmacia · PDV',
    url: '/farmacia/pdv/',
    flujo: [
      'Buscar producto en #input-buscador (escribe "parace"/"amox", espera el fragmento AJAX).',
      'Click en un resultado para agregar al carrito (#tabla-carrito-body).',
      'Verificar que el total (#res-total) sube y que no dice SIN STOCK indebidamente.',
      'Aplicar un descuento si hay control de descuento.',
      'Abrir cobro (abrirModalPago) y revisar el modal de pago.',
      'NO completar la venta real salvo que se indique; cerrar el modal.',
    ],
    verificar: 'búsqueda devuelve productos, carrito suma, modal de pago abre',
  },
  {
    modulo: 'Farmacia · Devolución/Cancelación',
    url: '/farmacia/devoluciones/buscar/',
    flujo: [
      'Buscar una venta por folio.',
      'Verificar que devolución exige rol gerente/admin (si el usuario no lo es, 403).',
    ],
    verificar: 'gate de rol presente, no doble devolución',
  },
  {
    modulo: 'Consultorio · Consulta',
    url: '/consultorio/',
    flujo: [
      'Abrir agenda/lista de consultas.',
      'Abrir una consulta (SOAP) y revisar que cargan los campos.',
      'Probar el cobro de consulta (/consultorio/cobros/) — NO cobrar dos veces.',
    ],
    verificar: 'SOAP carga, cobro idempotente (fix K1), sin 500',
  },
  {
    modulo: 'Director · Dashboard/War-room',
    url: '/director/',
    flujo: [
      'Cargar dashboard, buzón, ranking, autorizaciones, incidencias.',
      'Abrir war-room y verificar que los widgets cargan datos (no spinners infinitos).',
    ],
    verificar: 'widgets con datos, sin errores JS de app (ignorar QZ Tray 8181-8485)',
  },
  { modulo: 'Seguridad · 2FA', url: '/seguridad/2fa/', flujo: ['Revisar configuración 2FA y dispositivos.'], verificar: 'página carga, sin 500' },
  {
    modulo: 'Notificaciones · Centro',
    url: '/notificaciones/',
    flujo: [
      'Abrir el centro de notificaciones; verificar que SOLO lista las propias (destinatario=tú) y las globales, no las de otros usuarios del mismo tenant.',
      'Revisar el badge (/notificaciones/badge/): el conteo de no-leídas coincide con propias+globales y no incluye notificaciones ajenas.',
      'Marcar una notificación propia como leída (POST) y confirmar que el contador baja.',
      'Intentar (vía POST directo) marcar una notificación de OTRO usuario (id ajeno): debe responder 403 "Sin permisos", NUNCA 200.',
      'Usuario sin empresa: el listado no debe mostrar datos de otra empresa (corte por empresa).',
    ],
    verificar: 'aislamiento por destinatario+empresa, badge correcto, marcar-leída IDOR-safe (403). Verificado en interfaz humana 2026-06: sin fuga.',
  },
  { modulo: 'Contabilidad', url: '/contabilidad/', flujo: ['Abrir reportes/cortes; abrir un detalle.'], verificar: 'reportes cargan' },
  { modulo: 'Inventario', url: '/silo-lab/', flujo: ['Listar productos/lotes; abrir un detalle de lote.'], verificar: 'stock visible' },
  { modulo: 'Academia', url: '/academia/', flujo: ['Abrir cursos/contenidos.'], verificar: 'carga' },
  { modulo: 'Bienestar', url: '/bienestar/', flujo: ['Abrir recursos.'], verificar: 'carga' },
  { modulo: 'IA / PRIS', url: '/ia/', flujo: ['Abrir asistente; enviar una consulta de prueba.'], verificar: 'responde o degrada sin 500' },
];

// ── Selector inteligente: variantes a probar antes de reportar "no encontrado" ─
// intent: {role:'search'|'submit'|'patient'|'product', label?:string}
export function resolveSelectorVariants(intent) {
  const byRole = {
    search: [
      'input[type="search"]', '#input-buscador', 'input[name="q"]',
      'input[placeholder*="uscar" i]', 'input[type="text"]',
    ],
    submit: [
      'button[type="submit"]', 'input[type="submit"]',
      'button:has-text("Iniciar")', 'button:has-text("Guardar")',
      'button:has-text("Cobrar")', 'button.btn-primary',
    ],
    patient: [
      '#buscar_paciente', 'input[placeholder*="aciente" i]',
      'input[name*="paciente" i]', 'input[type="text"]',
    ],
    product: [
      '#input-buscador', 'input[placeholder*="edicament" i]',
      'input[placeholder*="roducto" i]', 'input[type="search"]', 'input[type="text"]',
    ],
  };
  return byRole[intent.role] || ['input[type="text"]', 'button'];
}

// ── Anti-loop: detecta repetición de la misma herramienta/argumentos ──────────
export class LoopGuard {
  constructor(maxRepeat = 3) { this.maxRepeat = maxRepeat; this.recent = []; }
  isStuck(tool, args) {
    const sig = `${tool}:${JSON.stringify(args || {})}`;
    this.recent.push(sig);
    if (this.recent.length > 6) this.recent.shift();
    const n = this.recent.filter((s) => s === sig).length;
    return n >= this.maxRepeat;
  }
  reset() { this.recent = []; }
}

// ── Presupuesto por módulo: reparte pasos para que TODOS los módulos se cubran ─
export function perModuleBudget(totalSteps, modules = MODULE_FLOWS) {
  const reserva = 6; // login + dashboard + cierre
  const porModulo = Math.max(6, Math.floor((totalSteps - reserva) / modules.length));
  return { porModulo, reserva };
}

// ── System prompt: convierte al agente en un QA humano con checklist real ─────
export function buildSystemPrompt(baseUrl, user, pass) {
  const cred = user && pass
    ? `CREDENCIALES (úsalas en /login/): usuario="${user}", contraseña="${pass}". ` +
      `Llena input[name="username"] e input[type="password"] y haz click en "Iniciar Sesión".`
    : 'Sin credenciales: solo páginas públicas y el flujo de login.';

  const flujos = MODULE_FLOWS.map((m, i) =>
    `### ${i + 1}. ${m.modulo}  (${baseUrl}${m.url})\n` +
    m.flujo.map((p) => `   - ${p}`).join('\n') +
    `\n   ✓ Verificar: ${m.verificar}`
  ).join('\n\n');

  return `Eres un AUDITOR QA HUMANO de PRISLAB. NO navegas leyendo títulos: EJECUTAS FLUJOS reales como un usuario que trabaja en el sistema.

${cred}

REGLAS DE EFICIENCIA (no desperdicies pasos):
- Tienes un PRESUPUESTO POR MÓDULO. Cubre TODOS los módulos; no te quedes en uno.
- NO repitas get_page_state ni find_elements más de 2 veces seguidas. Si un selector exacto
  falla, prueba VARIANTES (por placeholder, name, type o texto visible) UNA vez; si tras 2-3
  variantes no aparece, reporta MEDIUM "selector no encontrado (revisar UI)" y AVANZA.
- Un selector que no existe NO es bug crítico: clasifícalo MEDIUM y sigue. Solo es HIGH/ CRITICAL
  un 500, un dato de otro tenant, un bloqueo de flujo, o una acción que corrompe datos.
- Errores WebSocket a localhost:8181-8485 son QZ Tray (impresora) -> IGNÓRALOS, no son bug.
- Tras 3 acciones idénticas seguidas, cambia de estrategia o avanza al siguiente módulo.

CÓMO AUDITAR CADA MÓDULO (flujo humano, paso a paso):
${flujos}

SEVERIDAD CORRECTA:
- CRITICAL: 500 en flujo principal, fuga de datos entre empresas, pérdida de datos.
- HIGH: flujo bloqueado (no se puede completar la tarea), permiso saltado.
- MEDIUM: selector/elemento no encontrado, UX rota no bloqueante.
- INFO: módulo carga y funciona.

Al terminar cada módulo, reporta un finding-resumen. Al final llama finish_audit() con
un veredicto por módulo (✅/⚠️/❌) y la lista de hallazgos accionables.`;
}
