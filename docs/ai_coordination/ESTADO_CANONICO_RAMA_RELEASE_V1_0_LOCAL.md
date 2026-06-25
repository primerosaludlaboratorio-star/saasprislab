# Estado Canonico de PRISLAB SaaS

Fecha de consolidacion: 2026-06-25  
Rama canonica: `release/v1.0-local`

## Proposito

Este documento existe para que Copilot, Claude, Cascada y Codex lean una sola verdad.

Todo reporte nuevo debe contrastarse contra la rama `release/v1.0-local` y no contra snapshots viejos o ramas vacias.

## Lectura obligatoria

1. `CHECKLIST_CONTROL_PRISLAB.md`
2. `REPORTE_COMPLETO_PARA_CLAUDE_2026-06-18.md`
3. `AI_COORDINATION_STATUS.md`
4. `docs/ai_coordination/GUIA_OPERATIVA_FINAL.md`
5. `docs/ai_coordination/PROTOCOLO_AUDITORIA_MULTI_IA_PRISLAB.md`
6. `docs/ai_coordination/PROCEDIMIENTO_VERIFICACION_HUMANA_UI.md`

## Estado real confirmado

- La rama `release/v1.0-local` es la linea vigente de trabajo.
- El historial reciente incluye el fix `650f1ef` para analisis globales y acceso a expediente de director.
- El historial reciente incluye `c802eb5` para endurecer 2FA y caducidad de resultados publicos.
- El historial reciente incluye `a7b0d8b` para blindar el auto-repair de Sentinel por tenant.
- No debe usarse `main` como fuente de verdad operativa.

## Modulos cerrados en esta linea de trabajo

- Consultorio PDF / tenant efectivo -> `RESUELTO`
- Director -> `RESUELTO`
- IA/PRIS (timezone local en el alcance Director/IA/PRIS) -> `RESUELTO`
- Pacientes (alta de paciente / form / template faltante) -> `RESUELTO`
- Laboratorio (flujo funcional principal) -> `RESUELTO` con deuda arquitectonica legacy/LIMS documentada
- Enfermeria -> `RESUELTO`
- Inventario -> `RESUELTO`

## Modulos casi cerrados en esta linea de trabajo

- Farmacia -> `ESTABILIZADO`, con deuda menor y cobertura faltante en algunos flujos
- Logistica -> `ESTABILIZADO`, pendiente de cierre canonico final
- Mantenimiento -> `ESTABILIZADO`, pendiente de cierre canonico final
- Bienestar -> `ESTABILIZADO`, pendiente de cierre canonico final
- Academia -> `ESTABILIZADO`, pendiente de cierre canonico final
- Marketing -> `ESTABILIZADO`, pendiente de cierre canonico final

## Modulos que siguen abiertos

- Buzon / Comunicacion / Notificaciones
- Seguridad
- RH / Nomina
- Contabilidad
- Operaciones
- Recepcion

## Hallazgos que siguen vigentes

### Consultorio PDF / tenant efectivo

Estado actual del codigo:

- `consultorio/pdf_views_prislab.py` ya usa `empresa_efectiva_request(request)` en las rutas vivas `pdf_receta_paciente` y `api_receta_pdf`
- `consultorio/pdf_views.py` ya usa `empresa_efectiva_request(request)` en `imprimir_expediente_forense`
- existe regresion dedicada en `consultorio/test_pdf_tenant.py`
- la suite del modulo queda verde en el arbol actual: `manage.py test consultorio --keepdb -v 1` -> `41 OK`

Conclusion:

- RESUELTO — no reabrir salvo evidencia nueva de fuga tenant en rutas PDF de consultorio

### Director + IA/PRIS timezone UTC/local

Estado actual del codigo:

- `war_room.py`, `ia_dashboard.py`, `pris_ia.py`, `pris_jarvis.py`, `pris_tools_operativos.py`, `ai_brain.py`, `ranking.py` e `incidencias.py` ya usan fecha local del proyecto en el alcance Director/IA/PRIS
- regresiones presentes:
  - `core/tests/test_director_dashboard_tz.py`
  - `core/tests/test_ia_pris_tz.py`
  - `core/tests/test_finanzas_caja_tz.py`

Conclusion:

- RESUELTO — no reabrir el bug de KPIs/tableros nocturnos en Director/IA/PRIS sin repro nueva contra esta rama

### Pacientes - formulario de alta y template faltante

Estado actual del codigo:

- `pacientes/views.py` ya usa campos reales del modelo en `PacienteForm`
- `pacientes/templates/pacientes/crear_paciente.html` ya existe
- la suite del modulo valida el flujo principal de alta/listado/busqueda

Conclusion:

- RESUELTO — no reabrir el bug de alta de pacientes salvo repro nueva contra esta rama

### Farmacia - fixes post-refactor ya integrados

Estado actual del codigo:

- `farmacia/urls.py` ya consolida `api/lotes-producto` sobre la implementacion de `pdv.py`
- `farmacia/views/soporte.py` ya filtra apertura de caja por `empresa`
- `farmacia/views/__init__.py` ya corta `KardexListView` con `objects.none()` cuando no hay empresa
- `farmacia/views/pdv.py` ya usa `_empresa_desde_request(request)` en `pdv_farmacia`
- la suite de modulo reportada queda verde: `31 OK`

Conclusion:

- ESTABILIZADO / CASI_CERRADO — no reabrir los 4 hallazgos ya corregidos
- mantener como deuda menor la inconsistencia baja de `autorizar_devolucion` y la cobertura faltante de algunos flujos

### Enfermeria - cierre con pruebas reales

Estado actual del codigo:

- `enfermeria/tests.py` cubre rutas, vistas, formularios y aislamiento por tenant
- el reporte tecnico del modulo ya fue persistido en `docs/ai_coordination/reporte_auditoria_enfermeria.md`

Conclusion:

- RESUELTO — no reabrir Enfermeria sin evidencia nueva contra esta rama

### Inventario - cierre por bugs reales y pruebas verdes

Estado actual del codigo:

- los `Coalesce(Sum(...), Value(...))` del modulo ya usan salida decimal consistente
- `lista_lotes.html` ya consume `lote.semaforo` sin usar atributos privados prohibidos en templates
- `inventario/models.py` ya expone la propiedad publica `semaforo`
- existe suite dedicada `inventario/tests/test_inventario.py` con cobertura del flujo operativo principal

Conclusion:

- RESUELTO — no reabrir Inventario salvo repro nueva contra esta rama

### Bloque operativo parcial - Logistica / Mantenimiento / Bienestar / Academia / Marketing

Estado actual del codigo y evidencia reportada:

- logistica reporta `7/7` pruebas verdes y scoping operativo estabilizado
- mantenimiento reporta `4/4` pruebas verdes y consultas aisladas por empresa
- bienestar reporta `4/4` pruebas verdes y guards de empresa/permisos aplicados
- academia reporta `8/8` pruebas verdes con regresiones de aislamiento cross-tenant
- marketing reporta `9/9` pruebas verdes con bloqueo de `empresa=None`

Conclusion:

- ESTABILIZADOS / CASI_CERRADOS — no tratarlos como modulos criticos abiertos, pero tampoco inflar un `100% cerrado` hasta completar el mismo nivel de contraste canonico sobre el arbol final

### Recepcion - pendiente de cierre definitivo

Estado actual:

- el reporte operativo indica mejoras reales de validacion/redirects
- aun no queda asentado en el canon con el mismo nivel de evidencia de pruebas explicitas que los otros modulos del bloque

Conclusion:

- PENDIENTE DE CIERRE DEFINITIVO — no elevarlo a abierto critico, pero tampoco marcarlo como cerrado total todavia

## Verificacion humana de interfaz

- Si la extensión de Claude, Copilot u otra IA no responde, la verificación de UI no se detiene.
- El flujo de validación humana debe seguir el documento `docs/ai_coordination/PROCEDIMIENTO_VERIFICACION_HUMANA_UI.md`.
- Las verificaciones funcionales de navegador hechas por IA son apoyo, no sustituto del usuario humano.

### 1. 2FA

Archivo:

- `core/views/autenticacion_2fa.py`

Hallazgo:

- el bypass generico por `192.168.*` / `10.*` ya no existe
- el bypass por `127.0.0.1` solo aplica en `DEBUG`
- en produccion solo exenta IPs/CIDRs explicitas declaradas en `IPS_INTERNAS_2FA_BYPASS`
- el riesgo real ahora depende de la configuracion explicita del VPS, no de un bypass hardcoded

### 2. Resultados publicos

Archivo:

- `core/views/entrega_resultados.py`

Hallazgo:

- los tokens publicos ahora usan una caducidad configurable
- default actual: 7 dias via `RESULTADOS_PUBLICOS_TOKEN_MAX_AGE_SECONDS`
- el comentario viejo de "30 dias" ya no describe el comportamiento real

### 3. Sesiones

Archivo:

- `config/settings.py`

Hallazgo:

- `SESSION_COOKIE_AGE` sigue con default de 30 dias
- `SESSION_EXPIRE_AT_BROWSER_CLOSE = False`
- `SESSION_SAVE_EVERY_REQUEST = True`
- `SECURE_SSL_REDIRECT` queda forzado en produccion, pero el default base sigue siendo `False`
- esto es una decision de negocio/operacion, no un bug; si se quiere endurecer, debe bajar por env var

### 4. Sentinel

Archivos:

- `core/views/sentinel_api.py`
- `core/middleware/sentinel.py`
- `core/services/auto_repair.py`

Hallazgo:

- ya no depende de `SECRET_KEY` como fallback
- el reporte viejo de `admin_token` por GET ya no describe el estado actual
- el auto-repair de permisos ya no debe regenerar sesion para superuser sin empresa
- sigue habiendo hardening y revisiones pendientes, pero no ese vector viejo

## Hallazgos desactualizados

### P2 Director Analizadores

Estado actual del codigo:

- `core/views/director.py` ya usa `Equipo.objects.all()`
- `laboratorio.models.Equipo` sigue siendo un catalogo global

Conclusion:

- el `FieldError` reportado por versiones anteriores ya no aplica al estado actual de la rama
- debe tratarse como `resuelto/obsoleto` en esta linea de trabajo

### H3 Medico Expediente

Estado actual del codigo:

- `core/views/expediente.py` ya permite acceso a `DIRECTOR`, `ADMIN`, `ADMINISTRADOR`, `GERENTE` y `MEDICO`
- Sentinel limita reintentos 403

Conclusion:

- no debe seguir etiquetandose como `loop infinito` sin repro actual
- si alguien quiere reabrirlo, debe reproducirse contra esta rama actual y con paciente real

### Auto-repair Sentinel / Tenant

Estado actual del codigo:

- `core/services/auto_repair.py` ya bloquea la regeneracion automatica cuando `user.empresa` es `None`
- superuser sigue pudiendo recuperarse solo dentro de su tenant valido

Conclusion:

- bypass real cerrado en `a7b0d8b`
- Sentinel ya no debe usarse para saltarse la obligacion de empresa

### H1 Farmacia 301

Estado actual del codigo:

- el reporte venia de una ruta legacy de auditoria
- el endpoint real de farmacia usa la ruta API correcta

Conclusion:

- es falso positivo de auditor legacy

### H2 Auditoria Lab deprecated

Estado actual del codigo:

- `auditoria_lab_full.py` sigue siendo deprecated a proposito

Conclusion:

- es deuda de herramienta, no bug de producto

### Sentinel loops criticos (S2, S3)

Estado actual del codigo:

- `core/middleware/sentinel.py` usa cache `retries < 1` para cortar el loop en el primer reintento
- `PermissionDenied` y response 403 usan caches separados; no se solapan
- tests en `core/tests/test_auto_repair_tenant_guard.py` verifican el corte

Conclusion:

- RESUELTO — no reabrir salvo evidencia nueva de loop reproducible

### Devoluciones cruzadas (financiero)

Estado actual del codigo:

- `core/services/ventas/venta_farmacia_service.py` suma `_total_devuelto_core + _total_devuelto_erp` antes de autorizar
- el bloqueo financiero impide doble devolucion entre ambos arboles funcionales
- la coexistencia de dos implementaciones (`core/views/farmacia.py` y `farmacia/views/soporte.py`) sigue como decision arquitectonica pendiente

Conclusion:

- RESUELTO a nivel financiero — no reabrir como bug
- la coexistencia arquitectonica es decision de negocio, no hallazgo de seguridad

### H-GEN1 RECEPCION divergencia grupo vs campo rol

Archivo:

- `core/views/general.py` lineas 260-261 y 288

Hallazgo:

- grupo `RECEPCION` redirige a `consultorio:tablero_recepcion` (agenda medica)
- campo `rol='RECEPCION'` redirige a `recepcion_lab` (laboratorio)
- ambos destinos validan empresa; no hay bypass de seguridad

Conclusion:

- DECISION ARQUITECTONICA PENDIENTE — no es bug
- corresponde a M2 del cierre 2026-06-19; requiere decision de diseno sobre sincronizacion grupo/campo rol
- no reabrir como hallazgo de seguridad

### H-SOP1a buscar_venta_para_devolucion sin user_passes_test

Archivo:

- `farmacia/views/soporte.py` linea 94

Hallazgo:

- solo `@login_required`; empresa validada internamente; query scoped por empresa
- cualquier usuario autenticado con empresa puede buscar ventas pero no procesarlas

Conclusion:

- DISENO INTENCIONAL — la separacion buscar/procesar es deliberada por UX
- no es bypass

### H-SOP1b autorizar_devolucion orden de validacion inconsistente

Archivo:

- `farmacia/views/soporte.py` lineas 383-392

Hallazgo:

- valida grupo DIRECTOR antes de validar empresa
- usuario con grupo DIRECTOR sin empresa pasa el check de rol y solo se bloquea en la linea siguiente
- no es bypass real porque el bloqueo existe; el patron es inconsistente con `_es_gerente_o_admin`

Conclusion:

- INCONSISTENCIA PROBABLE de baja severidad
- candidato a alinearse con el patron canonico en futura iteracion
- no elevar a bypass; no requiere fix urgente

### N1 administracion_usuarios superuser cross-tenant

Archivo:

- `core/views/administracion_usuarios.py` lineas 26-29, 136-137

Hallazgo:

- superuser sin empresa puede obtener y editar usuarios de cualquier tenant
- bloqueo de reasignacion de empresa existe (linea 142-148) pero no el acceso cross-tenant a otros campos
- mismo patron que `auto_repair.py` antes de `a7b0d8b`

Conclusion:

- ARQUITECTONICO de severidad media — decision de diseno actual: superuser es global
- sin evidencia de superuser descontrolado en produccion; no es bypass activo
- inconsistente con patron canonico post-`a7b0d8b`; candidato a alinear en futura iteracion
- no reabrir como bypass salvo superuser sin empresa confirmado en produccion

### N3 configuracion.py alias ADMINISTRADOR no contemplado

Archivo:

- `core/views/configuracion.py` linea 24

Hallazgo:

- `_puede_administrar_configuracion` acepta `ADMIN` y `DIRECTOR` pero no `ADMINISTRADOR`
- el alias `ADMINISTRADOR` si existe en `general.py` linea 282

Conclusion:

- INCONSISTENCIA PROBABLE de baja severidad — misma clase que H-SOP1b
- candidato a alinear en futura iteracion; no es bypass

## Cobertura de auditoria 2026-06-23

Cobertura al corte actual:

- hay modulos ya cerrados tecnicamente, otros casi cerrados y otros todavia abiertos
- Inventario ya forma parte del bloque de modulos cerrados con evidencia tecnica y pruebas
- no debe afirmarse que todo el arbol esta cerrado; el canon vigente ya reconoce pendientes reales en Buzon/Comunicacion/Notificaciones, RH/Nomina, Contabilidad, Seguridad, Operaciones y Recepcion
- los documentos Markdown no son tratados como hallazgos de seguridad por si mismos

Pendientes arquitectonicos documentados (no bugs):
- H-GEN1: divergencia grupo/rol RECEPCION — decision de diseno
- N1: superuser cross-tenant en administracion_usuarios — decision de diseno
- H-SOP1b / N3: orden de validacion y alias de rol — inconsistencias probables de baja severidad

Para reabrir cualquier frente se requiere reproduccion concreta contra esta rama.

## Linea operativa para Copilot

- usar esta rama como verdad
- si un reporte contradice este documento, primero revisar el codigo actual
- no reabrir bugs viejos sin reproduccion en `release/v1.0-local`
- cuando haya hallazgo real nuevo, citar archivo, linea y evidencia tecnica
