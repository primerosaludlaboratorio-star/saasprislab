# TAREA ACTIVA PARA CASCADA - Auditoría Técnica de Evidencia

## Rol

Cascada debe trabajar como analista técnico de evidencia y auditor estático. No debe quedarse esperando reportes.

## Objetivo inmediato

Mientras Codex corrige Laboratorio y Claude prueba UI, Cascada debe auditar riesgos transversales que no requieran navegador ni producción.

## Reglas obligatorias

- No tocar código salvo autorización explícita.
- No hacer deploy.
- No repetir auditorías ya cerradas con commit + test.
- No declarar deuda como bug si no hay ruta, archivo, línea y consecuencia operacional.
- Clasificar todo como: `CONFIRMADO`, `PROBABLE`, `PENDIENTE_VALIDAR`, `OPERATIVO`, `LIMITACION_HERRAMIENTA`, `RUIDO`.

## Trabajo asignado ahora

### Bloque A - Doble arquitectura Farmacia

Auditar y mapear:

1. URLs bajo `/farmacia/`.
2. URLs bajo `/farmacia/erp/` si existen.
3. Vistas en `core/views/farmacia.py`.
4. Vistas/modelos en app `farmacia/`.
5. Modelos paralelos de venta/devolución/caja.
6. Rutas duplicadas o solapadas.
7. Riesgo real para producción.

Debe entregar:

- Qué árbol parece ser PDV operativo.
- Qué árbol parece ser ERP administrativo.
- Qué rutas chocan.
- Qué modelos duplican responsabilidad.
- Recomendación de arquitectura: unificar, separar prefijos o deprecar.
- Nivel de riesgo: crítico/alto/medio/bajo.

### Bloque B - Permisos partidos rol/grupos

Auditar:

1. Uso de `request.user.rol`.
2. Uso de `groups`.
3. Decoradores custom.
4. Middleware de admin/access.
5. Herramientas PRIS IA con RBAC.
6. Inconsistencias donde un rol pueda pasar una pantalla pero fallar en API.

Debe entregar:

- Lista de políticas encontradas.
- Riesgos de bypass o bloqueo falso.
- Propuesta de helper común.
- Archivos principales afectados.

### Bloque C - Revisión de patrón LIMS/legacy

Sin tocar código, revisar si quedan usos peligrosos de:

- `detalle.estudio`
- `select_related('estudio')` sobre `OrdenDeServicio.detalles`
- `prefetch_related('detalles__estudio')`

Separar:

- Ruido válido de modelos legacy de app `laboratorio`.
- Riesgo real en `core.models.DetalleOrden`.

## Entregable

Guardar reporte completo en:

`docs/ai_coordination/drop/cascada/AUDITORIA_TECNICA_TRANSVERSAL_FARMACIA_PERMISOS_LIMS.md`

Formato obligatorio:

```md
# Reporte Cascada - Auditoría Técnica Transversal

## Resumen Ejecutivo
- Riesgos críticos:
- Riesgos altos:
- Riesgos medios:
- Ruido descartado:

## Bloque A - Doble Farmacia

## Bloque B - Permisos Rol/Grupos

## Bloque C - LIMS/Legacy

## Recomendaciones priorizadas

## Pendientes que requieren decisión humana
```
