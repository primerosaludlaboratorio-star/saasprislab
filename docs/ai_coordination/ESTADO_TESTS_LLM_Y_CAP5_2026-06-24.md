# Estado de Tests LLM y Deuda CAP-05 - PRISLAB

Fecha: 2026-06-24

Este documento separa lo verificado hoy de la deuda tecnica que sigue abierta.

## 1. Estado real verificado hoy

- Tests sin LLM: **696/701 pasando**
- Regresiones nuevas: **ninguna**

Interpretacion:

- La base no-LLM esta estable.
- Los 5 fallos restantes fueron reportados como preexistentes.

## 2. Tests con LLM

- Total reportado: **30 tests**
- Estado hoy: **no corridos**
- Motivo: costo/API/tiempo de ejecucion aproximado elevado

Estado canonico:

- **Pendiente de validar**
- No se debe afirmar estabilidad actual sin una corrida reciente

## 3. Fallos preexistentes que permanecen

1. `test_fastapi_performance`
   - SLO de latencia
   - Probable condicion de hardware/carga

2. `test_openapi_schema_fast`
   - timing

3. `test_malformed_tool_args_json_handled`
   - preexistente

4. `test_agent_executes_plan_documents_locally_when_requested`
   - preexistente

5. `test_soak_memory_leak`
   - timeout en Windows con path resolution

## 4. Deuda tecnica estructural pendiente

### CAP-05

- El agente hace 6 rondas LLM cuando deberia hacer 3
- Impacto: timeout frágil sigue existiendo
- Estado: pendiente

## 5. Clasificacion canonica

- Lo de los 30 tests LLM no corridos hoy es **deuda de verificacion**, no bug nuevo.
- Los 5 fallos listados arriba siguen siendo **preexistentes** hasta que haya evidencia nueva.
- CAP-05 sigue siendo **deuda tecnica estructural**.

## 6. Regla operativa

Antes de tratar cualquiera de estos puntos como hallazgo nuevo:

1. Verificar si ya esta clasificado como preexistente.
2. Verificar si hay corrida reciente.
3. Verificar si afecta produccion o solo un harness de prueba.
