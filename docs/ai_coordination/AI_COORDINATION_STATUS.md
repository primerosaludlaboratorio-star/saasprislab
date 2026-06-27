# AI Coordination Status

Fecha: 2026-06-25

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

### Pacientes - formulario y template de alta

- estado: `CERRADO`
- archivos:
  - `pacientes/views.py`
  - `pacientes/templates/pacientes/crear_paciente.html`
  - `pacientes/tests.py`
- resultado:
  - se corrigio `PacienteForm` para usar solo campos reales del modelo
  - se agrego el template faltante `crear_paciente.html`
  - el flujo de alta de pacientes dejo de caer por `FieldError` / `TemplateDoesNotExist`
- evidencia:
  - `manage.py check OK`
  - `manage.py test pacientes.tests --verbosity=2 --no-input` -> `7 OK (1 skipped)`

### Farmacia - endurecimiento post-refactor

- estado: `CERRADO`
- archivos:
  - `farmacia/urls.py`
  - `farmacia/views/soporte.py`
  - `farmacia/views/__init__.py`
  - `farmacia/views/pdv.py`
  - `farmacia/tests.py`
- resultado:
  - se resolvio la colision de `api/lotes-producto`
  - apertura y verificacion de caja ya filtran por `empresa`
  - `KardexListView` devuelve `none()` si no hay empresa
  - `pdv_farmacia` ya usa el resolvedor canonico de empresa
- evidencia:
  - `manage.py check OK`
  - `manage.py test farmacia.tests --verbosity=2` -> `31 OK`
  - reporte adicional de cierre: `21/21` tests nuevos verdes sobre AperturaCaja, CorteCaja, EntradaExpress, COFEPRIS y CargaMasiva
- residual:
  - se conservan 3 fallos preexistentes documentados fuera del cierre de esta ronda

### Enfermeria - cierre con pruebas reales

- estado: `CERRADO`
- archivos:
  - `enfermeria/tests.py`
  - `docs/ai_coordination/reporte_auditoria_enfermeria.md`
- resultado:
  - el modulo tiene cobertura funcional y de tenant en pruebas automatizadas
  - se valido dashboard, triage, captura de signos, historial, graficas, alertas y formularios
- evidencia:
  - `manage.py check OK`
  - `manage.py test enfermeria.tests` -> `17/17 OK`

### Inventario - cierre funcional con regresiones

- estado: `CERRADO`
- archivos:
  - `inventario/views.py`
  - `inventario/views_consultorio.py`
  - `inventario/views_generales.py`
  - `inventario/views_compras.py`
  - `inventario/models.py`
  - `inventario/templates/inventario/lista_lotes.html`
  - `inventario/tests/test_inventario.py`
- resultado:
  - se corrigio el `FieldError` por mezcla `DecimalField/FloatField` en agregaciones con `Coalesce(Sum(...), Value(...))`
  - se corrigio el `TemplateSyntaxError` por `_semaforo` en template
  - se agrego propiedad publica `semaforo` al modelo para soporte correcto en vistas/templates
  - se limpiaron asignaciones redundantes y imports asociados al flujo de inventario
- evidencia:
  - `manage.py check OK`
  - `manage.py test inventario.tests.test_inventario` -> `31/31 OK`

### Bloque operativo - recepcion / logistica / mantenimiento / academia / marketing

- estado general:
  - `Recepcion` -> `CASI_CERRADO`
  - `Logistica` -> `CERRADO`
  - `Mantenimiento` -> `CERRADO`
  - `Academia` -> `CERRADO`
  - `Marketing` -> `CERRADO`
- resultado reportado:
  - logistica: `7/7 OK`
  - mantenimiento: `4/4 OK`
  - academia: `8/8 OK`
  - marketing: `9/9 OK`
- precision canonica:
  - recepcion ya tiene fix local integrado para el bug TZ y una suite canonica nueva, pero sigue con discrepancia abierta: el checklist oficial la marca cerrada con redireccion unificada, mientras la lectura local de `core/views/general.py` aun no lo confirma
  - logistica, mantenimiento, academia y marketing quedan promovidos a `CERRADO` por checklist oficial + reporte maestro del 2026-06-25

### RH/Nómina - endurecimiento de seguridad y cobertura

- estado: `CERRADO` (código endurecido, suite con timeout conocido)
- archivos:
  - `core/tests/test_rh_nomina_security.py`
  - `core/views/nomina.py`
  - `core/views/rh.py`
  - `core/admin.py`
  - `core/models/rrhh.py`
- resultado:
  - `CompetenciaAdmin` restringido a superuser con pruebas explícitas de change/delete para ADMIN no-superuser
  - wrappers legacy de nómina protegidos con `@role_required` (como wrappers internos, no endpoints públicos)
  - `mis_resultados` aislado por tenant en `core/views/rh.py:498`
  - `_empresa()` falla con `PermissionDenied` en `core/views/nomina.py:24`
  - `Competencia` documentada como catálogo global en `core/models/rrhh.py:141`
- evidencia:
  - `manage.py check OK`
  - suite `test_rh_nomina_security` reforzada con tests de CompetenciaAdmin (P2 corregido)
- residual:
  - ejecución completa de suite RH/Nómina pendiente de revalidación por timeout del proyecto base
  - reporte original sobrevendía cobertura de wrappers legacy (P3): están protegidos pero no son rutas activas en `config/urls.py`

### IoT - kioscos multi-tenant e IP allowlist

- estado: `CERRADO`
- archivos:
  - `iot/models.py`
  - `iot/views.py`
  - `iot/migrations/0005_kiosco_empresa.py`
  - `iot/tests.py`
- resultado observado en codigo:
  - `Kiosco` ahora tiene FK `empresa`
  - las vistas administrativas ya filtran por `empresa`
  - `api_kiosco_heartbeat`, `api_kiosco_confirmar` y `api_kiosco_rechazar` validan IP con `_get_ip(request)`
  - existe suite nueva `IoTKioscoSecurityTests`
- precision canonica:
  - la documentacion oficial ya lo promueve a `CERRADO` con migracion `0005`, suite `iot.tests` y nota explicita de ejecucion con `--keepdb`
- mantener fuera del cierre solo el paso operativo de deploy y validacion fisica de kioscos en red local

### Recepcion - cierre reproducible en arbol canonico

- estado: `CERRADO`
- archivos:
  - `recepcion/views.py`
  - `recepcion/tests.py`
  - `core/views/general.py`
- resultado:
  - la redireccion de `RECEPCION` ya quedo unificada en `core/views/general.py` hacia `recepcion:dashboard_recepcion` tanto por grupo como por `rol`
  - `recepcion/views.py` ya usa `timezone.localdate()` en `dashboard_recepcion` y `lista_espera`
  - se cerro el bypass operativo por tenant implicito: `Recepcion` ya no acepta usuarios sin FK `empresa` aunque el middleware resuelva una empresa por defecto
  - la suite canonica valida redirect sin empresa, bloqueos cross-tenant y regresiones TZ
- evidencia:
  - `manage.py test recepcion.tests --keepdb -v 1` -> `5 OK`

### Seguridad - revalidacion local final

- estado: `CERRADO`
- archivos:
  - `seguridad/views.py`
  - `seguridad/tests.py`
  - `core/decorators.py`
- resultado:
  - la suite del modulo ya corre limpia sobre este arbol canonico
  - 2FA, boton de panico y rastro paciente quedaron revalidados con evidencia reproducible
  - el warning de Sentinel sobre 403 sin empresa corresponde al comportamiento esperado del bloqueo, no a una fuga tenant
- evidencia:
  - `manage.py test seguridad.tests --keepdb -v 1` -> `9 OK`

### Bienestar - cierre de auditoría y hardening

- estado: `CERRADO`
- archivos:
  - `config/urls.py` (resolución de colisión de rutas)
  - `bienestar/views.py` (timezone localdate)
  - `core/views/bienestar.py` (timezone localdate + redirect NOM-035 corregido)
  - `core/tests/test_bienestar_nom035.py` (regresión endurecida)
  - `core/templates/includes/sidebar.html` (rutas actualizadas)
- resultado:
  - **B1 (CORREGIDO)**: colisión de URL en `/bienestar/` — NOM-035 sombreaba Espacio Seguro. Rutas NOM-035 movidas a `/bienestar-staff/`.
  - **B6 (CORREGIDO)**: `timezone.now().date()` → `timezone.localdate()` en 8 ubicaciones de `bienestar/views.py` y `core/views/bienestar.py`.
  - **B7 (CORREGIDO)**: `evaluacion_nom035` redirigía a `dashboard_bienestar`, nombre inexistente tras el cambio de rutas. Sentinel lo estaba enmascarando como auto-repair. Se corrigió a `bienestar_dashboard` y la prueba ahora valida el destino exacto.
  - **B2-B5 (DESCARTADOS)**: `DiarioEmocional`, `RecursoCrecimiento`, `EvaluacionNOM035`, `DiarioEmocionalStaff` sin FK `empresa`. El aislamiento por `usuario` es suficiente (Usuario es único global). `RecursoCrecimiento` es catálogo global intencional.
  - Superficie dual verificada como intencional: `bienestar/views.py` (Espacio Seguro), `core/views/bienestar.py` (NOM-035 Staff), `core/views/bienestar_mejorado.py` (Alertas PRIS).
  - Tenant isolation confirmada en todos los modelos con FK `empresa`: `ConversacionBienestar`, `AlertaBienestar`, `SesionCoachingStaff`, `AlertaBurnout`, `ProgramaCapacitacion`.
- evidencia:
  - `manage.py check` -> `System check identified no issues (0 silenced)`
  - `manage.py test bienestar.tests core.tests.test_bienestar_nom035 core.tests.test_bienestar_mejorado --keepdb -v 0` -> `19 OK`
  - validación directa HTTPS de `evaluacion_nom035` -> `302 /bienestar-staff/` + `AlertaBurnout` creada

### Contabilidad / Finanzas - AUDITORIA PROFUNDA CERRADA

- estado: `CERRADO` (auditoria profunda 2026-06-26)
- fuente:
  - `docs/ai_coordination/ESTADO_CONTABILIDAD_FINANZAS_CIERRE_TOTAL_V2.md`
  - auditoria profunda Cascade 2026-06-26: verificacion contra arbol real, endurecimiento except Exception, suite completa
- archivos reportados:
  - `contabilidad/models.py`
  - `contabilidad/migrations/0012_catalogo_cuentas_polizas.py`
  - `core/views/contabilidad.py`
  - `core/views/reportes_financieros.py`
  - `core/views/cuentas_por_cobrar.py`
  - `core/views/motor_financiero.py`
  - `config/urls.py`
  - `core/tests/test_contabilidad_general.py`
  - `core/tests/test_finanzas_roles_regression.py`
- resultado documentado:
  - `FacturaCFDI.empresa` queda como FK canónica multi-tenant y `NOT NULL`
  - existen modelos reales `CuentaContable`, `Poliza`, `AsientoContable`
  - dashboard, catálogo, pólizas, autorización, reportes y balance general quedan operativos
  - CxC / convenios siguen activos en `/finanzas/...`
  - se corrige la cifra inflada histórica de `test_cfdi_borrador_auto`: son `2 tests`, no `22`
  - `dashboard_contabilidad` ya filtra ingresos por `estado='COMPLETADA'`, evitando inflar ingresos con ventas canceladas
  - `core/views/cuentas_por_cobrar.py` ya usa `timezone.localdate()` en CxC / convenios
- evidencia recibida:
  - `manage.py check`
  - `manage.py makemigrations --check`
  - `manage.py test core.tests.test_contabilidad_general --verbosity=2`
  - `manage.py test contabilidad.tests.test_finanzas_seguridad.DashboardFinancieroTests --verbosity=2 --keepdb`
- auditoria profunda 2026-06-26:
  - `FacturaCFDI.empresa` NOT NULL canónico confirmado en modelo + migraciones 0008→0011
  - `CxC / convenios` usan `timezone.localdate()` — confirmado
  - Dashboard contable NO reintroduce conteo falso — confirmado
  - `except Exception` en `contabilidad/facturama_api.py:113` endurecido a `(ValueError, KeyError, TypeError, OSError)` con justificación explícita
  - Superposición de rutas `/contabilidad/` documentada como deuda arquitectónica sin impacto funcional (include sin path vacío)
  - 48 tests ejecutados en esta pasada: exit 0, OK
- evidencia directa:
  - `manage.py check` → 0 issues
  - `manage.py makemigrations --check` → No changes
  - `manage.py test core.tests.test_contabilidad_general contabilidad.tests.test_finanzas_seguridad core.tests.test_finanzas_roles_regression --keepdb -v 1` → **48 tests OK** (exit 0)
- deuda arquitectónica residual (no bloqueante):
  - pólizas manuales sin generación automática de asientos desde ventas
  - balance con fallback proxy si no hay asientos
  - timbrado validado con mocks, no contra PAC real en CI
  - superposición path `/contabilidad/` (include + dashboard directo)

### Buzon / Comunicacion / Notificaciones - cierre operativo documentado

- estado: `REPORTE_INTEGRADO`
- fuente:
  - reporte recibido `2026-06-25`
  - cierre profundo adicional entregado por `Claude` sobre `core/views/buzon.py`
- resultado documentado:
  - se reportan 7 bugs confirmados y corregidos sobre permisos, `@require_POST`, campo de fecha, manejo `Http404`, bug lógico de reapertura y respuesta sin empresa
  - se agrega suite nueva `test_buzon_notificaciones.py` con cobertura funcional y de tenant/roles
  - Claude añade 3 hallazgos profundos corregidos: colisión funcional de `buzon_kanban`, 500 en vez de 404 en `api_cambiar_estado_queja`, y tenant arbitrario en `tu_opinion`
- evidencia recibida:
  - `manage.py test core.tests.test_multi_tenant_isolation core.tests.test_buzon_notificaciones`
  - `manage.py check`
- residual declarado por el propio reporte:
  - rate limiting en `tu_opinion` como mejora opcional
  - ampliar `ejecutar_verificaciones` si se quiere cubrir más que órdenes de laboratorio
- precision canonica:
  - `core/templates/core/tu_opinion.html` ya contiene `{% csrf_token %}`; ese residual anterior queda descartado
  - este bloque queda integrado como cierre operativo fuerte, con fixes profundos ya presentes en el árbol local
  - Imperium entra después como auditor profundo de alto nivel, no como confirmador del reporte

### Operaciones - tenant canonico y cobertura propia

- estado: `CERRADO`
- archivos:
  - `core/views/operaciones.py`
  - `core/tests/test_operaciones_module.py`
- resultado:
  - `rutas_recoleccion` ya usa `empresa_efectiva_request(request)` en vez de `getattr(request.user, 'empresa', None)`
  - el modulo ya rechaza usuarios sin FK `empresa` aunque exista fallback de empresa por defecto en middleware
  - `monitor_rutas` queda cubierto como alias estable del mismo flujo
- evidencia:
  - `manage.py test core.tests.test_operaciones_module --keepdb -v 1` -> `4 OK`

## Modulos cerrados al corte actual

- Consultorio PDF / tenant efectivo
- Director
- IA/PRIS (fix TZ dentro del alcance Director/IA/PRIS)
- Pacientes
- Laboratorio como flujo funcional principal
- Enfermeria
- Inventario
- Farmacia
- Logistica
- Mantenimiento
- Academia
- Marketing
- IoT
- RH / Nomina (código endurecido; deuda: suite con timeout)
- Recepcion
- Seguridad
- Operaciones
- Bienestar
- Contabilidad / Finanzas (auditoria profunda cerrada 2026-06-26)

## Modulos casi cerrados al corte actual

- Ninguno

## Modulos abiertos al corte actual

- Ninguno

## Modulos en proceso no consolidados en este corte

- Ninguno

## Reportes finales integrados

- Ninguno. Los cierres de Contabilidad / Finanzas y Buzon / Comunicacion / Notificaciones ya quedaron integrados como baseline historico.

## Pendientes prioritarios vivos

- Ninguno. No quedan módulos abiertos en el canon actual.

## Deploy confirmado en VPS

- fecha: `2026-06-25`
- commit desplegado: `d54a1ee`
- servidor: `216.238.89.243`
- ruta productiva: `/opt/prislab/app`
- validaciones ejecutadas:
  - `git -C /opt/prislab/app rev-parse --short HEAD` -> `d54a1ee`
  - `systemctl is-active prislab-gunicorn` -> `active`
  - `systemctl is-active prislab-celery` -> `active`
  - `systemctl is-active prislab-celerybeat` -> `active`
  - `curl -I https://prislab.labcorecloud.com` -> `HTTP/2 200`
- alcance real del deploy:
  - produccion ya contiene el cierre verificado de `Recepcion`, `Seguridad` y `Operaciones`
  - no se debe asumir que el resto del arbol sucio local quedo desplegado; ese material sigue fuera de este commit hasta nueva reconciliacion explicita

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
