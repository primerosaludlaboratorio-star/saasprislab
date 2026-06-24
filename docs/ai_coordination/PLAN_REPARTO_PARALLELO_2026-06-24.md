# Plan de Reparto Paralelo - PRISLAB

Fecha: 2026-06-24

Este plan separa trabajo para que Claude y Cascada no reciban el mismo objetivo.

---

## 1. Mapa completo de lo que sigue faltando

### A. Superficie IA / LLM real

- Proveedores Gemini / DeepSeek
- RAG
- OCR documental
- voz / asistente
- validacion IA
- agente PRIS
- tests y comandos de IA

### B. Evidencia humana / runner UI

- salida real de `human:ui`
- persistencia del `report.md` y `report.json`
- comparacion contra reportes viejos

### C. Limpieza documental / legacy

- reportes viejos
- scripts viejos
- placeholders
- carpetas historicas
- ruido que no debe competir con el canon

### D. Gaps funcionales no-IA

- siguiente flujo operativo despues de la corrida base
- pendientes de laboratorio / farmacia / consultorio / seguridad

### E. Deuda tecnica y regresiones

- CAP-05
- suite LLM pendiente
- pruebas sin cobertura o sin corrida reciente

---

## 2. Reparto de trabajo

### Claude

Objetivo:

- auditar la **superficie IA/LLM real**
- revisar providers, servicios, vistas, agente, tests y comandos de IA
- detectar riesgos reales de RBAC, tenant scope, escalada, mutaciones y acoplamiento clinico

No debe hacer:

- limpieza documental masiva
- inventario completo del repo
- reauditoria de legacy viejo
- auditoria funcional de laboratorio/farmacia/consultorio salvo que sea necesario para el acoplamiento IA

Entregable:

- `docs/ai_coordination/outbox/REPORTE_CLAUDE_IA_LLM_2026-06-24.md`

### Cascada

Objetivo:

- auditar la **evidencia humana y el ruido documental**
- clasificar runner outputs, legacy, placeholders, docs viejos y pendientes operativos no-IA
- decidir qué se archiva, qué se conserva y qué sigue vivo

No debe hacer:

- repetir la auditoria IA/LLM de Claude
- reauditar desde memoria
- abrir hallazgos cerrados sin diff nuevo

Entregable:

- `docs/ai_coordination/outbox/REPORTE_CASCADA_EVIDENCIA_LEGACY_2026-06-24.md`

### Codex

Objetivo:

- corregir codigo real
- agregar regresiones
- limpiar canon documental
- integrar cambios solo cuando ya existan hallazgos validados

---

## 3. Orden de intercambio

1. Claude trabaja IA/LLM.
2. Cascada trabaja evidencia/legacy/runner outputs.
3. Claude revisa el reporte de Cascada.
4. Cascada revisa el reporte de Claude.
5. Codex integra lo que ambos confirmen.
6. El usuario autoriza el cierre final.

---

## 4. Regla de cero solapamiento

- Claude no toma legacy/document cleanup.
- Cascada no toma IA/LLM runtime.
- Si alguno encuentra algo fuera de su carril, lo reporta como hallazgo colateral y lo deja pendiente de asignacion.

---

## 5. Criterio de cierre

Una tarea solo se cierra cuando:

- hay evidencia reproducible,
- hay reporte maestro propio,
- hay cruce con el otro agente,
- y Codex la integra al canon oficial.

