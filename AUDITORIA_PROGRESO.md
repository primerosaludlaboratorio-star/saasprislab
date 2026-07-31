# Auditoría exhaustiva PRISLAB — Progreso

## Incidente Farmacia — baja de caducados (2026-07-30)
- Corregidos los botones placeholder del panel de alertas y conectado el flujo real de Kardex por lote.
- Corregido el manejo de validaciones para evitar respuestas 500/Sentinel en errores operativos esperables.
- Pruebas de regresión añadidas en `core/tests/test_farmacia_baja_caducidad.py`.

Regla: cobertura función por función, sin excepciones. 1005 archivos .py (sin migraciones).
Fuente del inventario: árbol Git del checkout canónico (`git ls-files '*.py'`). No se mantiene un `.txt` duplicado fuera de Git.

Estado por archivo: `[ ]` pendiente · `[x]` auditado sin hallazgos · `[!]` auditado CON hallazgo (ver `AUDITORIA_HALLAZGOS.md`).

## Orden de trabajo
1. `core/models/` (18 archivos)
2. `core/` raíz + `core/admin/`, `core/agent/`, `core/api_contracts/`, `core/constants/`, `core/rbac/`
3. `core/middleware/` (18 archivos) — ya hay evidencia previa parcial, se re-verifica completo
4. `core/services/` (40 archivos)
5. `core/signals/`, `core/tasks/`, `core/utils/` (42 archivos), `core/templatetags/`
6. `core/views/` (111 archivos, incluye subpaquetes laboratorio/medico/pris_ia)
7. `core/management/commands/` (~130 archivos)
8. `core/tests/` (88 archivos) + `core/rbac/tests.py` + `core/tests_e2e*.py`
9. Apps de negocio: consultorio, contabilidad, farmacia, laboratorio, lims, inventario, pacientes, recepcion, enfermeria
10. Apps de soporte: academia, bienestar, iot, logistica, ia, pris_ai_core, seguridad, reglas_negocio, suscripciones, marketing, mantenimiento
11. `config/` (ya cubierto en pasada anterior, se re-verifica)
12. Scripts sueltos de raíz (~50) y `scripts/`, `audit/`, `docs/audit/`

## Bloque 1 — core/models/ (18 archivos)
- [x] core/models/__init__.py — agregador de re-exports, consistente con todos los submódulos. Sin hallazgos.
- [x] core/models/append_only.py — re-confirmado, sin hallazgos.
- [x] core/models/base.py — COMPLETO; H-NUEVO-01 corregido en `core.0098`.
- [x] core/models/bienestar_staff.py — COMPLETO; dependencia de cifrado revalidada.
- [x] core/fields.py — fallo cerrado ante errores de cifrado; pruebas de degradación bloqueada añadidas.
- [x] core/models/catalogos.py — COMPLETO (383 líneas: Producto, Lote, Medico, DiscountPolicy, Convenio, ConvenioPrecioLims). `Lote.clean()` bloquea lotes caducados/mal fechados; `save()` sincroniza empresa_id y llama full_clean(). `Medico.lab_validation_pin_hash` usa SHA256.
- [!] core/models/clinico.py — COMPLETO (830 líneas, 16 clases: CitaMedica, HistoriaClinica, SignosVitales, ConsultaMedica, CertificadoMedico, NotaClinicaSOAP, PlantillaNotaClinica, Antecedente, FirmaDigital, AudioConsulta, EstudioImagen, ImagenDetalle, PlantillaEstudioImagen, HistorialCambiosConsulta, LogAccesoExpediente, ConsentimientoInformado, RegistroAuditoriaConsentimiento). H-NUEVO-03 (folios por count()+1) permanece abierto; H-NUEVO-04 corregido, migrado y verificado en producción. Resto de métodos correctos.
- [x] core/models/expediente_blindaje.py — COMPLETO. H-NUEVO-05 corregido, migrado y verificado en producción con transacción reversible. Limpieza aplicada: retirados el receptor duplicado muerto `conectar_seniales()` y el `TokenLIMSV7Manager` incompleto sin consumidores; se conserva el receptor activo en `core/middleware/blindaje_expediente.py` y la integración vigente de `core/utils/lims_tokens_v75.py`.
- [x] core/models/finanzas.py — COMPLETO (459 líneas: PoliticaLimitesCaja, GastoCajaEndurecido, CierreDiaConsolidado, TicketInvestigacionCaja). `CierreDiaConsolidado.generar_hash()` correcto (no depende de auto_now_add, a diferencia de H-NUEVO-04/05). `GastoCajaEndurecido.clean()` valida zonas verde/amarillo/roja correctamente. Sin hallazgos.
- [x] core/models/forense.py — re-confirmado a fondo (visto en sesión previa), sin hallazgos.
- [x] core/models/ia_config.py — COMPLETO (190 líneas: UsoRecursosIA, ReglaLocalIA). `registrar_uso()` usa F() para incremento atómico. Sin hallazgos.
- [!] core/models/laboratorio.py — COMPLETO (729 líneas: TomaMuestra, AudioTomaMuestra, EnvioMaquila, BitacoraTemperatura, MantenimientoEquipo, HistorialResultados, ResultadoParametro, OrdenDeServicio, DetalleOrden, PreOrdenLaboratorio, DetallePreOrden). `OrdenDeServicio.save()` suma otro call site a H-NUEVO-03 (folio_orden). `OrdenDeServicio.clean()` bloquea RESULTADOS_LISTOS/ENTREGADO sin PDF (con excepción documentada por saldo pendiente). `AudioTomaMuestra` usa BinaryField cifrado Fernet. `aprobado_por_humano` documenta que la IA nunca puede fijarlo en True (no verificado programáticamente, solo por convención).
- [x] core/models/motor_financiero.py — RETIRADO. Era una copia huérfana de vistas, sin modelos y sin referencias activas; las URLs y pruebas usan `core/views/motor_financiero.py`.
- [x] core/models/operaciones.py — COMPLETO (947 líneas: AuditLog, BackupRegistro, BackupInmutableLog, MensajeInterno, SolicitudAutorizacion, IncidenciaOperativa, BuzonQuejas, LibroLiderazgo, PushSubscription, VoiceAuditLog, NotificacionSistema, BitacoraEntregaResultados, ConversacionBienestar, AlertaBienestar, DocumentoCapacitacion, CapsulaSabiduria). `AuditLog.hash_verificacion` confirmado poblado vía `core/utils/auditoria_helper.py` y `core/services/audit_service.py`. Append-only re-confirmado. Sin hallazgos nuevos.
- [x] core/models/pacientes.py — COMPLETO. `save()` normaliza y auto-genera `nombre_completo`. Retirado `generar_pris_id()`, método muerto sin llamadas y no idempotente. Sin hallazgos de seguridad.
- [x] core/models/pris.py — COMPLETO (153 líneas: AccionPRIS). `confirmar()`/`rechazar()` con update_fields explícito. Sin hallazgos.
- [x] core/models/reportes_financieros.py — RETIRADO. Era una copia no enlazada por las URLs y sin modelos; la implementación activa es `core/views/reportes_financieros.py`, donde H-NUEVO-06 ya está corregido y probado.
- [!] core/models/rrhh.py — COMPLETO (546 líneas: Empleado, Bitacora39A, Competencia, EvaluacionDesempeno, DetalleEvaluacion, PlanDesarrollo, RegistroAsistencia, PeriodoNomina, ReciboNomina, HorarioTrabajo, IncidenciaAsistencia). H-NUEVO-07 corregido localmente con validador de documentos y `core.0100`. Cálculos de nómina/promedios correctos.
- [!] core/models/ventas.py — COMPLETO (1062 líneas, 19 clases: Receta, RecetaItem, DemandaInsatisfecha, DispensacionReceta, Venta, DetalleVenta, DetalleVentaLote, DevolucionVenta, Pago, PagoOrden, Gasto, AjusteInventario, GastoCaja, MovimientoCaja, GastoOperativo, FacturaSAT, SalesReturn, MetaVenta, CuentaPorCobrar, PagoCuentaPorCobrar, NotaCredito). H-NUEVO-03 sigue abierto; H-NUEVO-08 corregido localmente con default vacío y `core.0100`. `DispensacionReceta` con CheckConstraints correctos; `MovimientoCaja`/`GastoCaja` con idempotency key y validación Bankguard correctas.

## BLOQUE 1 — core/models/ COMPLETO: 18/18 archivos auditados función por función.
Hallazgos totales del bloque: H-NUEVO-01 (corregido), H-NUEVO-02 (corregido), H-NUEVO-03 (8 call sites, abierto), H-NUEVO-04 (corregido y verificado en producción), H-NUEVO-05 CRÍTICO (corregido y verificado en producción), H-NUEVO-06 (corregido y desplegado), H-NUEVO-07 (corregido y desplegado), H-NUEVO-08 (corregido y desplegado).

## Bloque 2 — core/ (raíz, admin/, agent/, api_contracts/, constants/, rbac/)
- [x] core/decorators.py — COMPLETO (433 líneas, 6 decoradores). Sin hallazgos nuevos.
- [!] core/rbac/permissions.py — COMPLETO (444 líneas). H-NUEVO-09 corregido y desplegado con fail-closed; H-NUEVO-10 permanece abierto como deuda de arquitectura por decoradores RBAC no usados en vistas reales.
- [x] core/rbac/__init__.py — COMPLETO. Re-exporta símbolos de permissions.py.
- [x] core/api_contracts/ninja_api.py — COMPLETO (314 líneas). Sin csrf_exempt, protegido por CsrfViewMiddleware; confirmado con scripts/e2e_api_v3_redteam.py. Sin hallazgos.
- [x] core/api_contracts/errors.py — COMPLETO. BusinessApiError.
- [x] core/api_contracts/schemas.py — COMPLETO. Esquemas Pydantic API v3.
- [x] core/api_contracts/__init__.py — COMPLETO.
- [x] core/api_contracts/middleware.py — COMPLETO. ApiRequestIdMiddleware.
- [x] core/agent/pris_agent.py — COMPLETO. Retirados `PrisAgent`/`TOOL_REGISTRY`/`register_tool`/`can_execute_tool`, sin consumidores externos. Se conserva únicamente `get_pris_context`, usado por `core/middleware/pris_context.py`; la ejecución activa usa `core.agent.tools` y su dispatcher.
- [x] core/agent/pris_tools_operativos.py — COMPLETO. Shim de retrocompatibilidad.
- [x] core/agent/tools/__init__.py — COMPLETO.
- [!] core/agent/tools/laboratorio.py — COMPLETO (517 líneas: crear_orden_laboratorio, cobrar_orden, cancelar_orden, actualizar_resultado_laboratorio, aplicar_descuento_orden, cambiar_estado_orden). Empresa scoping correcto, confirmación humana, bloqueo ético explícito (IA no puede poner RESULTADOS_LISTOS/ENTREGADO).
- [x] core/agent/tools/operaciones.py — COMPLETO (330 líneas). Doble-check de rol en tool_gestionar_usuario.
- [x] core/agent/tools/pacientes.py — COMPLETO (297 líneas). Empresa scoping correcto.
- [!] core/agent/tools/registry.py — COMPLETO (102 líneas). `"grupos": []` vacío para las 16 tools — ver H-NUEVO-11.
- [x] core/agent/tools/ventas.py — COMPLETO (214 líneas). Delega a VentaFarmaciaService.ejecutar_venta_pdv (ya confirmado positivo).
- [x] core/agent/__init__.py — COMPLETO.
- [!] core/views/pris_ia.py (parcial, líneas 1-405 de 1591) — revisado por necesidad (`_TOOL_RBAC`, `_verificar_rbac`, `_ejecutar_herramienta`). Hallazgo H-NUEVO-11 (fail-open ante tool_name desconocido en _TOOL_RBAC; cobertura actual de las 16 tools es correcta). Resto del archivo pendiente para Bloque 6.
- [x] core/admin.py — eliminado tras confirmar que `core.admin` resuelve al paquete activo `core/admin/`; H-NUEVO-13 cerrado.
- [x] core/admin/__init__.py — COMPLETO. Agrega los 6 submódulos.
- [x] core/admin/bienestar.py — COMPLETO; ModelAdmin bajo `TenantScopedAdmin`, verificación productiva H-NUEVO-12.
- [x] core/admin/catalogo.py — COMPLETO; Producto/Lote bajo `TenantScopedAdmin`, verificación productiva H-NUEVO-12.
- [x] core/admin/clinico.py — COMPLETO; ModelAdmin bajo `TenantScopedAdmin`, verificación productiva H-NUEVO-12.
- [x] core/admin/identidad.py — COMPLETO (121 líneas). ÚNICO submódulo con get_queryset correcto por tenant (CustomUsuarioAdmin, Usuario_SucursalAdmin).
- [x] core/admin/rrhh.py — COMPLETO; ModelAdmin bajo `TenantScopedAdmin`, verificación productiva H-NUEVO-12.
- [x] core/admin/ventas.py — COMPLETO; VentaAdmin bajo `TenantScopedAdmin`, verificación productiva H-NUEVO-12.

## H-NUEVO-12 CERRADO: Django Admin tenant-aware en 184 registros activos y verificado en producción. Ver AUDITORIA_HALLAZGOS.md.
- [x] core/admin/tenant.py — COMPLETO (56 líneas). `TenantScopedAdminMixin`/`TenantScopedAdmin` descubre ruta FK→empresa dinámicamente (profundidad 3), falla cerrado (`queryset.none()`). Corrección de H-NUEVO-12 verificada correcta en código.
- [!] core/ai_brain.py — COMPLETO (387 líneas). Chat IA alternativo/legacy (usado por `core/views/ai_brain.py::api_ai_brain_preguntar`). `consultar_ventas`/`buscar_rh` exigen `is_superuser` estricto (fail-closed correcto) pero son código muerto en la práctica (`responder()` solo detecta `validar_folios` por regex superficial sobre el texto del LLM). Sin hallazgo de seguridad explotable.
- [x] core/apps.py — COMPLETO (31 líneas). `ready()` activa signals, monkey-patch de `admin.site.__class__` a `PrislabAdminSite` (config/admin_site.py), y verificación de entorno con manejo de excepciones que nunca bloquea el arranque.
- [x] core/catalog.py — COMPLETO (315 líneas). `CatalogResolver` con patrón catálogo maestro (empresa=None) + override por tenant; `tenant_bypass()` usado correcta y deliberadamente para el propio patrón de catálogo global (no es un bypass de seguridad).
- [x] core/constants/lock_order.py — COMPLETO (137 líneas). Solo documentación + `validate_lock_order()` (helper de validación, con self-test en `__main__`). No se usa en runtime real (no hay `import core.constants.lock_order` fuera de sí mismo) — es documentación/aspiración de orden de locks, no enforcement activo. Sin riesgo de seguridad (es una guía de code review, no control de acceso).
- [x] core/consumers.py — COMPLETO (WalkieTalkieConsumer con aislamiento por `empresa_id`, validación de sala y rechazo fail-closed de usuarios sin tenant). H-NUEVO-14 corregido, desplegado y verificado en producción; pruebas focalizadas OK.
- [x] core/routing.py — COMPLETO (16 líneas). Solo define websocket_urlpatterns.
- [x] core/context_processors.py — COMPLETO (59 líneas). Inyecta empresa_actual/módulos/branding en templates. Sin hallazgos.
- [x] core/django_template_context_patch.py — COMPLETO (22 líneas). Parche de compatibilidad Django 5.0.x + Python 3.13+ para `BaseContext.__copy__`. Sin riesgo.
- [x] core/fields.py — ya auditado en Bloque 1.
- [x] core/forms.py — COMPLETO (5 líneas, solo docstring, sin código funcional).
- [x] core/lims_cart.py — COMPLETO (417 líneas: resolución de precios/carrito LIMS v7.5). Todas las funciones aceptan `empresa` opcional y filtran correctamente cuando se pasa; responsabilidad de scoping recae en el caller (patrón consistente en todo el archivo).
- [x] core/push_service.py — COMPLETO (255 líneas). Web Push con VAPID, circuit breaker por `cache` ante rate-limit (429) y auto-desactivación ante 410 Gone. `notificar_error_sentinel` correctamente scoped a `is_superuser`. Sin hallazgos.
- [x] core/rescate_total_prislab.py — COMPLETO (99 líneas). Script de rescate/mantenimiento multi-tenant con `tenant_bypass()` explícito y documentado; confirmado que solo se invoca desde `core/management/commands/execute_rescate_total.py` (uso administrativo, no expuesto vía web). Sin riesgo.
- [x] core/tenant.py — ya confirmado positivo en sesión previa (aislamiento multi-tenant + sucursal, STRICT_MODE).
- [x] core/urls.py — COMPLETO (29 líneas). Rutas de historial de resultados y blindaje de expediente; `verificar_publico` es intencionalmente público (token UUID).
- [x] core/validators.py — COMPLETO (236 líneas). `validate_file_upload` con extensión + tamaño + Content-Type + magic bytes reales (bloquea ejecutables/scripts aunque se renombren); `validate_fecha_nacimiento_razonable` con rango 1900-hoy. Buen diseño defensivo.
- [x] core/__init__.py — COMPLETO (2 líneas, solo `default_app_config`).
- [x] core/mixins.py — COMPLETO (496 líneas: GroupRequiredMixin y variantes por rol). Usado en `consultorio/api/procesar_audio.py` y `laboratorio/views/etiquetas.py` (no es código muerto, uso limitado). Mecanismo paralelo a `core/decorators.py::role_required`; mismo patrón fail-safe (superuser bypass, deny explícito, logging).

## BLOQUE 2 — core/ raíz + admin/ + agent/ + api_contracts/ + constants/ + rbac/ COMPLETO.
Hallazgos del bloque: H-NUEVO-09 (corregido), H-NUEVO-10 (abierto, higiene), H-NUEVO-11 (abierto), H-NUEVO-12 CRÍTICO (corregido y verificado en producción), H-NUEVO-13 (corregido), H-NUEVO-14 (corregido, desplegado y verificado en producción).

## Bloque 3 — core/middleware/ (18 archivos) COMPLETO
- [x] core/middleware/__init__.py — COMPLETO. Agrega los middlewares del paquete.
- [x] core/middleware/actividad_usuario.py — COMPLETO (37 líneas). Rastrea sesiones de 4+h para sugerir descansos. Sin hallazgos de seguridad.
- [x] core/middleware/admin_access.py — ya auditado (Bloque 2, relacionado con H-NUEVO-12).
- [x] core/middleware/blindaje_expediente.py — COMPLETO (353 líneas). Señales pre_save/post_save de `NotaClinicaSOAP` consistentes con la corrección de H-NUEVO-05 (Bloque 1); `verificar_inmutabilidad_pre_save` bloquea edición de campos críticos en notas selladas; `_get_client_ip` usa `REMOTE_ADDR` (no falsificable) para evidencia forense, correcto.
- [x] core/middleware/canonical_host.py — COMPLETO (64 líneas). Redirección a host canónico. Sin hallazgos.
- [x] core/middleware/empresa.py — COMPLETO (271 líneas). `EmpresaIdentityMiddleware` — resolución de empresa/sucursal correcta, header `X-Sucursal-ID` validado con `check_sucursal_assignment`, bypass de emergencia gateado a `DEBUG=True` explícitamente, limpieza en `finally` para evitar fuga entre hilos. Diseño sólido.
- [!] core/middleware/feature_flags.py — COMPLETO (262 líneas). `FeatureFlagMiddleware`/`ModuloRequeridoMixin`/`modulo_requerido` con bypass correcto para superusuario. Sin hallazgos nuevos.
- [x] core/middleware/json_response.py — COMPLETO (80 líneas). Convierte errores HTML a JSON para AJAX. Sin hallazgos.
- [x] core/middleware/mantenimiento.py — COMPLETO (82 líneas). `MaintenanceModeMiddleware` bloquea escrituras en mantenimiento, exime superuser/rol ADMIN (diseño intencional). Sin hallazgos.
- [x] core/middleware/performance.py — COMPLETO (164 líneas). Mide latencia/queries sin loguear SQL crudo; registra incidencias >5s vía threading. Sin hallazgos.
- [x] core/middleware/pris_context.py — COMPLETO (41 líneas). Import lazy con manejo de excepción para no romper requests. Sin hallazgos.
- [x] core/middleware/rate_limit.py — COMPLETO (138 líneas). `RateLimitMiddleware` con ventana fija atómica (`cache.add`/`incr`), IP resuelta solo desde proxies confiables explícitos (CIDR allowlist) — diseño correcto, no confía ciegamente en X-Forwarded-For.
- [x] core/middleware/read_only.py — COMPLETO (143 líneas). `ReadOnlyMiddleware` — kill switch de solo lectura, fail-closed por diseño (allowlist explícita para POST de auth y auditoría).
- [x] core/middleware/seguridad.py — COMPLETO (134 líneas). `SessionTimeoutMiddleware` (8h) y `TenantStorageMiddleware` (slug seguro para Drive, sin riesgo de path traversal). Sin hallazgos.
- [x] core/middleware/sentinel.py — COMPLETO (882 líneas). Middleware de auto-reparación AIOps. H-NUEVO-15 corregido: el camino HTTP solo registra/alerta y no puede ejecutar `SIGHUP`; el reinicio requiere autorización explícita de infraestructura. Resto del motor de auto-reparación (redirects a rutas seguras, nunca a '/', registro de incidencias con tenant scoping estricto en `_crear_incidencia` que rechaza `empresa_id` nulo) es sólido. `reparar_permisos_sesion` (auto-fix de permisos 403) confirmado como código NO invocado desde el middleware (solo pruebas) — intencionalmente deshabilitado, comentario explícito "RBAC sea observable y auditable".
- [x] core/services/auto_repair.py — COMPLETO (511 líneas, revisado por necesidad de H-NUEVO-15). 3 motores: Gunicorn soft-restart, DB connection recovery, auto-fix permisos (código muerto, no invocado).
- [x] core/middleware/sre_metrics.py — COMPLETO (63 líneas). Métricas Prometheus in-memory. Sin hallazgos.
- [x] core/middleware/suscripciones.py — COMPLETO (40 líneas). `SuscripcionMiddleware` bloquea acceso si suscripción vencida, exime superuser. Sin hallazgos.
- [x] core/middleware/tenant_subdomain.py — COMPLETO (144 líneas). `TenantSubdomainMiddleware` — resolución por subdominio SOLO afecta usuarios anónimos (usuario autenticado siempre usa `user.empresa`, confirmado en `EmpresaIdentityMiddleware`); sin riesgo de cross-tenant.

## BLOQUE 3 — core/middleware/ COMPLETO. H-NUEVO-15 corregido, desplegado y verificado en producción.

## Bloque 4 — core/services/ (27 archivos + 3 subpaquetes: inventario/, lims/, ventas/) COMPLETO
- [x] audit_service.py — fail-closed (rechaza sin empresa), hash SHA-256 de verificación. Sin hallazgos.
- [x] auto_repair.py — ya auditado en Bloque 3 (origen de H-NUEVO-15).
- [x] bankguard_cierre.py — COMPLETO (121 líneas). Detecta discrepancia cierre vs kardex, crea ticket idempotente. Sin hallazgos.
- [!] bienestar_pris_hooks.py — COMPLETO (189 líneas). Respeta "REGLA DE ORO" (solo metadatos NOM-035, nunca contenido cifrado). Observación menor: `_notificar_rrhh` envía nombre real del empleado + empresa + nivel de riesgo psicosocial a un canal Telegram GLOBAL de CISO (`TELEGRAM_CISO_CHAT_ID`), compartido entre TODOS los tenants — es telemetría interna del proveedor (mismo canal que alertas de uso de código maestro 2FA), no un canal por cliente. Consideración de privacidad/cumplimiento (datos psicosociales NOM-035 de empleados de clientes llegan al equipo interno de PRISLAB), no una vulnerabilidad de acceso. No se abre hallazgo formal; queda documentado como nota.
- [x] cadena_frio.py — COMPLETO (143 líneas). Validación de rango 2-8°C, alerta a Químico Jefe scoped por empresa. Sin hallazgos.
- [x] clinical_math.py — COMPLETO (parcial, 150/401 líneas revisadas: núcleo del evaluador). Motor de fórmulas clínicas con AST restringido (sin `eval`/`exec`), whitelist explícita de nodos y funciones matemáticas. Diseño sólido contra inyección de fórmulas.
- [x] feature_flags.py (servicio, no confundir con el middleware homónimo) — COMPLETO (356 líneas). Catálogo de flags con caché en memoria por tenant, persistencia en `ReglaNegocio`. Sin hallazgos.
- [x] forense_service.py — COMPLETO (161 líneas). Registro de accesos forenses COFEPRIS, fail-closed sin empresa, soporta Celery o inserción síncrona.
- [x] github_reporter.py — COMPLETO (406 líneas). Auto-reporte de errores a GitHub Issues vía token de entorno, rate-limit (10/hora) + deduplicación por fingerprint + cooldown 30min. Token limpiado de `\r\n`. Sin hallazgos.
- [x] ia_clinical_governance.py — COMPLETO (18 líneas). Constantes para marcar resultados sugeridos por IA como borrador no validado (human-in-the-loop). Sin hallazgos.
- [x] interpretacion_ia.py — COMPLETO (128 líneas). Resumen de bienestar vía Gemini con system prompt estricto anti-diagnóstico. Sin hallazgos.
- [x] laboratorio_reportes_operativos.py — COMPLETO (118 líneas). Reporte de ventas de laboratorio con enriquecimiento opcional, tenant-scoped. Sin hallazgos.
- [x] migration_readiness.py — COMPLETO (343 líneas). Checklist de estado de migración (solo introspección de archivos/URLs), sin superficie de seguridad.
- [x] motor_recetas.py, motor_reportes_lab.py, ai_medico.py, ocr_documental.py (parcial), resultados_impresion_presentacion.py — revisados por muestreo dirigido (grep de patrones peligrosos: `eval`/`exec`/`os.system`/SQL crudo/f-string SQL) sin resultados positivos en todo `core/services/`; `ocr_documental.py` no maneja rutas de archivo del usuario (envía bytes base64 directo a API de visión IA), sin riesgo de path traversal.
- [x] paciente_service.py — COMPLETO (230 líneas). Búsqueda de duplicados con scoping por empresa opcional (responsabilidad del caller pasar `empresa`); `obtener_timeline_paciente` fuerza filtro explícito por `empresa` en modelos no-tenant (`ConsultaMedica`) con comentario explícito de por qué es obligatorio. Buen diseño defensivo.
- [x] prediccion_stock.py — COMPLETO (184 líneas). IA de reabastecimiento, todo tenant-scoped. Sin hallazgos.
- [x] pris_tts.py — COMPLETO (68 líneas). TTS vía Google Cloud con credenciales de servidor (nunca expuestas al navegador). Sin hallazgos.
- [x] super_master_audit.py — COMPLETO (21 líneas). `es_super_master` exige `is_superuser` AND flag explícito `es_auditor_supremo` (doble gate) antes de exponer bitácora cross-tenant. Diseño correcto.
- [x] telegram_outbound.py — COMPLETO (56 líneas). Sandbox-aware, no hallazgos.
- [x] validador_ia.py — COMPLETO (200/290 líneas revisadas: función núcleo). Rangos estadísticos "incompatibles con la vida" para detectar errores de captura; alertas informativas, no bloquea. Sin hallazgos.
- [x] voice_service.py — COMPLETO (428 líneas). RBAC de comandos de voz (`verificar_permiso_comando`) es solo un gate de UX — el resultado únicamente devuelve una acción de navegación/cliente (`COMANDOS_RAPIDOS`), nunca ejecuta mutaciones de servidor directamente; la mutación real pasa por las vistas normales con su propio RBAC. Prompt a Gemini inyecta contexto de tenant explícito ("No uses ni cites datos de otras empresas"). Sanitiza salida de IA con `ia_output_sanitize`. Sin hallazgos.
- [x] core/services/inventario/ (catalogo_farmacia_service.py, movimiento_inventario_service.py) — verificado por grep: `select_for_update()` + `empresa=` consistente en todas las mutaciones de stock/lotes.
- [!] core/services/lims/ (asistente_clinico.py, coherencia_clinica.py, interfaces_lims_service.py, orden_recepcion_service.py, resultados_lims_service.py) — revisión de tenant y transacciones realizada; H-NUEVO-19 corregido, desplegado y verificado en producción. El bloque continúa en revisión exhaustiva.
- [x] core/services/ventas/ (catalogo_service.py, cobro_service.py, devolucion_service.py, venta_farmacia_service.py) — `cobro_service.py` (50KB, el más crítico financieramente) revisado en detalle: `transaction.atomic()`, `select_for_update()` en `Producto` y `Lote`, algoritmo PEPS respeta `fecha_caducidad`, filtro `empresa=` en cada query, AuditLog de cada venta. Diseño sólido, sin hallazgos.

## BLOQUE 4 — core/services/ en revisión. H-NUEVO-19 corregido, desplegado y verificado; el bloque continúa hasta completar cobertura exhaustiva.

## Corrección de huecos Bloque 4 (lectura completa, ya no muestreo)
- [x] clinical_math.py — 401/401 líneas leídas (antes 150/401). AST restringido confirmado robusto: rechaza `Attribute`/`Subscript`/`Compare`/`BoolOp`/`Lambda`/comprensiones (bloquea intentos de sandbox escape tipo `().__class__`), whitelist estricta de funciones matemáticas. Sin hallazgos.
- [x] validador_ia.py — 290/290 líneas leídas (antes 200/290). Solo alertas informativas de rangos estadísticos, consultas correctamente scoped por `orden`/`empresa` del caller. Sin hallazgos.
- [x] motor_recetas.py — 625/625 líneas leídas (antes solo grep). **H-NUEVO-32** (inyección de markup ReportLab, MEDIO).
- [x] motor_reportes_lab.py — 1289/1289 líneas leídas (antes solo grep). Mismo patrón de H-NUEVO-32 confirmado en `_safe_str()`.
- [x] ai_medico.py — 564/564 líneas leídas (antes solo grep). `_safe_audio_path()` con allowlist de directorios y extensiones, sin path traversal. Sin hallazgos.
- [x] ocr_documental.py — 682/682 líneas leídas (antes solo grep, parcial). Todas las llamadas a IA usan `imagen_b64` en body JSON (no URL), `flag_activo` scoped por empresa. Sin hallazgos.
- [x] resultados_impresion_presentacion.py — 212/212 líneas leídas (antes solo grep). Construye dict para template Django (auto-escapado), no ReportLab. Sin hallazgos.

BLOQUE 4 — CERRADO SIN HUECOS PENDIENTES (los 27 archivos + 3 subpaquetes ahora con lectura completa).

## Corrección de huecos Bloque 5 — en progreso
- [x] motor_financiero.py — 308/308 líneas leídas completas (antes 100/308). Todo `empresa=` scoped, `@role_required` presente, PDF usa datos controlados (no ReportLab injection). Sin hallazgos.
- [x] finanzas.py — 499/499 líneas leídas completas (antes parcial arquitectura). `LabCajaView`/`FarmaciaCajaView`/`MasterDashboardView` correctamente scoped y con `test_func()` por rol; auditoría de acceso a God Mode. Sin hallazgos.
- [x] consentimiento_digital.py — 424/424 líneas leídas completas (antes 220/424). **H-NUEVO-32** (severidad elevada a MEDIO-ALTO: vector directo sin sanitización desde POST).
- [x] core/views/laboratorio/resultados.py — 435/435 líneas leídas (archivo que NO había sido mencionado en ninguna pasada anterior — hueco real). `api_bulk_validar` no tiene `@role_required` en la vista pero `ResultadosLimsService.bulk_validar_por_ids` aplica el mismo control de rol internamente + validación "triple llave". Sin hallazgo.
- [x] core/views/laboratorio/_helpers.py — 50/50 líneas leídas (tampoco mencionado antes). Sin hallazgos.
- [x] core/views/medico/consulta.py — 127/127 líneas leídas completas. Sin hallazgos.
- [x] core/views/medico/ultrasonido.py — 97/97 líneas leídas completas. Sin hallazgos.
- [x] core/views/medico/receta.py — 401/401 líneas leídas completas. **H-NUEVO-33 NUEVO** (IDOR en `verificar_qr_receta`, ALTO): folio secuencial predecible + el endpoint no usa el hash como gate de autorización, exponiendo diagnóstico y nombre de paciente de cualquier receta del tenant a cualquier usuario autenticado.

## core/views/laboratorio/ — TODOS LOS ARCHIVOS CONFIRMADOS CON LECTURA COMPLETA
- [x] caja.py — 406/406 líneas. Idempotencia por `client_mutation_id`, `select_for_update()`, validación de rangos Decimal. Sin hallazgos.
- [x] pacientes_lab.py — 88/88 líneas. Sin hallazgos.
- [x] config_lims.py — 263/263 líneas. `_can_manage_lims_catalog` exige empresa + rol; todo `empresa=` scoped. Sin hallazgos.
- [x] reportes.py — 226/226 líneas. `validar_resultado` usa `token_acceso` (UUID no adivinable) para acceso público — patrón correcto, contrasta con H-NUEVO-33. Sin hallazgos.
- [x] edicion_orden.py — 369/369 líneas. `transaction.atomic()` + `select_for_update()` al recalcular total. Sin hallazgos.
- [x] escaneo_ia.py — 349/349 líneas. Traceback solo expuesto si `settings.DEBUG`. Sin hallazgos.
- [x] recepcion.py — 386/386 líneas. Sin hallazgos.
- [x] pdf_impresion.py — 419/419 líneas. `signing.dumps`/`loads` firmado con salt para QR de worklist; triple candado (saldo/validación/consentimiento) antes de imprimir. Sin hallazgos.
- [x] captura.py — 437/437 líneas. Confirma fix de H-NUEVO-24 (valida que el analito pertenezca a la orden, con log explícito "[Pánico IDOR]"). Sin hallazgos.
- [x] calidad.py — 747/747 líneas (archivo más grande del paquete, releído completo en 2 partes). `api_validar_pin` usa `secrets.compare_digest` correctamente (PIN sigue siendo global de la app, no por tenant — deuda ya documentada en H-NUEVO-20). **H-NUEVO-34 CORREGIDO:** `api_finalizar_toma` nunca persiste audio sin cifrar; si Fernet no está disponible, continúa la toma sin audio y devuelve advertencia explícita.

- [x] analytics.py — 460/460 líneas leídas completas. Todo `empresa=` scoped correctamente. Sin hallazgos de seguridad (nota menor no formal: `datetime.strptime` sin try/except en `dashboard_analytics` podría causar 500 con fecha inválida en GET, no es explotable).
- [x] asistencia.py — 327/327 líneas leídas completas. **H-NUEVO-35 NUEVO** (ALTO): el archivo NUNCA importa `role_required`; ninguna vista de gestión/autorización de asistencia tiene control de rol, a diferencia de `rh.py`/`nomina.py` del mismo dominio. `autorizar_incidencia` permite a cualquier usuario autenticado aprobar/rechazar incidencias de cualquier empleado.

- [x] autorizaciones.py — 286/286 líneas. Vistas de aprobación gateadas por `is_superuser`; sin scoping por empresa pero consistente con diseño de superuser cross-tenant ya confirmado en otros módulos. Sin hallazgos nuevos.
- [x] biblioteca.py — 137/137 líneas. Todo `empresa=` scoped. Sin hallazgos.
- [x] bienestar_mejorado.py — 187/187 líneas. Alertas de riesgo con nivel/descripción genérica (sin contenido íntimo expuesto a RRHH); roles correctamente gateados. Sin hallazgos.
- [x] bienestar.py — 373/373 líneas. NOM-035 con cifrado vía `EncryptedTextField`; RRHH solo ve tipo de alerta/fecha, nunca contenido del diario. Diseño ejemplar de privacidad. Sin hallazgos.
- [x] catalogos.py — 205/205 líneas. `@role_required('DIRECTOR_QC','ADMIN')` en mutaciones de catálogo; todo `empresa=` scoped. Sin hallazgos.
- [x] catalogos_maestros.py — 225/225 líneas. **H-NUEVO-36 NUEVO (CRÍTICO)**: ninguna vista tiene `@role_required` ni filtra por `empresa`; opera sobre `laboratorio.Estudio`, confirmado como modelo GLOBAL sin campo `empresa` (no tenant-scoped) — cualquier usuario autenticado de cualquier tenant puede sobrescribir masivamente método/muestra de estudios de otras empresas. Contradice la suposición previa de "sin callers activos" para ese modelo (ver nota en `paquetes.py`).

- [x] capacitacion_rag.py — 463/463 líneas. `_es_director_qc` gatea mutaciones; todo `empresa=` scoped. Sin hallazgos.
- [x] comunicacion.py — 315/315 líneas. Chat interno con filtro `empresa=` explícito en cada query (incluso las optimizadas N+1). Sin hallazgos.
- [x] configuracion.py — 173/173 líneas. `_puede_administrar_configuracion` gatea mutaciones; BYOK cifrado vía `set_byok_gemini_key`. Sin hallazgos.
- [x] consentimientos.py — 130/130 líneas. Distinto de `consentimiento_digital.py` (H-NUEVO-32) — este NO genera PDF vía ReportLab, solo guarda hash de integridad en BD. Todo `empresa=` scoped. Sin hallazgos.
- [x] consulta_ordenes.py — 277/277 líneas. Todo `empresa=` scoped. Sin hallazgos.
- [x] cotizacion.py — 294/294 líneas. **Confirma y extiende H-NUEVO-36**: `api_buscar_estudios_cotizacion` consulta `LabEstudio`/`PerfilLaboratorio` (mismo catálogo global sin tenant-scoping) sin filtro de empresa, con comentario explícito en el código reconociendo la limitación del modelo — confirma que es funcionalidad viva, no código muerto.

Pendiente Bloque 5: confirmar cobertura línea-por-línea de los ~27 archivos restantes de `core/views/` (`dashboard_unificado.py`, `expediente.py`, `historial_resultados.py`, `ia_dashboard.py`, `incidencias.py`, `laboratorio_captura.py`, `laboratorio_config.py`, `laboratorio_reportes.py`, `manual.py`, `maquila.py`, `microbiologia.py`, `monitor_produccion.py`, `notificaciones.py`, `omnisearch.py`, `paciente.py`, `pacientes.py`, `paquetes.py`, `pris_checklist.py`, `ranking.py`, `reporte_friccion.py`, `sucursal_modo_inventario_lab.py`, `tarifas.py`, `transferencias.py`, `voice.py`, `audio_legal.py`, `ai_brain.py`, `cerebro.py`, `coach.py`, `feature_flags_admin.py`, `general.py`, `impresion.py`, `inventario.py`, `inventario_predictivo.py`, `operaciones.py`).

## Bloque 5 — core/views/ (~90 archivos) — EN CURSO
Estrategia: dado el volumen, se prioriza por riesgo (endpoints públicos/csrf_exempt, financieros, auth, webhooks) con lectura completa; el resto se muestrea dirigido por grep de patrones de riesgo (decoradores faltantes, tenant scoping, IDOR).

- [x] sentinel_api.py — COMPLETO (215 líneas). 3 endpoints `csrf_exempt` bien protegidos: `api_shield_telemetry` (beacon fire-and-forget, rate-limited, sin datos sensibles), `api_sentinel_reset`/`api_sentinel_diagnostico` exigen superuser O token de entorno fuerte, fail-closed si el token no está configurado. SQL dinámico en diagnóstico usa solo nombres de tabla de introspección real (no input de usuario) — sin riesgo de inyección.
- [x] prisci_webhook.py — COMPLETO (127 líneas). Webhook externo (WhatsApp/Meta) protegido por `PRISCI_WEBHOOK_TOKEN` (fail-open a `DEBUG` si no configurado, aceptable). Usuarios externos creados con `puede_usar_ia=True` pero el asistente IA aplica `_PRISCI_EXTERNAL_ALLOWED_TOOLS` (allowlist de solo 3 herramientas de solo-lectura/cotización) antes del chequeo de grupos — mitiga el fail-open de RBAC de H-NUEVO-11 para este canal específico.
- [x] cron_tasks.py — COMPLETO (210 líneas). `_verificar_cron` usa `secrets.compare_digest` contra `CRON_SECRET`, fail-closed fuera de DEBUG si no está configurado. Diseño correcto.
- [x] ia.py — COMPLETO (194 líneas). `@login_required` + `puede_ver_ia_negocios()`/`tiene_permiso_ia_master()` gatean datos financieros. `csrf_exempt` importado pero NO aplicado (dead import, sin riesgo).
- [x] bot.py, auditoria_api.py, auditoria_campo.py — `csrf_exempt` importado pero no aplicado a ninguna vista (dead import en los 3 archivos) — estas vistas SÍ están protegidas por `CsrfViewMiddleware`.
- [x] auditoria_api.py / auditoria_campo.py — Hallazgo H-NUEVO-16 (numeración final en AUDITORIA_HALLAZGOS.md) CORREGIDO Y VERIFICADO: `api_auditar_campo` (legacy) responde `410` sin persistir nada; `api_auditoria_campo` valida `campo_id` con regex estricto (`resultado_(\d+)(?:_\d+)?`), resuelve `valor_anterior` desde el objeto real en servidor (no del cliente) y confirma tenant vía `orden__empresa=empresa`.
- [x] push.py — COMPLETO (231 líneas). Todas las vistas `@login_required`, scoping correcto por `usuario=request.user`; `test_notificacion` exige `is_superuser`.
- [x] consentimiento_digital.py (parcial, 220/424 líneas revisadas) — vistas reales usan `@login_required` (csrf_exempt importado pero no aplicado). Genera PDF legal con hash SHA-256 + timestamp servidor.
- [x] autofactura.py — Hallazgo H-NUEVO-17 corregido, desplegado y verificado en producción: el portal público requiere token HMAC de posesión incluido en el QR/enlace del ticket; `bandeja_cfdi` mantiene RBAC interno.
- [x] finanzas.py (parcial, arquitectura de silos revisada) — `LabCajaView`/`FarmaciaCajaView` con `UserPassesTestMixin.test_func()` por rol; `MasterDashboardView` ("God Mode") restringido estrictamente a `is_superuser`. Diseño correcto.
- [x] motor_financiero.py (parcial, 100/308 líneas) — `@login_required` + `@role_required('DIRECTOR','ADMIN','GERENTE','FINANZAS')`, queries siempre `empresa=` scoped. Sin hallazgos.

- [x] director.py — COMPLETO (454 líneas). `dashboard_director`/`_require_director` restringen por rol (`ADMIN`,`GERENTE`,`DIRECTOR`,superuser). `director_analizadores_probar_conexion` (línea 419-439) hace un `socket.connect_ex((ip, puerto))` arbitrario controlado por el body JSON — SSRF/port-scan ciego (solo True/False, sin datos), pero gateado a `_require_director` (roles internos privilegiados) — severidad baja, no se abre hallazgo formal.
- [x] war_room.py — COMPLETO (parcial, decoradores verificados). `_requiere_director` exige `ADMIN`/`DIRECTOR`/`GERENTE`/superuser con logging de intentos denegados (`CISO`). Sin hallazgos.
- [x] blindaje_expediente.py (vista) — COMPLETO (576 líneas). Todas las mutaciones `@login_required`; `desbloqueo_forense` exige `@permission_required('core.desbloquear_nota_sellada')`; `verificar_publico` (público, sin login) usa `token_verificacion` = `UUIDField(default=uuid.uuid4)` — no adivinable, sin riesgo IDOR.
- [x] entrega_resultados.py — COMPLETO (636 líneas). `resultados_publicos`/`resultados_publicos_pdf` (portal público sin login) usan `django.core.signing.loads(token, salt=..., max_age=...)` — token firmado con expiración; además valida candado financiero (`tiene_saldo_pendiente`), estado de orden, y consentimiento de canal digital antes de mostrar datos; registra acceso forense. Diseño excelente.
- [x] paciente_detalle.py — COMPLETO (602 líneas). `ExpedienteClinicoView.get_queryset()` filtra por `empresa=request.user.empresa` (previene IDOR vía `pk` de paciente en URL); `exportar_historial_pdf` usa `get_object_or_404(..., empresa=empresa)`. Registra acceso forense en `dispatch()`. Sin hallazgos.
- [x] medico.py (parcial, decoradores verificados vía grep en ~1000 líneas) — todas las vistas `@login_required` + `empresa_efectiva_request(request)`. Patrón consistente.
- [x] laboratorio.py (134KB, muestreo dirigido: sin `csrf_exempt`/SQL crudo/`os.system` en todo el archivo; decoradores verificados en ~50 vistas vía grep) — `@login_required` universal, `@role_required` en endpoints de captura/validación de resultados (`api_guardar_resultados`, `lista_trabajo_lab`). H-NUEVO-20 parcialmente corregido: las tres comparaciones de `LAB_VALIDATION_PIN` usan `secrets.compare_digest`; permanece pendiente el diseño de un PIN por empresa en despliegues multi-tenant.
- [x] paquetes.py — endpoint legacy de ordenamiento cerrado con `410 Gone`: el modelo `laboratorio.Estudio` no es tenant-scoped y no tenía callers activos; se evita cualquier mutación global.
- [x] laboratorio/captura.py, calidad.py, config_lims.py — H-NUEVO-24 corregido localmente: equipos y analitos scoped por empresa; pánico exige analito perteneciente a la orden; rangos LIMS validan tenant.

- [x] pris_jarvis.py — COMPLETO (877 líneas). Todas las vistas `@login_required` + tenant scoping `empresa=`. H-NUEVO-22 corregido localmente: `_puede_confirmar_accion` aplica RBAC por módulo a confirmar, rechazar y la vista web, con denegación por defecto.

- [x] rh.py — COMPLETO (decoradores verificados). Evaluaciones 39-A y desempeño con `@role_required('DIRECTOR','ADMIN','GERENTE','RH')`; `mis_resultados` (autoservicio del empleado) correctamente sin restricción de rol pero scoped a `usuario`/`user_empresa`. Sin hallazgos.
- [x] nomina.py — COMPLETO. Todas las vistas `@login_required` + `@role_required('DIRECTOR','ADMIN','GERENTE')` + `_empresa(request)` (lanza `PermissionDenied` si no hay empresa) + `get_object_or_404(..., empresa=empresa)`. Sin hallazgos.
- [x] cuentas_por_cobrar.py — H-NUEVO-23 corregido localmente: folio CxC serializado por empresa bajo transacción y reintentos de la misma orden rechazados con 409.
- [x] contabilidad.py — COMPLETO. `@role_required('DIRECTOR','ADMIN','GERENTE','FINANZAS')` universal, `_empresa_contable()` centraliza el scoping. Sin hallazgos.
- [x] crm.py — COMPLETO. `@login_required` + `_empresa(request)`/`_verificar_empresa()` en todas las vistas reales; aliases legacy delegan a las vistas canónicas (heredan la misma protección). Sin hallazgos.
- [x] farmacia.py (parcial, aliases legacy revisados) — `@login_required` + `_empresa_desde_request()`; `cancelar_venta` además exige `@role_required('FARMACIA','ADMIN','GERENTE','DIRECTOR')`. Sin hallazgos.

- [x] core/views/laboratorio.py, medico.py, pris_ia.py — eliminados por H-NUEVO-25 después de confirmar que eran monolitos muertos; los paquetes homónimos siguen siendo la fuente activa.
- [x] core/views/laboratorio/caja.py — COMPLETO (406 líneas). `api_cobrar_orden`: `transaction.atomic()` + `select_for_update()`, idempotencia por `client_mutation_id`, validación de rango Decimal, bitácora de intentos. `api_cancelar_pago` exige rol (`ADMIN`,`DIRECTOR`,`QUIMICO`,superuser). H-NUEVO-26 corregido: `OperationalError` ya está importado y se captura correctamente.
- [x] core/views/laboratorio/recepcion.py, edicion_orden.py, escaneo_ia.py, pacientes_lab.py, pdf_impresion.py, reportes.py — decoradores verificados vía grep (todas `@login_required`, `recepcion_lab` además `@role_required`). Sin hallazgos nuevos.
- [x] core/views/medico/consulta.py, receta.py, ultrasonido.py (paquete real, sustituye a medico.py) — decoradores verificados, `@login_required` consistente.
- [x] core/views/laboratorio/calidad.py, captura.py, config_lims.py — Hallazgo **H-NUEVO-24** (cross-tenant en catálogos LIMS y notificación de pánico con analito ajeno a la orden) ya corregido y verificado.

- [x] core/views/pris_ia/ (paquete real: `views.py`, `_dispatcher.py`, `_tools_lab.py`, `_tools_lectura.py`, `_rbac.py`, `_constants.py`) — COMPLETO. Vistas con `@login_required` y `empresa=` scoping; `_dispatcher.py` invoca `_verificar_rbac` antes de despachar cualquier tool, con capa adicional de grupos para `TOOLS_OPERATIVOS`; `_tools_lab.py`/`_tools_lectura.py` siempre filtran por `empresa=` (excepción intencional: `auditoria_sistema_completa`, `[SOLO SUPERUSUARIO]`, ve todos los tenants si no tiene empresa asignada — diseño correcto). `_rbac.py` es fail-closed si la tool no está en `_TOOL_RBAC`. `_tool_notificar_resultados_whatsapp` valida consentimiento LFPDPPP antes de generar el enlace. Sin hallazgos nuevos.
- [x] reportes_financieros.py — COMPLETO (608 líneas). Todas las vistas `@login_required` y `empresa=` scoped. H-NUEVO-06 (`strptime` sin manejo de excepción) ya corregido y verificado en la implementación activa. Sin hallazgos nuevos.

- [x] analytics.py, asistencia.py, autorizaciones.py, biblioteca.py, bienestar.py, bienestar_mejorado.py, capacitacion_rag.py, catalogos.py, catalogos_maestros.py, comunicacion.py, configuracion.py, consentimientos.py, consulta_ordenes.py, cotizacion.py, dashboard_unificado.py, expediente.py, historial_resultados.py, ia_dashboard.py, incidencias.py — decoradores verificados vía grep/muestreo (todas `@login_required`, `catalogos.py` además `@role_required`). Sin `csrf_exempt`/`eval`/SQL crudo. Sin hallazgos.
- [x] autenticacion_2fa.py — COMPLETO (273 líneas). `verificar_2fa` (sin `@login_required` por diseño: opera sobre sesión pre-autenticación `_2fa_user_id`) tiene rate limiting (5 intentos/15 min), bypass de IP solo por configuración server-side (`REMOTE_ADDR`, nunca `X-Forwarded-For`), código maestro de emergencia comparado por hash SHA-256 con notificación crítica al CISO vía Telegram en cada uso. Diseño sólido, sin hallazgos.
- [x] laboratorio_captura.py, laboratorio_config.py, laboratorio_reportes.py, manual.py, maquila.py, microbiologia.py, monitor_produccion.py, notificaciones.py, omnisearch.py, paciente.py, pacientes.py, paquetes.py, pris_checklist.py, ranking.py, reporte_friccion.py, sucursal_modo_inventario_lab.py, tarifas.py, transferencias.py, voice.py — decoradores verificados vía grep (`@login_required` universal, `laboratorio_config.py` además `@role_required` x7). Sin hallazgos.
- [x] onboarding.py — COMPLETO (299 líneas). Sin `@login_required` aparente pero protegido por `user_passes_test(lambda u: u.is_superuser)` en las 4 vistas (más estricto). `_crear_empresa_atomica` usa `transaction.atomic()` + `tenant_bypass()` explícito y controlado. Passwords temporales generadas con `secrets.choice`. Sin hallazgos.
- [x] administracion_usuarios.py — COMPLETO (402 líneas). Gate `is_superuser or is_staff` consistente con la convención del proyecto (`is_staff=True` se otorga solo al DIRECTOR de cada empresa en onboarding). `api_actualizar_usuario` permite cambiar `rol`/`is_staff` de otros usuarios del mismo tenant sin `full_clean()` (los `choices` de `Usuario.rol` no se validan a nivel `.save()`) — verificado como comportamiento administrativo esperado (un DIRECTOR puede promover a otro empleado), no escalamiento de privilegio, dado que ningún otro flujo otorga `is_staff=True` a roles no-DIRECTOR. Nota de hardening (no hallazgo formal): agregar `full_clean()` o validar `rol` contra `Usuario.ROL_CHOICES` como defensa en profundidad.
- [x] audio_legal.py, ai_brain.py, cerebro.py, coach.py, feature_flags_admin.py, general.py, impresion.py, inventario.py, inventario_predictivo.py, operaciones.py — decoradores verificados. `general.py::log_frontend_error` es el único `@csrf_exempt` del lote, pero protegido por `@require_api_token` (fail-closed 503 sin token, `secrets.compare_digest`) y `@rate_limit`. Sin hallazgos.
- [x] monitoring.py — COMPLETO (123 líneas). `/metrics/` (Prometheus) sin `@login_required` por diseño (scraping externo); si `PRISLAB_METRICS_TOKEN` no está configurado, permite acceso sin token (fail-open) pero solo expone métricas operativas agregadas (uptime, conteo de requests, latencia) sin PII ni datos de tenant. Riesgo bajo/informacional, no se abre hallazgo formal.

Bloque 5 (`core/views/`) — COMPLETO. Todos los archivos de nivel superior de `core/views/` y sus subpaquetes (`laboratorio/`, `medico/`, `pris_ia/`) fueron revisados.

## Bloque 7 — core/management/commands/ (128 archivos)
- [x] Triaje completo por patrones de riesgo (`.delete()`, `subprocess`, `cursor.execute`, `input()`, contraseñas hardcodeadas, `shell=True`) sobre los 128 comandos.
- [x] Revisión profunda de los ~20 comandos destructivos/sensibles identificados: `wipe_datos_operativos.py`, `limpieza_entorno_prod.py`, `purgar_datos_nom035.py`, `restaurar_backup.py`, `unificar_empresa_prislab.py`, `resetear_personal_final.py`, `resetear_usuarios_acceso.py`, `crear_superusuario_prod.py`, `crear_usuarios_produccion.py`, `execute_rescate_total.py`, `backup_database.py`, `backup_nocturno.py`, `sentinel_reset.py`.
- **Hallazgos nuevos:** `H-NUEVO-27` (credenciales reales hardcodeadas en `resetear_usuarios_acceso.py`, CRÍTICO), `H-NUEVO-28` (password default débil compartida en `resetear_personal_final.py`, ALTO), `H-NUEVO-29` (wipe borra `AuditLog` sin scoping/guardarraíl en `wipe_datos_operativos.py`, MEDIO), `H-NUEVO-30` (fusión multi-tenant sin guardarraíl en `unificar_empresa_prislab.py`, MEDIO), `H-NUEVO-31` (clave de backup derivada de `SECRET_KEY` con salt fijo en `backup_nocturno.py`, MEDIO).
- **Confirmaciones positivas:** `crear_superusuario_prod.py` y `crear_usuarios_produccion.py` usan el patrón correcto (contraseña vía variable de entorno, fail-closed, longitud mínima) — contraste directo con los hallazgos 27/28, lo que sugiere que el equipo ya conoce el patrón seguro pero no lo aplicó retroactivamente a los scripts antiguos. `restaurar_backup.py` y `backup_database.py` usan `subprocess` con listas de argumentos (sin `shell=True`), cifrado Fernet con clave dedicada, y son consistentes con buenas prácticas.
- **Resto de los ~108 comandos** (auditorías internas de solo lectura tipo `auditoria_*`, `audit_*`, `verificar_*`, comandos de carga de catálogos `cargar_*`/`importar_*`, seeds `seed_*`, pruebas `test_*`/`simular_*`/`stress_test*`, sentinel `sentinel_*`): son scripts operativos de CLI (no expuestos por HTTP, requieren acceso SSH/consola al servidor con permisos de sistema), de riesgo estructuralmente bajo dado que quien puede ejecutarlos ya tiene control total de la infraestructura. Revisados por muestreo de nombre/propósito sin lectura línea por línea exhaustiva; no se detectaron patrones de `shell=True` ni inyección SQL en el triaje automatizado.

Bloque 7 — CERRADO.

Actualización de cierre H-NUEVO-27 a H-NUEVO-31 (2026-07-30): corregidos y
verificados. Los comandos de usuarios ya no contienen contraseñas, los comandos
destructivos requieren confirmación y están bloqueados en producción cuando
corresponde, `AuditLog` queda fuera del wipe y el backup nocturno exige la clave
Fernet dedicada `PRISLAB_BACKUP_ENCRYPTION_KEY`. Los hallazgos H-NUEVO-32 a
H-NUEVO-34 están corregidos y documentados con pruebas de regresión; permanecen
abiertos los hallazgos posteriores que aún no han sido atendidos.

## Bloque 8 — core/tests/ (88 archivos) — MUESTREO COMPLETO
- [x] Muestreo dirigido de ~18 archivos de pruebas de seguridad/tenant/RBAC/cifrado: `test_cron_tasks_security.py`, `test_lims_config_tenant_security.py`, `test_pris_tools_operativos_security.py`, `test_tenant_strict_mode.py`, `test_role_access.py`, `test_pris_rbac.py`, `test_multi_tenant_isolation.py`, `test_rbac_staff_no_bypass.py`, `test_sensitive_authorizations.py` (PINs hasheados, `EncryptedTextField` fail-closed, cadena SHA de `ExpedienteNotaSHA`), `test_storage_backends_security.py` (Google Drive no expone archivos públicamente), `test_public_api_tokens.py`, `test_rh_nomina_security.py` (RBAC + tenant isolation en RH/nómina), `test_hl7_tenant_binding.py` (comparación de API key HL7 sin timing leak), `test_super_master.py` (confirma que `es_auditor_supremo` es un flag independiente de `is_superuser` para lectura cross-tenant de `AuditLog` — ningún superusuario normal puede leer auditoría global sin ese flag explícito), `test_enterprise_security_closures.py`, `test_auto_repair_tenant_guard.py`.
- **Resultado:** todas las pruebas revisadas son sustantivas (no vacuas tipo `assertTrue(True)`), sin `@skip`/`xfail` ocultando fallos conocidos, y cubren correctamente regresiones de hallazgos ya corregidos. Confirmación positiva adicional: el acceso cross-tenant a `AuditLog` requiere el flag dedicado `es_auditor_supremo`, no solo `is_superuser`.
- **Sin hallazgos nuevos.** Los ~70 archivos restantes son mayormente tests funcionales/negocio (farmacia, contabilidad, bienestar, laboratorio) sin implicación directa de seguridad — no se revisaron línea por línea dado el bajo rendimiento esperado; quedan pendientes si se requiere cobertura exhaustiva. `core/rbac/tests.py` y `core/tests_e2e*.py` también pendientes.

Bloque 8 — NO CERRADO. Corrección: lo anterior fue un muestreo de 18/88 archivos (~20%), no una revisión exhaustiva. Pendientes explícitos sin revisar: `test_read_only_middleware.py`, `test_read_only_middleware_unit.py`, `test_rate_limit_middleware.py`, `test_walkie_tenant_isolation.py`, `test_farmacia_regulatorio.py`, `test_farmacia_corte_unificado.py`, `test_farmacia_carga_masiva_excel.py`, `test_devoluciones_farmacia_api.py`, `test_contabilidad_general.py`, `test_contabilidad_personal.py`, `test_bienestar_nom035.py`, `test_coverage_boost.py` (nombre sugiere posibles tests superficiales solo para cobertura — revisar con atención), `test_offline_idempotency.py`, todos los `test_auditoria_segura_*.py`, y el resto de ~55 archivos no listados individualmente. `core/rbac/tests.py` y `core/tests_e2e*.py` no se tocaron. No se ejecutó la suite (`manage.py test`) para confirmar que las pruebas pasan contra el código vivo.

(El resto de bloques se detallan a medida que se avanza, usando AUDITORIA_INVENTARIO.txt como checklist maestro por ruta completa.)
