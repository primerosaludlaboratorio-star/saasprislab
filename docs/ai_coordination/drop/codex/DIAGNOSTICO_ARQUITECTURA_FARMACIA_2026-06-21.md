# Diagnostico arquitectura Farmacia - 2026-06-21

## Veredicto

Farmacia tiene dos capas activas y acopladas, pero no deben fusionarse con un parche rapido:

- `core/views/farmacia.py` es el flujo operativo diario: PDV, busqueda de productos, ventas, tickets, devoluciones core, cancelacion, corte unificado, inventario general.
- `farmacia/` es la capa ERP/soporte: Kardex, compras, alertas, caja avanzada, devoluciones ERP, antibioticos, entrada express, semaforo de caducidad y stock critico.

La deuda arquitectonica es real, pero el riesgo mayor seria mover URLs/modelos sin pruebas de caracterizacion. La decision segura es estabilizar permisos y documentar contratos antes de unificar.

## Rutas canonicas observadas

### Capa core operativa

- `/farmacia/` -> dashboard farmacia core.
- `/farmacia/pdv/` -> PDV operativo.
- `/farmacia/api/buscar-producto-pdv/` -> busqueda PDV.
- `/farmacia/api/lotes-producto/<producto_id>/` -> lotes para PDV.
- `/farmacia/historial-ventas/` -> ventas.
- `/farmacia/devoluciones/` -> historial devoluciones core.
- `/farmacia/devoluciones/buscar/` -> API JSON core para buscar venta por `busqueda` o `folio`.
- `/farmacia/devoluciones/procesar/` -> API JSON core para procesar devolucion.
- `/farmacia/ventas/cancelar/<venta_id>/` -> cancelacion core.
- `/farmacia/corte-caja/` -> corte de caja unificado.

### Capa ERP/soporte

Montada en `/farmacia/erp/` con namespace `farmacia:`.

- `/farmacia/erp/kardex/`
- `/farmacia/erp/kardex/crear-movimiento/`
- `/farmacia/erp/compras/registrar/`
- `/farmacia/erp/corte-caja/`
- `/farmacia/erp/devoluciones/`
- `/farmacia/erp/devoluciones/buscar/`
- `/farmacia/erp/devoluciones/procesar/`
- `/farmacia/erp/devoluciones/autorizar/<id>/`
- `/farmacia/erp/caja/verificar/`
- `/farmacia/erp/caja/abrir/`
- `/farmacia/erp/antibioticos/validar/`
- `/farmacia/erp/entrada-express/`
- `/farmacia/erp/semaforo-caducidad/`
- `/farmacia/erp/stock-critico/`

## Contratos importantes

- `core/templates/core/devoluciones.html` consume rutas absolutas core:
  - `/farmacia/devoluciones/buscar/`
  - `/farmacia/devoluciones/procesar/`
- `farmacia/templates/farmacia/devoluciones/buscar_venta.html` consume namespace ERP:
  - `{% url 'farmacia:buscar_venta_devolucion' %}`
  - `{% url 'farmacia:procesar_devolucion' %}`
- El sidebar mezcla ambas capas de forma intencional por ahora:
  - PDV/historial core.
  - Kardex/compras/corte ERP.

## Riesgos confirmados

1. Hay duplicidad conceptual de devoluciones:
   - Core usa `SalesReturn` y servicio `VentaFarmaciaService.registrar_devolucion_resultado`.
   - ERP usa `farmacia.models.DevolucionVenta`, `MovimientoInventario` y `MermaFarmacia`.

2. Hay nombres similares con contratos distintos:
   - Core `/farmacia/devoluciones/buscar/` responde JSON y requiere parametro.
   - ERP `/farmacia/erp/devoluciones/buscar/` renderiza formulario en GET y busca por POST.

3. El helper core `es_gerente_o_admin()` tenia bypass de `is_superuser` sin empresa. Corregido en esta sesion para igualar el patron seguro de ERP.

## Fix aplicado en esta sesion

Archivo: `core/views/farmacia.py`

- `es_gerente_o_admin()` ahora exige empresa antes de permitir superuser/staff.
- Tambien permite roles `ADMIN`, `ADMINISTRADOR`, `GERENTE` con empresa.

Archivo: `core/tests/test_devoluciones_farmacia_api.py`

- Agregada regresion para confirmar que superuser sin empresa no puede bypassar el helper de devoluciones/cancelaciones.

## Validaciones ejecutadas

- `python manage.py check` -> OK.
- `python -m py_compile core/views/farmacia.py core/tests/test_devoluciones_farmacia_api.py` -> OK.
- Deploy VPS a commit `06eb2f7` -> OK.
- Smoke produccion:
  - `https://prislab.labcorecloud.com/` -> HTTP 200.
  - `/farmacia/devoluciones/buscar/` sin sesion -> HTTP 302 a login, esperado por `@login_required`.
- Ajuste operativo aplicado en VPS: permisos de `staticfiles` normalizados a directorios `755` y archivos `644`; `pdv_farmacia*.js` paso a HTTP 200.

Nota: el runner Django focalizado de `core.tests.test_devoluciones_farmacia_api` excedio timeout local antes de producir salida. No se toma como fallo del cambio; queda pendiente repetir en entorno estable o CI.

## Decision recomendada para unificacion

No redirigir ni renombrar rutas aun.

Plan seguro:

1. Crear tests de caracterizacion para rutas core y ERP.
2. Definir canonicidad por flujo:
   - PDV y venta diaria: core.
   - Kardex, compras, caja avanzada y control sanitario: ERP.
   - Devoluciones: decidir si core `SalesReturn` o ERP `DevolucionVenta` sera el modelo canonico.
3. Migrar una sola funcion a la vez con wrappers/aliases y pruebas.
4. Solo despues de estabilizar datos, deprecar rutas legacy con redirects 301/302 controlados.

## Instruccion para otras IAs

No proponer "unificar farmacia" como parche inmediato. Primero deben entregar:

- Mapa exacto de modelo origen/destino.
- Contrato de API esperado por cada template/JS.
- Plan de migracion de datos para devoluciones.
- Tests que prueben el comportamiento actual antes de cambiarlo.
