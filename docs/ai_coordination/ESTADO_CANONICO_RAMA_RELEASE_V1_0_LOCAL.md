# Estado Canonico de PRISLAB SaaS

Fecha de consolidacion: 2026-07-27 (última actualización: auditoría de despliegue y producción)
Rama canonica: `release/v1.0-local`

## Proposito

Este documento existe para que Copilot, Claude, Cascada y Codex lean una sola verdad.

Todo reporte nuevo debe contrastarse contra la rama `release/v1.0-local` y no contra snapshots viejos o ramas vacias.

## Corte vigente 2026-07-27

- Producción está alineada con el checkout local en `6ef947e1c25b6fe797cb6b7a52a0e46100442041`, desplegado por artefacto local VPS.
- Migraciones nuevas `ia.0004` y `laboratorio.0017` aplicadas; Gunicorn, Celery y Celery Beat activos; `/live/`, `/ready/`, `/health/` y `/login/` responden HTTP 200.
- Verificación humana productiva de Farmacia: búsqueda de Paracetamol, selección, selección FEFO de `LOTE-TEST-001`, agregado al carrito y total `$15.00`; consola sin errores ni warnings después del endurecimiento del capturador de teclado.
- Verificación humana productiva de Laboratorio/LIMS: recepción, toma, registro de resultados, control de calidad, entrega, catálogo de analitos y catálogo de estudios cargan correctamente y sin errores de consola.
- El catálogo productivo contiene UREA (`codigo=URE`, numérico) y BUN (`codigo=171`, numérico). El pendiente histórico de UREA/BUN queda cerrado como falso pendiente documental.
- CCI/Westgard sigue abierto porque producción tiene `0` mediciones CCI persistidas; no se fabrican controles, lotes ni resultados clínicos para aparentar cierre.

## Corte de auditoria 2026-07-24

- Laboratorio/LIMS continua `ABIERTO` hasta completar la verificacion humana en produccion; no se declara cerrado solo por pruebas locales.
- La suite focalizada de Laboratorio/LIMS paso `64 tests OK` con `PRISLAB_TEST_NO_MIGRATIONS=1`; `manage.py check` y `makemigrations --check --noinput` tambien pasaron.
- Se corrigio el cierre desde Monitor: ahora genera y adjunta el PDF antes de completar una orden cuando falta, y devuelve `400` controlado sin cambiar el estado si el PDF no puede generarse.
- Se restauro el simbolo de compatibilidad `evaluar_asistencia_clinica_orden` en `core.services.lims.resultados_lims_service` para integraciones y pruebas que lo consumen.
- La prueba `laboratorio.tests.test_cci_lj_postgres_guard` queda marcada como `SKIPPED` en SQLite local; requiere PostgreSQL real para su validacion efectiva.
- Pendiente despues del despliegue: flujo humano productivo de recepcion, toma, captura, validacion, PDF, entrega, rechazo/repeticion, cancelacion/reembolso, calidad y consumo de reactivos/insumos; tambien equipos, impresoras y HL7 fisicos.
- Despliegue completado en produccion con la revision documental `82f26a9`, que incluye el fix funcional `c94b92b`; migraciones sin pendientes, servicios activos y `/health/` correcto.
- Verificacion humana productiva del 2026-07-24: `22` pantallas y rutas de Laboratorio/LIMS navegadas, formulario de nueva orden abierto correctamente y consola del navegador con `0` errores y `0` warnings.
- La navegacion productiva no se contabiliza como cierre E2E: faltan ejecutar con datos QA controlados las operaciones con efectos laterales y las validaciones de equipos, impresoras, HL7 y consumo fisico.

## Lectura obligatoria

1. `CHECKLIST_CONTROL_PRISLAB.md`
2. `REPORTE_COMPLETO_PARA_CLAUDE_2026-06-18.md`
3. `AI_COORDINATION_STATUS.md`
4. `docs/ai_coordination/GUIA_OPERATIVA_FINAL.md`
5. `docs/ai_coordination/PROTOCOLO_AUDITORIA_MULTI_IA_PRISLAB.md`
6. `docs/ai_coordination/PROCEDIMIENTO_VERIFICACION_HUMANA_UI.md`
7. `DESPLIEGUE_UNICO_PRISLAB_VPS_LOCAL.md`

## Estado real confirmado

- La rama `release/v1.0-local` es la linea vigente de trabajo.
- El historial reciente incluye el fix `650f1ef` para analisis globales y acceso a expediente de director.
- El historial reciente incluye `c802eb5` para endurecer 2FA y caducidad de resultados publicos.
- El historial reciente incluye `a7b0d8b` para blindar el auto-repair de Sentinel por tenant.
- No debe usarse `main` como fuente de verdad operativa.
- El commit `2a7fe9d` deshabilita el razonamiento de DeepSeek en las respuestas operativas para evitar que `max_tokens` se consuma antes de entregar `content`.
- El código funcional actual de la rama es `1ea5bcb`; las validaciones locales de Django y PRIS están verdes.
- `1ea5bcb` esta desplegado en produccion mediante artefacto local directo; `/opt/prislab/app/DEPLOYED_REVISION` lo confirma.
- La interfaz productiva muestra PRIS unificada y no muestra `PRIS-Jarvis` ni `Gemini`.
- La bateria humana de PRIS paso cuatro escenarios de orientacion, accion con confirmacion, seguridad y criterio clinico; el navegador no reporto errores ni warnings.

## Modulos cerrados en esta linea de trabajo

- Consultorio PDF / tenant efectivo -> `RESUELTO`
- Director -> `RESUELTO`
- IA/PRIS (timezone local en el alcance Director/IA/PRIS) -> `RESUELTO`
- Pacientes (alta de paciente / form / template faltante) -> `RESUELTO`
- Laboratorio (flujo funcional principal) -> `ABIERTO` hasta completar la matriz humana E2E; el esquema y catálogo LIMS autoritativos ya están disponibles
  - auditoría humana UI en desarrollo del 2026-07-21: login, recepción, toma, captura, validación, PDF y entrega OK para `LAB-20260721-002`; la ruta feliz básica ya persiste y entrega una orden
  - la auditoría posterior en QA cerró con evidencia la creación CxC parcial (`$85/$40/$45`), la cortesía con total/saldo cobrable `$0`, la toma manual 6/6 y el envío a Maquila (`EN_MAQUILA`)
  - QA 2026-07-21 cerró valores fuera de rango con justificación QFB, rechazo/repetición, complemento de pago, cancelación/reembolso y Levey-Jennings básico con 3 fixtures; sigue pendiente Westgard CCI estricto y la segunda auditoría humana completa
  - se corrigió el JSON escapado de `parametros_lista_json` en Control de Calidad; el histórico aceptó `GLUCOSA` lote `QA-GLU-2026` con valores 100/101/99 y desviaciones 0/+1/-1
  - se reemplazó el `prompt()` de validación por diálogo SweetAlert con textarea; el backend bloquea `400 JUSTIFICACION_QC_REQUERIDA` antes de generar PDF y registra la justificación QFB en el detalle
  - Worklist ya envía el `DetalleOrden` correcto al rechazo; Recepción expone el botón de cancelación y genera el movimiento negativo de caja
  - se corrigió `core/services/validador_ia.py` para usar `ResultadoParametro.analito`; el avance de Monitor sin PDF quedó protegido con respuesta `400` controlada en lugar de `500`
  - evidencia: `docs/ai_coordination/inbox/20260721_human_ui_dev_laboratorio.md`
  - revalidado en produccion el 2026-07-20: `preparacion_toma` dejo de caer por el campo obsoleto `firmado` y la orden `LAB-20260720-001` vuelve a abrir cubiculo
  - revalidado en produccion el 2026-07-20: `api_iniciar_toma` y `api_finalizar_toma` persistieron `TomaMuestra` para `LAB-20260720-001` y la orden regreso a `lista-trabajo`
  - revalidado y endurecido el 2026-07-20: la captura de resultados para filas de un solo analito ya envía el valor crudo y la validación no bloquea si falla el storage del PDF
  - revalidado en produccion el 2026-07-20: `ResultadosLimsService` pudo validar la orden `LAB-20260620-001` con `PESO=70`, persistio `ResultadoParametro` y dejo `validado=True` sin romper la transaccion
  - revalidado en produccion el 2026-07-20: la orden `LAB-202607-00005` paso a `RESULTADOS_LISTOS` con `BILIRRUBINA TOTAL=1.2`, se registro consentimiento de prueba y `/laboratorio/imprimir/9/` devolvio PDF real
  - corregido y revalidado en produccion el 2026-07-21: `cancelar_orden`, `rechazar_muestra` y `validar_valor_critico` devuelven `404` JSON para IDs inexistentes, sin `500` ni traza de error interno
  - corregido y revalidado en produccion el 2026-07-21: `etiqueta-termica` y `etiqueta-termica-qr` devuelven PDF valido; la validacion repetida de la orden `9` es idempotente y conserva `RESULTADOS_LISTOS`
  - ejecutado en produccion el 2026-07-21: rechazo de muestra en `LAB-202607-00009` reinicio el detalle a `PENDIENTE_TOMA`; validacion LIMS sin rango legacy en `LAB-202607-00010` devolvio respuesta controlada; cancelacion de `LAB-202607-00011` genero devolucion `GastoCaja=-95.00`
  - segunda auditoria E2E ejecutada en produccion el 2026-07-21: todas las pantallas operativas, APIs de consulta, resultados, tickets, etiquetas, historial de paciente, catalogo LIMS, preordenes y guardas anonimas respondieron conforme al contrato; `qa_auditor` autentico por cliente Django y la orden `9` quedo `ENTREGADO`
  - corregido y revalidado en produccion el 2026-07-21: el historial de pacientes usaba el reverse inexistente `detalle_orden`; ahora usa `detalle_orden_view` y la ruta `/laboratorio/paciente/21/historial/` responde `200`
  - `inventario.signals` dejo de hacer `select_for_update()` sobre el lado nullable de `orden`, evitando el `NotSupportedError` que contaminaba el atomic de laboratorio
  - `core/views/war_room.py` ya usa `core.models.EvaluacionNOM035` y `Sum('total')` para no lanzar errores obsoletos desde el panel lateral
  - revalidado en producción el 2026-07-21: la interfaz autenticada cargó recepción, toma, worklist, captura, entrega, consulta, pacientes, historial válido, monitor, maquila, LIMS y control de calidad; se corrigió y desplegó el JSON autoescapado que rompía JavaScript en control de calidad
  - revalidado en producción el 2026-07-21: la migración `lims.0011_perfilanalito_alter_perfillims_analitos_and_more` estaba pendiente; se aplicó sin borrar catálogos y `/laboratorio/api/estudios/1/parametros/` pasó a `200 application/json` sin `lims_perfilanalito`
  - revalidado en producción el 2026-07-21: el catálogo LIMS autoritativo contiene 101 perfiles y 810 analitos; el catálogo legado de estudios no representa el inventario LIMS operativo
  - revalidado en producción el 2026-07-21: el proceso Gunicorn efectivo tiene HSTS, redirección SSL y cookies seguras activas; los hosts alternos no canónicos son rechazados por `ALLOWED_HOSTS` de forma intencional
  - revalidado en producción el 2026-07-21: las pantallas y PDFs operativos responden; la medición histórica de 2.6–3.3 segundos queda como mejora de rendimiento, no como fallo funcional bloqueante
  - corregido y desplegado en producción el 2026-07-21: tokens públicos inválidos de resultados siguen respondiendo `400`, pero ya no generan traceback; se registran como advertencia controlada
  - corregido y desplegado en producción el 2026-07-21: Maquila solo lista órdenes con `requiere_maquila=True`, exige POST y registra laboratorio externo, guía, notas y fecha en `EnvioMaquila`; una orden QA sin laboratorio fue rechazada y una marcada pasó a `EN_MAQUILA`
  - corregido y desplegado en producción el 2026-07-21: Sentinel ya no crea incidencias para `404` JSON controlados de APIs; una cancelación QA inexistente devolvió `404` sin nueva incidencia
  - corregido y desplegado en producción el 2026-07-21: el resumen IA opcional no intenta llamadas externas ni genera advertencias cuando no hay proveedor configurado; los PDFs siguen generándose
  - corregido y desplegado en producción el 2026-07-21: `api_parametros_estudio` pasó de 32 a 11 consultas en la medición QA mediante `Count('rangos')`, conservando respuesta `200` y 29 parámetros
  - auditoría segura productiva ejecutada el 2026-07-21: `20 OK`, `0 FAIL`; snapshot empresa 1 con 806 analitos, 101 perfiles, 17 paquetes, 13 órdenes y 8 resultados; quedan 2 detalles de órdenes históricas legacy sin llave LIMS, no se modifican por preservar trazabilidad clínica
- Enfermeria -> `RESUELTO`
- Inventario -> `RESUELTO`
- Farmacia -> `RESUELTO` en esta ronda de refactor + endurecimiento, con 21/21 tests nuevos reportados y hallazgos H1-H4 cerrados
  - revalidado en produccion el 2026-07-18 con interfaz real: busqueda, alta de producto, cambio de cantidad y retiro de linea
  - revalidado adicionalmente el 2026-07-18 con apertura de caja, devolucion real, corte operativo y registro de gasto en produccion
  - adicionalmente se valido una devolucion parcial real sobre una venta de prueba distinta para cubrir el flujo parcial
  - no se detecto un flujo separado de "precorte" como modulo canonico independiente; el corte diario vigente vive en `core.views.farmacia.corte_caja_dia`
- Logistica -> `RESUELTO` segun checklist oficial y reporte maestro del 2026-06-25
- Mantenimiento -> `RESUELTO` segun checklist oficial y reporte maestro del 2026-06-25
- Academia -> `RESUELTO` con 8/8 tests reportados en checklist oficial
- Marketing -> `RESUELTO` con 9/9 tests reportados en checklist oficial
- RH / Nomina -> `RESUELTO` con 25 tests reportados, Competencia consolidado como catalogo global y endurecimiento tenant/roles ya integrado
- IoT -> `RESUELTO` con `0005_kiosco_empresa`, suite `iot.tests` y cierre oficial documentado
- Recepcion -> `RESUELTO` con fix de timezone y suite completa verde
- Seguridad -> `RESUELTO` con `9/9` tests en el arbol local
- Operaciones -> `RESUELTO` con tenant canonico y `4/4` tests dedicados
- Bienestar -> `RESUELTO` con hardening de rutas NOM-035, `localdate()` y redirect final revalidado
- Contabilidad / Finanzas -> `RESUELTO` con auditoria profunda 2026-06-26: `FacturaCFDI.empresa` NOT NULL canónico, timbrado idempotente, `except Exception` en `facturama_api.py:113` endurecido a `(ValueError, KeyError, TypeError, OSError)`, 48 tests OK (exit 0)

## Modulos que siguen abiertos

- Laboratorio: matriz de pruebas humanas con efectos laterales aún no ejecutada completamente; el catálogo LIMS autoritativo y la migración de relación perfil-analito ya están disponibles.
- Laboratorio/LIMS: falta ejecutar con datos QA trazables la matriz completa de recepción, toma, captura, valores críticos, rechazo/repetición, cancelación/reembolso, entrega, control de calidad estricto Westgard y consumo de reactivos/insumos por analito.
- Laboratorio/LIMS: faltan validar en sitio los equipos, impresoras, integración HL7 y la configuración real de reactivos/insumos; el código no puede sustituir esa verificación física.
- IA documental: DeepSeek quedó operativo para texto y JSON. El OCR de recetas, facturas y notas sigue dependiendo del proveedor visual configurado en `core/services/ocr_documental.py`; debe probarse con imágenes reales y una credencial visual válida antes de declararlo cerrado.
- Operación multi-tenant: producción tiene `PRISLAB_DEFAULT_EMPRESA_ID=1`; el tenant 1 está registrado como `Primero Salud Laboratorio SAS de CV` y el tenant 2 permanece separado como `Laboratorio del Valle`.
- `branch protection` / `rulesets` en GitHub: verificados por evidencia funcional; `H-001` corregido en `release/v1.0-local`.
- Laboratorio: la autenticación administrativa y navegación UI ya fueron verificadas; no se debe afirmar cierre humano total hasta ejecutar recepción, toma, captura, críticos, rechazo/repetición, cancelación/reembolso, entrega y control de calidad con datos QA trazables.
- Laboratorio: la confirmación de recepción ya fue reproducida aceptando el modal y la ruta feliz quedó persistida; no contar esto como cierre total porque la matriz de excepciones continúa abierta.

## Reportes finales integrados

- Buzon / Comunicacion / Notificaciones

## Hallazgos que siguen vigentes

### Hallazgos de auditoria anterior ya descartados en el arbol actual

- `role_required` no permite bypass por `is_staff`; el decorador solo deja pasar a `is_superuser` o al rol permitido.
- `_requiere_lims_captura` ya no permite `is_staff` como bypass.
- `AuditLog` y `ForenseAcceso` ya son append-only a nivel modelo mediante `save()` y `delete()`.
- `chromadb` ya no forma parte del baseline de `requirements.txt`; el motor RAG lo trata como opcional con activacion explicita.
- El despliegue vigente tiene dos rutas: `deploy.sh` para Docker Compose local/staging y `scripts/deploy_vps.sh` para ejecutarse dentro de la VPS. `.github/workflows/deploy-vps.yml` automatiza la segunda ruta, pero requiere los secretos/variables del Environment `production`.
- El `NameError path` del middleware Sentinel no se reproduce en el arbol actual: `path` queda definido antes de cada uso relevante.

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

### Farmacia - cierre de refactorizacion y endurecimiento

Estado actual del codigo:

- `farmacia/urls.py` ya consolida `api/lotes-producto` sobre la implementacion de `pdv.py`
- `farmacia/views/soporte.py` ya filtra apertura de caja por `empresa`
- `farmacia/views/__init__.py` ya corta `KardexListView` con `objects.none()` cuando no hay empresa
- `farmacia/views/pdv.py` ya mantiene guard estricto por `getattr(request.user, 'empresa', None)` en `pdv_farmacia`
- existen 21 tests nuevos reportados para AperturaCaja, CorteCaja, EntradaExpress, COFEPRIS y CargaMasiva
- el reporte de cierre marca `21/21 OK` sobre esa tanda nueva y deja 3 fallos preexistentes documentados fuera del cierre

Conclusion:

- RESUELTO / CERRADO — no reabrir H1-H4 ni la refactorizacion principal sin repro nueva
- mantener fuera del cierre solo los 3 fallos preexistentes explicitamente documentados, como deuda separada del modulo

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
- bienestar reporta `18/18` pruebas verdes, superficie canonica dual explicitada y cobertura ampliada a `alertas_rrhh`, `marcar_alerta_vista`, cross-tenant y rutas NOM-035
- academia reporta `8/8` pruebas verdes con regresiones de aislamiento cross-tenant
- marketing reporta `9/9` pruebas verdes con bloqueo de `empresa=None`
- recepcion tiene el fix de timezone integrado y la suite completa ya quedo verde; la auditoria vieja de desalineacion de rol/grupo queda descartada en esta rama

Conclusion:

- Bienestar -> `RESUELTO/CERRADO` en esta ronda.
- Logistica, Mantenimiento, Academia y Marketing -> `RESUELTOS/CERRADOS` en la documentacion oficial vigente del 2026-06-25.
- Recepcion -> `RESUELTO`; no reabrir el bug viejo sin reproduccion nueva contra esta rama.

### RH / Nomina - cierre oficial consolidado

Estado actual del codigo:

- `core/views/rh.py` ya tiene `@role_required('DIRECTOR', 'ADMIN', 'GERENTE', 'RH')` en las vistas sensibles
- `core/views/rh.py::mis_resultados` ya valida que `empleado.empresa_id == user.empresa.id`
- `core/views/nomina.py::_empresa()` ya falla con `PermissionDenied` si el usuario no tiene empresa
- `core/views/nomina.py` ya protege los wrappers legacy `ver_periodo`, `ver_nomina`, `cerrar_periodo`
- `core/models/rrhh.py::Competencia` ya queda documentado como catalogo global
- `core/admin.py::CompetenciaAdmin` ya restringe add/change/delete a superuser
- `core/tests/test_rh_nomina_security.py` ya cubre el caso delicado de `ADMIN` no-superuser en admin

Conclusion:

- RESUELTO / CERRADO — la documentacion oficial ya lo promueve a cerrado con `25 tests OK` usando `--keepdb`
- decision final consolidada: `Competencia` permanece como catalogo global y no debe reabrirse como bug funcional

### Contabilidad / Finanzas - cierre operativo reportado

Estado actual documentado:

- existe reporte final local `docs/ai_coordination/ESTADO_CONTABILIDAD_FINANZAS_CIERRE_TOTAL_V2.md`
- `FacturaCFDI.empresa` queda reportada como FK canónica multi-tenant y `NOT NULL`
- existen modelos reales `CuentaContable`, `Poliza`, `AsientoContable` con migración `0012_catalogo_cuentas_polizas`
- `core/views/contabilidad.py` y `core/views/reportes_financieros.py` ya representan el frente operativo del módulo
- Claude añadió verificación profunda adicional:
  - `dashboard_contabilidad` ya filtra ingresos por `estado='COMPLETADA'`
  - `core/views/cuentas_por_cobrar.py` ya usa `timezone.localdate()` en los puntos críticos de CxC / convenios
- el cierre reportado reconoce que la suite grande del dominio financiero no quedó revalidada completa por timeout, pero sí quedaron verdes las sub-suites críticas y `makemigrations --check`

Conclusion:

- REPORTE_INTEGRADO — el cierre operativo queda incorporado al canon como baseline válida para la auditoría profunda de Imperium
- no tratar este módulo como “pendiente sin contexto”
- tampoco venderlo como blindado absoluto antes de la pasada profunda
- deuda residual documentada: stubs contables profundos y fragilidad arquitectónica por superposición de rutas `/contabilidad/`

### Buzon / Comunicacion / Notificaciones - cierre operativo casi completo reportado

Estado actual documentado:

- se recibió reporte final de cierre operativo sobre `core/views/buzon.py`, `core/views/notificaciones.py` y `core/tests/test_buzon_notificaciones.py`
- Claude añadió hallazgos profundos ya visibles en el árbol local:
  - colisión funcional de `buzon_kanban` resuelta
  - `api_cambiar_estado_queja` ya no convierte 404 tenant/inexistente en 500
  - `tu_opinion` ya no asigna empresa arbitraria
- bugs reportados como corregidos: permisos de `buzon_kanban`, `@require_POST` faltantes, bug lógico de reapertura, `Http404` mal manejado, respuesta sin empresa, campo `fecha_creacion`
- evidencia reportada: `manage.py test core.tests.test_multi_tenant_isolation core.tests.test_buzon_notificaciones` + `manage.py check`
- `core/templates/core/tu_opinion.html` ya contiene `{% csrf_token %}`
- residual real vigente: `rate limiting` en `tu_opinion` y ampliación funcional de `ejecutar_verificaciones` como mejoras no bloqueantes

Conclusion:

- REPORTE_INTEGRADO — usar como baseline para la auditoría profunda de Imperium
- el módulo ya no debe figurar como “simplemente en proceso”; su siguiente etapa es auditoría de estrés, no exploración básica

### Bienestar - cierre de auditoría y hardening (2026-06-25)

Estado actual del código:

- `config/urls.py`: corregida colisión de URL — NOM-035 movido de `/bienestar/` a `/bienestar-staff/` para no sombrear Espacio Seguro
- `bienestar/views.py`: `timezone.now().date()` → `timezone.localdate()` en 4 ubicaciones
- `core/views/bienestar.py`: `timezone.now().date()` → `timezone.localdate()` en 4 ubicaciones + redirect final de `evaluacion_nom035` corregido a `bienestar_dashboard`
- `core/templates/includes/sidebar.html`: rutas NOM-035 actualizadas a `/bienestar-staff/`
- `core/tests/test_bienestar_nom035.py`: la regresión de NOM-035 ahora exige el redirect correcto a `bienestar_dashboard`
- Superficie dual verificada como intencional (Espacio Seguro + NOM-035 Staff + Alertas PRIS)
- Modelos con FK `empresa`: `ConversacionBienestar`, `AlertaBienestar`, `SesionCoachingStaff`, `AlertaBurnout`, `ProgramaCapacitacion`
- Modelos sin FK `empresa` (aislamiento por `usuario`, suficiente): `DiarioEmocional`, `RecursoCrecimiento`, `EvaluacionNOM035`, `DiarioEmocionalStaff`
- 19 tests en 3 suites: `bienestar.tests`, `test_bienestar_nom035`, `test_bienestar_mejorado`

Hallazgos:
- B1 (CORREGIDO): colisión URL `/bienestar/` entre NOM-035 y Espacio Seguro
- B2-B5 (DESCARTADOS): modelos sin FK `empresa` — aislamiento por `usuario` suficiente
- B6 (CORREGIDO): patrón `timezone.now().date()` → `timezone.localdate()`
- B7 (CORREGIDO): redirect roto `dashboard_bienestar` sobrevivía oculto por Sentinel; ya apunta a `bienestar_dashboard`

Conclusion:

- CERRADO — 19/19 tests OK, `manage.py check` limpio, redirect NOM-035 revalidado, 0 deuda viva

### Recepcion - cierre definitivo en arbol canonico

Estado actual:

- `core/views/general.py` ya unifica `RECEPCION` hacia `recepcion:dashboard_recepcion` tanto por grupo como por `rol`
- `recepcion/views.py` ya usa `timezone.localdate()` en `dashboard_recepcion` y `lista_espera`
- `recepcion/tests.py` ya no es stub; ahora contiene regresiones canonicas para:
  - redirect sin empresa
  - bloqueo cross-tenant en `check_in_paciente`
  - bloqueo cross-tenant en `cobrar_consulta`
  - discriminacion TZ en dashboard y lista de espera
- `manage.py check` pasa
- el helper `_empresa_recepcion()` ya no acepta el fallback de empresa por defecto del middleware para usuarios sin FK `empresa`
- corrida reproducible local reportada en el cierre anterior:
  - `manage.py test recepcion.tests --keepdb -v 0` -> `5 OK`
  - la suite completa quedó verde y el cierre se considera definitivo en esta rama

Conclusion:

- RESUELTO / CERRADO definitivo en esta rama

### Seguridad - revalidacion local final

Estado actual:

- `seguridad/tests.py` corre limpio en este arbol
- el warning Sentinel sobre `panic_button` sin empresa corresponde al bloqueo esperado del endpoint
- la validacion 2FA, backup codes y aislamiento tenant del boton de panico/rastro paciente quedaron revalidados
- corrida reproducible local:
  - `manage.py test seguridad.tests --keepdb -v 1` -> `9 OK`

Conclusion:

- RESUELTO / CERRADO — no reabrir Seguridad sin evidencia nueva contra esta rama

### Operaciones - cierre con tenant canonico y pruebas propias

Estado actual:

- `core/views/operaciones.py` ya usa `empresa_efectiva_request(request)`
- el flujo rechaza usuarios sin FK `empresa` en vez de aceptar la empresa por defecto del middleware
- `monitor_rutas` queda cubierto como alias estable del mismo dashboard
- existe suite dedicada:
  - `core/tests/test_operaciones_module.py`
- corrida reproducible local:
  - `manage.py test core.tests.test_operaciones_module --keepdb -v 1` -> `4 OK`

Conclusion:

- RESUELTO / CERRADO — Operaciones ya no queda abierto en este corte

### IoT - kioscos multi-tenant

Estado actual del codigo:

- `iot/models.py` ya agrega FK `empresa` en `Kiosco`
- `iot/views.py` ya filtra dashboards y operaciones por `empresa`
- los endpoints publicos de kiosco (`heartbeat`, `confirmar`, `rechazar`) ya validan IP contra `kiosco.ip_address`
- existen `iot/migrations/0005_kiosco_empresa.py` e `iot/tests.py` como piezas nuevas del cierre

Conclusion:

- RESUELTO / CERRADO — la documentacion oficial del 2026-06-25 lo promueve a cerrado con `7 tests OK` y uso explicito de `--keepdb` para evitar falsos timeouts por I/O local
- mantener como pendiente operativo separado solo el deploy y validacion fisica de emparejamiento de kioscos

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

- hay modulos ya cerrados tecnicamente y 3 modulos explicitamente excluidos de esta consolidacion por seguir en proceso
- Inventario ya forma parte del bloque de modulos cerrados con evidencia tecnica y pruebas
- no debe afirmarse que todo el arbol esta blindado; aunque Bienestar ya fue integrado y Contabilidad/Buzon ya tienen reportes finales integrados, Imperium todavía puede encontrar defectos nuevos de alto nivel fuera del alcance de los cierres operativos
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

## Corte 2026-07-27 — CCI/Westgard

Se corrigio el manejo de errores en `laboratorio/services/cci_canal.py`: se
importaron las excepciones Django usadas por el flujo y se eliminaron llamadas
a `send_alert`, simbolo inexistente. Si falla la persistencia de la
notificacion, el estado del canal permanece en `ALERTA_QC` y el rechazo no se
convierte en una caida del proceso.

La regresion esta cubierta por `laboratorio.tests.test_cci_canal`, incluida en
los gates SQLite y PostgreSQL. Validacion local: 18 pruebas OK y 3 omitidas por
requerir PostgreSQL. CCI/Westgard sigue abierto operacionalmente: produccion
tenia cero mediciones de control en el corte, por lo que no se declara cierre
funcional hasta cargar datos reales del laboratorio.
