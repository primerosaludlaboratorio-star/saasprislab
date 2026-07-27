# Usuarios de auditoria productiva — 2026-07-27

Estado: creados y comprobados en producción.

Producción: `https://prislab.labcorecloud.com`

Empresa: `1` / sucursal principal.

## Cuentas nuevas

| Usuario | Rol | Alcance | Debe poder | No debe poder | Vencimiento |
|---|---|---|---|---|---|
| `auditoria_total_10d_20260727` | `ADMIN` + superusuario | Todo el sistema | Laboratorio/LIMS, Farmacia, Consultorio, administración y auditoría | Ninguna restricción funcional dentro del tenant | 2026-08-06 14:53 UTC |
| `auditoria_farmacia_admin_10d_20260727` | `FARMACIA` | Farmacia completa | PDV, inventario, entradas, lotes, Kardex, caja y reportes operativos | Laboratorio/LIMS, Consultorio y administración global | 2026-08-06 14:53 UTC |
| `auditoria_farmacia_empleado_10d_20260727` | `CAJERO` | Operación de Farmacia | PDV, ventas, devoluciones permitidas por rol, cortes y operación de turno | Ganancias, administración, Laboratorio/LIMS y funciones de administrador | 2026-08-06 14:53 UTC |

## Expiracion automatica

Las cuentas anteriores no se modificaron. Para esta tanda se habilitó el temporizador independiente:

`prislab-expire-auditoria-users-20260727.timer`

El temporizador desactiva exclusivamente los tres usuarios nuevos al vencimiento indicado. El temporizador anterior de las cuentas `*_10d` existentes permanece intacto.

## Claves

Las contraseñas completas están en el archivo local no versionado:

`docs/ai_coordination/CREDENCIALES_AUDITORIA_PRODUCTIVA_2026-07-27.local.md`

No se incluyen contraseñas en documentación versionada, logs, commits ni respuestas públicas.

## Evidencia de creación

- Las tres cuentas se crearon con `empresa_id=1`.
- El administrador total quedó con `is_superuser=True`.
- El administrador de Farmacia quedó con rol `FARMACIA` y sin superusuario.
- El empleado quedó con rol `CAJERO`, sin `is_staff` y sin superusuario.
- El temporizador fue validado con `systemd-analyze verify` y aparece activo en `systemctl list-timers`.

## Pendiente de auditoria humana

Falta iniciar sesión con cada cuenta y ejecutar la matriz completa de navegación y acciones en la interfaz productiva. La prueba debe registrar tanto accesos esperados como respuestas `403` esperadas en áreas fuera del rol.
