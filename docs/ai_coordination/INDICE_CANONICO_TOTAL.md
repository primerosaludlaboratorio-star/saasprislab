# Indice Canonico Total - PRISLAB AI Coordination

Fecha: 2026-06-23

Este documento es el mapa maestro de lo que ya existe, lo que está operativo, lo que sigue pendiente y lo que se considera legado/ruido.

## 1. Documentos canonicos vigentes

### Estado y reglas
- [AI_COORDINATION_STATUS.md](./AI_COORDINATION_STATUS.md)
- [ESTADO_CANONICO_RAMA_RELEASE_V1_0_LOCAL.md](./ESTADO_CANONICO_RAMA_RELEASE_V1_0_LOCAL.md)
- [ESTANDAR_TESTEABILIDAD_AUDITABILIDAD.md](./ESTANDAR_TESTEABILIDAD_AUDITABILIDAD.md)
- [NEXT_ACTIONS.md](./NEXT_ACTIONS.md)
- [GUIA_OPERATIVA_FINAL.md](./GUIA_OPERATIVA_FINAL.md)
- **[PROTOCOLO_EJECUCION_PARALELA.md](./PROTOCOLO_EJECUCION_PARALELA.md)** — obligatorio leer antes de cada ronda
- [PLAN_REPARTO_PARALLELO_2026-06-24.md](./PLAN_REPARTO_PARALLELO_2026-06-24.md)
- [PLAN_REPARTO_MODULAR_2026-06-24.md](./PLAN_REPARTO_MODULAR_2026-06-24.md)

### Verificacion humana / UI
- [PROCEDIMIENTO_VERIFICACION_HUMANA_UI.md](./PROCEDIMIENTO_VERIFICACION_HUMANA_UI.md)
- **[INVENTARIO_MAESTRO_TOTAL.md](./INVENTARIO_MAESTRO_TOTAL.md)** — fuente de verdad completa (790 py + 2140 no-py)
- [INVENTARIO_UNIFICADO_RECONCILIADO_2026-06-24.md](./INVENTARIO_UNIFICADO_RECONCILIADO_2026-06-24.md)
- [INVENTARIO_REAL_REPO.md](./INVENTARIO_REAL_REPO.md)

### Estado de tests / deuda tecnica
- [ESTADO_TESTS_LLM_Y_CAP5_2026-06-24.md](./ESTADO_TESTS_LLM_Y_CAP5_2026-06-24.md)

### Coordinacion de agentes
- [outbox/brief_claude.md](./outbox/brief_claude.md)
- [outbox/brief_cascada.md](./outbox/brief_cascada.md)
- [outbox/brief_codex.md](./outbox/brief_codex.md)
- [outbox/TAREA_ACTIVA_CLAUDE.md](./outbox/TAREA_ACTIVA_CLAUDE.md)
- [outbox/TAREA_ACTIVA_CLAUDE_MODULAR_2026-06-24.md](./outbox/TAREA_ACTIVA_CLAUDE_MODULAR_2026-06-24.md)
- [outbox/TAREA_ACTIVA_CASCADA.md](./outbox/TAREA_ACTIVA_CASCADA.md)
- [outbox/TAREA_ACTIVA_CASCADA_MODULAR_2026-06-24.md](./outbox/TAREA_ACTIVA_CASCADA_MODULAR_2026-06-24.md)
- [outbox/TAREA_ACTIVA_CASCADA_RECONCILIACION_2026-06-24.md](./outbox/TAREA_ACTIVA_CASCADA_RECONCILIACION_2026-06-24.md)
- [outbox/TAREA_ACTIVA_CASCADA_PROFUNDIZACION_2026-06-24.md](./outbox/TAREA_ACTIVA_CASCADA_PROFUNDIZACION_2026-06-24.md)

## 2. Herramientas canonicas vigentes

- `npm run human:ui`
- `npm run human:ui:local`
- `npm run human:ui:cloud`
- `run_human_ui_audit.bat`
- `tools/run_human_ui_audit.mjs`
- `tools/run_omni_suite.mjs`
- `tools/last_suite.json`
- `tools/last_suite_summary.json`

## 3. Estado actual de trabajo

### Cerrado y validado
- Runner humano de UI creado y probado.
- Documentacion base de UI humana creada.
- Instrucciones para Claude y Cascada alineadas al runner humano.
- Registro de ruido benigno QZ/WebSocket documentado.

### Pendiente operativo
- Persistir en remoto la salida real del runner humano si se quiere que Claude/Cascada la lean sin depender del árbol local.
- Seguir con limpieza del ruido documental antiguo.
- Revisar la siguiente superficie funcional que se decida auditar.

### Pendiente de decision humana
- Que artefactos locales se promueven a canon remoto.
- Que borrados masivos de docs legacy se confirman definitivamente.
- Que flujo sigue despues de la verificacion humana base.

## 4. Mapa de modulos y flujos cubiertos

### Laboratorio
- Recepcion
- Busqueda/creacion de paciente
- Orden
- Estudios
- Cobro
- Toma de muestra
- Procesamiento
- Captura de resultados
- Validacion
- PDF / entrega

### Farmacia
- PDV
- Busqueda de producto
- Carrito
- Cobro
- Cancelacion
- Devolucion
- Corte de caja

### Consultorio
- Agenda
- Consulta
- Receta
- Expediente

### Director
- Dashboard
- Analizadores
- War Room
- Metricas

### Seguridad / Sentinel
- Login
- Home / dashboard
- Anti-loop de redirects
- 2FA / permisos

## 5. Pendientes que siguen existiendo

- Auditoria funcional humana completa del flujo que siga a la corrida base.
- Clasificacion de nuevas evidencias por Claude/Cascada.
- Fixes de codigo que aparezcan a partir de evidencia nueva.
- Limpieza final de legado y reportes viejos que siguen en el working tree.

## 6. Legado / ruido

- Los archivos viejos de auditoria, reportes y scripts marcados como `D` en git no son canon operativo.
- Solo se recuperan si una instruccion explicita los reabre.
- No deben competir con los documentos de esta carpeta.

## 7. Regla de oro

Si algo no aparece en esta carpeta, no es la fuente de verdad para coordinación multi-IA.
