# Inventario Real del Repositorio - PRISLAB

Generado: 2026-06-23  
Metodo: escaneo automatico del arbol `release/v1.0-local`  
HEAD: d598c83

Este documento reemplaza estimaciones manuales. Cualquier agente que diga
"no sabia que existia X" debe leer este archivo primero.

---

## 1. Apps Django del proyecto (18)

Cada app tiene `models.py`. Las marcadas con `*` tienen `urls.py` propias.

- `academia`
- `bienestar` *
- `consultorio` *
- `contabilidad` *
- `core` * (app principal — vistas, middleware, servicios, utils)
- `config` (settings, urls raiz, wsgi)
- `enfermeria` *
- `farmacia` * (ERP — kardex, proveedores, devoluciones ERP)
- `ia` *
- `inventario` *
- `iot` *
- `laboratorio` *
- `lims` * (analitica — analitos, perfiles, paquetes, precios)
- `logistica` *
- `mantenimiento`
- `marketing` *
- `pacientes` *
- `recepcion` *
- `reglas_negocio` *
- `seguridad` *

**Apps sin models.py propios (vistas/urls en core o config):**
- `finanzas` (vistas en `core/views/finanzas.py`)
- `director` (vistas en `core/views/director.py`)

---

## 2. Tests del proyecto (92 archivos unicos)

### Canon reciente — con commit y cobertura de regresion

| Test | Modulo | Estado |
|------|--------|--------|
| `test_auto_repair_tenant_guard.py` | Sentinel | ACTIVO — cubre S2/S3/a7b0d8b |
| `test_hardening_2fa_resultados.py` | 2FA / tokens | ACTIVO — cubre d598c83/c802eb5 |
| `test_devoluciones_farmacia_api.py` | Farmacia devoluciones | ACTIVO — cubre fa9b02a |
| `test_farmacia_corte_unificado.py` | Corte caja | ACTIVO — cubre f3e43e9 |
| `test_farmacia_lotes_api.py` | Lotes farmacia | ACTIVO — cubre 7371e10 |
| `test_laboratorio_recepcion_tenant.py` | Lab tenant | ACTIVO — cubre 97da7c7 |
| `test_lims_config_tenant_security.py` | LIMS tenant | ACTIVO — cubre b82334a |
| `test_auditoria_segura_farmacia.py` | Auditoria solo-lectura | ACTIVO — cubre 5ec53dc |
| `test_auditoria_segura_laboratorio.py` | Auditoria solo-lectura | ACTIVO |
| `test_auditoria_segura_consultorio.py` | Auditoria solo-lectura | ACTIVO |
| `test_auditoria_segura_pacientes.py` | Auditoria solo-lectura | ACTIVO |
| `test_auditoria_segura_global.py` | Auditoria solo-lectura | ACTIVO |
| `test_farmacia_permission_helpers.py` | Permisos farmacia | ACTIVO — cubre 15b857e |

### Tests en raiz del proyecto (fuera de apps)

Estos existian antes de la auditoria formal. Estado: no clasificados como activos ni como legado.
Requieren decision humana sobre si corren en CI o son scripts manuales.

- `test_api.py`
- `test_conexion_storage.py`
- `test_consultorio_full_e2e.py`
- `test_consultorio_qa.py`
- `test_farmacia_full_user_flow.py`
- `test_farmacia_pdv_e2e.py`
- `test_farmacia_step_by_step.py`
- `test_final_verification.py`
- `test_integracion_real.py`
- `test_lab_detailed.py`
- `test_lab_flow.py`
- `test_laboratorio_full_e2e.py`
- `test_pdv_buttons_snapshot.py`
- `test_subida_pdf_drive.py`
- `test_ui_playwright.py`

### Tests en `scripts_cursor_e2e/tests/` (e2e externos)

- `test_01_guardian_golden_lifecycle.py`
- `test_02_lims_inventory_sync.py`
- `test_03_math_ui_integrity.py`
- `test_04_finance_caja_sync.py`
- `test_05_hl7_mock_device.py`
- `test_06_role_permission_hygiene.py`
- `test_07_pdf_branding_consistency.py`
- `test_08_jarvis_escudo_ui.py`
- `test_09_sucursal_modo_inventario_ui.py`
- `test_robot_chemist_flows.py`

Estado: no integrados en CI de la rama actual. Pendiente de clasificar.

### Tests en apps especificas

| App | Test |
|-----|------|
| `contabilidad` | `test_cfdi_borrador_auto.py`, `test_validators_cfdi40.py` |
| `inventario` | `test_critical_stock.py`, `test_fefo_analito_calculado.py`, `test_gestion_inventario_bypass_lab.py` |
| `laboratorio` | `test_cci_lj_postgres_guard.py`, `test_hl7_handshake.py`, `test_westgard.py` |
| `reglas_negocio` | `test_validadores_y_flags.py` |

### Tests como management commands (en `core/management/commands/`)

Estos se ejecutan con `manage.py` y no con `pytest`. No son tests de CI convencionales.

- `test_drive_connection.py`
- `test_estructura_drive.py`
- `test_gemini_connection.py`
- `test_gemini_v1.py`
- `test_github_sentinel.py`
- `test_pdf_receta.py`
- `test_pris_vida.py`

---

## 3. Management commands del proyecto (169)

### Categoria: Auditoria / verificacion (solo lectura)

- `auditoria_segura_farmacia.py`, `auditoria_segura_laboratorio.py`, `auditoria_segura_consultorio.py`, `auditoria_segura_pacientes.py`, `auditoria_segura_global.py` — ACTIVOS, canon
- `audit_roles.py`, `audit_system.py`, `audit_tenant_readiness.py`, `auditar_rutas.py`
- `verificar_aislamiento_multitenant.py`, `verificar_sistema_completo.py`, `verificar_integridad.py`, `verificar_todo_sistema.py`
- `matriz_integridad.py`, `omni_audit.py`, `diagnostico_pris.py`, `diagnostico_total.py`

### Categoria: Seeds / carga de datos

- `seed_catalogos.py`, `seed_estudios.py`, `seed_grupos_permisos.py`, `seed_motivos_ajuste.py`
- `seed_pacientes_revision_prislab.py`, `seed_parametros_lab.py`, `seed_pdv_audit_20.py`
- `seed_productos_prueba.py`, `seed_rangos_iso15189.py`, `seed_super_master_role.py`
- `cargar_catalogo_lab.py`, `cargar_inventario_excel.py`, `cargar_productos_farmacia.py`

### Categoria: Migracion / backfill

- `backfill_inventario_idempotency.py`, `backfill_lotes_operativos_farmacia.py`
- `backfill_movimientos_caja_v114.py`, `backfill_ventas_inventario_descontado.py`
- `migrar_lab_completo.py`, `migrar_lab_master.py`

### Categoria: Backup / restore

- `backup_database.py`, `backup_db_drive.py`, `backup_nocturno.py`
- `restaurar_backup.py`, `registrar_backup_inmutable.py`, `verificar_backup_cifrado.py`

### Categoria: Setup / provision

- `crear_superusuario_prod.py`, `crear_usuarios_produccion.py`, `crear_grupos_roles.py`
- `setup_roles.py`, `provision_usuarios_base.py`, `sincronizar_roles_grupos.py`

### Categoria: Sentinel / reparacion

- `sentinel_auto_cleanup.py`, `sentinel_reporte_semanal.py`, `sentinel_reset.py`
- `sentinel_amnistia_pre_produccion.py`, `resolver_incidencias.py`
- `saneamiento_global_sentinel_buzon.py`

### Categoria: Simulacion / estres (NO ejecutar en produccion)

- `simular_flujo_completo.py`, `simular_laboratorio_completo.py`
- `simular_operacion_anual.py`, `simular_ventas_farmacia_completo.py`
- `stress_test_extremo.py`, `war_room_stress_test.py`, `estres_ventas_farmacia.py`

### Categoria: Destructivos / purgado (requieren autorizacion explicita)

- `wipe_datos_operativos.py` — DESTRUCTIVO
- `purgar_datos_nom035.py`, `purgar_lims.py`
- `limpiar_pruebas.py`, `limpieza_entorno_prod.py`

---

## 3b. Scripts Python en raiz del proyecto (55 archivos)

Estos archivos existen en la raiz del checkout y **no estan integrados en ninguna app Django ni en CI**.
No deben ejecutarse en produccion sin leerlos primero. Clasificacion por tipo:

### Scripts de setup / provision (util, idempotentes si el sistema esta limpio)
- `manage.py` — entrypoint Django, canonico
- `create_admin.py`, `create_e2e_user.py`, `reset_admin_password.py`, `reset_password.py`
- `setup_admin_access.py`, `configurar_admin.py`, `configurar_admin_completo.py`
- `crear_demo.py`, `completar_todo_funcional.py`

### Scripts de debug / diagnostico (solo lectura, util en local)
- `debug_get_paciente.py`, `debug_post_paciente.py`, `debug_sentinel_response.py`
- `smoke_test.py`, `verificar_sistema.py`, `verificar_requisitos.py`
- `verificar_pacientes_bd.py`, `verificar_carga_inventario.py`
- `probar_registro_pacientes.py`

### Scripts de carga de datos (riesgo medio — mutan BD)
- `cargar_excel_forzado.py`, `cargar_excel_robusto.py`, `cargar_tarifas.py`
- `ver_primeras_filas.py`, `poblar_recursos_bienestar.py`
- `generar_migraciones_consolidacion.py`

### Tests manuales / e2e sin integrar en CI
- `test_api.py`, `test_conexion_storage.py`, `test_consultorio_full_e2e.py`
- `test_consultorio_qa.py`, `test_farmacia_full_user_flow.py`, `test_farmacia_pdv_e2e.py`
- `test_farmacia_step_by_step.py`, `test_final_verification.py`, `test_integracion_real.py`
- `test_lab_detailed.py`, `test_lab_flow.py`, `test_laboratorio_full_e2e.py`
- `test_pdv_buttons_snapshot.py`, `test_subida_pdf_drive.py`, `test_ui_playwright.py`
- `e2e_test_prod.py`, `ejecutar_pruebas_e2e.py`, `ejecutar_pruebas_playwright.py`
- `run_tests_and_report.py`, `run_tests_save_output.py`

### Scripts de fix masivo (legacy — no ejecutar sin revision)
- `fix_all_tests_aggressive.py`, `fix_farmacia.py`, `fix_tests_batch_v3.py`, `fix_tests_masivo.py`
- `diagnose_and_fix_tests.py`

### Scripts de migracion / limpieza (riesgo alto — mutan datos)
- `migracion_ordenes_forense.py`, `desactivar_usuarios_antiguos.py`, `limpiar_usuarios_antiguos.py`
- `temp_create_admin_remote.py`

### Utilitarios varios
- `generar_vapid_keys.py`, `procesar_firma_brizia.py`, `validate_security_fixes.py`

---

## 3c. Directorio `middleware_local/` — middleware de equipos fisicos

**Funcionalidad real, no legacy.** Agente local que conecta analizadores de laboratorio via serial/USB.

- `agente_laboratorio.py` — proceso principal del agente local
- `config.yaml` — configuracion de puertos y drivers
- `requirements.txt` — dependencias propias (independientes del venv Django)
- `drivers/fuji_nx600.py` — analizador Fuji NX600
- `drivers/incca_chem.py` — analizador INCCA
- `drivers/mission_u120.py` — analizador Mission U120
- `drivers/norma_icon.py` — analizador Norma ICON
- `drivers/serial_compat.py` — capa de compatibilidad serial
- `drivers/wondfo_finecare.py` — analizador Wondfo Finecare

**Estado: ACTIVO — requiere documentacion de despliegue separada. No esta en CI.**

---

## 3d. Directorio `scripts/` — operacion de infraestructura

Scripts de deploy, backup y servicios del sistema.

- `deploy_vps.sh` — script de despliegue al VPS (216.238.89.243)
- `setup_servidor.sh` — provision inicial del servidor
- `web_entrypoint.sh` — entrypoint de contenedor/gunicorn
- `aplicar_fixes_produccion.sh` — aplicar fixes en caliente (riesgo alto)
- `activar_wildcard_ssl.sh` — configuracion SSL
- `backup_to_drive.py` — backup a Google Drive
- `sync_live_tariff_prices.py` — sincronizacion de precios en produccion
- `regenerar_catalogos_lims_desde_excel.py` — regenera catalogos LIMS
- `ai_coordination_hub.py` — hub de coordinacion multi-IA
- `iniciar_ai_coordination_hub.ps1` — wrapper Windows del hub
- `run_manage_with_env.py` — ejecuta manage.py con env especifico
- `generar_token_oauth_drive.py` — genera token OAuth para Drive
- `validar_drive_setup.py` — valida configuracion de Drive
- `api_v3_redteam_e2e.py`, `e2e_api_v3_redteam.py` — tests de red team API v3
- `generate_levantamiento_md.py` — genera documentacion de levantamiento
- Archivos `.service` para systemd: `prislab-gunicorn.service`, `prislab-celery.service`, `prislab-celerybeat.service`

---

## 3e. Directorio `scripts_legacy/` — scripts de provision obsoletos

No ejecutar. Reemplazados por management commands y `scripts/`.

- `crear_admin_limpio.py`, `crear_superusuario_admin.py`, `crear_superusuario_completo.py`
- `crear_datos_prueba.py`, `crear_datos_prueba_completos.py`
- `crear_equipo_oficial.py`, `crear_equipo_prislab.py`
- `crear_responsable_sanitario.py`, `crear_usuarios.py`, `provision_usuarios.py`
- `migrar_lab_v2.py` — migracion legacy reemplazada
- `stress_e2e_prod.py` — stress test legacy

---

## 3f. Directorio `scripts_cascade_e2e/` — runner e2e de Cascade (legacy)

- `_e2e_pdv_audit.mjs`, `octogono_ui_audit.mjs`, `playwright_auth.mjs` — runners legacy
- `output/octogono_ui_audit_report.json` — **PLACEHOLDER OBSOLETO** (no usar como evidencia)
- `output/*.png` — capturas de corridas anteriores (mayo 2026)

**Estado: LEGACY. El runner canonico es `tools/run_human_ui_audit.mjs`.**

---

## 3g. Directorio `scripts_cursor_e2e/` — suite e2e de Cursor

- `run_cursor_reliability_suite.py` — runner de la suite
- `tests/test_01` a `test_09` + `test_robot_chemist_flows.py` — 10 tests e2e
- **Estado: NO integrados en CI de `release/v1.0-local`. Pendiente de clasificar.**

---

## 3h. Directorio `datos_lims/` — datos de catalogo para importar

CSVs de referencia para seed de LIMS. No son codigo ejecutable.

- `Examenes.csv`, `Examenes_Perfil.csv`, `Paquetes.csv`, `Paquetes_Perfil.csv`
- `Parametros.csv`, `Tarifa_estudios de laboratorio.csv`, `Valores_normalidad.csv`

---

## 3i. Directorio `nginx/` — configuracion del servidor web

- `nginx.conf` — configuracion principal
- `conf.d/prislab.conf` — configuracion del sitio
- `conf.d/proxy_params.conf` — parametros de proxy

---

## 3j. Directorio `templates/` en raiz — templates globales

Templates que no viven dentro de ninguna app especifica:

- `403.html` — pagina de acceso denegado global
- `consultorio/lista_trabajo_medico.html`, `nueva_consulta_soap.html`, `tablero_recepcion.html`
- `pdfs/resultado_lab_print.html` — template de impresion de resultados
- `seguridad/2fa/activar_totp.html`, `codigos_backup.html`, `configuracion.html`
- `seguridad/auditoria/dashboard.html`, `logs.html`
- `seguridad/sesiones/lista.html`

---

## 3k. Directorio `audit_findings/` y `audit_artifacts/` — artefactos de auditorias pasadas

Logs, reportes y salidas de corridas anteriores. **No son evidencia activa.**

- `audit_findings/` — 50 archivos: logs de tests, exit codes, inventarios JSON, lista de todos
- `audit_artifacts/` — 12 archivos: artefactos de auditorias de Cascade anteriores

**Estado: HISTORICO. No usar como evidencia. Solo consultar si se necesita contexto de una corrida pasada especifica.**

---

## 3l. Directorio `release_candidate/`

- `validate_security_fixes.py`, `verificar_aislamiento_simple.py` — scripts de validacion de RC
- `audit_total_report_final.md`, `BLOQUE2_COVERAGE_REPORT.md` — reportes del RC
- `coverage_initial.dat`, `omni_full.log` — datos de cobertura
- `README_CERTIFICATION.txt` — nota de certificacion

---

## 3m. Directorio `diagnostico_omni_*/` — corridas diagnostico (mayo 2026)

15 carpetas con timestamp de mayo 2026. Cada una contiene reportes de diagnostico automatico.
**Estado: HISTORICO. No relevar como evidencia actual.**

---

## 3n. Directorios de capturas de tests

Carpetas vacias o con capturas de corridas de tests pasadas:

- `test_screenshots_consultorio/`, `test_screenshots_farmacia/`, `test_screenshots_farmacia_full/`
- `test_screenshots_farmacia_steps/`, `test_screenshots_final_verification/`, `test_screenshots_laboratorio/`
- `screenshots_e2e/` — 54 archivos de capturas de e2e

---

## 4. Runners / herramientas JS (17)

### Canon activo (usar estos)

- `tools/run_human_ui_audit.mjs` — runner principal de UI humana
- `run_human_ui_audit.bat` — wrapper Windows
- `tools/run_omni_suite.mjs` — suite completa

### Legacy / experimental (no usar sin instruccion explicita)

- `_audit_api_smoke.mjs`
- `_audit_farmacia_full.mjs`
- `_audit_role_matrix.mjs`
- `_audit_system_map_smoke.mjs`
- `_e2e_pdv_audit.mjs` (duplicado detectado)
- `_e2e_ui_omni.mjs`
- `octogono_ui_audit.mjs` — genera el placeholder `octogono_ui_audit_report.json`
- `playwright_auth.mjs`

### Scripts de operacion (no son runners de audit)

- `CARGAR_INVENTARIO_AHORA.bat`
- `DESPLEGAR_A_PRODUCCION.bat`
- `INICIAR_PRUEBAS_CLINICAS.bat`
- `iniciar_servidor.bat`
- `run_e2e_full.bat`

---

## 5. Artefactos de salida del runner (estado actual)

| Artefacto | Tipo | Estado |
|-----------|------|--------|
| `auditoria_ui_20260623_194712/` | Corrida real sin auth | LIMITACION DE HERRAMIENTA — no auditable |
| `auditoria_ui_20260623_194820/` | Corrida real sin auth | LIMITACION DE HERRAMIENTA — no auditable |
| `auditoria_ui_20260623_212952/` | Corrida real (pendiente push) | PENDIENTE_VALIDAR — existe local, no en remoto |
| `scripts_cascade_e2e/output/octogono_ui_audit_report.json` | Placeholder | OBSOLETO — no usar como evidencia |

---

## 6. Lo que no existia en el inventario anterior y ahora si esta documentado

- 169 management commands (antes: "algunos comandos")
- 17 runners JS con clasificacion canon/legacy/operacion
- 92 tests con clasificacion por ubicacion y estado
- 18 apps con modelos propios
- 3 corridas reales de `human:ui` con clasificacion de estado
- El placeholder `octogono_ui_audit_report.json` marcado como obsoleto

---

## 6. Archivos sueltos en raíz no documentados anteriormente

### Infraestructura y configuracion (activos)

- `Dockerfile` — imagen de produccion (modificado 19/06/2026)
- `docker-compose.yml` — compose local/staging (modificado 19/06/2026)
- `Procfile` — entrypoint para Heroku/Railway
- `runtime.txt` — version de Python declarada
- `requirements.txt` — dependencias de produccion (modificado 20/06/2026)
- `requirements-dev.txt` — dependencias de desarrollo
- `package.json` — dependencias JS/Node (modificado 23/06/2026 — contiene scripts `human:ui`)
- `package-lock.json`
- `deploy.sh`, `verify_deployment.sh` — scripts de deploy en raiz
- `EJECUTAR_EN_SERVIDOR.sh` — script de ejecucion en servidor
- `migracion_ia.ps1` — script PowerShell de migracion IA
- `nginx/` — ya documentado en 3i

### Archivos sensibles — **requieren manejo cuidadoso**

- `.env` — variables de entorno activas (modificado 31/05/2026) — **NO versionar, NO compartir**
- `.env.example` — plantilla publica (modificado 21/06/2026)
- `.env.production.example` — plantilla de produccion (modificado 21/06/2026)
- `env.example` — plantilla legacy
- `env_produccion.txt` — variables de produccion en texto plano (modificado 20/06/2026) — **RIESGO: revisar si contiene credenciales reales**
- `gdrive_credentials.json` — credenciales de Google Drive (modificado 26/05/2026) — **SENSIBLE**
- `.runtimeconfig.json.backup` — backup de config runtime
- `REPORTE_CREDENCIALES_Y_SECRETOS_PRISLAB.md` — reporte de credenciales (01/06/2026) — **SENSIBLE**

### Datos CSV/XLSX en raiz (datos reales de negocio)

- `inventario.csv` + `inventario.csv.xlsx` — inventario de farmacia
- `Productos-farmacia-2026-02-10-10-31.csv` + `.xlsx` — catalogo de productos
- `resultados.csv` — resultados de algun proceso (verificar contenido)
- `tarifas.csv` — tarifas de estudios

### Logs activos en raiz

- `debug.log` — log de debug activo (modificado 23/06/2026)
- `server.log`, `server_err.log`, `server_error.log` — logs de servidor
- `runserver.err.log`, `runserver.out.log` — logs de runserver local
- `db.sqlite3` — base de datos SQLite local (modificado 23/06/2026 — **contiene datos reales de sesion local**)
- `prislab_deploy_payload.zip` — payload de deploy (31/05/2026)

### Archivos de texto con contenido operativo

- `urls_sistema.txt` — mapa de URLs del sistema
- `env_produccion.txt` — **ya marcado arriba como sensible**
- `modelos_en_migraciones.txt` — listado de modelos
- `_MASTER_DOC.txt` — documento maestro legacy
- `GUIA_RAPIDA_REGISTRO_PACIENTES.txt`, `LEER_ANTES_DE_INICIAR.txt` — guias operativas
- `test_output*.txt` (7 archivos) — salidas de tests mayo 2026 — HISTORICO
- `commit_*.txt` (5 archivos) — mensajes de commit guardados — HISTORICO
- `ultimos_500.txt`, `errores_*.txt`, `logs_*.txt` — logs de errores historicos

### MDs activos en raiz (junio 2026 — NO son legado)

- `README.md` — documentacion principal del proyecto
- `CHECKLIST_CONTROL_PRISLAB.md` — checklist operativo activo
- `REPORTE_COMPLETO_PARA_CLAUDE_2026-06-18.md` — reporte para Claude
- `PROTOCOLO_AUDITORIA_MULTI_IA_PRISLAB.md` — protocolo multi-IA
- `AI_COORDINATION_STATUS.md` — estado de coordinacion (ya en canon)
- `GAP_ANALYSIS_ISO15189.md` — analisis de brechas ISO 15189
- `VULTR_OBJECT_STORAGE_SETUP.md` — setup de Vultr Object Storage
- `ACCESO_Y_DEPLOY_OPERATIVO_VPS.md` — guia de acceso y deploy al VPS
- `DEPLOY.md` — instrucciones de deploy
- `INFORME_AUDITORIA_ESTRICTA_2026-06-19.md` — informe de auditoria
- `REPORTE_CREDENCIALES_Y_SECRETOS_PRISLAB.md` — **SENSIBLE**
- `MATRIZ_MIGRACION_PRISLAB_VS_PRISLAB_SAAS.md` — matriz de migracion
- `PLAN_CIERRE_MIGRACION_PRISLAB.md`, `ANEXO_TECNICO_PRISLAB_LEGACY_VS_SAAS.md`, `PLAN_BLOQUE_POR_BLOQUE_PRISLAB.md` — documentos de cierre de migracion
- `EVIDENCIA_FINAL.md` — evidencia de auditoria (08/05/2026)

### MDs de legado en raiz (abril 2026 — ~80 archivos, todos con timestamp 28/04/2026)

Bloque completo de documentos generados durante la fase inicial del proyecto.
**No son canon operativo. No compiten con los documentos actuales.**
No se listan individualmente — todos tienen `LastWriteTime = 28/04/2026 08:51:58`.
Ejemplos representativos: `SISTEMA_COMPLETADO_100.md`, `PLAN_MAESTRO_*.md`, `IMPLEMENTACION_*.md`, `SOLUCION_*.md`, `REFACTORIZACION_*.md`.

**Decision pendiente:** confirmar si se borran, se mueven a `docs/legacy/` o se conservan.

---

## 6b. Directorio `tools/` — suite de auditoria automatizada

**Contiene runners activos, salidas de corridas reales y scripts de auditoria.**

### Runners canonicos
- `run_human_ui_audit.mjs` — runner principal (ya en seccion 4)
- `run_omni_suite.mjs` — suite completa

### Scripts de auditoria Python
- `audit_coverage_gate.py` — verifica cobertura minima
- `audit_data_integrity.py` — verifica integridad de datos
- `audit_url_inventory.py` — inventario de URLs
- `summarize_url_inventory.py` — resumen de inventario URLs
- `github_close_all_issues.py` — cierra issues en GitHub (**destructivo en GitHub**)
- `patch_sw_offline.py` — aplica parche de service worker offline

### Salidas de corridas reales (evidencia util)
- `last_suite.json`, `last_suite_summary.json`, `last_suite_human_summary.json` — ultima corrida de la suite
- `human_ui_last.json` — ultima corrida del runner humano
- `cloud__api_smoke.json`, `cloud__pdv_e2e.json`, `cloud__role_matrix.json`, `cloud__ui_omni.json` — corridas cloud
- `local__api_smoke.json`, `local__pdv_e2e.json`, `local__role_matrix.json`, `local__ui_omni.json` — corridas local
- `local__coverage_gate.json`, `local__data_integrity.json`, `local__url_inventory.json` — auditorias locales
- `coverage_gate_report.json`, `url_inventory.json`, `url_inventory_summary.json`, `omni_manifest.json`
- Archivos `.stderr.txt` correspondientes a cada corrida

### Otros
- `offline_sync.js` — logica de sincronizacion offline (service worker)

---

## 6c. Subcarpetas internas de apps no documentadas

### `core/` — subcarpetas funcionales

- `core/agent/` — `pris_agent.py`, `pris_tools_operativos.py` — agente IA de PRIS
- `core/api_contracts/` — `ninja_api.py`, `schemas.py`, `errors.py`, `middleware.py` — contratos de API v3 (Django Ninja)
- `core/constants/` — `lock_order.py` — orden de locks para deadlock prevention
- `core/tasks/` — `notificaciones_tasks.py`, `storage_tasks.py` — tareas Celery
- `core/templatetags/` — `auth_extras.py`, `math_filters.py`, `saludos_tags.py`, `tenant_tags.py`
- `core/utils/` — 35 utilidades: `empresa_request.py`, `pdf_generator.py`, `gemini_client.py`, `deepseek_client.py`, `google_drive.py`, `whatsapp_sender.py`, `rag_engine.py`, `tenant_strict.py`, `lims_tokens_v75.py`, `candado_financiero.py`, `escudo_clinico_check.py`, y mas
- `core/middleware/` — middleware del proyecto (Sentinel, rate limit, etc.)
- `core/models/` — modelos divididos en submodulos
- `core/services/` — servicios de negocio
- `core/views/` — vistas divididas en submodulos
- `core/tests/` — tests de la app principal

### `farmacia/` — subcarpetas
- `farmacia/services/` — `venta_farmacia_service.py`, `corte_caja_unificado.py`, `alertas.py`, `impresora_termica.py`
- `farmacia/views/` — vistas divididas (ya auditadas)

### `consultorio/`
- `consultorio/api/` — `procesar_audio.py` — procesamiento de audio para consulta

### `inventario/`
- `inventario/services/` — `critical_stock.py`

### `contabilidad/`
- `contabilidad/services/` — `cfdi_borrador_auto.py`, `timbrado_cfdi.py` — CFDI 4.0

---

## 6d. Directorio `docs/` — subdirectorios no documentados

### `docs/api/` (3 archivos)
- `payload_farmacia_ok.json`, `payload_lims_ok.json` — payloads de prueba validados
- `V3_QA_PAYLOADS.md` — documentacion de payloads QA para API v3

### `docs/audit/` (25 archivos) — reportes de auditorias pasadas
Incluye: `GUARDIAN_360_REPORT.md`, `REPORTE_AUDITORIA_CODEX_2026-06-20.md`, `VEREDICTO_LIMS_CASCADE.md`, `FUNCIONES_EXHAUSTIVO_POR_RUTA.md`, `INVENTARIO_URLS.txt`, `GO_LIVE_CHECKLIST_v8.5.md`, `SOP_DESPLIEGUE_SEGURO.md`, `DRP_RUNBOOK_ACAYUCAN.md`, `LEGACY_BOUNDARY_FASE0.md`, `TECH_DEBT_TEST_CLIENT_PY314.md`, y mas.
Estado: algunos activos (GO_LIVE, SOP, DRP), la mayoria historicos.

### `docs/manual/` (6 archivos)
- `APENDICE_FORMULAS_LIMS_v75.md`, `MANUAL_INVENTARIO_FEDERADO_v75.md`, `MODULO_INVENTARIO_FEDERADO.md`
- `DRP_RUNBOOK_ACAYUCAN.md`, `GO_LIVE_CHECKLIST_v8.5.md`, `SOP_DESPLIEGUE_SEGURO.md`

### `docs/ai_coordination/inbox/` — evidencia activa pendiente de clasificar
- `20260621_030813_HALLAZGO_3_BLOQUEADOR_LABORATORIO.md` — **PENDIENTE_VALIDAR** — hallazgo de Claude del 21/06/2026 sobre orden LAB persistida en "Por Validar". Fue clasificado como PENDIENTE en sesion previa; no ha sido procesado.

### `docs/ai_coordination/processed/claude/`
- El mismo archivo del inbox — indica que fue leido pero no clasificado formalmente en el canon.

### `docs/ai_coordination/drop/` — buzon de entrega para agentes
- Subcarpetas `cascada/`, `claude/`, `codex/` — actualmente vacias.

---

## 7. Regla operativa

- Para auditar: usar solo salida de `human:ui` con auth real.
- Para seeds: usar `seed_*` en entorno de prueba, nunca directamente en produccion sin respaldo.
- Para destructivos: `wipe_datos_operativos.py` y `purgar_*` requieren autorizacion explicita del usuario.
- Para clasificar hallazgos: Cascada usa este inventario como referencia, no estimaciones.

## 8. Estado actual de la suite de tests y deuda tecnica

- Tests sin LLM: **696/701 pasando**.
- Tests con LLM: **30 tests no corridos hoy**; se consideran pendiente de validacion, no regresion nueva.
- Fallos preexistentes que permanecen:
  - `test_fastapi_performance`
  - `test_openapi_schema_fast`
  - `test_malformed_tool_args_json_handled`
  - `test_agent_executes_plan_documents_locally_when_requested`
  - `test_soak_memory_leak`
- Deuda tecnica estructural pendiente:
  - **CAP-05**: el agente hace 6 rondas LLM cuando deberia hacer 3.
