# Revision Codex - Fixes SEC-H2 a SEC-H5 de Cascada

Fecha: 2026-06-21

## Veredicto

Codex reviso los cambios aplicados por Cascada y los acepta con correcciones.

La regla canonica queda:

1. Todo endpoint tenant-sensitive debe exigir usuario autenticado con empresa asignada.
2. `is_superuser` y `is_staff` no pueden operar sin empresa.
3. `is_superuser` y `is_staff` si pueden operar cuando tienen empresa valida, pero solo sobre objetos filtrados por esa empresa.
4. No se acepta fallback silencioso a `request.empresa_actual` en APIs clinicas/farmacia cuando la funcion requiere empresa explicita del usuario.

## Cambios aceptados

- `consultorio/api_views.py`: acceso a audio exige empresa; staff/superuser con empresa siguen permitidos.
- `lims/views/analitos.py`, `perfiles.py`, `paquetes.py`, `precios.py`: permisos LIMS exigen empresa antes de staff/superuser.
- `core/views/administracion_usuarios.py`: APIs de tarifa/permisos ya no permiten operar sin empresa.
- `core/views/laboratorio_captura.py`: captura de resultados exige empresa y mantiene staff/superuser con empresa.
- `core/views/laboratorio_reportes.py`: reportes y generacion de PDF exigen que la orden pertenezca a la empresa del usuario.

## Correcciones Codex sobre la propuesta

- `core/views/laboratorio_config.py`: ademas de permisos, se agrego scoping por empresa en lecturas LIMS legacy:
  - `api_parametros_estudio`
  - `api_rangos_parametro`
  - `api_rango_detalle`
  - `api_soft_delete_parametro`
  - `api_buscar_parametros`
- `consultorio/views.py`: se endurecieron endpoints tenant-sensitive para usar empresa explicita del usuario, no fallback del middleware.
- `farmacia/views/__init__.py`: no se acepta cambio a fallback `request.empresa_actual`; queda pendiente sin commit si no hay justificacion arquitectonica.

## Cambios no aceptados en este commit

- `core/tests/test_auditoria_funcional_20260621.py`: los tests agregados por Cascada no se commitean en este bloque porque incluyen imports/endpoints que no coinciden con la ruta real actual:
  - `OrdenDeServicio` vive en `core.models`, no en `laboratorio.models`.
  - El endpoint `/laboratorio/reportes/orden/<id>/` no aparece en `config/urls.py`.
  - Deben separarse en tests focalizados por modulo y validarse antes de entrar al repo.

## Validacion Codex

- `python manage.py check`: OK, 0 issues.
- `python -m py_compile` sobre archivos tocados: OK.
- Nuevo test focalizado agregado: `core/tests/test_lims_config_tenant_security.py`.
- El runner local de tests se quedo colgado preparando BD de pruebas; se deja documentado y se validara con smoke post-deploy.

## Siguiente paso

Comitear solo archivos validados por Codex, desplegar a VPS, reiniciar servicios y ejecutar smoke de:

- `/laboratorio/recepcion/`
- `/lims/api/parametros/buscar/?q=Glucosa`
- endpoints LIMS configuracion con usuario autenticado PRISLAB.
