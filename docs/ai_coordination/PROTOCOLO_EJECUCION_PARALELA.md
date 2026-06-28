# PROTOCOLO DE EJECUCION PARALELA — PRISLAB Multi-IA

Fecha: 2026-06-24  
Autor: Usuario (integrador y curador del canon)  
Estado: ACTIVO — obligatorio para toda ronda de trabajo

---

## Roles fijos

| Agente | Rol | Prohibido |
|--------|-----|-----------|
| **Claude** | Ejecuta, revalida, produce evidencia | Solo anotar, solo leer, solo resumir |
| **Cascada** | Ejecuta, revalida, produce evidencia | Solo anotar, solo leer, solo resumir |
| **Codex** | Corrige código, integra al canon técnico | Abrir hallazgos sin evidencia |
| **Usuario** | Árbitro, integrador, curador del canon | Ninguno |

---

## Flujo por ronda

### 1. Asignación (Usuario)

- Define el módulo, flujo o deuda objetivo.
- Lo asigna a Claude Y a Cascada en paralelo sobre el mismo objetivo.
- Ambos reciben el mismo contexto de entrada.

### 2. Ejecución paralela (Claude + Cascada)

Cada uno trabaja **independientemente** sobre el mismo objetivo.  
Cada uno **produce cambios o hallazgos reales** — no solo resúmenes.  
Cada uno entrega su propio documento de reporte (ver formato abajo).

### 3. Cruce (Claude revisa a Cascada, Cascada revisa a Claude)

- Cada agente lee el reporte del otro.
- Si coinciden: se marca como **ALINEADO**.
- Si no coinciden: se marca como **CONTRADICCION** — no se cierra, no se promueve.
- El cruce también detecta omisiones que uno vio y el otro no.

### 4. Integración final (Usuario)

- Compara ambos resultados.
- Resuelve contradicciones.
- Decide qué entra al canon oficial.
- Decide qué se archiva.
- Detecta huecos que ambos dejaron pasar.
- **Solo después de esta autorización se promueve al canon oficial.**

### 5. Implementación (Codex)

- Recibe instrucciones precisas del usuario.
- Aplica cambios de código o limpieza de canon.
- Entrega diff verificable.

---

## Formato obligatorio de reporte por agente

Cada ronda produce un archivo:  
`docs/ai_coordination/outbox/REPORTE_[AGENTE]_[MODULO]_[FECHA].md`

```
# Reporte de [Agente] — [Módulo] — [Fecha]

## Objetivo
## Alcance (archivos revisados con rutas absolutas)
## Evidencia encontrada (con referencia a línea o salida de runner)
## Cambios aplicados (si alguno, con justificación)
## Riesgos detectados
## Qué quedó cerrado
## Qué quedó pendiente
## Qué debe revisar el otro agente
## Qué debe integrar Codex al canon oficial
```

---

## Reglas de oro

1. **Nada se da por cerrado solo porque una IA lo dijo.**
2. **Nada se integra al índice maestro hasta que esté cruzado y alineado.**
3. **Una contradicción entre Claude y Cascada es valiosa — no se resuelve sin el usuario.**
4. **El inventario ya existe — no regenerar, usar como base.**
5. **No reabrir hallazgos cerrados sin diff nuevo o evidencia nueva.**
6. **No mezclar legado/ruido con evidencia activa.**
7. **No usar memoria como fuente de verdad — siempre leer el documento canónico vigente.**

---

## Qué acelera este modelo

- Duplica la revisión útil por ronda.
- Reduce omisiones (lo que uno pasa el otro lo encuentra).
- Detecta errores antes de que lleguen al canon.
- El usuario cierra sin que entre ruido.
- Codex solo trabaja sobre instrucciones ya validadas — no improvisa.

---

## Qué documentos leer antes de cada ronda

1. `INDICE_CANONICO_TOTAL.md` — estado del canon
2. `INVENTARIO_MAESTRO_TOTAL.md` — árbol completo
3. `AI_COORDINATION_STATUS.md` — estado de coordinación actual
4. El brief del agente correspondiente (`outbox/brief_[agente].md`)
5. La tarea activa asignada (`outbox/TAREA_ACTIVA_[AGENTE]_*.md`)
