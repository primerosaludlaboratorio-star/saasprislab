# INVENTARIO MAESTRO TOTAL - PRISLAB SaaS

Generado: 2026-06-23  
Método: escaneo automático completo del árbol (`release/v1.0-local`)  
HEAD: d598c83  
Archivos Python escaneados: 790  
Archivos no-Python escaneados: 2140  
**Este documento es la fuente de verdad completa. No hay nada fuera de él.**

---

## PARTE 1 — APPS DJANGO (20)

### Apps con modelos propios (18)

| App | Templates HTML | Tests propios | Commands propios | Services |
|-----|---------------|---------------|-----------------|----------|
| `academia` | 2 | `tests.py` | `sincronizar_academia_bunny` | `access.py`, `bunny_stream.py` |
| `bienestar` | 9 | `tests.py` | `poblar_recursos` | — |
| `consultorio` | 35 | `tests.py` | — | — |
| `contabilidad` | 6 | `test_cfdi_borrador_auto`, `test_validators_cfdi40` | `reconciliar_facturas_pendientes` | `cfdi_borrador_auto.py`, `timbrado_cfdi.py` |
| `enfermeria` | 6 | `tests.py` | — | — |
| `farmacia` | 14 | `tests.py` | — | `venta_farmacia_service`, `corte_caja_unificado`, `alertas`, `impresora_termica` |
| `ia` | 6 | `tests.py` | — | — |
| `inventario` | 35 | `test_critical_stock`, `test_fefo_analito_calculado`, `test_gestion_inventario_bypass_lab` | `auditar_bom_consumo_reactivo`, `auditar_integridad_inventario`, `backfill_inventario_idempotency` | `critical_stock.py` |
| `iot` | 1 | `tests.py` | — | — |
| `laboratorio` | 6 | `test_cci_lj_postgres_guard`, `test_hl7_handshake`, `test_westgard` | 13 commands | `cci_canal`, `escudo_clinico_lims`, `etiquetas_zpl`, `hl7_handshake`, `iso15189`, `metrologia_lab`, `unificacion`, `westgard` |
| `lims` | 10 | `tests.py` | 8 commands | `views/analitos`, `views/paquetes`, `views/perfiles`, `views/precios`, `views/tenant_lims` |
| `logistica` | 8 | `tests.py` | — | — |
| `mantenimiento` | 22 | — | `check_certificados_metrologicos`, `sync_incca_csv` | `consumo_refacciones_service.py` |
| `marketing` | 10 | `tests.py` | — | — |
| `pacientes` | 13 | `tests.py` | — | — |
| `recepcion` | 7 | `tests.py` | — | — |
| `reglas_negocio` | — | `test_validadores_y_flags` | — | — |
| `seguridad` | 7 | `tests.py` | — | — |

### Apps sin modelos propios (2)

- `config/` — settings, urls raíz, asgi, wsgi, celery, storage backends, admin_site, drive_credentials
- `core/` — app principal (ver Parte 2)

---

## PARTE 2 — APP `core/` (612 archivos — la más grande del proyecto)

### `core/views/` (81 archivos de vista)

Cada archivo es un módulo de vista independiente:

- **Autenticación/Seguridad:** `general.py`, `autenticacion_2fa.py`, `configuracion.py`, `administracion_usuarios.py`
- **Laboratorio:** `laboratorio.py`, `laboratorio_captura.py`, `laboratorio_config.py`, `laboratorio_reportes.py`, `microbiologia.py`, `excepciones_lab.py`, `entrega_resultados.py`, `historial_resultados.py`, `sucursal_modo_inventario_lab.py`
- **Farmacia:** `farmacia.py`, `inventario.py`, `inventario_predictivo.py`, `transferencias.py`, `tarifas.py`, `paquetes.py`, `catalogos.py`, `catalogos_maestros.py`, `cotizacion.py`, `maquila.py`
- **Consultorio:** `medico.py`, `expediente.py`, `blindaje_expediente.py`, `consentimientos.py`, `consentimiento_digital.py`, `operaciones.py`, `pris_checklist.py`
- **Finanzas:** `finanzas.py`, `motor_financiero.py`, `reportes_financieros.py`, `contabilidad.py`, `contabilidad_personal.py`, `cuentas_por_cobrar.py`, `autofactura.py`
- **RRHH/Asistencia:** `rh.py`, `asistencia.py`, `nomina.py`, `ranking.py`, `bienestar.py`, `bienestar_mejorado.py`
- **IA/Agente:** `ia.py`, `ia_dashboard.py`, `ai_brain.py`, `pris_ia.py`, `pris_jarvis.py`, `cerebro.py`, `coach.py`, `voice.py`, `bot.py`, `capacitacion.py`, `capacitacion_rag.py`, `audio_legal.py`
- **Dirección:** `director.py`, `war_room.py`, `dashboard_unificado.py`, `analytics.py`, `monitor_produccion.py`, `reporte_friccion.py`
- **Operaciones:** `paciente.py`, `pacientes.py`, `paciente_detalle.py`, `consul ta_ordenes.py`, `incidencias.py`, `autorizaciones.py`, `buzon.py`
- **Integraciones:** `prisci_webhook.py`, `push.py`, `notificaciones.py`, `comunicacion.py`, `crm.py`, `onboarding.py`
- **Admin/Config:** `feature_flags_admin.py`, `sentinel_api.py`, `auditoria_api.py`, `auditoria_campo.py`, `manual.py`, `impresion.py`, `omnisearch.py`, `biblioteca.py`

### `core/models/` (submodelos)

- `base.py`, `bienestar_staff.py`, `catalogos.py`, `clinico.py`, `expediente_blindaje.py`
- `finanzas.py`, `forense.py`, `ia_config.py`, `laboratorio.py`, `operaciones.py`
- `pacientes.py`, `pris.py`, `rrhh.py`, `ventas.py`

### `core/middleware/` (14 archivos)

- `sentinel.py` — middleware principal de permisos/redirects
- `rate_limit.py` — límite de peticiones
- `read_only.py` — modo solo lectura
- `empresa.py` — inyección de tenant
- `seguridad.py` — cabeceras de seguridad
- `performance.py` — métricas de rendimiento
- `canonical_host.py` — normalización de host
- `actividad_usuario.py` — registro de actividad
- `admin_access.py`, `admin_access_restrict.py` — restricción de admin
- `blindaje_expediente.py` — protección de expedientes
- `feature_flags.py` — flags de features
- `json_response.py` — respuestas JSON
- `mantenimiento.py`, `pris_context.py`

### `core/services/` (subservicios)

- **IA médica:** `ai_medico.py`, `ai_medico_backup.py`, `interpretacion_ia.py`, `ia_clinical_governance.py`, `validador_ia.py`
- **Clínico:** `clinical_math.py`, `escudo_clinico_check.py` (en utils), `motor_recetas.py`, `motor_reportes_lab.py`, `resultados_impresion_presentacion.py`
- **Inventario:** `inventario/catalogo_farmacia_service.py`, `inventario/movimiento_inventario_service.py`
- **LIMS:** `lims/interfaces_lims_service.py`, `lims/orden_recepcion_service.py`, `lims/resultados_lims_service.py`
- **Ventas:** `ventas/venta_farmacia_service.py`
- **Operaciones:** `audit_service.py`, `auto_repair.py`, `bankguard_cierre.py`, `forense_service.py`, `github_reporter.py`, `migration_readiness.py`, `ocr_documental.py`, `paciente_service.py`, `prediccion_stock.py`, `super_master_audit.py`, `telegram_outbound.py`, `voice_service.py`
- **Infraestructura:** `bienestar_pris_hooks.py`, `cadena_frio.py`, `feature_flags.py`

### `core/utils/` (35 archivos)

- **Clientes externos:** `gemini_client.py`, `deepseek_client.py`, `google_drive.py`, `whatsapp_sender.py`
- **Tenant/Empresa:** `empresa_request.py`, `default_empresa.py`, `farmacia_tenant.py`, `tenant_strict.py`
- **PDF/Docs:** `pdf_generator.py`, `drive_archive.py`, `backup_inmutable.py`
- **IA:** `rag_engine.py`, `ia_cache.py`, `ia_output_sanitize.py`, `ia_permissions.py`, `ia_resources.py`, `pris_audio_vision.py`
- **Auditoría:** `auditoria_helper.py`, `auditoria_nativa.py`, `trazabilidad.py`
- **Clínico/Lab:** `referencia_lims_edad.py`, `lims_tokens_v75.py`, `escudo_clinico_check.py`, `lfpdppp_resultados.py`, `estandares_industriales.py`, `detalle_orden.py`
- **Operaciones:** `candado_financiero.py`, `corrector_errores.py`, `analizador_quejas.py`, `notificaciones.py`, `ranking.py`, `rh_utils.py`, `marketing_tracking.py`, `saludos.py`, `paths.py`

### `core/agent/`

- `pris_agent.py` — agente principal PRIS
- `pris_tools_operativos.py` — herramientas del agente

### `core/api_contracts/` (API v3 Django Ninja)

- `ninja_api.py` — registro de API
- `schemas.py` — esquemas Pydantic
- `errors.py` — errores estandarizados
- `middleware.py` — middleware de API

### `core/management/commands/_archive_legacy/`

- `diagnostico_total.py`, `import_estudios_excel.py`, `seed_catalogos.py` — archivos de comandos archivados

### `core/` archivos raíz importantes

- `ai_brain.py`, `catalog.py`, `consumers.py` (WebSocket), `context_processors.py`
- `decorators.py`, `django_template_context_patch.py`, `fields.py`, `forms.py`
- `lims_cart.py`, `mixins.py`, `push_service.py`, `rescate_total_prislab.py`
- `routing.py` (ASGI channels), `signals.py`, `tasks.py`, `tenant.py`, `validators.py`
- `tests_e2e.py`, `tests_e2e_playwright.py` — tests e2e en raíz del app

### `core/tests/` (57 tests canónicos — ya clasificados en INVENTARIO_REAL_REPO.md)

### Salud actual de la suite de tests

- Tests sin LLM: **696/701 pasando**.
- Tests con LLM: **30 tests no corridos hoy**; deben tratarse como pendiente de validación, no como regresión nueva.
- Fallos preexistentes reportados:
  - `test_fastapi_performance`
  - `test_openapi_schema_fast`
  - `test_malformed_tool_args_json_handled`
  - `test_agent_executes_plan_documents_locally_when_requested`
  - `test_soak_memory_leak`
- Deuda técnica estructural pendiente:
  - **CAP-05**: el agente hace 6 rondas LLM cuando debería hacer 3.

---

## PARTE 3 — TEMPLATES HTML (408 archivos total)

| App | Cantidad | Ubicación |
|-----|----------|-----------|
| `core` | 200 | `core/templates/core/` |
| `inventario` | 35 | `inventario/templates/inventario/` |
| `consultorio` | 35 | `consultorio/templates/consultorio/` |
| `mantenimiento` | 22 | `mantenimiento/templates/mantenimiento/` |
| `farmacia` | 14 | `farmacia/templates/farmacia/` |
| `pacientes` | 13 | `pacientes/templates/pacientes/` |
| `templates/` raíz | 11 | `templates/` |
| `lims` | 10 | `lims/templates/lims/` |
| `marketing` | 10 | `marketing/templates/marketing/` |
| `bienestar` | 9 | `bienestar/templates/bienestar/` |
| `logistica` | 8 | `logistica/templates/logistica/` |
| `seguridad` | 7 | `seguridad/templates/seguridad/` |
| `recepcion` | 7 | `recepcion/templates/recepcion/` |
| `ia` | 6 | `ia/templates/ia/` |
| `contabilidad` | 6 | `contabilidad/templates/contabilidad/` |
| `laboratorio` | 6 | `laboratorio/templates/laboratorio/` |
| `enfermeria` | 6 | `enfermeria/templates/enfermeria/` |
| `academia` | 2 | `academia/templates/academia/` |
| `iot` | 1 | `iot/templates/iot/` |

**Nota:** Los templates viven dentro de cada app. Los de `templates/` raíz son globales (403, 2FA, auditoría, sesiones — ya documentados).

---

## PARTE 4 — TESTS (92 archivos únicos)

### Canon activo (con cobertura de regresión documentada)

Ver `INVENTARIO_REAL_REPO.md` sección 2 para la tabla completa.

### Tests adicionales descubiertos en este escaneo

- `core/tests_e2e.py` — tests e2e dentro de la app core (no en `core/tests/`)
- `core/tests_e2e_playwright.py` — tests Playwright dentro de la app core
- `farmacia/tests.py` — tests de la app farmacia (archivo único, no en subdirectorio)
- `laboratorio/tests.py` — tests de laboratorio raíz (además de los 3 en `laboratorio/tests/`)
- `lims/tests.py` — tests de lims raíz
- `logistica/tests.py` — tests de logística
- `ia/tests.py`, `iot/tests.py` — tests de IA e IoT

---

## PARTE 5 — MANAGEMENT COMMANDS (169 + 3 en _archive_legacy)

### Comandos en `laboratorio/management/commands/` (13)

- `actualizar_precios_con_auditoria.py`
- `cargar_catalogo_pruebas.py`, `cargar_estructura_resultados.py`, `cargar_tarifas_csv.py`
- `crear_perfiles_quimica.py`
- `importar_catalogo_maestro.py`, `importar_tarifas_lab.py`, `importar_tarifas.py`
- `migrar_lab_completo.py`, `migrar_lab_master.py`
- `poblar_sistema.py`, `seed_rangos_iso15189.py`
- `simular_laboratorio_completo.py`

### Comandos en `lims/management/commands/` (8)

- `ensamblar_lims_v75.py`, `importar_catalogo_lims.py`, `importar_datos_lims.py`
- `importar_examenes_perfil_lims.py`, `importar_paquetes_perfil_lims.py`
- `lims_amnistia_empresa.py`, `purgar_lims.py`, `sincronizar_precios_lims.py`

### Comandos en `inventario/management/commands/` (3)

- `auditar_bom_consumo_reactivo.py`, `auditar_integridad_inventario.py`, `backfill_inventario_idempotency.py`

### Comandos en `mantenimiento/management/commands/` (2)

- `check_certificados_metrologicos.py`, `sync_incca_csv.py`

### Comandos en `academia/management/commands/` (1)

- `sincronizar_academia_bunny.py`

### Comandos en `bienestar/management/commands/` (1)

- `poblar_recursos.py`

### Comandos en `contabilidad/management/commands/` (1)

- `reconciliar_facturas_pendientes.py`

### Comandos en `core/management/commands/` (169 — ver INVENTARIO_REAL_REPO.md sección 3)

---

## PARTE 6 — LABORATORIO: subcarpetas especializadas

### `laboratorio/services/` (8 servicios)

- `cci_canal.py` — canal CCI (control de calidad inter-laboratorio)
- `escudo_clinico_lims.py` — validación clínica LIMS
- `etiquetas_zpl.py` — generación de etiquetas ZPL para impresoras
- `hl7_handshake.py` — protocolo HL7 con equipos
- `iso15189.py` — norma ISO 15189
- `metrologia_lab.py` — metrología de equipos
- `unificacion.py` — unificación de resultados
- `westgard.py` — reglas de Westgard (control de calidad)

### `laboratorio/views/` (5 vistas especializadas)

- `cci_api.py` — API de CCI
- `etiquetas.py` — impresión de etiquetas
- `hl7_receptor.py` — receptor HL7
- `imprimir_zpl.py` — impresión ZPL

### `laboratorio/api/` — API REST de laboratorio

### `laboratorio/utils/`

- `label_printer.py` — utilidad de impresora de etiquetas

### `laboratorio/cci_models.py` — modelos de CCI (Levy-Jennings)

---

## PARTE 7 — ARCHIVOS FUNCIONALES ESPECIALES (no en apps)

### `middleware_local/` — drivers de analizadores físicos (ACTIVO)

- `agente_laboratorio.py` — proceso principal
- `drivers/`: `fuji_nx600.py`, `incca_chem.py`, `mission_u120.py`, `norma_icon.py`, `serial_compat.py`, `wondfo_finecare.py`

### `config/` — configuración central

- `settings.py` — configuración Django principal
- `celery.py` — configuración Celery
- `drive_credentials.py` — credenciales Drive
- `storage_backends.py` — backends de almacenamiento (S3/Vultr/local)
- `admin_site.py` — customización del admin
- `urls.py` — URLs raíz del proyecto

---

## PARTE 8 — RUNNERS Y HERRAMIENTAS (ya en INVENTARIO_REAL_REPO.md, secciones 4 y 6b)

Resumen rápido:
- Canon: `tools/run_human_ui_audit.mjs`, `tools/run_omni_suite.mjs`
- Evidencia real en `tools/`: 12+ JSON de corridas cloud y local
- Legacy: `scripts_cascade_e2e/`, runners con prefijo `_`
- Destructivo en GitHub: `tools/github_close_all_issues.py`

---

## PARTE 9 — ARCHIVOS ESTÁTICOS Y ASSETS

### `static/` (39 archivos de código)

- `.js` (24), `.css` (9), `.svg` (3), `.pdf` (2), `.json` (1)
- Además: fuentes (woff, woff2, ttf, eot), imágenes PNG

### Templates distribuidos en 408 archivos HTML (ver Parte 3)

---

## PARTE 10 — ARCHIVOS DE INFRAESTRUCTURA Y CONFIGURACIÓN

### Docker y deploy

- `Dockerfile`, `docker-compose.yml`, `Procfile`, `runtime.txt`
- `scripts/deploy_vps.sh`, `scripts/setup_servidor.sh`, `scripts/web_entrypoint.sh`
- `scripts/prislab-gunicorn.service`, `scripts/prislab-celery.service`, `scripts/prislab-celerybeat.service`
- `deploy.sh`, `EJECUTAR_EN_SERVIDOR.sh`, `verify_deployment.sh`
- `nginx/nginx.conf`, `nginx/conf.d/prislab.conf`, `nginx/conf.d/proxy_params.conf`

### Dependencias

- `requirements.txt` — producción (actualizado 20/06/2026)
- `requirements-dev.txt` — desarrollo
- `package.json` — Node.js (actualizado 23/06/2026)
- `middleware_local/requirements.txt` — dependencias del agente local (independientes)

### Archivos sensibles (en .gitignore — NO versionar)

- `.env` — variables de entorno activas
- `gdrive_credentials.json` — credenciales Google Drive
- `db.sqlite3` — base de datos local activa
- `env_produccion.txt` — **REVISAR: puede contener credenciales en texto plano**
- `REPORTE_CREDENCIALES_Y_SECRETOS_PRISLAB.md` — documento con credenciales

---

## PARTE 11 — DOCUMENTACIÓN ACTIVA (no legacy)

### `docs/ai_coordination/` (canon multi-IA)

- `AI_COORDINATION_STATUS.md`, `INDICE_CANONICO_TOTAL.md`
- `ESTADO_CANONICO_RAMA_RELEASE_V1_0_LOCAL.md`
- `GUIA_OPERATIVA_FINAL.md`, `NEXT_ACTIONS.md`
- `PROCEDIMIENTO_VERIFICACION_HUMANA_UI.md`
- `INVENTARIO_REAL_REPO.md` (superado por este documento)
- `INVENTARIO_UNIFICADO_RECONCILIADO_2026-06-24.md`
- `PENDIENTES_CANONICOS.md`
- `outbox/`: 7 archivos (briefs + tareas activas)
- `inbox/`: hallazgo LAB pendiente de clasificar
- `processed/claude/`: mismo hallazgo (leído, no cerrado)

### `docs/audit/` (25 archivos — mezcla de activos e históricos)

Activos operativos:
- `GO_LIVE_CHECKLIST_v8.5.md` — checklist de go-live
- `SOP_DESPLIEGUE_SEGURO.md` — procedimiento de despliegue seguro
- `DRP_RUNBOOK_ACAYUCAN.md` — plan de recuperación de desastres
- `LEGACY_BOUNDARY_FASE0.md` — límite del legacy

Históricos (útiles como referencia):
- `GUARDIAN_360_REPORT.md`, `REPORTE_AUDITORIA_CODEX_2026-06-20.md`, `VEREDICTO_LIMS_CASCADE.md`
- `FUNCIONES_EXHAUSTIVO_POR_RUTA.md`, `INVENTARIO_URLS.txt`

Scripts en `docs/audit/` (ejecutables):
- `_regen_comandos_manage.py`, `_regen_exhaustivo_rutas.py`, `FASE_4_5_POSTGRES_ROADMAP.py`

### `docs/manual/` (6 archivos)

- `APENDICE_FORMULAS_LIMS_v75.md`, `MANUAL_INVENTARIO_FEDERADO_v75.md`
- `MODULO_INVENTARIO_FEDERADO.md`
- `DRP_RUNBOOK_ACAYUCAN.md`, `GO_LIVE_CHECKLIST_v8.5.md`, `SOP_DESPLIEGUE_SEGURO.md`

### `docs/api/` (3 archivos)

- `payload_farmacia_ok.json`, `payload_lims_ok.json`, `V3_QA_PAYLOADS.md`

### MDs activos en raíz

- `README.md`, `CHECKLIST_CONTROL_PRISLAB.md`, `PROTOCOLO_AUDITORIA_MULTI_IA_PRISLAB.md`
- `GAP_ANALYSIS_ISO15189.md`, `VULTR_OBJECT_STORAGE_SETUP.md`
- `ACCESO_Y_DEPLOY_OPERATIVO_VPS.md`, `DEPLOY.md`
- `INFORME_AUDITORIA_ESTRICTA_2026-06-19.md`, `REPORTE_COMPLETO_PARA_CLAUDE_2026-06-18.md`
- `MATRIZ_MIGRACION_PRISLAB_VS_PRISLAB_SAAS.md`, `PLAN_CIERRE_MIGRACION_PRISLAB.md`
- `ANEXO_TECNICO_PRISLAB_LEGACY_VS_SAAS.md`, `PLAN_BLOQUE_POR_BLOQUE_PRISLAB.md`

---

## PARTE 12 — LEGADO Y RUIDO (no usar como evidencia ni canon)

### MDs de legado en raíz (~80 archivos, timestamp 28/04/2026)

Todos con `LastWriteTime = 28/04/2026`. Ejemplos: `SISTEMA_COMPLETADO_100.md`, todos los `PLAN_MAESTRO_*.md`, `IMPLEMENTACION_*.md`, `SOLUCION_*.md`, `REFACTORIZACION_*.md`.  
**Decisión pendiente del usuario:** borrar / mover a `docs/legacy/` / conservar.

### `scripts_legacy/` (12 scripts)

Reemplazados por management commands. No ejecutar.

### `scripts_cascade_e2e/` (legacy)

Runner obsoleto + placeholder `octogono_ui_audit_report.json`. No usar como evidencia.

### `diagnostico_omni_*/` (15 carpetas, mayo 2026)

Histórico. No relevar como evidencia actual.

### `audit_findings/` y `audit_artifacts/` (62 archivos)

Logs y salidas de corridas pasadas. Solo consultar si se necesita contexto específico.

### `release_candidate/` (7 archivos)

Scripts y reportes del RC previo. Conservar como referencia, no como canon activo.

### Archivos de texto basura en raíz

`test_output*.txt` (7), `commit_*.txt` (5), `errores_*.txt`, `logs_*.txt`, `ultimos_500.txt`, `test_boost*.txt`. Historico puro.

### Directorios de capturas vacíos

`test_screenshots_*/` (6 carpetas vacías), `screenshots_e2e/` (54 capturas de mayo 2026).

---

## PARTE 13 — DATOS DE NEGOCIO EN EL ÁRBOL

Estos archivos contienen datos reales y no son código:

- `datos_lims/` — 7 CSVs de catálogo LIMS (examenes, paquetes, parámetros, tarifas)
- `inventario.csv` + `.xlsx` — inventario de farmacia
- `Productos-farmacia-2026-02-10-10-31.csv` + `.xlsx` — catálogo de productos
- `tarifas.csv` — tarifas de estudios
- `resultados.csv` — resultados (verificar contenido)
- `firma_brizia.jpg`, `firma_brizia_original.jpg` — firma digital de responsable sanitario

---

## PARTE 14 — LOGS Y ESTADO RUNTIME

- `debug.log` — activo, modificado hoy
- `server.log`, `server_err.log`, `server_error.log` — logs de servidor
- `runserver.err.log`, `runserver.out.log` — logs de desarrollo local
- `logs/bankguard_audit.log`, `logs/omni_baseline.json`, `logs/prislab_audit.log`, `logs/prislab_errors.log`
- `.coverage` — datos de cobertura de tests
- `db.sqlite3` — BD local activa

---

## PENDIENTES QUE ESTE INVENTARIO REVELA

1. **`env_produccion.txt`** — revisar si contiene credenciales reales expuestas.
2. **`docs/ai_coordination/inbox/20260621_030813_HALLAZGO_3_BLOQUEADOR_LABORATORIO.md`** — hallazgo LAB sin clasificar formalmente.
3. **`core/tests_e2e.py` y `core/tests_e2e_playwright.py`** — tests en raíz del app, no en `core/tests/` — estado no clasificado.
4. **`_archive_legacy/`** dentro de management commands — 3 comandos archivados, verificar si son necesarios.
5. **`docs/audit/FASE_4_5_POSTGRES_ROADMAP.py`** — script Python dentro de docs (inusual), verificar función.
6. **MDs de legado (~80)** — decisión pendiente de purga o movimiento.
7. **`consultorio/sentinel_service.py`** y **`consultorio/views_integracion_lab.py`** — vistas adicionales de consultorio fuera del subdirectorio estándar.
8. **`inventario/concurrency.py`** — manejo de concurrencia en inventario, no documentado previamente.
9. **`pacientes/portal_models.py`** y **`pacientes/portal_views.py`** — portal de pacientes, módulo completo no documentado.
10. **`marketing/tracking_signing.py`** — firma de tracking de marketing, no documentado.
11. **`config/drive_credentials.py`** — gestión de credenciales Drive en configuración central.
12. **`core/rescate_total_prislab.py`** — script de rescate total dentro del app core, verificar si está en uso.

---

## PARTE 15 — SUPERFICIE IA/LLM CLASIFICADA (verificada 2026-06-24)

Clasificación por acoplamiento real al código — no por nombre de archivo.  
Evidencia: escaneo de importaciones en vivo + lectura de archivos fuente.

---

### CATEGORÍA 1 — IA ACTIVA DE NEGOCIO

Acoplada a flujos clínicos o transaccionales reales. Si falla, el flujo de negocio falla o degrada.

| Archivo | Llamado desde | Función real |
|---------|--------------|-------------|
| `core/utils/gemini_client.py` | `pris_ia.py`, `ia/views.py`, `cerebro.py` | Proveedor principal LLM con fallback a DeepSeek. Lógica de selección de modelo y retry. |
| `core/utils/deepseek_client.py` | `gemini_client.py` como fallback | Proveedor alternativo LLM |
| `core/services/ia_clinical_governance.py` | `pris_ia.py:605` | Genera borradores de resultados clínicos para el captador de lab |
| `core/services/ocr_documental.py` | `pris_ia.py:1056` | OCR de documentos en flujo de análisis |
| `core/services/interpretacion_ia.py` | `motor_reportes_lab.py:792`, `ia_dashboard.py` | Genera "Resumen de Bienestar" para el paciente en el PDF de resultados |
| `core/services/validador_ia.py` | `monitor_produccion.py:518`, `ia_dashboard.py:180,303` | Valida resultados de lab contra rangos imposibles + genera sugerencias de proceso |
| `core/services/ai_medico.py` | `consultorio/api_views.py:80,175`, `consultorio/api/procesar_audio.py:19` | Procesamiento de audio médico y consulta dictada → datos estructurados |
| `core/utils/rag_engine.py` | `cerebro.py:14`, `capacitacion_rag.py:298,400`, `pris_ia.py:1493` | Motor RAG para Cerebro y módulo de capacitación |
| `core/utils/ia_output_sanitize.py` | `pris_ia.py:1232` | Sanea respuestas IA antes de devolverlas al frontend |

---

### CATEGORÍA 2 — IA DE SOPORTE / OPERACIÓN

Acoplada a operaciones internas, no a flujos directos de paciente o resultado clínico.

| Archivo | Función real |
|---------|-------------|
| `core/agent/pris_agent.py` | Agente principal PRIS. **RIESGO CRÍTICO:** importado en `core/middleware/pris_context.py` — un fallo de import rompe cada request del sistema. |
| `core/agent/pris_tools_operativos.py` | Herramientas del agente: buscar paciente, cambiar estado orden, registrar venta. Mediadas por el agente. |
| `core/views/pris_ia.py` | Vista principal IA (1590+ líneas). Punto de entrada de toda la superficie IA al frontend. |
| `core/views/ai_brain.py` | Delega a `core/ai_brain.responder` — conversación interna |
| `core/views/cerebro.py` | Consulta RAG por pregunta — soporte de conocimiento |
| `core/views/capacitacion_rag.py` | Ingestión y consulta de documentos PDF para capacitación |
| `core/ai_brain.py` | Lógica de conversación con function calling (validar folios, consultar ventas, buscar RH). Acceso restringido por rol. |
| `core/utils/ia_resources.py` | Gestión de recursos IA por empresa |
| `core/utils/ia_cache.py` | Cache de respuestas IA |
| `core/utils/ia_permissions.py` | Control de acceso a funciones IA por empresa/rol |

---

### CATEGORÍA 3 — TESTS Y COMANDOS

**3a — Tests de regresión IA activos (mantener en suite):**

| Archivo | Qué prueba |
|---------|-----------|
| `core/tests/test_ai_provider_views.py` | Endpoints de proveedor IA |
| `core/tests/test_ai_provider_deepseek.py` | Cliente DeepSeek |
| `core/tests/test_prisci_unified_ai.py` | IA unificada PRISCI |
| `core/tests/test_pris_tools_operativos_security.py` | Seguridad tools del agente |
| `core/tests/test_buscar_o_crear_paciente_confirmation.py` | Tool específica agente |
| `core/tests/test_ia_ethics_p18.py` | Restricciones éticas IA |

Estado: 30 tests LLM pendientes de corrida — deuda de verificación, no bug nuevo.

**3b — Comandos de smoke / herramienta (NO ejecutar en producción sin motivo):**

| Comando | Tipo |
|---------|------|
| `core/management/commands/test_gemini_connection.py` | SMOKE — verifica que API responde |
| `core/management/commands/test_gemini_v1.py` | SMOKE — versión anterior |
| `core/management/commands/test_pris_vida.py` | SMOKE — vida del sistema |
| `core/management/commands/auditoria_ia.py` | HERRAMIENTA — audita config IA en el árbol |
| `core/management/commands/generar_auditoria_gemini.py` | HERRAMIENTA — paquete anonimizado para Gemini externo |
| `core/management/commands/auditoria_gemini_prime.py` | HERRAMIENTA — variante de auditoría |
| `core/management/commands/supervisor_ia_revisar_ventas.py` | OPERATIVO — revisa anomalías de descuento (sin LLM directo) |

---

### CATEGORÍA 4 — APP `ia/` — ACTIVA (no legado)

**Corrección respecto al análisis previo:** la app `ia/` tiene URL activa registrada en `config/urls.py:355`:
```python
path('ia/', include(('ia.urls', 'ia'), namespace='ia')),
```
Sus vistas (`ia/views.py`) llaman a `gemini_client` directamente para OCR, voz y asistente.  
**No es legado. Es una superficie IA alternativa/complementaria a `pris_ia.py`.**  
Pendiente determinar si hay duplicación funcional real con `pris_ia.py` — requiere decisión del usuario antes de cualquier cambio.

---

### RIESGOS IDENTIFICADOS

| Riesgo | Severidad | Archivo |
|--------|-----------|---------|
| `pris_agent` en middleware — import crítico que afecta cada request | **CRÍTICO** | `core/middleware/pris_context.py` |
| `ocr_documental` falla silenciosamente sin mensaje al usuario | MEDIO | `pris_ia.py:1056` |
| `gemini_client` sin DeepSeek configurado = sin fallback | MEDIO | `core/utils/gemini_client.py` |
| App `ia/` y `pris_ia.py` pueden tener funcionalidad duplicada | BAJO | `ia/views.py` vs `core/views/pris_ia.py` |

---

## REGLA FINAL

Este documento cubre los 790 archivos Python y 2140 archivos no-Python del checkout activo.  
Ninguna IA debe volver a decir "no sabía que existía X".  
Si algo nuevo aparece en el árbol, se agrega aquí antes de trabajar con ello.
