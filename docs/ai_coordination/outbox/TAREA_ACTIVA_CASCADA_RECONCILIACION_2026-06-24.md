# Tarea Activa para Cascada - Reconciliacion de Inventarios

Fecha: 2026-06-24

## Contexto

Ya existen dos lecturas distintas del repositorio:

- `INVENTARIO_REAL_REPO.md` = inventario ejecutable real.
- El inventario estructural de Claude = mapa amplio del sistema, aun pendiente de persistir como archivo canónico si se decide hacerlo.

El objetivo de esta tarea es que Cascada no vuelva a trabajar con ruido documental ni con estimaciones viejas.

## Trabajo asignado

1. Leer:
   - `AI_COORDINATION_STATUS.md`
   - `INDICE_CANONICO_TOTAL.md`
   - `INVENTARIO_UNIFICADO_RECONCILIADO_2026-06-24.md`
   - `INVENTARIO_REAL_REPO.md`

2. Clasificar cualquier evidencia nueva que aparezca en el working tree como una de estas categorias:
   - `CONFIRMADO`
   - `PROBABLE`
   - `PENDIENTE_VALIDAR`
   - `OPERATIVO`
   - `LIMITACION_HERRAMIENTA`
   - `RUIDO`

3. Separar claramente:
   - legacy util
   - legacy ruido
   - canon activo
   - evidencia nueva

4. No reauditar desde cero lo que ya esta cerrado.

5. Si aparece una salida nueva de `human:ui`, auditar solo `report.md` / `report.json` / capturas ligadas a esa corrida.

6. Si no hay evidencia nueva real, detenerse y reportar que no hay diff nuevo que clasificar.

## Regla operativa

- No inventar puntos de partida.
- No abrir hallazgos cerrados sin evidencia nueva.
- No tratar documentos historicos como si fueran ejecucion actual.

## Entregable esperado

- Un reporte corto de clasificacion por archivo o artefacto.
- Separacion clara entre:
  - canon
  - legacy
  - ruido
  - pendiente

