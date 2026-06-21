# Revision Codex - Lote 2 Seguridad Tenant

Fecha: 2026-06-21

## Veredicto

Lote 2 aprobado con una correccion de Codex.

## Aprobado

### Correccion 6 - Limpieza de `pass`

Aceptada.

`core/views/laboratorio_captura.py` conserva la regla:

- empresa obligatoria primero.
- staff/superuser con empresa pueden operar.
- usuarios no staff deben pasar por rol o grupo.

El cambio solo mejora claridad y no altera el permiso efectivo.

### Correccion 7 - Helper `get_empresa_usuario`

Aceptada.

`core/utils/empresa_request.py` centraliza la lectura directa de `user.empresa`.

Aplicado en:

- `consultorio/api_views.py`
- `lims/views/analitos.py`
- `lims/views/perfiles.py`
- `lims/views/paquetes.py`
- `lims/views/precios.py`

No cambia semantica de tenant: sigue exigiendo empresa asignada al usuario.

## Corregido por Codex

### Correccion 10 - Roles LIMS precios

La propuesta removia `GERENTE` y grupo `GERENCIA` de `lims/views/precios.py`.

Codex NO acepta removerlos sin decision de negocio, porque el sistema ya usa `GERENTE`/`GERENCIA` en modulos financieros, farmacia, dashboards y sidebar.

Decision aplicada:

- Se conserva `GERENTE`.
- Se conserva grupo `GERENCIA`.
- Se mantiene empresa obligatoria via `get_empresa_usuario`.

## Validacion

- `python -m py_compile` sobre archivos del lote: OK.
- `python manage.py check`: OK, 0 issues.

## Estado

Listo para commit/deploy como lote independiente.
