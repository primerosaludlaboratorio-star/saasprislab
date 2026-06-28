# Tarea Activa para Cascada - Evidencia, Legacy y Ruido

Fecha: 2026-06-24

## Contexto

Tu carril ya no es la superficie IA/LLM. Tu tarea ahora es limpiar y clasificar la parte que sigue haciendo ruido y la evidencia humana/runner que ya existe.

## Objetivo

Auditar y clasificar:

- salidas reales de `human:ui`
- reportes viejos
- scripts legacy
- placeholders
- documentos historicos
- ruido documental

## Fuentes canonicas a leer antes de empezar

- `docs/ai_coordination/PROTOCOLO_EJECUCION_PARALELA.md`
- `docs/ai_coordination/PLAN_REPARTO_PARALLELO_2026-06-24.md`
- `docs/ai_coordination/INDICE_CANONICO_TOTAL.md`
- `docs/ai_coordination/AI_COORDINATION_STATUS.md`
- `docs/ai_coordination/PENDIENTES_CANONICOS.md`
- `docs/ai_coordination/INVENTARIO_REAL_REPO.md`

## Que debes revisar

### 1) Evidencia humana / runner

- `auditoria_ui_*`
- `report.md`
- `report.json`
- capturas asociadas

### 2) Legacy documental

- MDs viejos de auditoria
- scripts obsoletos
- placeholders
- carpetas historicas

### 3) Ruido operativo

- artefactos que no deben competir con el canon
- docs que repiten informacion ya canonizada
- salidas de corridas viejas sin valor actual

### 4) Pendientes no-IA

- lo que sigue faltando despues de la corrida humana base
- gaps funcionales que no pertenecen a la superficie IA/LLM

## Reglas

- No reauditar IA/LLM.
- No usar memoria.
- No reabrir lo cerrado.
- No generar inventarios nuevos.
- Si algo solo documenta historia, clasificalo como legacy o ruido.

## Entregable esperado

Un reporte maestro con:

1. Evidencia humana valida.
2. Legacy util.
3. Ruido a borrar o archivar.
4. Pendientes no-IA.
5. Que debe quedar canon y que debe salir del camino.

## Formato obligatorio

`docs/ai_coordination/outbox/REPORTE_CASCADA_EVIDENCIA_LEGACY_2026-06-24.md`

