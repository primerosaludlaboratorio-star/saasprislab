# TAREA ACTIVA PARA CLAUDE - Auditoría Funcional Producción

## Rol

Claude debe trabajar como auditor funcional humano en producción, no como desarrollador.

## Objetivo inmediato

Mientras Codex corrige y prueba deuda técnica de Laboratorio, Claude debe avanzar con auditoría funcional de módulos que no dependan del fix actual de `DetalleOrden.estudio`.

## Reglas obligatorias

- No tocar código.
- No hacer deploy.
- No declarar un módulo como aprobado si no completó flujo humano real.
- Si Chrome/extensión falla, reportar `LIMITACION_HERRAMIENTA` y pasar al siguiente módulo visual disponible.
- Si aparece 500, clasificar primero como `OPERATIVO` y pedir logs antes de llamarlo bug funcional.
- Cada hallazgo debe incluir: URL, usuario, paso, esperado, resultado real, evidencia visible, severidad y si bloquea operación.

## Credenciales funcionales de auditoría

- URL: `https://prislab.labcorecloud.com/`
- Usuarios conocidos para probar:
  - `admin / [redacted]`
  - `jonathan / [redacted]`
  - `olga / [redacted]`
  - `admin_director / [redacted]`

## Trabajo asignado ahora

### Bloque 1 - Farmacia funcional completa

Auditar como usuario real:

1. Entrar a Farmacia/PDV.
2. Buscar producto existente.
3. Crear producto si el flujo lo permite.
4. Verificar stock visible.
5. Realizar venta normal.
6. Probar venta con descuento.
7. Probar venta con pago mixto.
8. Probar devolución/cancelación si existe UI.
9. Verificar ticket/impresión o vista de comprobante.
10. Verificar que la venta aparece en historial/corte/caja.

### Bloque 2 - Pacientes

1. Crear paciente nuevo.
2. Editar datos del paciente.
3. Buscar por nombre parcial.
4. Verificar expediente/historial.
5. Confirmar que no se muestran errores 500 ni datos de otra empresa.

### Bloque 3 - Consultorio básico

1. Agendar cita.
2. Abrir consulta.
3. Capturar signos vitales.
4. Guardar nota/consulta.
5. Crear receta si existe.
6. Verificar que vuelve al historial del paciente.

## Entregable

Guardar reporte completo en:

`docs/ai_coordination/drop/claude/AUDITORIA_FUNCIONAL_FARMACIA_PACIENTES_CONSULTORIO.md`

Formato obligatorio:

```md
# Reporte Claude - Auditoría Funcional

## Resumen
- Módulos auditados:
- Usuario usado:
- Bloqueadores:
- Hallazgos críticos:
- Hallazgos medios:
- Hallazgos menores:

## Hallazgos

### H1 - Título
- Clasificación:
- Severidad:
- Módulo:
- URL:
- Paso:
- Esperado:
- Real:
- Evidencia:
- Bloquea operación: Sí/No
- Reproducible: Sí/No

## Flujos completados sin fallo

## Flujos no probados y por qué
```
