# VALIDACION PRODUCCION POST-FARMACIA 2026-06-21

## Estado

Codex desplego y valido produccion despues de:
- `d685712` busqueda pacientes laboratorio + fecha agenda.
- `c48f7d7` importador farmacia con `empresa_id` en lotes.

## Deploy VPS

Ruta: `/opt/prislab/app`

Estado:
- `HEAD`: `c48f7d7 fix: asignar empresa a lotes importados de farmacia`
- `manage.py check`: OK
- `prislab-gunicorn`: active
- `prislab-celery`: active
- `prislab-celerybeat`: active
- nginx reload: OK

## Catalogo farmacia

Comando ejecutado:

```bash
python manage.py importar_excel_inventario Productos-farmacia-2026-02-10-10-31.xlsx --empresa-id 1 --reset-stock
```

Resultado:
- Productos creados: 0
- Productos actualizados: 674
- Lotes creados: 715
- Lotes existentes: 1
- Errores: 0
- Productos totales empresa 1: 693
- Productos con stock: 265
- Lotes totales empresa 1: 715
- Lotes con stock activo: 287

## Smoke API no destructivo

Script:

```bash
node _audit_api_smoke.mjs
```

Entorno:
- `BASE_URL=https://prislab.labcorecloud.com`
- usuario: `jonathan`

Resultado:
- Login: OK
- `/farmacia/pdv/`: 200
- `/farmacia/pdv/buscar-fragmento/?q=am`: 200
- `/farmacia/api/buscar-producto-pdv/?termino=am`: 200 JSON
- El JSON devuelve productos con stock.

## Role Matrix no destructivo

Script:

```bash
node _audit_role_matrix.mjs
```

Resultado:
- `/dashboard/`: 200
- `/farmacia/pdv/`: 200
- `/farmacia/pdv/buscar-fragmento/?q=am`: 200
- `/farmacia/api/buscar-producto-pdv/?termino=am`: 200
- `/laboratorio/lista-trabajo/`: 200
- Sin redirects a login.

## Decision Codex

Farmacia H1 queda **cerrado tecnicamente**:
- Ya hay catalogo.
- Ya hay stock/lotes.
- PDV responde con productos.

Pendiente de validacion humana:
- Agregar producto a carrito.
- Cobro real controlado de una venta minima.
- Verificar descuento/devolucion/corte, pero no ejecutar ventas masivas.

## Seguridad scripts

No ejecutar todavia:
- `auditoria_farmacia_full.py`
- `auditoria_core_full.py`
- `auditoria_medico_full.py`
- `auditoria_lab_full.py`

Motivo: no son solo lectura; crean datos mediante ORM o estan deprecated.
