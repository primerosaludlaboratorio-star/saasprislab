# Tarea Activa para Cascada - Profundizacion del Inventario

Fecha: 2026-06-24

## Contexto

La instruccion vigente no es reconciliar inventarios, sino **profundizar** el mapa del repo con evidencia real.

Referencias canonicas a leer antes de empezar:

- `AI_COORDINATION_STATUS.md`
- `INDICE_CANONICO_TOTAL.md`
- `INVENTARIO_UNIFICADO_RECONCILIADO_2026-06-24.md`
- `INVENTARIO_REAL_REPO.md`

## Objetivo

Expandir el inventario con mas detalle util, sin inventar nada y sin reauditar desde cero lo ya cerrado.

## Areas a profundizar

1. **Management commands**
   - separar mejor auditoria / seed / migracion / backup / sentinel / destructivos
   - marcar cuales son de produccion, cuales son de prueba y cuales no se deben ejecutar sin autorizacion

2. **Tests**
   - clasificar tests por cobertura real
   - separar tests canónicos, e2e externos, scripts manuales y placeholders

3. **Runners**
   - identificar runners activos, legacy y duplicados
   - decir cuales producen evidencia confiable y cuales solo generan ruido

4. **Legacy documental**
   - separar doc util de doc ruido
   - identificar grupos de markdown historicos que no deben competir con el canon

5. **Superficies operativas**
   - señalar donde estan los flujos realmente ejecutables hoy
   - señalar donde solo existe documentacion o historial

## Reglas

- No usar memoria.
- No usar estimaciones si existe evidencia concreta.
- No reabrir hallazgos cerrados sin diff nuevo.
- No mezclar el mapa estructural con el operativo.
- Si un archivo solo documenta historia, marcarlo como legado o ruido si no es parte del canon.

## Entregable esperado

Un reporte de profundizacion con:

- categorias mas finas
- riesgos operativos
- artefactos util
- artefactos legado
- huecos de cobertura

