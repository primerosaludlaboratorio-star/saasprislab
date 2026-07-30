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
- [!] core/models/clinico.py — COMPLETO (830 líneas, 16 clases: CitaMedica, HistoriaClinica, SignosVitales, ConsultaMedica, CertificadoMedico, NotaClinicaSOAP, PlantillaNotaClinica, Antecedente, FirmaDigital, AudioConsulta, EstudioImagen, ImagenDetalle, PlantillaEstudioImagen, HistorialCambiosConsulta, LogAccesoExpediente, ConsentimientoInformado, RegistroAuditoriaConsentimiento). Hallazgos H-NUEVO-03 (folios por count()+1) y H-NUEVO-04 (hash con timestamp None). Resto de métodos (IMC, clasificación OMS, hash de consentimiento) correctos.
- [!] core/models/expediente_blindaje.py — COMPLETO (1098 líneas: ExpedienteNotaSHA, SnapshotNotaMiddleware, NotaClinicaSellar, TokenLIMSV7Manager, ReglaPreparacionAnalito, OrdenTokenLIMS, CatalogoCIE10, HashRaizDiario). H-NUEVO-05 confirmado y corregido localmente con `core.0099`, normalización de `user_agent`, encadenamiento previo al hash y `compare_digest`; pendiente de despliegue y verificación productiva. Hallazgos menores: signal duplicado muerto con docstring falso, TokenLIMSV7Manager sin usar/incompleto.
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
Hallazgos totales del bloque: H-NUEVO-01 (corregido), H-NUEVO-02 (corregido), H-NUEVO-03 (8 call sites, abierto), H-NUEVO-04 (abierto), H-NUEVO-05 CRÍTICO (corregido localmente, pendiente de despliegue), H-NUEVO-06 (corregido localmente), H-NUEVO-07 (corregido localmente), H-NUEVO-08 (corregido localmente).

## Bloque 2 — core/ (raíz, admin/, agent/, api_contracts/, constants/, rbac/)
- [x] core/decorators.py — COMPLETO (433 líneas, 6 decoradores). Sin hallazgos nuevos.
- [!] core/rbac/permissions.py — COMPLETO (444 líneas). Hallazgos H-NUEVO-09 (require_sucursal_access fail-open, mitigado por ser código muerto) y H-NUEVO-10 (decoradores RBAC no usados en vistas reales).
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
- [!] core/admin.py — COMPLETO. CONFIRMADO EMPÍRICAMENTE código muerto/huérfano (`find_spec('core.admin')` resuelve al paquete, no a este archivo). Ver H-NUEVO-13.
- [x] core/admin/__init__.py — COMPLETO. Agrega los 6 submódulos.
- [!] core/admin/bienestar.py — COMPLETO (209 líneas, ~13 ModelAdmin). Sin get_queryset por tenant — ver H-NUEVO-12.
- [!] core/admin/catalogo.py — COMPLETO (76 líneas: ProductoAdmin, LoteAdmin). Sin get_queryset por tenant — ver H-NUEVO-12.
- [!] core/admin/clinico.py — COMPLETO (409 líneas, ~12 ModelAdmin incluyendo OrdenDeServicio, HistoriaClinica vía otros submódulos). Sin get_queryset por tenant — ver H-NUEVO-12.
- [x] core/admin/identidad.py — COMPLETO (121 líneas). ÚNICO submódulo con get_queryset correcto por tenant (CustomUsuarioAdmin, Usuario_SucursalAdmin).
- [!] core/admin/rrhh.py — COMPLETO (313 líneas, ~15 ModelAdmin). Sin get_queryset por tenant — ver H-NUEVO-12.
- [!] core/admin/ventas.py — COMPLETO (79 líneas: VentaAdmin). Sin get_queryset por tenant — ver H-NUEVO-12.

## HALLAZGO CRÍTICO H-NUEVO-12: Django Admin sin aislamiento multi-tenant en ~43 de 45 ModelAdmin. Ver AUDITORIA_HALLAZGOS.md.
- [ ] core/ai_brain.py
- [ ] core/apps.py
- [ ] core/catalog.py
- [ ] core/constants/lock_order.py
- [ ] core/consumers.py
- [ ] core/context_processors.py
- [ ] core/django_template_context_patch.py
- [x] core/fields.py — ya auditado en Bloque 1.
- [ ] core/forms.py
- [ ] core/lims_cart.py
- [ ] core/push_service.py
- [ ] core/rescate_total_prislab.py
- [ ] core/routing.py
- [x] core/tenant.py — ya confirmado positivo en sesión previa (aislamiento multi-tenant + sucursal, STRICT_MODE).
- [ ] core/urls.py
- [ ] core/validators.py
- [ ] core/__init__.py
- [ ] core/mixins.py

Hallazgos nuevos del Bloque 2 (hasta ahora): H-NUEVO-09, H-NUEVO-10, H-NUEVO-11.

(El resto de bloques se detallan a medida que se avanza, usando AUDITORIA_INVENTARIO.txt como checklist maestro por ruta completa.)
