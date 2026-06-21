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

Conclusion: el cierre unificado ya crea cierre formal y cierra apertura. Falta decidir si la vista clasica HTML debe migrar a este servicio.

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
- Bloquea `Venta` con `select_for_update` antes de crear la devolucion.
- Calcula monto disponible restando devoluciones core (`SalesReturn`) y ERP (`farmacia.DevolucionVenta`).
- Crea `SalesReturn`.
- Crea `MovimientoInventario` tipo `ENTRADA_DEVOLUCION` si aplica.
- No se encontro idempotency key propia de devolucion.

Conclusion: devolucion core ya bloquea duplicado secuencial y cruce core/ERP. Sigue pendiente idempotencia explicita por request.

### Devolucion ERP

Archivo: `farmacia/views/soporte.py`

- `procesar_devolucion()` usa `transaction.atomic`.
- Bloquea `Venta` con `select_for_update` antes de crear la devolucion.
- Calcula monto disponible restando devoluciones core (`SalesReturn`) y ERP (`farmacia.DevolucionVenta`).
- Crea `farmacia.models.DevolucionVenta`.
- Reingresa stock por `MovimientoInventario` o genera `MermaFarmacia`.
- Usa helper `_es_gerente_o_admin()` protegido por empresa.

Conclusion: ERP tiene trazabilidad farmaceutica y ya comparte guard financiero con PDV. Sigue pendiente idempotencia explicita por request.

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

### Lotes producto core y ERP

Rutas:

- Core/PDV: `/farmacia/api/lotes-producto/<producto_id>/`
- ERP: `/farmacia/erp/api/lotes-producto/<producto_id>/`

Estado tras cierre:

- Ambos endpoints devuelven `producto`.
- Ambos endpoints devuelven `lotes`.
- El contrato minimo de lote incluye `id`, `numero_lote`, `fecha_caducidad`, `cantidad`, `costo_adquisicion`, `dias_restantes`, `es_vencido`.
- El contrato minimo de producto incluye `stock_total`, `lote_id`, `numero_lote_proximo`, `sin_stock_vigente`.
- ERP mantiene campos extra utiles para inventario, como `stock_total_fisico` y `lotes_vencidos_count`.

Conclusion: el contrato minimo core/ERP quedo alineado sin romper campos existentes.

## Hallazgos clasificados

### CONFIRMADO

- Doble capa funcional core/ERP.
- Producto/Lote/Venta son compartidos desde core.
- Devoluciones tienen mas de un modelo operativo.
- Core y ERP tienen endpoints de devolucion con contratos distintos.
- Cancelacion core tiene locks; devoluciones core y ERP tambien bloquean `Venta`.
- Core y ERP rechazan doble devolucion total secuencial sobre la misma venta.
- Core y ERP rechazan doble devolucion cruzada sobre la misma venta (PDV -> ERP y ERP -> PDV).
- Corte de caja tiene constraint y servicio unificado parcial.

### RECHAZADO

- "Existe farmacia.Producto huerfano": no confirmado; no existe modelo propio en `farmacia/models.py`.
- "No hay ningun control de corte": falso; existen OneToOne/UniqueConstraint y servicio unificado.
- "Aplicar redirects 301 en POST": rechazado por riesgo de perder body.

### HIPOTESIS

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

## Fix de devoluciones cruzadas tras Fase 0

Commit: `fa9b02a` (`fix: bloquear devoluciones cruzadas farmacia core erp`)

Cambios:

- `core.services.ventas.venta_farmacia_service.registrar_devolucion_resultado()` suma devoluciones core + ERP antes de permitir nuevo reembolso.
- `farmacia.views.soporte.procesar_devolucion()` suma devoluciones core + ERP antes de permitir nuevo reembolso.
- Ambos caminos revalidan el disponible dentro de `transaction.atomic()` y con `Venta.objects.select_for_update()`.
- La serializacion ERP de busqueda de venta muestra `total_devuelto`, `disponible_devolver` y `tiene_devoluciones` considerando ambos arboles.

Pruebas agregadas/ampliadas:

- `test_core_luego_erp_rechaza_devolucion_cruzada_misma_venta`
- `test_erp_luego_core_rechaza_devolucion_cruzada_misma_venta`
- Ajuste de `test_permiso_devolucion_requiere_empresa_para_superuser` para forzar usuario sin tenant real, evitando la autoasignacion de `Usuario.save()`.

Validacion local:

- `python manage.py test core.tests.test_devoluciones_farmacia_api --keepdb -v 2` -> 10/10 OK.
- `python manage.py check` -> OK.

Validacion VPS:

- VPS en `fa9b02a`.
- `python manage.py test core.tests.test_devoluciones_farmacia_api --keepdb -v 2` -> 10/10 OK.
- `python manage.py check` -> OK.
- Servicios `prislab-gunicorn`, `prislab-celery`, `prislab-celerybeat` -> active.
- `https://prislab.labcorecloud.com/` -> HTTP 200.
- Estaticos Django/admin -> HTTP 200.

## Fix de contrato de lotes core/ERP

Cambios:

- `core.views.farmacia.api_lotes_producto()` ahora devuelve `lotes` ademas de `producto`.
- El contrato de lotes core se alinea con el contrato ERP sin retirar ningun campo usado por PDV.
- Se agrego cobertura en `core.tests.test_farmacia_lotes_api`.

Validacion local:

- `python manage.py test core.tests.test_farmacia_lotes_api --keepdb -v 2` -> 2/2 OK.
- `python manage.py check` -> OK.

## Fix de corte de caja unificado

Cambios:

- `farmacia.services.corte_caja_unificado._cerrar_farmacia()` ahora crea `CierreTurnoFarmacia`.
- El cierre formal queda vinculado a `AperturaCaja`.
- `AperturaCaja` queda cerrada por el flujo propio de `CierreTurnoFarmacia.save()`.
- El corte consolidado calcula `fondo_inicial`, `efectivo_esperado` y diferencia contra efectivo declarado.
- Una segunda ejecucion sin apertura activa no duplica cierre.

Pruebas agregadas:

- `core.tests.test_farmacia_corte_unificado.CorteCajaUnificadoTest.test_corte_unificado_crea_cierre_formal_y_cierra_apertura`
- `core.tests.test_farmacia_corte_unificado.CorteCajaUnificadoTest.test_corte_unificado_no_duplica_cierre_si_no_hay_apertura_activa`

Validacion local:

- `python manage.py test core.tests.test_farmacia_corte_unificado --keepdb -v 2` -> 2/2 OK.
- `python manage.py check` -> OK.

## Siguiente paso aprobado

Crear tests de caracterizacion para:

1. Resolver rutas core y ERP a las vistas esperadas.
2. Confirmar que `farmacia.Producto` no existe y ERP usa `core.Producto`.
3. Confirmar FKs de devoluciones hacia `Venta`.
4. Confirmar constraint `unique_cierre_por_apertura`.
5. Probar que core/ERP no permiten doble devolucion sobre la misma venta (COMPLETADO en `fa9b02a`).
6. Probar compatibilidad/diferencia de JSON de lotes core vs ERP (COMPLETADO; contrato minimo alineado).
