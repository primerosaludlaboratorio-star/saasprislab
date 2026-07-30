# Auditoría exhaustiva PRISLAB — Progreso

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
- [!] core/models/expediente_blindaje.py — COMPLETO (1098 líneas: ExpedienteNotaSHA, SnapshotNotaMiddleware, NotaClinicaSellar, TokenLIMSV7Manager, ReglaPreparacionAnalito, OrdenTokenLIMS, CatalogoCIE10, HashRaizDiario). H-NUEVO-05 corregido, migrado y verificado en producción con transacción reversible. Hallazgos menores: signal duplicado muerto con docstring falso, TokenLIMSV7Manager sin usar/incompleto.
- [x] core/models/finanzas.py — COMPLETO (459 líneas: PoliticaLimitesCaja, GastoCajaEndurecido, CierreDiaConsolidado, TicketInvestigacionCaja). `CierreDiaConsolidado.generar_hash()` correcto (no depende de auto_now_add, a diferencia de H-NUEVO-04/05). `GastoCajaEndurecido.clean()` valida zonas verde/amarillo/roja correctamente. Sin hallazgos.
- [x] core/models/forense.py — re-confirmado a fondo (visto en sesión previa), sin hallazgos.
- [x] core/models/ia_config.py — COMPLETO (190 líneas: UsoRecursosIA, ReglaLocalIA). `registrar_uso()` usa F() para incremento atómico. Sin hallazgos.
- [!] core/models/laboratorio.py — COMPLETO (729 líneas: TomaMuestra, AudioTomaMuestra, EnvioMaquila, BitacoraTemperatura, MantenimientoEquipo, HistorialResultados, ResultadoParametro, OrdenDeServicio, DetalleOrden, PreOrdenLaboratorio, DetallePreOrden). `OrdenDeServicio.save()` suma otro call site a H-NUEVO-03 (folio_orden). `OrdenDeServicio.clean()` bloquea RESULTADOS_LISTOS/ENTREGADO sin PDF (con excepción documentada por saldo pendiente). `AudioTomaMuestra` usa BinaryField cifrado Fernet. `aprobado_por_humano` documenta que la IA nunca puede fijarlo en True (no verificado programáticamente, solo por convención).
- [!] core/models/motor_financiero.py — COMPLETO (367 líneas). ADVERTENCIA DE ORGANIZACIÓN: este archivo vive en `core/models/` pero NO contiene ni una sola clase de modelo — son 4 vistas (`genera_reporte_caja`, `exportar_reporte_excel`, `exportar_reporte_pdf`, `api_resumen_ejecutivo_pris`) con decoradores `@login_required`/`@role_required`. RBAC correcto. `exportar_reporte_excel` no sanitiza contra inyección de fórmulas CSV/Excel (valores con `=`,`+`,`-`,`@` al inicio) — riesgo bajo (folio es server-generado, username es admin-controlado) pero no hay sanitización defensiva.
- [x] core/models/operaciones.py — COMPLETO (947 líneas: AuditLog, BackupRegistro, BackupInmutableLog, MensajeInterno, SolicitudAutorizacion, IncidenciaOperativa, BuzonQuejas, LibroLiderazgo, PushSubscription, VoiceAuditLog, NotificacionSistema, BitacoraEntregaResultados, ConversacionBienestar, AlertaBienestar, DocumentoCapacitacion, CapsulaSabiduria). `AuditLog.hash_verificacion` confirmado poblado vía `core/utils/auditoria_helper.py` y `core/services/audit_service.py`. Append-only re-confirmado. Sin hallazgos nuevos.
- [x] core/models/pacientes.py — COMPLETO (176 líneas). `save()` normaliza y auto-genera nombre_completo. `generar_pris_id()` es código muerto (no se llama en ningún sitio, ni es idempotente). Sin hallazgos de seguridad.
- [x] core/models/pris.py — COMPLETO (153 líneas: AccionPRIS). `confirmar()`/`rechazar()` con update_fields explícito. Sin hallazgos.
- [!] core/models/reportes_financieros.py — COMPLETO (598 líneas, 8 vistas/helpers, sin clases de modelo). Es copia no enlazada por las URLs; H-NUEVO-06 se corrigió en la implementación activa `core/views/reportes_financieros.py` con `_fecha_segura` y prueba focalizada. RBAC correcto.
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
- [x] core/agent/pris_agent.py — COMPLETO (174 líneas). `PrisAgent`/`TOOL_REGISTRY`/`register_tool`/`can_execute_tool` son código MUERTO (sin usos fuera del archivo). `get_pris_context` sí se usa (core/middleware/pris_context.py).
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
- [x] core/consumers.py — COMPLETO (WalkieTalkieConsumer con aislamiento por `empresa_id`, validación de sala y rechazo fail-closed de usuarios sin tenant). H-NUEVO-14 corregido localmente; pruebas focalizadas OK.
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
Hallazgos del bloque: H-NUEVO-09 (corregido), H-NUEVO-10 (abierto, higiene), H-NUEVO-11 (abierto), H-NUEVO-12 CRÍTICO (corregido y verificado en producción), H-NUEVO-13 (corregido), H-NUEVO-14 (corregido localmente; pendiente despliegue).

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
- [!] core/middleware/sentinel.py — COMPLETO (882 líneas). Middleware de auto-reparación AIOps. Hallazgo H-NUEVO-15 (restart de Gunicorn disparable sin autenticación ante 3 excepciones tipo timeout/memoria en 60s). Resto del motor de auto-reparación (redirects a rutas seguras, nunca a '/', registro de incidencias con tenant scoping estricto en `_crear_incidencia` que rechaza `empresa_id` nulo) es sólido. `reparar_permisos_sesion` (auto-fix de permisos 403) confirmado como código NO invocado desde el middleware (solo pruebas) — intencionalmente deshabilitado, comentario explícito "RBAC sea observable y auditable".
- [x] core/services/auto_repair.py — COMPLETO (511 líneas, revisado por necesidad de H-NUEVO-15). 3 motores: Gunicorn soft-restart, DB connection recovery, auto-fix permisos (código muerto, no invocado).
- [x] core/middleware/sre_metrics.py — COMPLETO (63 líneas). Métricas Prometheus in-memory. Sin hallazgos.
- [x] core/middleware/suscripciones.py — COMPLETO (40 líneas). `SuscripcionMiddleware` bloquea acceso si suscripción vencida, exime superuser. Sin hallazgos.
- [x] core/middleware/tenant_subdomain.py — COMPLETO (144 líneas). `TenantSubdomainMiddleware` — resolución por subdominio SOLO afecta usuarios anónimos (usuario autenticado siempre usa `user.empresa`, confirmado en `EmpresaIdentityMiddleware`); sin riesgo de cross-tenant.

## BLOQUE 3 — core/middleware/ COMPLETO. Hallazgo nuevo: H-NUEVO-15 (abierto).

(El resto de bloques se detallan a medida que se avanza, usando AUDITORIA_INVENTARIO.txt como checklist maestro por ruta completa.)
