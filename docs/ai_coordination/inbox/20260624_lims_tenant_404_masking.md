# LIMS Tenant - 404 Masking y Contradiccion Canonica

Fecha: 2026-06-24

Reporte persistido para cerrar con precision la prioridad LIMS tenant.

## Hallazgo real

- El reporte de Claude apuntaba a que el aparente problema cross-tenant de `api_rangos_parametro` no era fuga de datos.
- El filtro por empresa era correcto, pero quedaba una contradicción canónica:
  - `Usuario.save()` auto-asignaba empresa por defecto y volvía difícil reproducir "staff/superuser sin empresa".
  - Sentinel convertía `Http404` a una página degradada con `503`.

## Verificación final en este checkout

- `lims.views.tenant_lims.empresa_lims()` ahora solo acepta la FK explícita del usuario.
- `Usuario.save()` ya no inventa una empresa por defecto al crear cuentas.
- `core.tests.test_lims_config_tenant_security` pasó completo (`5/5`).
- `api_rangos_parametro` vuelve a respetar `404` real para analitos ajenos.

## Cierre

- Contradicción canónica resuelta:
  - LIMS no usa fallback de tenant para usuarios sin empresa explícita.
  - Sentinel conserva degradación para otros errores, pero `Http404` vuelve a expresarse como `404`.
- No quedan cambios de código pendientes por este caso.
