# Estándar de Testeabilidad y Auditabilidad - PRISLAB

Fecha: 2026-06-24

Este documento fija una regla operativa obligatoria para todo el repositorio:

> Todo módulo, flujo y función que forme parte del sistema canónico debe poder probarse y auditarse con evidencia reproducible.

## Regla central

Ningún cambio se considera realmente cerrado si no cumple al menos una de estas vías:

1. Prueba automática reproducible.
2. Runner humano de UI con `report.md` y `report.json`.
3. Evidencia técnica verificable en código, logs o traceback reproducible.

Si una función no tiene cobertura de prueba, debe quedar explícitamente marcada como pendiente de cobertura.
Si un módulo no tiene runner o test, debe documentarse como hueco real, no como cierre.

## Criterios mínimos por superficie

### Backend / lógica

- Toda función nueva o corregida debe tener prueba focalizada o evidencia ejecutable.
- Todo bug confirmado debe quedar con regresión.
- Toda API importante debe responder con contrato estable y verificable.

### UI / flujo humano

- Todo flujo de usuario debe poder auditarse con `npm run human:ui`.
- Si un flujo no es navegable por UI, debe quedar documentado como limitación real.
- La evidencia primaria de interfaz debe ser el `report.md` y `report.json` generados por el runner.

### Integraciones y servicios

- Cualquier integración externa debe tener prueba de contrato, mock o verificación controlada.
- Los fallos de entorno deben separarse de los fallos de código.

### Documentación / canon

- Si una función, módulo o runner existe pero no está en el canon, no se usa como fuente de verdad.
- Si algo quedó solo en un reporte viejo, debe persistirse o descartarse.
- El inventario maestro es la base para decidir qué falta probar.

## Definición de cierre

Un módulo o función solo se considera alineado cuando existen:

- código revisado,
- prueba automática o runner humano,
- documento canónico actualizado,
- y evidencia reproducible de su estado.

## Consecuencia operativa

Si algo no se puede probar ni auditar, sigue siendo pendiente.
Si algo no está documentado en el canon, no se toma como cerrado.

