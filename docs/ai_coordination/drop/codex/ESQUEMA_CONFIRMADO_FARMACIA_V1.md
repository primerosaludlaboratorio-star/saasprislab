# Esquema Confirmado Farmacia v1.0

Fecha: 2026-06-21

Estado: Fase 0 completada con evidencia local de codigo/modelos.

## Resumen ejecutivo

Farmacia tiene doble capa activa:

- Core/PDV: flujo operativo diario.
- App `farmacia`/ERP: Kardex, caja avanzada, compras, devoluciones ERP y control sanitario.

El riesgo principal no es un catalogo duplicado de productos, sino **doble logica operativa sobre entidades compartidas** (`core.Producto`, `core.Lote`, `core.Venta`).

No se autoriza una unificacion productiva todavia. El siguiente paso correcto son tests de caracterizacion y luego servicio comun para devoluciones/caja.

## Evidencia de rutas

### Core/PDV

Archivo: `config/urls.py`

- `/farmacia/corte-caja/` -> redirect temporal a `/farmacia/pdv/?accion=corte`.
- `/farmacia/` -> `views.dashboard_farmacia`.
- `/farmacia/pdv/` -> `views.pdv_farmacia`.
- `/farmacia/devoluciones/` -> `views.historial_devoluciones`.
- `/farmacia/devoluciones/buscar/` -> `views.buscar_venta_devolucion`.
- `/farmacia/devoluciones/procesar/` -> `views.procesar_devolucion`.
- `/farmacia/ventas/cancelar/<venta_id>/` -> `views.cancelar_venta`.
- `/farmacia/compras/registrar/` -> `views.registrar_compra`.
- `/farmacia/inventario/` -> `farmacia_views.inventario_general`.
- `/farmacia/api/lotes-producto/<producto_id>/` -> `views.api_lotes_producto`.

### ERP/soporte

Archivo: `farmacia/urls.py`

Montado en `config/urls.py` como `/farmacia/erp/`.

- `/farmacia/erp/kardex/` -> `KardexListView`.
- `/farmacia/erp/kardex/crear-movimiento/` -> `crear_movimiento_manual`.
- `/farmacia/erp/compras/registrar/` -> `registrar_compra`.
- `/farmacia/erp/corte-caja/` -> `corte_caja_farmacia`.
- `/farmacia/erp/api/lotes-producto/<producto_id>/` -> `api_lotes_producto`.
- `/farmacia/erp/devoluciones/` -> `dashboard_devoluciones`.
- `/farmacia/erp/devoluciones/buscar/` -> `buscar_venta_para_devolucion`.
- `/farmacia/erp/devoluciones/procesar/` -> `procesar_devolucion`.

## Evidencia de modelos

### Producto, Lote y Venta

No existe modelo `farmacia.Producto`.

Evidencia:

- `farmacia/models.py` importa `Producto`, `Lote`, `Venta` desde `core.models`.
- `core/models/catalogos.py` define `Producto`.
- `core/models/catalogos.py` define `Lote`.
- `core/models/ventas.py` define `Venta`.

Conclusion: ERP y core comparten producto/lote/venta.

### Devoluciones

Hay tres modelos relacionados:

- `core.models.ventas.SalesReturn`
- `core.models.ventas.DevolucionVenta`
- `farmacia.models.DevolucionVenta`

Evidencia por introspeccion Django:

- `farmacia.models.DevolucionVenta.venta_original` -> FK a `Venta`.
- `core.models.ventas.SalesReturn.venta_original` -> FK a `Venta`.
- `core.models.ventas.DevolucionVenta.venta_original` -> FK a `Venta`.

Conclusion: devoluciones es el punto con mayor riesgo de doble registro/doble efecto operativo.

### Corte de caja

Evidencia:

- `farmacia.models.CierreTurnoFarmacia.apertura_caja` es `OneToOneField` a `AperturaCaja`.
- `farmacia.models.CierreTurnoFarmacia` tiene constraint `unique_cierre_por_apertura`.
- `farmacia.models.AperturaCaja.cerrada_con` es `OneToOneField` a `CierreTurnoFarmacia`.
- Existe servicio `farmacia/services/corte_caja_unificado.py`.
- Existe ruta `api/caja/corte-unificado/`.

Conclusion: hay proteccion parcial existente. Falta validar cobertura real del flujo usado por usuarios.

## Evidencia de locks/transacciones

### Venta PDV

Archivo: `core/services/ventas/venta_farmacia_service.py`

- `ejecutar_venta_pdv()` usa `transaction.atomic`.
- Usa `Producto.objects.select_for_update()`.
- Usa `Lote.objects.select_for_update()`.
- Crea `MovimientoInventario` para salida de venta.

### Cancelacion core

Archivo: `core/services/ventas/venta_farmacia_service.py`

- `cancelar_venta_resultado()` usa `transaction.atomic`.
- Bloquea `Venta` con `select_for_update`.
- Bloquea `MovimientoInventario` originales con `select_for_update`.
- Crea movimientos de entrada por reversion.

### Devolucion core

Archivo: `core/services/ventas/venta_farmacia_service.py`

- `registrar_devolucion_resultado()` usa `transaction.atomic`.
- Crea `SalesReturn`.
- Crea `MovimientoInventario` tipo `ENTRADA_DEVOLUCION` si aplica.
- No se encontro `select_for_update` sobre `Venta` dentro de esta funcion.
- No se encontro idempotency key propia de devolucion.

Conclusion: devolucion core requiere test de concurrencia e idempotencia antes de unificar.

### Devolucion ERP

Archivo: `farmacia/views/soporte.py`

- `procesar_devolucion()` usa `transaction.atomic`.
- Crea `farmacia.models.DevolucionVenta`.
- Reingresa stock por `MovimientoInventario` o genera `MermaFarmacia`.
- Usa helper `_es_gerente_o_admin()` protegido por empresa.

Conclusion: ERP tiene trazabilidad farmacéutica, pero tambien requiere idempotencia/lock comun si va a ser canonico.

## Contratos de endpoints duplicados

### Buscar devolucion core

Ruta: `/farmacia/devoluciones/buscar/`

- Metodo esperado: GET.
- Parametros: `busqueda` o `folio`.
- Sin parametro: JSON 400.
- Sin sesion: redirect 302 a login.
- Con venta encontrada: JSON con `status: success` y bloque `venta`.

### Buscar devolucion ERP

Ruta: `/farmacia/erp/devoluciones/buscar/`

- GET: renderiza formulario HTML.
- POST: busca venta por `folio` y devuelve JSON.

Conclusion: aunque los nombres sean similares, los contratos no son equivalentes. No usar redirect simple.

### Procesar devolucion core

Ruta: `/farmacia/devoluciones/procesar/`

- POST JSON.
- Delega a `VentaFarmaciaService.registrar_devolucion_resultado`.
- Registra `SalesReturn`.

### Procesar devolucion ERP

Ruta: `/farmacia/erp/devoluciones/procesar/`

- POST JSON.
- Registra `farmacia.models.DevolucionVenta`.

Conclusion: esta duplicidad debe resolverse con servicio comun y tests, no con renombrado de URLs.

## Hallazgos clasificados

### CONFIRMADO

- Doble capa funcional core/ERP.
- Producto/Lote/Venta son compartidos desde core.
- Devoluciones tienen mas de un modelo operativo.
- Core y ERP tienen endpoints de devolucion con contratos distintos.
- Cancelacion core tiene locks; devolucion core no muestra lock de Venta.
- Corte de caja tiene constraint y servicio unificado parcial.

### RECHAZADO

- "Existe farmacia.Producto huerfano": no confirmado; no existe modelo propio en `farmacia/models.py`.
- "No hay ningun control de corte": falso; existen OneToOne/UniqueConstraint y servicio unificado.
- "Aplicar redirects 301 en POST": rechazado por riesgo de perder body.

### HIPOTESIS

- Doble devolucion real en produccion entre core y ERP.
- Descuadre de caja por uso alternado de cortes.
- Divergencia JSON de lotes core vs ERP.

Estas hipotesis requieren tests de caracterizacion o evidencia de produccion.

### REQUIERE DECISION DE NEGOCIO

- Ruta/interfaz canonica para el personal: core/PDV o ERP.
- Quien autoriza devoluciones por rol real.
- Si ERP sera destino estrategico o solo capa administrativa parcial.

## Fix de seguridad agregado tras Fase 0

Se cerraron dos bypasses de permiso en helpers de Farmacia:

- `core.views.farmacia._verificar_acceso()` ahora exige empresa antes de permitir superuser/staff, rol o grupo.
- `farmacia.views.semaforo.es_farmacia_o_director()` ahora exige empresa antes de permitir superuser o grupo `FARMACIA`/`DIRECTOR`.

Pruebas agregadas:

- `core.tests.test_farmacia_permission_helpers`

Validacion:

- 7 tests de Farmacia arquitectura/permisos -> OK.
- `python manage.py check` -> OK.

## Siguiente paso aprobado

Crear tests de caracterizacion para:

1. Resolver rutas core y ERP a las vistas esperadas.
2. Confirmar que `farmacia.Producto` no existe y ERP usa `core.Producto`.
3. Confirmar FKs de devoluciones hacia `Venta`.
4. Confirmar constraint `unique_cierre_por_apertura`.
5. Probar que core/ERP no permiten doble devolucion sobre la misma venta (pendiente; requiere datos).
6. Probar compatibilidad/diferencia de JSON de lotes core vs ERP (pendiente; requiere datos).
