# Fix Tenant Fuera de LIMS 01 - 2026-06-21

## Alcance

Se reviso el reporte que marcaba vulnerabilidades fuera de LIMS y se aplico un primer lote de bajo riesgo.

Archivos corregidos:

- `core/views/configuracion.py`
- `core/views/bienestar.py`
- `seguridad/views.py`

## Decisiones

### Configuracion IA / BYOK

Antes:

- `is_superuser` podia pasar el gate de permiso antes de validar empresa.

Ahora:

- `get_empresa_usuario(user)` es obligatorio.
- `ADMIN`, `DIRECTOR` y `is_superuser` solo operan si tienen empresa valida.

### Bienestar / RRHH

Antes:

- El dashboard calculaba alertas RRHH si `is_superuser` aunque el usuario no tuviera empresa.
- `alertas_rrhh` permitia el gate privilegiado antes de rechazar usuarios sin empresa.

Ahora:

- Se usa `get_empresa_usuario(user)`.
- Alertas RRHH solo se calculan si existe empresa.
- La vista RRHH rechaza usuario sin empresa antes de evaluar rol/superuser.

### Seguridad / Auditoria

Antes:

- `dashboard_auditoria`, `logs_auditoria` y `api_estadisticas_seguridad` solo exigian `is_staff`.
- Las consultas eran globales sobre `LogAccionSensible`, `SesionActiva` y `DispositivoTOTP`.

Ahora:

- Staff debe tener empresa asignada.
- Logs y sesiones se filtran por `usuario__empresa=empresa`.
- Estadisticas 2FA se filtran por `usuario__empresa=empresa`.

## Clasificacion

No se acepta automaticamente el conteo "15/15 criticas" como verdad cerrada.

Este lote corrige hallazgos con evidencia directa de datos globales o permiso privilegiado antes de empresa.

## Validacion

- `python -m py_compile core/views/configuracion.py core/views/bienestar.py seguridad/views.py`: OK
- `python manage.py check`: OK

## Pendiente

Revisar en lotes separados:

- `consultorio/views.py`: muchas referencias a `empresa_efectiva_request`; requiere clasificacion por flujo, no reemplazo masivo.
- `farmacia/views/soporte.py`: el helper de rol tiene `is_superuser`, pero las operaciones vistas ya filtran por empresa. Requiere auditoria por funcion antes de tocar.
- Templates reportados como UI cross-tenant: requieren evidencia de condicion/render.
