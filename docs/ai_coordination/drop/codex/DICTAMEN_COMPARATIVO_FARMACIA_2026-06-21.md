# Dictamen comparativo Farmacia - 2026-06-21

## Objetivo

Comparar dos auditorias externas sobre la doble arquitectura de Farmacia y fijar una decision canonica para el equipo.

Reportes comparados:

1. `DICTAMEN DE AUDITORIA ARQUITECTONICA INTEGRAL`.
2. `Auditoria Tecnica Ampliada v3.0`.

## Decision Codex

Se adopta el **Reporte 2 / Auditoria Tecnica Ampliada v3.0** como base de trabajo.

Motivo: separa hechos de hipotesis, exige evidencia antes de tocar codigo, corrige riesgos tecnicos reales del reporte 1 y evita acciones peligrosas como redirects HTTP 301 en endpoints POST.

El Reporte 1 se conserva como alerta de negocio, pero no debe ejecutarse literalmente porque mezcla supuestos con afirmaciones forenses no demostradas.

## Hechos verificados en codigo real

### 1. Hay doble capa activa

Core/legacy:

- `config/urls.py`
- `core/views/farmacia.py`
- Rutas principales:
  - `/farmacia/pdv/`
  - `/farmacia/devoluciones/`
  - `/farmacia/devoluciones/buscar/`
  - `/farmacia/devoluciones/procesar/`
  - `/farmacia/compras/registrar/`
  - `/farmacia/inventario/`
  - `/farmacia/api/lotes-producto/<producto_id>/`

ERP/soporte:

- `farmacia/urls.py`
- `farmacia/views/`
- Montado en `/farmacia/erp/`
- Rutas principales:
  - `/farmacia/erp/kardex/`
  - `/farmacia/erp/compras/registrar/`
  - `/farmacia/erp/corte-caja/`
  - `/farmacia/erp/devoluciones/`
  - `/farmacia/erp/devoluciones/buscar/`
  - `/farmacia/erp/devoluciones/procesar/`
  - `/farmacia/erp/api/lotes-producto/<producto_id>/`

### 2. No existe `farmacia.Producto`

Verificado:

- `farmacia/models.py` importa `Producto`, `Lote` y `Venta` desde `core.models`.
- `Producto` vive en `core/models/catalogos.py`.
- `Lote` vive en `core/models/catalogos.py`.
- `Venta` vive en `core/models/ventas.py`.

Conclusion: el riesgo no es tener dos catalogos de producto separados, sino tener dos capas funcionales que operan sobre las mismas entidades core.

### 3. Devoluciones si estan duplicadas por modelo

Existen tres estructuras relacionadas:

- `core.models.ventas.SalesReturn`
- `core.models.ventas.DevolucionVenta`
- `farmacia.models.DevolucionVenta`

`farmacia.models.DevolucionVenta` tiene FK real a `core.Venta`.

`SalesReturn` tambien tiene FK real a `core.Venta`.

Conclusion: el riesgo de doble contabilizacion/devolucion es real, pero debe demostrarse con tests de caracterizacion antes de unificar.

### 4. Corte de caja ya tiene parte de proteccion

Verificado:

- `farmacia.models.CierreTurnoFarmacia` tiene `UniqueConstraint` `unique_cierre_por_apertura`.
- `AperturaCaja.cerrada_con` es `OneToOneField` a `CierreTurnoFarmacia`.
- Existe API unificada: `config/urls.py` ruta `api/caja/corte-unificado/`.

Conclusion: el reporte 1 sobredimensiona la ausencia total de control. Hay controles existentes, pero falta validar si cubren todo el flujo real.

### 5. Redirect 301 en POST es mala idea

Se adopta la observacion del reporte 2:

- No usar redirects HTTP para endpoints POST.
- Usar aliases de URL que apunten a la misma funcion Python durante la coexistencia.

## Puntos del Reporte 1 aceptados

- La duplicidad Farmacia core/ERP es real.
- Devoluciones es el punto mas delicado por impacto en dinero y stock.
- No se debe hacer una unificacion con machete.
- Se necesitan tests de caracterizacion antes de migrar.
- Deben existir controles de idempotencia y locks transaccionales en operaciones financieras/inventario.

## Puntos del Reporte 1 rechazados o corregidos

- `farmacia_producto` huerfana: no confirmado; no existe modelo `Producto` en `farmacia/models.py`.
- "No existe sincronizacion transaccional" como afirmacion absoluta: parcialmente cierto para rutas duplicadas, pero hay FK compartidas y restricciones existentes.
- Hotfix basado en hash con timestamp: no recomendado; usar idempotency key estable generada por cliente/servidor, no un hash que cambie por timestamp.
- Crear una tercera familia `/farmacia/admin/` sin justificar: aumenta superficie de mantenimiento. Si se crea, debe ser por decision de negocio; tecnicamente es preferible canonizar ERP o usar aliases hacia vistas canonicas.
- Redirects 301 para POST: rechazado.

## Plan aprobado

### Fase 0 - Evidencia obligatoria

No se implementa la unificacion hasta completar un documento `ESQUEMA_CONFIRMADO_FARMACIA_V1.md` con:

1. Rutas duplicadas reales con archivo y linea.
2. Modelos reales con FKs y constraints.
3. Contrato JSON/HTML de cada endpoint duplicado.
4. Confirmacion de si `select_for_update` existe y donde.
5. Decision de negocio: que interfaz usa hoy el personal y cual sera canonica.

### Fase 1 - Tests de caracterizacion

Agregar tests para:

- Core devolucion procesa una devolucion y deja stock/caja en estado esperado.
- ERP devolucion procesa una devolucion y deja stock/caja en estado esperado.
- Intentar procesar la misma venta por ambas rutas no debe duplicar stock ni reembolso.
- API core y API ERP de lotes para el mismo producto devuelven contrato compatible o se documentan diferencias.
- Corte de caja no permite dos cierres para la misma apertura.

### Fase 2 - Canonizacion

No usar redirects para POST.

Opciones:

- Canonizar ERP como fuente de verdad para devoluciones y hacer que la ruta core llame a la misma funcion/servicio.
- O canonizar core para devoluciones y hacer que ERP delegue al mismo servicio.

Decision tecnica preliminar: crear un **servicio comun** para devoluciones y hacer que ambas rutas llamen a ese servicio antes de eliminar una de ellas.

### Fase 3 - Idempotencia y concurrencia

Implementar:

- idempotency key unica para devoluciones.
- `select_for_update` sobre `Venta` y/o `DetalleVenta` dentro de `transaction.atomic`.
- auditoria administrativa separada.
- tests de concurrencia real con `TransactionTestCase`.

### Fase 4 - Deprecacion controlada

- Mantener aliases para POST.
- Usar logs para medir uso legacy.
- Solo usar redirects en GET.
- Eliminar legacy despues de periodo sin uso y con tablero de integridad estable.

## Instruccion para Claude/Cascada

No ejecutar ni proponer hotfixes de unificacion todavia.

Siguiente trabajo util:

1. Crear `ESQUEMA_CONFIRMADO_FARMACIA_V1.md` con evidencia real.
2. Proponer tests de caracterizacion exactos, sin tocar codigo productivo.
3. Marcar cada hallazgo como `CONFIRMADO`, `HIPOTESIS`, `RECHAZADO` o `REQUIERE_DECISION_NEGOCIO`.

## Estado

Decision tomada:

- Base canonica: Reporte 2.
- Reporte 1: util como alarma, no como plan ejecutable.
- Accion inmediata: Fase 0 + tests de caracterizacion, no migracion.

