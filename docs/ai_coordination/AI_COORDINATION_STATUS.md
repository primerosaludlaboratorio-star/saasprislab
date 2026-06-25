# AI Coordination Status

Fecha: 2026-06-23

## Estado actual

- La herramienta canónica de verificación humana de UI ya existe:
  - [tools/run_human_ui_audit.mjs](../../tools/run_human_ui_audit.mjs)
  - [run_human_ui_audit.bat](../../run_human_ui_audit.bat)
- La documentación de uso está en:
  - [PROCEDIMIENTO_VERIFICACION_HUMANA_UI.md](./PROCEDIMIENTO_VERIFICACION_HUMANA_UI.md)
- La regla de cierre técnico está en:
  - [ESTANDAR_TESTEABILIDAD_AUDITABILIDAD.md](./ESTANDAR_TESTEABILIDAD_AUDITABILIDAD.md)
- El flujo canónico de tareas está en:
  - [NEXT_ACTIONS.md](./NEXT_ACTIONS.md)
- El indice maestro completo está en:
  - [INDICE_CANONICO_TOTAL.md](./INDICE_CANONICO_TOTAL.md)
- Los pendientes canónicos están en:
  - [PENDIENTES_CANONICOS.md](./PENDIENTES_CANONICOS.md)
- El inventario físico del repo está en:
  - [INVENTARIO_CANONICO_REPO.md](./INVENTARIO_CANONICO_REPO.md) (historico / estructural)
  - [INVENTARIO_REAL_REPO.md](./INVENTARIO_REAL_REPO.md)
  - [INVENTARIO_UNIFICADO_RECONCILIADO_2026-06-24.md](./INVENTARIO_UNIFICADO_RECONCILIADO_2026-06-24.md)
  - [ESTADO_TESTS_LLM_Y_CAP5_2026-06-24.md](./ESTADO_TESTS_LLM_Y_CAP5_2026-06-24.md)

## Primer resultado validado

Se ejecutó la herramienta por primera vez contra producción con salida correcta:

- Target: `cloud`
- Base URL: `https://prislab.labcorecloud.com`
- Resultado: `ok: true`
- Hallazgos: `0`
- Artefactos:
  - `auditoria_ui_20260623_194820/report.json`
  - `auditoria_ui_20260623_194820/report.md`
  - `auditoria_ui_20260623_194820/screenshots/`

## Segundo resultado validado

Se ejecutó la herramienta con credenciales reales de prueba (`admin`) contra producción y quedó limpia:

- Target: `cloud`
- Base URL: `https://prislab.labcorecloud.com`
- Usuario: `admin`
- Resultado: `ok: true`
- Hallazgos: `0`
- Artefactos:
  - `auditoria_ui_20260623_212952/report.json`
  - `auditoria_ui_20260623_212952/report.md`
  - `auditoria_ui_20260623_212952/screenshots/`

## Cierres tecnicos integrados por Codex

### Consultorio - tenant efectivo en PDFs

- estado: `CERRADO`
- commit local Codex: `b9217b9`
- archivos:
  - `consultorio/pdf_views.py`
  - `consultorio/pdf_views_prislab.py`
  - `consultorio/tests.py`
  - `consultorio/test_pdf_tenant.py`
- resultado:
  - las rutas PDF vivas de Consultorio ya usan `empresa_efectiva_request(request)`
  - se corrigio la estructura rota de tests del modulo
  - una regresion nueva detecto y permitio corregir un bug real en `imprimir_expediente_forense`
- evidencia:
  - `py_compile OK`
  - `manage.py check OK`
  - `manage.py test consultorio --keepdb -v 1` -> `41 OK`

### Director + IA/PRIS - zona horaria local

- estado: `CERRADO`
- commit local Codex: `d26a09d`
- archivos:
  - `core/views/war_room.py`
  - `core/views/ia_dashboard.py`
  - `core/views/pris_ia.py`
  - `core/views/pris_jarvis.py`
  - `core/agent/pris_tools_operativos.py`
  - `core/ai_brain.py`
  - `core/views/ranking.py`
  - `core/views/incidencias.py`
  - `core/tests/test_director_dashboard_tz.py`
  - `core/tests/test_ia_pris_tz.py`
- resultado:
  - se reemplazo el patron UTC `timezone.now().date()` por `localdate()` en el alcance Director/IA/PRIS que seguia vivo en esta rama
  - se agregaron regresiones reales para dashboard Director y KPI IA/PRIS
- evidencia:
  - `py_compile OK`
  - `manage.py check OK`
  - `manage.py test core.tests.test_director_dashboard_tz core.tests.test_ia_pris_tz core.tests.test_finanzas_caja_tz -v 1` -> `3/3 OK`

## Ultima verificacion recibida de Claude

Se recibio un cierre de evidencia adicional sobre la tanda de seguridad / tests:

- `SEC-2FA` quedo verificado con la regla actual: `127.0.0.1` y `192.168.*` ya no exentan por defecto.
- La suite global reportada por Claude quedo mayormente verde:
  - `315` tests
  - `297` OK
  - `14` skipped
  - `2` errores de entorno/herramienta
- Consultorio quedo validado inicialmente con `36/36` tests OK.
- Farmacia quedo validada con `18/18` tests OK.
- La superficie IA quedo con `3` tests OK y placeholders claramente marcados.
- Pendiente real detectado por esa misma tanda:
  - contradiccion de aislamiento LIMS en `test_lims_config_tenant_security.py`
  - `api_rangos_parametro` expone datos cross-tenant en un caso de prueba
  - la configuracion LIMS necesita root-cause antes de darlo por cerrado
- Artefacto persistido:
  - [docs/ai_coordination/inbox/20260624_claude_SEC_2FA_TESTS_LIMS.md](./inbox/20260624_claude_SEC_2FA_TESTS_LIMS.md)

Nota de reconciliacion:

- el reporte de Claude sobre Director/IA/PRIS apuntaba a una PR separada; Codex confirmo que ese fix no estaba integrado en `release/v1.0-local` y lo reaplico/valido localmente en el arbol canonico actual
- el reporte viejo que decia que `INDICE_CANONICO_TOTAL.md` o `INVENTARIO_MAESTRO_TOTAL.md` no existian ya no aplica al estado actual del repo

## Verificacion de contrapeso sobre Core

Se reviso el reporte de Cascada sobre `core/middleware/pris_context.py` y el fix queda aprobado:

- el archivo real ya usa import lazy con fallback seguro
- `manage.py check` pasa sin issues
- la correccion valida es la resiliencia por-request ante fallos de `get_pris_context`
- la explicacion del riesgo en el reporte original se ajusto para no confundir fallo de arranque con fallo runtime
- artefacto persistido:
  - [docs/ai_coordination/inbox/20260624_cascada_CORE_PRIS_CONTEXT.md](./inbox/20260624_cascada_CORE_PRIS_CONTEXT.md)

## Revalidacion humana UI mas reciente

Se ejecuto nuevamente el runner humano en produccion y esta corrida reporto una falla de login:

- `ok: false`
- `findingsCount: 1`
- hallazgo: `Login did not redirect to a protected area`
- artefacto persistido:
  - [docs/ai_coordination/inbox/20260624_ui_rerun_login_fail.md](./inbox/20260624_ui_rerun_login_fail.md)

Nota:

- La corrida sigue confirmando que la raiz y el dashboard abren sin 500.
- La falla nueva queda como pendiente de revalidacion porque puede ser credencial/sesion/anti-automation o una regresion de login.

## Diagnostico adicional de login

Se valido que la causa no es 2FA:

- `admin` existe y esta activo
- `TOTP_ACTIVE = False`
- `2FA_FLAG = False`
- `authenticate(username='admin', password='[redacted]')` devolvio `False`

Conclusion:

- la credencial usada para la revalidacion no coincide con la base actual
- `/home/` sigue respondiendo `302` hacia `/login/`
- el problema reproducido es de autenticacion/credencial, no de 500 directo en `/home/`
- artefacto persistido:
  - [docs/ai_coordination/inbox/20260624_login_admin_invalid.md](./inbox/20260624_login_admin_invalid.md)

## Canonical host - normalizacion de dominio

Se alineo el middleware de host canonico para que deje de depender de valores hardcodeados y use entorno real:

- `PRISLAB_CANONICAL_HOST` ahora puede definir el host publico canónico
- `PRISLAB_LEGACY_HOSTS` permite listar hosts antiguos a redirigir
- `CSRF_TRUSTED_ORIGINS` recibe automaticamente el origen canonico cuando falta en produccion

Esto corrige el caso en el que el navegador normal y el modo incognito se comportaban distinto por host/cookie/cache de dominio.

Artefacto persistido:

- [core/middleware/canonical_host.py](../../core/middleware/canonical_host.py)
- [config/settings.py](../../config/settings.py)

## Verificacion humana UI - corrida limpia

Se ejecuto una corrida humana automatizada contra produccion con resultado general `OK`:

- login autenticado y redirigido correctamente
- `/` y `/home/` abrieron sin `500`
- Laboratorio acepto texto en el buscador
- Farmacia acepto texto en el buscador
- solo quedaron dos `WARN` de deteccion visual:
  - Consultorio: no se detecto boton de accion de cita en la pantalla inicial
  - Director: la pagina abrio, pero el runner no encontro una accion clave

Artefacto persistido:

- [docs/ai_coordination/inbox/20260624_human_ui_audit_ok.md](./inbox/20260624_human_ui_audit_ok.md)

## LIMS tenant - ajuste de causa raiz

El reporte nuevo de Claude apunta a que el supuesto cross-tenant no era fuga real de datos:

- el filtro por empresa funcionaba
- `lims.views.tenant_lims.empresa_lims()` ahora solo usa la FK explícita del usuario
- `Usuario.save()` ya no auto-asigna empresa por defecto
- `core.tests.test_lims_config_tenant_security` quedó verde (`5/5`)
- Sentinel conserva la degradación para otros errores, pero `Http404` vuelve a responder como `404`

- la contradicción canónica de "usuario sin empresa" quedó cerrada para LIMS

Artefacto persistido:

- [docs/ai_coordination/inbox/20260624_lims_tenant_404_masking.md](./inbox/20260624_lims_tenant_404_masking.md)

## Ruido benigno conocido

- La consola puede mostrar errores de WebSocket contra `localhost` o `localhost.qz.io` por el servicio de impresión/QZ.
- Ese ruido ya se filtró en la herramienta canónica y no debe contarse como hallazgo funcional de negocio.

## Regla de uso

- Todo módulo, flujo y función del canon debe poder probarse y auditarse con evidencia reproducible.
- Si no existe prueba automática, runner humano o evidencia técnica verificable, el tema queda pendiente.
- La verificación humana se ejecuta primero con la herramienta canónica.
- Las IAs leen el `report.md` o `report.json` y luego comparan evidencia.
- No se debe depender de extensiones de navegador para cerrar un flujo.
- No se debe reauditar sin nueva evidencia.
- Si algo no está reflejado en `INDICE_CANONICO_TOTAL.md`, no es fuente de verdad para coordinación.
- Si algo no está reflejado en `INVENTARIO_REAL_REPO.md`, no fue parte del corte ejecutable actual.
- Si algo quedó solo en una lectura estructural externa, debe persistirse antes de usarlo como canon.

## Limpieza de ruido documental

- Los reportes, scripts y notas históricas fuera del canon actual están siendo retirados del árbol de trabajo.
- Lo que queda como `D` en `git status` corresponde a ruido viejo ya separado del canon operativo.
- No debe volver a mezclarse con el flujo nuevo salvo que una instrucción explícita lo reabra.

## Orden operativo

1. Humano ejecuta `npm run human:ui -- --target cloud --user <usuario> --pass <clave>`.
2. Se revisa el `report.md` generado.
3. Codex corrige si hay fallos de código.
4. Claude y Cascada clasifican y contrastan reportes nuevos.
5. Se actualiza el estado canónico solo con evidencia nueva.
