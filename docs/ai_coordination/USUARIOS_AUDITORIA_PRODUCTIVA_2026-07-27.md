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

## Verificacion humana productiva inicial

Fecha: 2026-07-27. Revision ejecutada sobre la interfaz de producción después del despliegue `b6fa35317a39104dcec36136679289839fb6face`.

- `auditoria_total_10d_20260727`: inicio de sesión correcto; Recepción Laboratorio, LIMS, PDV y corte de caja cargaron correctamente.
- `auditoria_farmacia_admin_10d_20260727`: PDV y corte cargaron; Recepción Laboratorio y LIMS quedaron bloqueados; Finanzas Master quedó bloqueado.
- `auditoria_farmacia_empleado_10d_20260727`: PDV y corte cargaron; Recepción Laboratorio y LIMS quedaron bloqueados; Finanzas Master quedó bloqueado.
- La prueba encontró y corrigió el bypass por URL directa de Recepción Laboratorio para roles de Farmacia.
- La navegación de la cuenta total terminó sin errores de consola observables.
- Health de producción: `HTTP 200`.

## Limitacion de pruebas locales

`manage.py check` y compilación Python pasaron. La suite Django dirigida quedó bloqueada durante la creación de la base de pruebas, sin llegar a ejecutar aserciones; por ello esa suite no se marca como pasada y la evidencia de permisos se basa en la comprobación productiva y en la prueba de regresión añadida en `core/tests/test_auditoria_roles_ui.py`.
