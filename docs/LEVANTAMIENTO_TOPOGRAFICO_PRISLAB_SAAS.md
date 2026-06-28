# Levantamiento topográfico — PRISLAB SaaS

**Fecha del inventario:** 2 de abril de 2026.  
**Alcance:** código de aplicación (se excluyen `venv/`, `.venv-gate/` y plantillas empaquetadas en site-packages).  
**Nota:** `pacientes.models.Paciente` es app mínima; modelo operativo principal: `core.models.pacientes.Paciente` (`TenantModel`).

---

## 1. Directorios de aplicación Django

`bienestar`, `consultorio`, `contabilidad`, `core`, `enfermeria`, `farmacia`, `ia`, `inventario`, `iot`, `laboratorio`, `lims`, `logistica`, `mantenimiento`, `marketing`, `pacientes`, `recepcion`, `reglas_negocio`, `seguridad`.

Proyecto: `config/`. Estáticos/plantillas: `static/`, `templates/`, `core/templates/`, `<app>/templates/`. Integración local: `middleware_local/`.

---

## 2. INSTALLED_APPS (`config/settings.py`)

`corsheaders`, apps contrib (`admin`, `auth`, `contenttypes`, `sessions`, `messages`, `staticfiles`, `humanize`), apps negocio (`core` … `contabilidad` en el orden del archivo), `storages`, `pwa`, `channels`.

---

## 3. Middlewares activos (orden)

`SecurityMiddleware`, `WhiteNoiseMiddleware`, `CorsMiddleware`, `SessionMiddleware`, `CommonMiddleware`, `CanonicalHostMiddleware`, `CsrfViewMiddleware`, `AuthenticationMiddleware`, `ReadOnlyMiddleware`, `AdminAccessMiddleware`, `RateLimitMiddleware`, `EmpresaIdentityMiddleware`, `FeatureFlagMiddleware`, `JSONResponseMiddleware`, `ActividadUsuarioMiddleware`, `SentinelTelemetryMiddleware`, `PerformanceMiddleware`, `PrisContextMiddleware`, `MaintenanceModeMiddleware`, `SessionTimeoutMiddleware`, `TenantStorageMiddleware`, `BlindajeExpedienteMiddleware`, `SnapshotMiddleware`, `MessageMiddleware`, `XFrameOptionsMiddleware`.  
`LogAccesoExpedienteMiddleware` comentado. `admin_access_restrict.py` existe pero no está en la cadena.

**Clases en `core/middleware/`:** `JSONResponseMiddleware`, `EmpresaIdentityMiddleware`, `AdminAccessMiddleware`, `PerformanceMiddleware`, `ReadOnlyMiddleware`, `BlindajeExpedienteMiddleware`, `SnapshotMiddleware`, `SentinelTelemetryMiddleware`, `RateLimitMiddleware`, `SessionTimeoutMiddleware`, `TenantStorageMiddleware`, `LogAccesoExpedienteMiddleware`, `FeatureFlagMiddleware`, `ModuloRequeridoMixin`, `MaintenanceModeMiddleware`, `CanonicalHostMiddleware`, `ActividadUsuarioMiddleware`, `PrisContextMiddleware`.

---

## 4. Settings clave

CORS (`CORS_ALLOW_*`), `PRISLAB_DEFAULT_EMPRESA_ID`, `API_URL`, `AUTH_USER_MODEL`, `LOGIN_*`, sesión (`SESSION_*`), `CSRF_TRUSTED_ORIGINS`, DB cloud/SQLite, static WhiteNoise + manifest, media Drive/GCS, PWA, Channels, HL7, mantenimiento, CISO/2FA, etc. (detalle en `config/settings.py`).

---

## 5. URLs

- **`config/urls.py`:** raíz completa del sitio (admin, auth, farmacia, laboratorio, LIMS legacy en `laboratorio_config`, finanzas, CRM, nómina, IA, push, voz, Sentinel, includes de apps, `silo-lab/`, `mantenimiento/`, onboarding, autofactura, cron).  
- **`core/urls.py` (namespace `core`):** historial resultados, blindaje expediente.  
- **`lims/urls.py`, `farmacia/urls.py`, `laboratorio/urls.py`, `inventario/urls.py`, `mantenimiento/urls.py`, `seguridad/urls.py`, `recepcion/urls.py`, `consultorio/urls.py`, `pacientes/urls.py`, `marketing/urls.py`, `logistica/urls.py`, `enfermeria/urls.py`, `iot/urls.py`, `ia/urls.py`, `bienestar/urls.py`, `contabilidad/urls.py`:** ver archivos fuente para patrones exactos.

**WebSocket:** `core/routing.py` → `WalkieTalkieConsumer`, `VoiceCommandConsumer` (`core/consumers.py`).

---

## 6. Modelos (clases)

### `core/models/`
- `base.py`: AuditoriaModel, Empresa, Sucursal, ConfiguracionModulos, Usuario, DocumentoConocimiento, DatosFiscales, ControlCalidad, RutaLogistica  
- `laboratorio.py`: TomaMuestra, AudioTomaMuestra, EnvioMaquila, BitacoraTemperatura, MantenimientoEquipo, HistorialResultados, ResultadoParametro, OrdenDeServicio, DetalleOrden, PreOrdenLaboratorio, DetallePreOrden  
- `ventas.py`: Receta, RecetaItem, DemandaInsatisfecha, Venta, DetalleVenta, DetalleVentaLote, DevolucionVenta, Pago, PagoOrden, Gasto, AjusteInventario, GastoCaja, MovimientoCaja, GastoOperativo, FacturaSAT, SalesReturn, MetaVenta, CuentaPorCobrar, PagoCuentaPorCobrar, NotaCredito  
- `catalogos.py`: Producto, Lote, Medico, DiscountPolicy, Convenio, ConvenioPrecioLims  
- `pacientes.py`: Paciente  
- `forense.py`: ForenseAcceso  
- `clinico.py`: CitaMedica, HistoriaClinica, SignosVitales, ConsultaMedica, CertificadoMedico, NotaClinicaSOAP, PlantillaNotaClinica, Antecedente, FirmaDigital, AudioConsulta, EstudioImagen, ImagenDetalle, PlantillaEstudioImagen, HistorialCambiosConsulta, LogAccesoExpediente, ConsentimientoInformado, RegistroAuditoriaConsentimiento  
- `operaciones.py`: AuditLog, BackupRegistro, BackupInmutableLog, MensajeInterno, SolicitudAutorizacion, IncidenciaOperativa, BuzonQuejas, LibroLiderazgo, PushSubscription, VoiceAuditLog, NotificacionSistema, BitacoraEntregaResultados, ConversacionBienestar, AlertaBienestar, DocumentoCapacitacion, CapsulaSabiduria  
- `expediente_blindaje.py`: ExpedienteNotaSHA, NotaClinicaSellar, ReglaPreparacionAnalito, OrdenTokenLIMS, CatalogoCIE10, HashRaizDiario  
- `finanzas.py`: PoliticaLimitesCaja, GastoCajaEndurecido, CierreDiaConsolidado, TicketInvestigacionCaja  
- `ia_config.py`: UsoRecursosIA, ReglaLocalIA  
- `bienestar_staff.py`: EvaluacionNOM035, DiarioEmocionalStaff, SesionCoachingStaff, AlertaBurnout, ProgramaCapacitacion  
- `pris.py`: AccionPRIS  
- `rrhh.py`: Empleado, Bitacora39A, Competencia, EvaluacionDesempeno, DetalleEvaluacion, PlanDesarrollo, RegistroAsistencia, PeriodoNomina, ReciboNomina, HorarioTrabajo, IncidenciaAsistencia  

### Otras apps
- `lims`: Analito, ValorReferenciaAnalito, PerfilLims, PaqueteLims, PrecioItem  
- `farmacia`: Proveedor, MotivoAjuste, MovimientoInventario, MermaFarmacia, CierreTurnoFarmacia, AperturaCaja, DevolucionVenta, RegistroAntibiotico  
- `laboratorio`: CategoriaExamen, Equipo, CodigoParametroEquipo, Estudio, InsumoEstudio, PerfilLaboratorio, ValorReferencia, IndiceEritrocitario, DiferencialLeucocitario, ControlCalidad, EnvioMaquila, BitacoraMantenimiento, PrecursorCellular, Medico, Orden, Parametro, Resultado, DetalleOrden, ResponsableSanitario, NotificacionPanico, HistorialResultados, RangoReferenciaParametro, ResultadoHL7, ResultadoHL7Huerfano  
- `inventario`: ProveedorCompras, CatalogoReactivoLab, ConsumoEstudioReactivo, LoteReactivoLab, SalidaAnaliticaLab, SalidaTecnicaLab, CatalogoInsumoConsultorio, LoteInsumoConsultorio, SalidaConsumoConsultorio, CatalogoInsumoGeneral, LoteInsumoGeneral, ValeRequisicion, LineaValeRequisicion, OrdenDeCompra, LineaOrdenCompra, TraspasoInventario, LineaTraspasoInventario, NotificacionDiscrepancia  
- `mantenimiento`: ExpedienteEquipo, ProtocoloEquipo, PasoProtocolo, ArbolDiagnostico, ProcedimientoReparacion, PasoReparacion, NodoDiagnostico, EjecucionProtocolo, RespuestaPasoProtocolo, BypassChecklistAutorizacion, TicketMantenimientoCMMS, SalidaRefaccionMantenimiento, RegistroTCO, CertificadoMetrologia, SensorIoT, LecturaSensorIoT, InCCAInterfaceConfig, InCCAFileEvent, InCCAOutputRowStaging  
- `contabilidad`: ClienteFacturacion, FacturaCFDI, ConceptoFactura, ImpuestoConcepto  
- `consultorio`: AgendaCita, ConsultaMedica, Somatometria, NotaMedica, ConfiguracionMedico, Vademecum, ArchivoAdjuntoConsulta, ListaEspera, EncuestaSatisfaccion, SeguimientoTratamiento, AnalisisPatron, CajaConsultorio, CobroConsulta, ValeLiquidacion, IncidenciaSentinel, ReporteUltrasonido, ImagenUltrasonido  
- `marketing`: CampanaMarketing, CuponMarketing, CuponUso, ProspectoCRM, SeguimientoCRM, MarketingTrackingHit  
- `logistica`: RutaRecoleccion, VisitaDomicilio, TransferenciaInventario, DetalleTransferencia, LogTransferencia  
- `bienestar`: DiarioEmocional, RecursoCrecimiento  
- `reglas_negocio`: ReglaNegocio, EjecucionRegla  
- `seguridad`: ConfiguracionSeguridad, AlertaPanico, DispositivoTOTP, DispositivoSMS, CodigoBackup2FA, SesionActiva, LogAccionSensible  
- `iot`: Kiosco, VerificacionKiosco, TransaccionHL7  
- `ia`: CotizacionOCR, TranscripcionVoz  
- `pacientes`: Paciente  
- `enfermeria`, `recepcion`: `models.py` vacíos (placeholder)

---

## 7. Vistas — `core/views/`

81 archivos `.py` además de `__init__.py`. Reexportación masiva en `__init__.py` para `from core import views`.

**Módulos:** administracion_usuarios, ai_brain, analytics, asistencia, audio_legal, auditoria_api, auditoria_campo, autenticacion_2fa, autofactura, autorizaciones, biblioteca, bienestar, bienestar_mejorado, blindaje_expediente, bot, buzon, capacitacion, capacitacion_rag, catalogos, catalogos_maestros, cerebro, coach, comunicacion, configuracion, consentimiento_digital, consentimientos, consulta_ordenes, contabilidad, cotizacion, crm, cron_tasks, cuentas_por_cobrar, dashboard_unificado, director, entrega_resultados, excepciones_lab, expediente, farmacia, feature_flags_admin, finanzas, general, historial_resultados, ia, ia_dashboard, impresion, incidencias, inventario, inventario_predictivo, laboratorio (muy extenso), laboratorio_captura, laboratorio_config, laboratorio_reportes, manual, maquila, medico, microbiologia, monitor_produccion, motor_financiero, nomina, notificaciones, omnisearch, onboarding, operaciones, paciente, paciente_detalle, pacientes, paquetes, pris_checklist, pris_ia, pris_jarvis, push, ranking, reporte_friccion, reportes_financieros, rh, sentinel_api, sucursal_modo_inventario_lab, tarifas, transferencias, voice, war_room.

**Clases CBV destacadas:** `CustomLoginView`, `LabCajaView`, `FarmaciaCajaView`, `MasterDashboardView`, `ExpedienteClinicoView`, `OnboardingWizardView`, `OnboardingCrearEmpresaView`.

**Inventario AST de `def`/`class` a nivel módulo:** generado íntegramente en sesión de cartografía (listado función por función por archivo); `laboratorio.py` y `pris_ia.py` concentran el mayor número de endpoints.

### Otras apps (resumen)
- `lims/views/*`: analitos, perfiles, paquetes, precios (+ `_check_perm`, APIs).  
- `laboratorio/views/*`: `__init__`, hl7_receptor (`receptor_hl7`), cci_api, etiquetas, imprimir_zpl; `views_admin`: tarifas CSV.  
- `farmacia/views/*`: `__init__` (Kardex, alertas, compras), corte_caja_api, semaforo, soporte.  
- `inventario`: views + views_consultorio + views_generales + views_compras + views_traspasos.  
- `mantenimiento`: views + views_metrologia.  
- `consultorio`: views + pdf_views + pdf_views_prislab + api_views.  
- `recepcion`, `enfermeria`, `logistica`, `marketing` (+ `views_tracking`), `contabilidad`, `seguridad`, `iot`, `ia`, `bienestar`, `pacientes` (+ `portal_views`).  
- `reglas_negocio`: sin `views.py`.

---

## 8. Comandos de gestión

Listado exhaustivo en **Anexo A** (incluye subcarpetas como `core/management/commands/_archive_legacy/`). Total generado al ejecutar el script. Distribución principal por app: `core`, `farmacia`, `laboratorio`, `lims`, `inventario`, `mantenimiento`, `bienestar`, `contabilidad`.

---

## 9. Señales

- `core/signals.py`: múltiples `@receiver` (venta, orden, resultado, devolución, delete audit, auto empresa en modelos).  
- `farmacia/signals.py`: cierre de caja → email.  
- `laboratorio/signals.py`: ResultadoParametro pre/post save.  
- `inventario/signals.py`: ResultadoParametro, AgendaCita, ValeRequisicion, TicketMantenimientoCMMS.  
- `mantenimiento/signals.py`: SalidaRefaccionMantenimiento, LecturaSensorIoT.

---

## 10. `core/tenant.py` y `core/lims_cart.py`

- **tenant:** contexto thread-local, `TenantModel` / `TenantManager`, bypass, `assert_tenant_owns`, `tenant_required`, etc.  
- **lims_cart:** `parse_lims_cart_token`, `resolve_lims_cart_ids`, `search_lims_catalog`, `aplicar_precio_convenio`, `precio_publico_analito`, `detalle_orden_etiqueta`, etc.

## 11. `core/utils/`

34 módulos Python (pdf, IA, drive, permisos, auditoría, whatsapp, LIMS tokens, tenant_strict, etc.).

---

## 12. Plantillas HTML (proyecto)

**404** archivos bajo el repo excluyendo `venv`: `core` 198, `inventario` 35, `consultorio` 35, `mantenimiento` 22, `farmacia` 14, `pacientes` 13, `templates/` 11, `marketing` 10, `lims` 10, `bienestar` 9, `logistica` 8, `seguridad` 7, `recepcion` 7, `laboratorio` 6, `ia` 6, `enfermeria` 6, `contabilidad` 6, `iot` 1.

---

## 13. `static/js/`

Archivos: `audio_recorder.js`, `estandares_industriales.js`, `expediente_firma_consentimiento.js`, `laboratorio_ai.js`, `motor_calculo_formulas.js`, `offline_sync.js`, `paquetes_sortable.js`, `pdv_farmacia.js`, `prislab_main.js`, `pris_assistant.js`, `pris_voice_commander.js`, `push_notifications.js`, `sentinel_shield.js`, `sentinel_voice.js`, `speech_recognition.js`, `consultorio/dictado_voz.js`, `consultorio/grabadora_sesion.js`, `lims/parametros.js`.

**PDV (heurística):** `_pdvInyectarHtmlFragmento`, `_renderResultados`, `_agregarAlCarrito`, `_actualizarTotalesPanel`, `_csrf`, `_onVentaExitosa`, etc.

---

Los anexos A–C se generan automáticamente al ejecutar este script (listas exhaustivas).

## Anexo A — Comandos de gestión (exhaustivo)

- `bienestar/management/commands/poblar_recursos.py`
- `contabilidad/management/commands/reconciliar_facturas_pendientes.py`
- `core/management/commands/_archive_legacy/diagnostico_total.py`
- `core/management/commands/_archive_legacy/import_estudios_excel.py`
- `core/management/commands/_archive_legacy/seed_catalogos.py`
- `core/management/commands/activar_war_room.py`
- `core/management/commands/anclar_hashes_diarios.py`
- `core/management/commands/arranque_frio.py`
- `core/management/commands/audit_dump_code_markers.py`
- `core/management/commands/audit_roles.py`
- `core/management/commands/audit_system.py`
- `core/management/commands/auditar_farmacia_integridad.py`
- `core/management/commands/auditar_multitenant_async.py`
- `core/management/commands/auditar_rutas.py`
- `core/management/commands/auditar_sistema.py`
- `core/management/commands/auditoria_botones_pantallas.py`
- `core/management/commands/auditoria_coherencia_total.py`
- `core/management/commands/auditoria_core_full.py`
- `core/management/commands/auditoria_farmacia_full.py`
- `core/management/commands/auditoria_gemini_prime.py`
- `core/management/commands/auditoria_ia.py`
- `core/management/commands/auditoria_lab_full.py`
- `core/management/commands/auditoria_medico_full.py`
- `core/management/commands/auditoria_qa.py`
- `core/management/commands/auditoria_secuencial.py`
- `core/management/commands/backfill_movimientos_caja_v114.py`
- `core/management/commands/backfill_ventas_inventario_descontado.py`
- `core/management/commands/backup_database.py`
- `core/management/commands/backup_db_drive.py`
- `core/management/commands/backup_nocturno.py`
- `core/management/commands/bankguard_audit.py`
- `core/management/commands/bankguard_backfill.py`
- `core/management/commands/carga_inventario_csv.py`
- `core/management/commands/cargar_biblioteca_inicial.py`
- `core/management/commands/cargar_catalogo_lab.py`
- `core/management/commands/cargar_csv.py`
- `core/management/commands/cargar_datos_rh.py`
- `core/management/commands/cargar_inventario_xlsx.py`
- `core/management/commands/cargar_legacy.py`
- `core/management/commands/check_placeholder_resultados_lims.py`
- `core/management/commands/cierre_dia.py`
- `core/management/commands/configurar_equipo_elite.py`
- `core/management/commands/crear_grupos_roles.py`
- `core/management/commands/crear_superusuario_prod.py`
- `core/management/commands/crear_usuarios_produccion.py`
- `core/management/commands/cron_backup_3am.py`
- `core/management/commands/diagnostico_pris.py`
- `core/management/commands/estres_ventas_farmacia.py`
- `core/management/commands/execute_rescate_total.py`
- `core/management/commands/generar_auditoria_gemini.py`
- `core/management/commands/generar_data_operativa_v150.py`
- `core/management/commands/generar_muestras_reales.py`
- `core/management/commands/guardar_backup_config_drive.py`
- `core/management/commands/importar_catalogos_legacy.py`
- `core/management/commands/importar_csv_lab.py`
- `core/management/commands/importar_legacy.py`
- `core/management/commands/importar_precios.py`
- `core/management/commands/inicializar_pris_valle.py`
- `core/management/commands/leer_feedback_sentinel.py`
- `core/management/commands/limpiar_duplicados_cierres.py`
- `core/management/commands/limpiar_pruebas.py`
- `core/management/commands/limpiar_temporales.py`
- `core/management/commands/limpieza_entorno_prod.py`
- `core/management/commands/matriz_integridad.py`
- `core/management/commands/normalizar_tipo_lims.py`
- `core/management/commands/normalizar_usuarios_personal.py`
- `core/management/commands/omni_audit.py`
- `core/management/commands/provision_usuarios_base.py`
- `core/management/commands/purgar_datos_nom035.py`
- `core/management/commands/registrar_backup_inmutable.py`
- `core/management/commands/remap_placeholder_resultados.py`
- `core/management/commands/reparar_catalogo_estudios.py`
- `core/management/commands/rescate_farmacia_tenant.py`
- `core/management/commands/resetear_personal_final.py`
- `core/management/commands/resetear_usuarios_acceso.py`
- `core/management/commands/resolver_incidencias.py`
- `core/management/commands/restaurar_backup.py`
- `core/management/commands/saneamiento_global_sentinel_buzon.py`
- `core/management/commands/seed_estudios.py`
- `core/management/commands/seed_grupos_permisos.py`
- `core/management/commands/seed_pacientes_revision_prislab.py`
- `core/management/commands/seed_parametros_lab.py`
- `core/management/commands/seed_pdv_audit_20.py`
- `core/management/commands/sentinel_amnistia_pre_produccion.py`
- `core/management/commands/sentinel_auto_cleanup.py`
- `core/management/commands/sentinel_reporte_semanal.py`
- `core/management/commands/sentinel_reset.py`
- `core/management/commands/setup_demo_total.py`
- `core/management/commands/setup_demo_v75.py`
- `core/management/commands/setup_roles.py`
- `core/management/commands/simular_flujo_completo.py`
- `core/management/commands/simular_ventas_farmacia.py`
- `core/management/commands/simular_ventas_farmacia_completo.py`
- `core/management/commands/sincronizar_roles_grupos.py`
- `core/management/commands/stress_test_extremo.py`
- `core/management/commands/supervisor_ia_revisar_ventas.py`
- `core/management/commands/sync_usuario_empresa_default.py`
- `core/management/commands/test_drive_connection.py`
- `core/management/commands/test_estructura_drive.py`
- `core/management/commands/test_gemini_connection.py`
- `core/management/commands/test_gemini_v1.py`
- `core/management/commands/test_github_sentinel.py`
- `core/management/commands/test_pdf_receta.py`
- `core/management/commands/test_pris_vida.py`
- `core/management/commands/unificar_empresa_prislab.py`
- `core/management/commands/verificar_aislamiento_multitenant.py`
- `core/management/commands/verificar_backup_cifrado.py`
- `core/management/commands/verificar_drive.py`
- `core/management/commands/verificar_fk_ods_ia_iot.py`
- `core/management/commands/verificar_funcionalidades.py`
- `core/management/commands/verificar_integridad.py`
- `core/management/commands/verificar_modulos_usuario.py`
- `core/management/commands/verificar_sistema_completo.py`
- `core/management/commands/verificar_todo_sistema.py`
- `core/management/commands/verify_escudo_clinico.py`
- `core/management/commands/war_room_stress_test.py`
- `core/management/commands/wipe_datos_operativos.py`
- `farmacia/management/commands/cargar_inventario.py`
- `farmacia/management/commands/cargar_inventario_excel.py`
- `farmacia/management/commands/cargar_productos_csv.py`
- `farmacia/management/commands/cargar_productos_farmacia.py`
- `farmacia/management/commands/cargar_productos_pandas.py`
- `farmacia/management/commands/importar_excel_inventario.py`
- `farmacia/management/commands/marcar_antibioticos.py`
- `farmacia/management/commands/seed_motivos_ajuste.py`
- `farmacia/management/commands/seed_productos_prueba.py`
- `inventario/management/commands/auditar_bom_consumo_reactivo.py`
- `inventario/management/commands/auditar_integridad_inventario.py`
- `inventario/management/commands/backfill_inventario_idempotency.py`
- `laboratorio/management/commands/actualizar_precios_con_auditoria.py`
- `laboratorio/management/commands/cargar_catalogo_pruebas.py`
- `laboratorio/management/commands/cargar_estructura_resultados.py`
- `laboratorio/management/commands/cargar_tarifas_csv.py`
- `laboratorio/management/commands/crear_perfiles_quimica.py`
- `laboratorio/management/commands/importar_catalogo_maestro.py`
- `laboratorio/management/commands/importar_tarifas.py`
- `laboratorio/management/commands/importar_tarifas_lab.py`
- `laboratorio/management/commands/migrar_lab_completo.py`
- `laboratorio/management/commands/migrar_lab_master.py`
- `laboratorio/management/commands/poblar_sistema.py`
- `laboratorio/management/commands/seed_rangos_iso15189.py`
- `laboratorio/management/commands/simular_laboratorio_completo.py`
- `lims/management/commands/ensamblar_lims_v75.py`
- `lims/management/commands/importar_catalogo_lims.py`
- `lims/management/commands/importar_examenes_perfil_lims.py`
- `lims/management/commands/importar_paquetes_perfil_lims.py`
- `lims/management/commands/purgar_lims.py`
- `lims/management/commands/sincronizar_precios_lims.py`
- `mantenimiento/management/commands/check_certificados_metrologicos.py`
- `mantenimiento/management/commands/sync_incca_csv.py`

**Total:** 150 módulos de comando.


## Anexo B — Plantillas HTML (exhaustivo)

- `bienestar/templates/bienestar/alertas_director.html`
- `bienestar/templates/bienestar/chat.html`
- `bienestar/templates/bienestar/consultorio/agendar.html`
- `bienestar/templates/bienestar/dashboard.html`
- `bienestar/templates/bienestar/diario/estadisticas.html`
- `bienestar/templates/bienestar/diario/lista.html`
- `bienestar/templates/bienestar/diario/nueva_entrada.html`
- `bienestar/templates/bienestar/recursos/detalle.html`
- `bienestar/templates/bienestar/recursos/lista.html`
- `consultorio/templates/consultorio/agenda_diaria.html`
- `consultorio/templates/consultorio/agenda_medico.html`
- `consultorio/templates/consultorio/agendar_cita.html`
- `consultorio/templates/consultorio/analisis_patrones.html`
- `consultorio/templates/consultorio/archivos_paciente.html`
- `consultorio/templates/consultorio/buscar_paciente_consulta.html`
- `consultorio/templates/consultorio/campanas_marketing.html`
- `consultorio/templates/consultorio/captura_signos_vitales.html`
- `consultorio/templates/consultorio/cobro_consulta.html`
- `consultorio/templates/consultorio/configuracion_medico.html`
- `consultorio/templates/consultorio/consulta_sin_cita.html`
- `consultorio/templates/consultorio/dashboard_consultorio.html`
- `consultorio/templates/consultorio/encuestas_satisfaccion.html`
- `consultorio/templates/consultorio/generar_certificado.html`
- `consultorio/templates/consultorio/historial_clinico_paciente.html`
- `consultorio/templates/consultorio/historial_signos_vitales.html`
- `consultorio/templates/consultorio/lista_espera.html`
- `consultorio/templates/consultorio/lista_trabajo_medico.html`
- `consultorio/templates/consultorio/lista_triage.html`
- `consultorio/templates/consultorio/nueva_consulta.html`
- `consultorio/templates/consultorio/nueva_consulta_gemelo.html`
- `consultorio/templates/consultorio/nueva_consulta_soap.html`
- `consultorio/templates/consultorio/reporte_liquidacion.html`
- `consultorio/templates/consultorio/reportes_productividad.html`
- `consultorio/templates/consultorio/resultados_lab_consulta.html`
- `consultorio/templates/consultorio/seguimiento_tratamiento.html`
- `consultorio/templates/consultorio/sentinel_dashboard.html`
- `consultorio/templates/consultorio/sentinel_detalle.html`
- `consultorio/templates/consultorio/sentinel_ssh_guide.html`
- `consultorio/templates/consultorio/tablero_recepcion.html`
- `consultorio/templates/consultorio/triaje_pre_cita.html`
- `consultorio/templates/consultorio/vademecum.html`
- `consultorio/templates/consultorio/ver_certificado.html`
- `consultorio/templates/consultorio/ver_consulta_detalle.html`
- `consultorio/templates/consultorio/videollamada_segura.html`
- `contabilidad/templates/contabilidad/clientes/crear.html`
- `contabilidad/templates/contabilidad/clientes/lista.html`
- `contabilidad/templates/contabilidad/dashboard.html`
- `contabilidad/templates/contabilidad/facturas/crear.html`
- `contabilidad/templates/contabilidad/facturas/detalle.html`
- `contabilidad/templates/contabilidad/facturas/lista.html`
- `core/templates/base.html`
- `core/templates/core/2fa/activado.html`
- `core/templates/core/2fa/no_disponible.html`
- `core/templates/core/2fa/setup.html`
- `core/templates/core/2fa/verificar.html`
- `core/templates/core/administracion/usuarios.html`
- `core/templates/core/ajustes_inventario.html`
- `core/templates/core/analytics/dashboard.html`
- `core/templates/core/analytics/trazabilidad.html`
- `core/templates/core/asistencia/crear_horario.html`
- `core/templates/core/asistencia/crear_incidencia.html`
- `core/templates/core/asistencia/dashboard.html`
- `core/templates/core/asistencia/horarios_trabajo.html`
- `core/templates/core/asistencia/incidencias.html`
- `core/templates/core/asistencia/registrar_entrada_salida.html`
- `core/templates/core/asistencia/registro_asistencia.html`
- `core/templates/core/autofactura_publica.html`
- `core/templates/core/autorizacion_resuelta.html`
- `core/templates/core/autorizaciones_pendientes.html`
- `core/templates/core/autorizar_solicitud.html`
- `core/templates/core/biblioteca_liderazgo.html`
- `core/templates/core/bienestar/alertas_rrhh.html`
- `core/templates/core/bienestar/capacitaciones.html`
- `core/templates/core/bienestar/dashboard.html`
- `core/templates/core/bienestar/diario.html`
- `core/templates/core/bienestar/evaluacion_nom035.html`
- `core/templates/core/bienestar/proximamente.html`
- `core/templates/core/buzon_kanban.html`
- `core/templates/core/capacitacion/dashboard.html`
- `core/templates/core/capacitacion/ejecutiva.html`
- `core/templates/core/capacitacion/personal.html`
- `core/templates/core/capacitacion_rag/consultar_pris.html`
- `core/templates/core/capacitacion_rag/dashboard.html`
- `core/templates/core/capacitacion_rag/subir_documento.html`
- `core/templates/core/captura_resultados.html`
- `core/templates/core/captura_resultados_industrial.html`
- `core/templates/core/catalogos/convenio_precios.html`
- `core/templates/core/catalogos/convenios.html`
- `core/templates/core/catalogos/medicos.html`
- `core/templates/core/catalogos_maestros/metodos.html`
- `core/templates/core/catalogos_maestros/muestras.html`
- `core/templates/core/chat_experto.html`
- `core/templates/core/coach_ejecutivo.html`
- `core/templates/core/configuracion_dashboard.html`
- `core/templates/core/consulta_medica.html`
- `core/templates/core/consulta_ordenes.html`
- `core/templates/core/contabilidad/catalogo_cuentas.html`
- `core/templates/core/contabilidad/crear_cuenta.html`
- `core/templates/core/contabilidad/dashboard.html`
- `core/templates/core/control_calidad.html`
- `core/templates/core/convenios_lista.html`
- `core/templates/core/corte_caja_dia.html`
- `core/templates/core/cotizacion_rapida.html`
- `core/templates/core/crear_evaluacion_39a.html`
- `core/templates/core/crm/crear_prospecto.html`
- `core/templates/core/crm/dashboard.html`
- `core/templates/core/crm/detalle_prospecto.html`
- `core/templates/core/crm/lista_clientes.html`
- `core/templates/core/crm/lista_oportunidades.html`
- `core/templates/core/crm/lista_prospectos.html`
- `core/templates/core/cuentas_por_cobrar.html`
- `core/templates/core/dashboard.html`
- `core/templates/core/dashboard_director.html`
- `core/templates/core/dashboard_farmacia.html`
- `core/templates/core/dashboard_medico.html`
- `core/templates/core/dashboard_unificado.html`
- `core/templates/core/detalle_empleado_ranking.html`
- `core/templates/core/detalle_orden.html`
- `core/templates/core/detalle_venta_farmacia.html`
- `core/templates/core/devoluciones.html`
- `core/templates/core/director/war_room.html`
- `core/templates/core/director_analizadores.html`
- `core/templates/core/director_analizadores_mapeos.html`
- `core/templates/core/editar_estudio.html`
- `core/templates/core/entrada_mercancia.html`
- `core/templates/core/error.html`
- `core/templates/core/error_403.html`
- `core/templates/core/error_500.html`
- `core/templates/core/error_amable.html`
- `core/templates/core/error_sentinel.html`
- `core/templates/core/estadisticas.html`
- `core/templates/core/etiquetas_lab.html`
- `core/templates/core/expediente_clinico.html`
- `core/templates/core/expedientes/nota_sellada.html`
- `core/templates/core/facturacion/bandeja_cfdi.html`
- `core/templates/core/facturacion_40.html`
- `core/templates/core/farmacia/compra_form.html`
- `core/templates/core/feature_flags/panel.html`
- `core/templates/core/finanzas/caja_farmacia.html`
- `core/templates/core/finanzas/caja_laboratorio.html`
- `core/templates/core/finanzas/master_dashboard.html`
- `core/templates/core/historial_resultados/historial.html`
- `core/templates/core/historial_resultados/lista_pacientes.html`
- `core/templates/core/ia_dashboard.html`
- `core/templates/core/impresion/etiquetas_raw.html`
- `core/templates/core/impresion/ticket_raw.html`
- `core/templates/core/impresion/ticket_venta_raw.html`
- `core/templates/core/inventario/prediccion_stock.html`
- `core/templates/core/inventario_general.html`
- `core/templates/core/kiosco/consentimiento_firma.html`
- `core/templates/core/lab_pacientes/historial.html`
- `core/templates/core/lab_pacientes/lista.html`
- `core/templates/core/laboratorio/captura_resultados.html`
- `core/templates/core/laboratorio/dashboard_pendientes.html`
- `core/templates/core/laboratorio/entrega_resultados.html`
- `core/templates/core/laboratorio/maquila_envios.html`
- `core/templates/core/laboratorio/monitor_produccion.html`
- `core/templates/core/laboratorio/reporte_pdf.html`
- `core/templates/core/laboratorio/reporte_tiempos_proceso.html`
- `core/templates/core/laboratorio/validacion_resultado.html`
- `core/templates/core/libro_control.html`
- `core/templates/core/lims/configurar_prueba.html`
- `core/templates/core/lims/configurar_rangos.html`
- `core/templates/core/lims/editar_parametro.html`
- `core/templates/core/lims/lista_parametros.html`
- `core/templates/core/lims/lista_pruebas.html`
- `core/templates/core/lista_estudios.html`
- `core/templates/core/lista_evaluaciones_39a.html`
- `core/templates/core/lista_trabajo.html`
- `core/templates/core/lista_ventas_farmacia.html`
- `core/templates/core/login.html`
- `core/templates/core/mantenimiento.html`
- `core/templates/core/manual_usuario.html`
- `core/templates/core/matriz_talento.html`
- `core/templates/core/medico/captura_reporte_usg.html`
- `core/templates/core/medico/lista_trabajo_usg.html`
- `core/templates/core/medico/reporte_usg_pdf.html`
- `core/templates/core/mis_resultados.html`
- `core/templates/core/modal_espera_autorizacion.html`
- `core/templates/core/modal_registro_incidencia.html`
- `core/templates/core/modulo_inactivo.html`
- `core/templates/core/motor_financiero/reporte_caja.html`
- `core/templates/core/nomina/crear_periodo.html`
- `core/templates/core/nomina/dashboard.html`
- `core/templates/core/nomina/detalle_periodo.html`
- `core/templates/core/nomina/editar_recibo.html`
- `core/templates/core/nomina/lista_periodos.html`
- `core/templates/core/notificaciones/configurar.html`
- `core/templates/core/notificaciones/lista.html`
- `core/templates/core/nueva_evaluacion_desempeno.html`
- `core/templates/core/onboarding/wizard.html`
- `core/templates/core/paciente_timeline.html`
- `core/templates/core/panel_auditoria_incidencias.html`
- `core/templates/core/partials/escudo_ia_captura_badge.html`
- `core/templates/core/partials/modales_pdv.html`
- `core/templates/core/partials/pdv_buscar_fragmento.html`
- `core/templates/core/pdf/historial_clinico_pdf.html`
- `core/templates/core/pdv_farmacia.html`
- `core/templates/core/politicas_descuento.html`
- `core/templates/core/preparacion_toma.html`
- `core/templates/core/pris/lista_acciones.html`
- `core/templates/core/pris/validar_accion.html`
- `core/templates/core/pris/widget_pris.html`
- `core/templates/core/pris_chat.html`
- `core/templates/core/pris_ia_assistant.html`
- `core/templates/core/ranking_desempeno.html`
- `core/templates/core/rate_limited.html`
- `core/templates/core/read_only_contingencia.html`
- `core/templates/core/recepcion_lab.html`
- `core/templates/core/registro_gasto.html`
- `core/templates/core/reporte_fiscal.html`
- `core/templates/core/reporte_friccion.html`
- `core/templates/core/reportes_financieros/balance_general.html`
- `core/templates/core/reportes_financieros/flujo_caja.html`
- `core/templates/core/reportes_financieros/ingresos_egresos.html`
- `core/templates/core/resultados_portal_paciente.html`
- `core/templates/core/resultados_print.html`
- `core/templates/core/rutas_recoleccion.html`
- `core/templates/core/sucursales_modo_inventario_lab.html`
- `core/templates/core/tarifas/configuracion.html`
- `core/templates/core/ticket_lab.html`
- `core/templates/core/ticket_venta.html`
- `core/templates/core/toma_muestra_index.html`
- `core/templates/core/transferencias/crear_transferencia.html`
- `core/templates/core/transferencias/lista_transferencias.html`
- `core/templates/core/transferencias/ver_transferencia.html`
- `core/templates/core/tu_opinion.html`
- `core/templates/core/ver_evaluacion_39a.html`
- `core/templates/core/ver_evaluacion_desempeno.html`
- `core/templates/core/ver_receta_medica.html`
- `core/templates/core/voice_logs_dashboard.html`
- `core/templates/dashboards/dashboard_farmacia.html`
- `core/templates/dashboards/dashboard_laboratorio.html`
- `core/templates/dashboards/dashboard_medico.html`
- `core/templates/emails/resultados_listos.html`
- `core/templates/errors/403.html`
- `core/templates/errors/404.html`
- `core/templates/errors/500.html`
- `core/templates/farmacia/corte_caja_form.html`
- `core/templates/farmacia/corte_caja_resultado.html`
- `core/templates/farmacia/dashboard_alertas.html`
- `core/templates/farmacia/generar_etiquetas.html`
- `core/templates/farmacia/kardex_list.html`
- `core/templates/farmacia/registrar_compra.html`
- `core/templates/general/construccion.html`
- `core/templates/includes/sidebar.html`
- `core/templates/pacientes/historial_clinico.html`
- `core/templates/pris/widget.html`
- `enfermeria/templates/enfermeria/alertas_criticas.html`
- `enfermeria/templates/enfermeria/capturar_signos.html`
- `enfermeria/templates/enfermeria/dashboard.html`
- `enfermeria/templates/enfermeria/graficas_tendencias.html`
- `enfermeria/templates/enfermeria/historial_signos.html`
- `enfermeria/templates/enfermeria/lista_triage.html`
- `farmacia/templates/farmacia/antibioticos/reporte_cofepris.html`
- `farmacia/templates/farmacia/caja/abrir_caja.html`
- `farmacia/templates/farmacia/corte_caja_form.html`
- `farmacia/templates/farmacia/corte_caja_resultado.html`
- `farmacia/templates/farmacia/crear_movimiento.html`
- `farmacia/templates/farmacia/dashboard_alertas.html`
- `farmacia/templates/farmacia/devoluciones/buscar_venta.html`
- `farmacia/templates/farmacia/devoluciones/dashboard.html`
- `farmacia/templates/farmacia/generar_etiquetas.html`
- `farmacia/templates/farmacia/kardex_list.html`
- `farmacia/templates/farmacia/registrar_compra.html`
- `farmacia/templates/farmacia/reporte_valorizacion.html`
- `farmacia/templates/farmacia/semaforo_caducidad.html`
- `farmacia/templates/farmacia/stock_critico.html`
- `ia/templates/ia/asistente/chat.html`
- `ia/templates/ia/dashboard.html`
- `ia/templates/ia/ocr/procesar.html`
- `ia/templates/ia/ocr/resultados.html`
- `ia/templates/ia/voz/resultados.html`
- `ia/templates/ia/voz/transcripcion.html`
- `inventario/templates/inventario/compras/detalle_oc.html`
- `inventario/templates/inventario/compras/form_oc.html`
- `inventario/templates/inventario/compras/form_proveedor.html`
- `inventario/templates/inventario/compras/lista_ocs.html`
- `inventario/templates/inventario/compras/lista_proveedores.html`
- `inventario/templates/inventario/consultorio/dashboard.html`
- `inventario/templates/inventario/consultorio/form_insumo.html`
- `inventario/templates/inventario/consultorio/form_lote.html`
- `inventario/templates/inventario/consultorio/form_salida.html`
- `inventario/templates/inventario/consultorio/lista_insumos.html`
- `inventario/templates/inventario/consultorio/lista_lotes.html`
- `inventario/templates/inventario/consultorio/lista_salidas.html`
- `inventario/templates/inventario/dashboard_reactivos.html`
- `inventario/templates/inventario/detalle_lote.html`
- `inventario/templates/inventario/form_consumo.html`
- `inventario/templates/inventario/form_lote.html`
- `inventario/templates/inventario/form_reactivo.html`
- `inventario/templates/inventario/form_salida_tecnica.html`
- `inventario/templates/inventario/generales/dashboard.html`
- `inventario/templates/inventario/generales/detalle_vale.html`
- `inventario/templates/inventario/generales/form_insumo.html`
- `inventario/templates/inventario/generales/form_lote.html`
- `inventario/templates/inventario/generales/form_vale.html`
- `inventario/templates/inventario/generales/lista_insumos.html`
- `inventario/templates/inventario/generales/lista_lotes.html`
- `inventario/templates/inventario/generales/lista_vales.html`
- `inventario/templates/inventario/lista_consumo.html`
- `inventario/templates/inventario/lista_lotes.html`
- `inventario/templates/inventario/lista_reactivos.html`
- `inventario/templates/inventario/lista_salidas_tecnicas.html`
- `inventario/templates/inventario/traspasos/detalle.html`
- `inventario/templates/inventario/traspasos/form.html`
- `inventario/templates/inventario/traspasos/lista.html`
- `inventario/templates/inventario/traspasos/notificaciones.html`
- `inventario/templates/inventario/trazabilidad_lote.html`
- `iot/templates/iot/dashboard_kioscos.html`
- `laboratorio/templates/laboratorio/admin/cargar_tarifas.html`
- `laboratorio/templates/laboratorio/crear_orden.html`
- `laboratorio/templates/laboratorio/etiqueta_preview.html`
- `laboratorio/templates/laboratorio/kiosko/bienvenida.html`
- `laboratorio/templates/laboratorio/kiosko/index.html`
- `laboratorio/templates/laboratorio/kiosko/no_encontrado.html`
- `lims/templates/lims/analito_detalle.html`
- `lims/templates/lims/analito_editar.html`
- `lims/templates/lims/analitos_lista.html`
- `lims/templates/lims/paquete_detalle.html`
- `lims/templates/lims/paquete_editar.html`
- `lims/templates/lims/paquetes_lista.html`
- `lims/templates/lims/perfil_detalle.html`
- `lims/templates/lims/perfil_editar.html`
- `lims/templates/lims/perfiles_lista.html`
- `lims/templates/lims/precios.html`
- `logistica/templates/logistica/asignar_visita.html`
- `logistica/templates/logistica/crear_transferencia.html`
- `logistica/templates/logistica/detalle_transferencia.html`
- `logistica/templates/logistica/enviar_transferencia.html`
- `logistica/templates/logistica/lista_transferencias.html`
- `logistica/templates/logistica/mapa_rutas.html`
- `logistica/templates/logistica/rastrear_transferencia.html`
- `logistica/templates/logistica/recibir_transferencia.html`
- `mantenimiento/templates/mantenimiento/_nodo_arbol.html`
- `mantenimiento/templates/mantenimiento/dashboard_tco.html`
- `mantenimiento/templates/mantenimiento/detalle_expediente.html`
- `mantenimiento/templates/mantenimiento/detalle_ticket.html`
- `mantenimiento/templates/mantenimiento/diagnostico_inicio.html`
- `mantenimiento/templates/mantenimiento/diagnostico_nodo.html`
- `mantenimiento/templates/mantenimiento/ejecutar_checklist.html`
- `mantenimiento/templates/mantenimiento/form_expediente.html`
- `mantenimiento/templates/mantenimiento/form_ticket.html`
- `mantenimiento/templates/mantenimiento/lista_equipos_operativo.html`
- `mantenimiento/templates/mantenimiento/lista_expedientes.html`
- `mantenimiento/templates/mantenimiento/lista_tickets.html`
- `mantenimiento/templates/mantenimiento/metrologia/dashboard_sensores.html`
- `mantenimiento/templates/mantenimiento/metrologia/form_certificado.html`
- `mantenimiento/templates/mantenimiento/metrologia/form_lectura.html`
- `mantenimiento/templates/mantenimiento/metrologia/form_sensor.html`
- `mantenimiento/templates/mantenimiento/metrologia/lista_certificados.html`
- `mantenimiento/templates/mantenimiento/metrologia/lista_sensores.html`
- `mantenimiento/templates/mantenimiento/qr_equipo.html`
- `mantenimiento/templates/mantenimiento/wizard_arbol.html`
- `mantenimiento/templates/mantenimiento/wizard_dashboard.html`
- `mantenimiento/templates/mantenimiento/wizard_protocolo.html`
- `marketing/templates/marketing/campanas/crear.html`
- `marketing/templates/marketing/campanas/dashboard.html`
- `marketing/templates/marketing/campanas/lista.html`
- `marketing/templates/marketing/contactos/importar.html`
- `marketing/templates/marketing/contactos/lista.html`
- `marketing/templates/marketing/cupones/generar.html`
- `marketing/templates/marketing/cupones/lista.html`
- `marketing/templates/marketing/dashboard_marketing.html`
- `marketing/templates/marketing/entrenamiento_ia.html`
- `marketing/templates/marketing/reactivacion_ia.html`
- `pacientes/templates/pacientes/graficas_signos_vitales.html`
- `pacientes/templates/pacientes/historia_clinica_completa.html`
- `pacientes/templates/pacientes/historial_360.html`
- `pacientes/templates/pacientes/lista_pacientes.html`
- `pacientes/templates/pacientes/portal/cambiar_password.html`
- `pacientes/templates/pacientes/portal/dashboard.html`
- `pacientes/templates/pacientes/portal/login.html`
- `pacientes/templates/pacientes/portal/mi_perfil.html`
- `pacientes/templates/pacientes/portal/mis_consultas.html`
- `pacientes/templates/pacientes/portal/mis_estudios.html`
- `pacientes/templates/pacientes/portal/mis_recetas.html`
- `pacientes/templates/pacientes/portal/solicitar_acceso.html`
- `pacientes/templates/pacientes/timeline_consultas.html`
- `recepcion/templates/recepcion/agendar_cita.html`
- `recepcion/templates/recepcion/buscar_paciente.html`
- `recepcion/templates/recepcion/check_in.html`
- `recepcion/templates/recepcion/cobrar_consulta.html`
- `recepcion/templates/recepcion/dashboard.html`
- `recepcion/templates/recepcion/lista_espera.html`
- `recepcion/templates/recepcion/registrar_paciente.html`
- `seguridad/templates/seguridad/2fa/activar_totp.html`
- `seguridad/templates/seguridad/2fa/codigos_backup.html`
- `seguridad/templates/seguridad/2fa/configuracion.html`
- `seguridad/templates/seguridad/auditoria/dashboard.html`
- `seguridad/templates/seguridad/auditoria/logs.html`
- `seguridad/templates/seguridad/rastro_paciente.html`
- `seguridad/templates/seguridad/sesiones/lista.html`
- `templates/403.html`
- `templates/consultorio/lista_trabajo_medico.html`
- `templates/consultorio/nueva_consulta_soap.html`
- `templates/consultorio/tablero_recepcion.html`
- `templates/pdfs/resultado_lab_print.html`
- `templates/seguridad/2fa/activar_totp.html`
- `templates/seguridad/2fa/codigos_backup.html`
- `templates/seguridad/2fa/configuracion.html`
- `templates/seguridad/auditoria/dashboard.html`
- `templates/seguridad/auditoria/logs.html`
- `templates/seguridad/sesiones/lista.html`

**Total:** 404 archivos `.html`.


## Anexo C — `core/views/`: funciones y clases por archivo (AST)

### `core/views/administracion_usuarios.py`
- **Funciones:** `gestionar_usuarios`, `api_obtener_usuario`, `api_actualizar_usuario`, `api_actualizar_tarifa`, `api_actualizar_permiso`

### `core/views/ai_brain.py`
- **Funciones:** `api_ai_brain_preguntar`

### `core/views/analytics.py`
- **Funciones:** `dashboard_analytics`, `reporte_trazabilidad`, `api_metricas_tiempo_real`

### `core/views/asistencia.py`
- **Funciones:** `dashboard_asistencia`, `registro_asistencia`, `registrar_entrada_salida`, `horarios_trabajo`, `crear_horario`, `incidencias_asistencia`, `crear_incidencia`, `autorizar_incidencia`

### `core/views/audio_legal.py`
- **Funciones:** `api_sellar_audio`, `api_verificar_integridad_audio`

### `core/views/auditoria_api.py`
- **Funciones:** `api_auditar_campo`

### `core/views/auditoria_campo.py`
- **Funciones:** `api_auditoria_campo`

### `core/views/autenticacion_2fa.py`
- **Funciones:** `_get_client_ip`, `_ip_exenta_2fa`, `_2fa_obligatorio_por_rol`, `_2fa_activo_para_usuario`, `_verificar_codigo_maestro`, `_notificar_ciso_uso_codigo_maestro`, `_notificar_telegram`, `notificar_alerta_ciso_expedientes`, `setup_2fa`, `verificar_2fa`, `desactivar_2fa`

### `core/views/autofactura.py`
- **Funciones:** `autofactura_publica`, `bandeja_cfdi`, `api_marcar_cfdi_timbrada`

### `core/views/autorizaciones.py`
- **Funciones:** `crear_solicitud_autorizacion`, `verificar_estado_solicitud`, `listar_autorizaciones_pendientes`, `autorizar_solicitud`, `api_aprobar_solicitud`, `api_rechazar_solicitud`

### `core/views/biblioteca.py`
- **Funciones:** `biblioteca_liderazgo`, `api_cambiar_estado_libro`, `agregar_libro`

### `core/views/bienestar.py`
- **Funciones:** `_calcular_nivel_riesgo`, `_verificar_riesgo_burnout`, `dashboard_bienestar`, `diario_emocional`, `evaluacion_nom035`, `alertas_rrhh`, `capacitaciones`

### `core/views/bienestar_mejorado.py`
- **Funciones:** `chat_bienestar`, `enviar_mensaje_bienestar`, `alertas_bienestar_director`, `marcar_alerta_vista`

### `core/views/blindaje_expediente.py`
- **Funciones:** `pre_sellar_nota`, `sellar_con_pin`, `verificar_nota`, `desbloqueo_forense`, `configurar_pin_lab`, `verificar_publico`, `buscar_cie10`

### `core/views/bot.py`
- **Funciones:** `api_bot_pregunta`

### `core/views/buzon.py`
- **Funciones:** `tu_opinion`, `buzon_kanban`, `api_cambiar_estado_queja`, `api_obtener_quejas`

### `core/views/capacitacion.py`
- **Funciones:** `capacitacion_personal`, `capacitacion_ejecutiva`

### `core/views/capacitacion_rag.py`
- **Funciones:** `_es_director_qc`, `_resolver_documento_capacitacion`, `_procesar_pdf_background`, `dashboard_capacitacion`, `subir_documento_capacitacion`, `reprocesar_documento`, `estado_documento_rag`, `eliminar_documento`, `consultar_pris_rag`, `consultar_pris_worklist`, `obtener_tip_dia`

### `core/views/catalogos.py`
- **Funciones:** `lista_estudios`, `editar_estudio`, `api_vincular_componentes`, `catalogo_medicos`, `catalogo_convenios`, `convenio_precios`

### `core/views/catalogos_maestros.py`
- **Funciones:** `gestionar_metodos`, `api_obtener_metodo`, `api_actualizar_metodo`, `gestionar_muestras`, `api_actualizar_muestra`

### `core/views/cerebro.py`
- **Funciones:** `chat_experto`, `api_cerebro_preguntar`

### `core/views/coach.py`
- **Funciones:** `coach_ejecutivo`, `api_coach_preguntar`

### `core/views/comunicacion.py`
- **Funciones:** `chat_page`, `api_enviar_mensaje`, `api_enviar_audio`, `api_obtener_mensajes`, `api_listar_conversaciones`, `api_listar_usuarios`

### `core/views/configuracion.py`
- **Funciones:** `configuracion_dashboard`, `api_ia_consumo`, `api_cambiar_modo_ia`, `api_guardar_byok`

### `core/views/consentimiento_digital.py`
- **Funciones:** `_hash_firma`, `_generar_pdf_consentimiento`, `pagina_consentimiento`, `api_guardar_consentimiento`, `descargar_pdf_consentimiento`

### `core/views/consentimientos.py`
- **Funciones:** `api_guardar_consentimiento`, `api_verificar_consentimiento`, `validar_consentimiento_requerido`

### `core/views/consulta_ordenes.py`
- **Funciones:** `consulta_ordenes`, `detalle_orden_view`, `api_detalle_orden_completo`

### `core/views/contabilidad.py`
- **Funciones:** `dashboard_contabilidad`, `catalogo_cuentas`, `crear_cuenta`, `lista_polizas`, `crear_poliza`, `ver_poliza`, `autorizar_poliza`, `api_cuentas`

### `core/views/cotizacion.py`
- **Funciones:** `cotizacion_rapida`, `api_buscar_paciente_cotizacion`, `api_crear_paciente_rapido`, `api_buscar_estudios_cotizacion`, `api_calcular_total_cotizacion`, `api_enviar_whatsapp_cotizacion`, `convertir_cotizacion_orden`

### `core/views/crm.py`
- **Funciones:** `_empresa`, `_verificar_empresa`, `dashboard_crm`, `lista_prospectos`, `crear_prospecto`, `detalle_prospecto`, `agregar_seguimiento`, `lista_clientes_crm`, `crear_cliente_crm`, `ver_cliente_crm`, `crear_interaccion_crm`, `lista_oportunidades_crm`, `crear_oportunidad_crm`, `ver_oportunidad_crm`, `cerrar_oportunidad`, `api_kanban_crm`

### `core/views/cron_tasks.py`
- **Funciones:** `_verificar_cron`, `cron_check_metrologia`, `cron_check_stock_critico`, `cron_verify_escudo_clinico`

### `core/views/cuentas_por_cobrar.py`
- **Funciones:** `_empresa`, `cuentas_por_cobrar_dashboard`, `api_registrar_pago_cxc`, `api_crear_cxc`, `convenios_lista`, `api_crear_convenio`, `reporte_fiscal_mensual`

### `core/views/dashboard_unificado.py`
- **Funciones:** `dashboard_unificado`, `api_kpis_tiempo_real`

### `core/views/director.py`
- **Funciones:** `dashboard_director`, `_require_director`, `director_analizadores`, `director_analizadores_crear`, `director_analizadores_toggle`, `director_analizadores_mapeos`, `director_analizadores_probar_conexion`, `director_analizadores_eliminar_mapeo`

### `core/views/entrega_resultados.py`
- **Funciones:** `_contexto_meta_portal_paciente`, `_resumen_semaforo_portal`, `entrega_resultados`, `marcar_entregado`, `api_enviar_email_masivo_resultados`, `resultados_publicos`, `resultados_publicos_pdf`, `api_marcar_whatsapp_enviado`

### `core/views/excepciones_lab.py`
- **Funciones:** `_detalle_lims_key`, `_row_lims_key`, `es_superusuario`, `cancelar_orden`, `editar_paciente_orden`, `validar_valor_critico`, `rechazar_muestra`, `registrar_merma`, `agregar_estudio_orden`, `eliminar_estudio_orden`, `api_detalle_orden`

### `core/views/expediente.py`
- **Funciones:** `api_buscar_paciente_avanzado`, `expediente_clinico`

### `core/views/farmacia.py`
- **Funciones:** `_empresa_desde_request`, `_verificar_acceso`, `_buscar_productos_pdv_resultados`, `api_lotes_producto`, `api_buscar_producto_pdv`, `pdv_buscar_fragmento`, `pdv_farmacia`, `lista_ventas_farmacia`, `procesar_venta`, `entrada_mercancia`, `registrar_compra`, `api_buscar_productos_compra`, `carga_masiva_excel`, `libro_control_antibioticos`, `estadisticas_ventas`, `ajustes_inventario`, `inventario_general`, `registrar_gasto`, `api_saldo_caja`, `api_farmacia_kpis`, `facturacion_40`, `dashboard_farmacia`, `gestionar_politicas_descuento`, `historial_devoluciones`, `buscar_venta_devolucion`, `es_gerente_o_admin`, `procesar_devolucion`, `cancelar_venta`, `imprimir_ticket`, `imprimir_ticket_raw`, `corte_caja_dia`, `api_buscar_productos_lectura`, `api_validar_cupon`, `imprimir_etiquetas`, `validar_pin_precio_neto`, `api_carga_masiva_productos`

### `core/views/feature_flags_admin.py`
- **Funciones:** `_tiene_permiso`, `panel_feature_flags`, `api_toggle_flag`, `api_flags_estado`

### `core/views/finanzas.py`
- **Clases:** `LabCajaView`, `FarmaciaCajaView`, `MasterDashboardView`

### `core/views/general.py`
- **Clases:** `CustomLoginView`
- **Funciones:** `home_view`, `dashboard_medico`, `crear_admin_rescate`, `ingreso_magico`, `log_frontend_error`, `get_redirect_url_by_role`, `logout_view`, `service_worker_view`, `error_404`, `error_500`, `error_403`

### `core/views/historial_resultados.py`
- **Funciones:** `_ref_min_max_analito`, `historial_resultados`, `api_resultados_grafica`, `comparar_resultados`

### `core/views/ia.py`
- **Funciones:** `consultar_ia_negocios`, `generar_analisis_simulado`

### `core/views/ia_dashboard.py`
- **Funciones:** `ia_dashboard`, `api_ia_chat`, `api_ia_diagnostico`, `api_ia_consultar_negocios`

### `core/views/impresion.py`
- **Funciones:** `imprimir_etiquetas_raw`, `imprimir_ticket_raw`

### `core/views/incidencias.py`
- **Funciones:** `registrar_incidencia`, `panel_auditoria_incidencias`, `marcar_incidencia_revisada`

### `core/views/inventario.py`
- **Funciones:** `dashboard_inventario`, `lista_productos`, `movimientos_inventario`, `alertas_inventario`

### `core/views/inventario_predictivo.py`
- **Funciones:** `reporte_prediccion_stock`, `api_prediccion_stock`

### `core/views/laboratorio.py`
- **Funciones:** `_convenio_desde_tarifa`, `_lims_line_key_detalle`, `_lims_line_key_row`, `_detalle_codigo_lista`, `recepcion_lab`, `dashboard_laboratorio`, `api_buscar_estudios`, `api_listar_medicos`, `api_listar_convenios`, `api_precios_convenio`, `_parse_optional_client_mutation_uuid`, `_convenio_desde_tarifa_orden`, `_json_crear_orden_success`, `crear_orden_servicio`, `api_ordenes_recientes`, `imprimir_ticket_lab`, `registro_resultados_entrada`, `lista_trabajo_lab`, `imprimir_hoja_trabajo_pdf`, `abrir_worklist_qr`, `api_guardar_resultados`, `api_preview_formulas_lims`, `generar_qr_orden`, `imprimir_resultados_pdf`, `control_calidad`, `toma_muestra_index`, `api_toma_muestra`, `api_validar_pin`, `api_estado_orden`, `api_preordenes_pendientes`, `api_cargar_preorden`, `api_cobrar_orden`, `imprimir_etiquetas_lab`, `escanear_receta_ia`, `escanear_identidad_ia`, `dashboard_pendientes`, `api_bulk_validar`, `api_bulk_imprimir`, `reporte_tiempos_proceso`, `parsear_tiempo_proceso`, `api_historial_pagos`, `api_cancelar_pago`, `api_datos_orden`, `api_editar_datos_orden`, `api_editar_estudios_orden`, `preparacion_toma`, `api_iniciar_toma`, `api_finalizar_toma`, `lista_pacientes_lab`, `historial_lab_paciente`

### `core/views/laboratorio_captura.py`
- **Funciones:** `_estudio_like`, `_ref_analito`, `captura_resultados_industrial`, `registrar_notificacion_panico`

### `core/views/laboratorio_config.py`
- **Funciones:** `lista_pruebas`, `configurar_prueba`, `configurar_rangos`, `eliminar_prueba`, `duplicar_prueba`, `api_parametros_estudio`, `lista_parametros`, `editar_parametro`, `api_rangos_parametro`, `api_rango_detalle`, `api_soft_delete_parametro`, `api_buscar_parametros`, `_rango_lims_to_dict`

### `core/views/laboratorio_reportes.py`
- **Funciones:** `imprimir_resultados`, `api_generar_y_guardar_reporte`, `validar_resultado`

### `core/views/manual.py`
- **Funciones:** `manual_operativo`, `manual_operativo_pdf`

### `core/views/maquila.py`
- **Funciones:** `maquila_envios`, `enviar_a_maquila`

### `core/views/medico.py`
- **Funciones:** `consulta_medica`, `verificar_existencia_farmacia`, `ver_receta_medica`, `generar_pdf_receta`, `calcular_hash_verificacion_receta`, `verificar_qr_receta`, `lista_trabajo_usg`, `captura_reporte_usg`, `descargar_pdf_ultrasonido`

### `core/views/microbiologia.py`
- **Funciones:** `api_inyectar_antibiogramas`, `api_guardar_sensibilidad`

### `core/views/monitor_produccion.py`
- **Funciones:** `_calcular_metricas_tiempo`, `_formato_tiempo`, `_orden_to_card`, `monitor_produccion`, `api_monitor_datos`, `_descontar_insumos_orden`, `api_avanzar_estado`

### `core/views/motor_financiero.py`
- **Funciones:** `genera_reporte_caja`, `exportar_reporte_excel`, `exportar_reporte_pdf`, `api_resumen_ejecutivo_pris`

### `core/views/nomina.py`
- **Funciones:** `_empresa`, `dashboard_nomina`, `lista_periodos`, `crear_periodo`, `detalle_periodo`, `editar_recibo`, `marcar_periodo_pagado`, `ver_periodo`, `ver_nomina`, `cerrar_periodo`, `calcular_nomina`, `autorizar_nomina`, `api_resumen_nomina`

### `core/views/notificaciones.py`
- **Funciones:** `_json_no_store`, `lista_notificaciones`, `api_notificaciones_badge`, `marcar_leida`, `marcar_todas_leidas`, `configurar_notificaciones`, `ejecutar_verificaciones`, `api_crear_notificacion`

### `core/views/omnisearch.py`
- **Funciones:** `api_omnisearch`

### `core/views/onboarding.py`
- **Clases:** `OnboardingWizardView`, `OnboardingCrearEmpresaView`
- **Funciones:** `api_parse_excel_personal`, `api_listar_empresas`

### `core/views/operaciones.py`
- **Funciones:** `rutas_recoleccion`, `monitor_rutas`

### `core/views/paciente.py`
- **Funciones:** `timeline_paciente`, `buscar_paciente_api`, `lista_pacientes_api`

### `core/views/paciente_detalle.py`
- **Clases:** `ExpedienteClinicoView`
- **Funciones:** `exportar_historial_pdf`

### `core/views/pacientes.py`
- **Funciones:** `api_buscar_pacientes`, `api_guardar_paciente`, `buscar_paciente`

### `core/views/paquetes.py`
- **Funciones:** `api_actualizar_orden_paquete`

### `core/views/pris_checklist.py`
- **Funciones:** `_normalizar`, `_detectar_por_regex`, `_detectar_negaciones`, `_detectar_con_gemini`, `api_detectar_intents_checklist`, `api_guia_preguntas`

### `core/views/pris_ia.py`
- **Funciones:** `_gemini_rest_call`, `_build_system_prompt`, `_verificar_rbac`, `_ejecutar_herramienta`, `_tool_buscar_paciente`, `_tool_estadisticas_dia`, `_tool_buscar_ordenes`, `_tool_resultados_orden`, `_tool_guardar_resultado`, `_tool_buscar_medicamento`, `_tool_buscar_estudio`, `_tool_saldo_caja`, `_tool_ordenes_pendientes`, `_tool_consultar_inventario`, `_tool_auditar_errores_recientes`, `_tool_generar_corte_caja`, `_tool_auditoria_sistema_completa`, `_resumir_resultado_tool`, `_tool_analizar_imagen_documento`, `asistente_page`, `asistente_chat`, `_tool_buscar_reactivo_lab`, `_tool_consultar_stock_silos`, `_tool_validar_orden_laboratorio`, `_tool_notificar_resultados_whatsapp`, `_tool_consultar_manual_lab`, `asistente_reset`, `api_acciones_pendientes`, `api_confirmar_accion`, `api_rechazar_accion`, `_detectar_tool_call`

### `core/views/pris_jarvis.py`
- **Funciones:** `_crear_accion_pris`, `_ip_cliente`, `_rbac_dictado_resultado`, `_rbac_dictado_inventario`, `api_dictado_resultado`, `api_dictado_inventario`, `api_dictado_busqueda`, `api_dictado_validar_orden`, `api_ocr_documento`, `api_crear_archivo_raw`, `api_consulta_voz`, `api_generar_hoja_trabajo`, `api_crear_alerta_clinica`, `api_confirmar_accion`, `api_rechazar_accion`, `_ejecutar_accion_confirmada`, `lista_acciones_pris`, `validar_accion_pris`, `api_coach_toma_muestra`

### `core/views/push.py`
- **Funciones:** `_json_no_store`, `obtener_vapid_key`, `suscribir_push`, `desuscribir_push`, `estado_suscripciones`, `test_notificacion`

### `core/views/ranking.py`
- **Funciones:** `ranking_desempeno`, `detalle_empleado_ranking`

### `core/views/reporte_friccion.py`
- **Funciones:** `reporte_friccion`, `determinar_categoria_automatica`, `generar_punto_critico`, `api_pris_ayuda`, `buzon_kanban`

### `core/views/reportes_financieros.py`
- **Funciones:** `reporte_ingresos_egresos`, `reporte_balance_general`, `reporte_flujo_caja`, `api_ventas_por_mes`, `_excel_response`, `_estilo_encabezado`, `exportar_excel_ingresos_egresos`, `exportar_excel_flujo_caja`, `exportar_excel_balance`

### `core/views/rh.py`
- **Funciones:** `lista_evaluaciones_39a`, `crear_evaluacion_39a`, `ver_evaluacion_39a`, `descargar_pdf_evaluacion_39a`, `generar_pdf_evaluacion_39a`, `nueva_evaluacion_desempeno`, `ver_evaluacion_desempeno`, `mis_resultados`, `matriz_talento`

### `core/views/sentinel_api.py`
- **Funciones:** `api_shield_telemetry`, `api_sentinel_reset`, `api_sentinel_diagnostico`

### `core/views/sucursal_modo_inventario_lab.py`
- **Funciones:** `_acceso_director_o_admin`, `sucursales_modo_inventario_lab`

### `core/views/tarifas.py`
- **Funciones:** `mostrar_configuracion_tarifas`, `api_importar_tarifas_excel`

### `core/views/transferencias.py`
- **Funciones:** `lista_transferencias`, `crear_transferencia`, `ver_transferencia`, `enviar_transferencia`, `recibir_transferencia`, `api_buscar_productos_transferencia`

### `core/views/voice.py`
- **Funciones:** `procesar_comando_api`, `historial_comandos`, `dashboard_voice_logs`, `verificar_webauthn`

### `core/views/war_room.py`
- **Funciones:** `_requiere_director`, `_detectar_discrepancias_caja`, `_detectar_panico_sin_validar`, `_detectar_accesos_fallidos_bienestar`, `_detectar_stock_critico`, `_detectar_anomalias_silos`, `_detectar_cmms_criticos`, `_detectar_burnout_nom035`, `_obtener_flujo_caja`, `_obtener_metricas_rapidas`, `_obtener_tendencia_bienestar`, `_obtener_metricas_marketing`, `war_room`, `api_war_room_anomalias`

## Anexo D — Vistas fuera de `core/views/` (AST)


### Directorio `lims/views/`


### `lims/views/analitos.py`
- **Funciones:** `_check_perm`, `lista`, `detalle`, `editar`, `api_rangos`, `api_rango_eliminar`, `api_rango_item`

### `lims/views/paquetes.py`
- **Funciones:** `_check_perm`, `lista`, `nuevo`, `detalle`, `editar`, `api_agregar_analito`, `api_quitar_analito`, `api_agregar_perfil`, `api_quitar_perfil`

### `lims/views/perfiles.py`
- **Funciones:** `_check_perm`, `lista`, `nuevo`, `detalle`, `editar`, `api_buscar_analitos`, `api_agregar_analito`, `api_quitar_analito`

### `lims/views/precios.py`
- **Funciones:** `_check_perm`, `_get_o_crear_precio`, `_fila_precio_ui`, `lista`, `actualizar_precio`, `ajuste_masivo`, `api_buscar_analitos_precios`, `api_agregar_analito_precio`

### Directorio `laboratorio/views/`


### `laboratorio/views/cci_api.py`
- **Clases:** `_StdDevSample`
- **Funciones:** `_parse_positive_int`, `_base_qs`, `_target_from_lote`, `_float_or_none`, `_series_annotate_kwargs`, `api_cci_lj_summary`, `api_cci_lj_series`

### `laboratorio/views/etiquetas.py`
- **Funciones:** `imprimir_etiqueta_tubo`, `imprimir_etiquetas_lote`, `imprimir_etiqueta_qr`, `vista_previa_etiqueta`

### `laboratorio/views/hl7_receptor.py`
- **Clases:** `_EstadoHL7Compat`
- **Funciones:** `_resolver_empresa_hl7`, `_persistir_huerfano_hl7`, `_war_room_notificar_hl7`, `_get_hl7_active`, `_get_hl7_allowed_ips`, `_get_hl7_api_key`, `receptor_hl7`, `_autenticar_request_hl7`, `_es_muestra_control_por_pid`, `_parsear_mensaje`, `_get_estado_hl7`, `_parsear_obx_hl7`, `_parsear_resultado_astm`, `_buscar_analito_por_codigo_equipo`, `_resolver_equipo_por_ip`, `_extraer_message_control_id_hl7`, `_linea_transaccion_id_hl7`, `_hash_idempotencia_hl7`, `_procesar_item_hl7`, `_get_ip`

### `laboratorio/views/imprimir_zpl.py`
- **Funciones:** `imprimir_etiqueta_zpl`, `imprimir_etiquetas_lote_zpl`, `kiosko_check_in_qr`, `kiosko_index`, `_orden_to_dict`

### Directorio `farmacia/views/`


### `farmacia/views/corte_caja_api.py`
- **Funciones:** `api_corte_caja_unificado`

### `farmacia/views/semaforo.py`
- **Funciones:** `es_farmacia_o_director`, `dashboard_semaforo_caducidad`, `dashboard_stock_critico`

### `farmacia/views/soporte.py`
- **Funciones:** `_es_gerente_o_admin`, `buscar_venta_para_devolucion`, `procesar_devolucion`, `dashboard_devoluciones`, `autorizar_devolucion`, `verificar_apertura_caja`, `abrir_caja`, `validar_venta_antibiotico`, `reporte_cofepris`, `entrada_express`

### Archivos sueltos


### `inventario/views.py`
- **Funciones:** `_get_empresa`, `_empresa_required`, `dashboard_reactivos`, `lista_reactivos`, `crear_reactivo`, `editar_reactivo`, `eliminar_reactivo`, `lista_lotes`, `crear_lote`, `detalle_lote`, `liberar_lote_qc`, `baja_lote`, `lista_salidas_tecnicas`, `crear_salida_tecnica`, `lista_consumo`, `crear_consumo`, `editar_consumo`, `eliminar_consumo`, `trazabilidad_lote`, `api_stock_critico`, `api_lotes_por_reactivo`

### `inventario/views_consultorio.py`
- **Funciones:** `dashboard_consultorio`, `lista_insumos_consultorio`, `crear_insumo_consultorio`, `editar_insumo_consultorio`, `lista_lotes_consultorio`, `crear_lote_consultorio`, `lista_salidas_consultorio`, `registrar_salida_consultorio`

### `inventario/views_generales.py`
- **Funciones:** `dashboard_generales`, `lista_insumos_generales`, `crear_insumo_general`, `editar_insumo_general`, `lista_lotes_generales`, `crear_lote_general`, `lista_vales`, `crear_vale`, `detalle_vale`, `cancelar_vale`

### `inventario/views_compras.py`
- **Funciones:** `_get_ct`, `_folio_oc`, `lista_ordenes_compra`, `crear_orden_compra`, `detalle_oc`, `_recibir_mercancia`, `lista_proveedores`, `crear_proveedor`, `api_articulos_criticos`

### `inventario/views_traspasos.py`
- **Funciones:** `_nombre_articulo`, `_numero_lote`, `_folio_traspaso`, `lista_traspasos`, `crear_traspaso`, `detalle_traspaso`, `_ejecutar_despacho`, `_ejecutar_recepcion`, `_ejecutar_rechazo`, `lista_notificaciones`, `resolver_notificacion`, `api_lotes_silo`

### `mantenimiento/views.py`
- **Funciones:** `_empresa`, `_req_empresa`, `_get_ip`, `wizard_dashboard`, `lista_expedientes`, `crear_expediente`, `detalle_expediente`, `wizard_protocolo`, `wizard_arbol`, `lista_equipos_operativo`, `ejecutar_checklist`, `bypass_checklist`, `diagnostico_inicio`, `diagnostico_nodo`, `lista_tickets`, `crear_ticket`, `detalle_ticket`, `dashboard_tco`, `qr_equipo_publico`, `api_checklist_bloqueado`, `api_stock_lote_para_refaccion`

### `mantenimiento/views_metrologia.py`
- **Funciones:** `lista_certificados`, `subir_certificado`, `eliminar_certificado`, `lista_sensores`, `crear_sensor`, `dashboard_sensores`, `registrar_lectura_manual`, `api_iot_lectura`

### `consultorio/views.py`
- **Funciones:** `_int_or_none`, `_dec_or_none`, `_int_in_range`, `_dec_in_range`, `tablero_recepcion`, `check_in_cita`, `agendar_cita`, `lista_triage`, `captura_signos_vitales`, `lista_trabajo_medico`, `consulta_sin_cita`, `nueva_consulta_soap`, `historial_clinico_paciente`, `dashboard_consultorio`, `generar_certificado`, `ver_certificado`, `ver_consulta_detalle`, `nueva_consulta_simplificada`, `nueva_consulta_con_paciente`, `api_crear_consulta_directa`, `api_crear_paciente_y_consulta`, `api_buscar_pacientes`, `api_analizar_transcripcion`, `api_generar_receta_inmediata`, `api_generar_certificado_inmediato`, `api_generar_orden_laboratorio_inmediata`, `archivos_paciente`, `api_subir_archivo`, `api_eliminar_archivo`, `api_buscar_vademecum`, `api_signos_vitales_tendencia`, `configuracion_medico`, `api_plantillas_especialidad`, `api_usar_plantilla`, `analisis_patrones`, `api_generar_analisis_patron`, `lista_espera`, `api_agregar_lista_espera`, `vademecum_lista`, `historial_signos_vitales`, `agenda_medico`, `triaje_pre_cita`, `campanas_marketing`, `encuestas_satisfaccion`, `seguimiento_tratamiento`, `reportes_productividad`, `videollamada_segura`, `cobro_consulta`, `api_registrar_cobro`, `api_liquidar_vale`, `reporte_liquidacion`, `sentinel_dashboard`, `sentinel_ssh_guide`, `sentinel_detalle`, `api_sentinel_feedback`, `api_sentinel_exportar_cursor`, `api_sentinel_ssh`, `crear_paciente_express`, `api_test_github_sentinel`, `api_resultados_disponibles`, `api_resolver_incidencias_sentinel`, `api_sentinel_listar_feedback`

### `consultorio/pdf_views.py`
- **Funciones:** `imprimir_receta_paciente`, `imprimir_expediente_forense`

### `consultorio/pdf_views_prislab.py`
- **Funciones:** `imprimir_receta_profesional`, `api_generar_receta_pdf`

### `consultorio/api_views.py`
- **Funciones:** `procesar_audio_consulta`, `procesar_audio_laboratorio`, `verificar_api_gemini`

### `laboratorio/views_admin.py`
- **Funciones:** `cargar_tarifas_desde_csv`, `vista_cargar_tarifas`

### `recepcion/views.py`
- **Funciones:** `dashboard_recepcion`, `registrar_paciente`, `buscar_paciente`, `agendar_cita`, `check_in_paciente`, `lista_espera`, `cobrar_consulta`

### `enfermeria/views.py`
- **Funciones:** `dashboard_enfermeria`, `lista_pacientes_triage`, `capturar_signos_vitales`, `_crear_snapshot_signos_vitales`, `_evaluar_alertas_signos`, `historial_signos_paciente`, `graficas_tendencias`, `alertas_signos_criticos`

### `logistica/views.py`
- **Funciones:** `mapa_rutas`, `asignar_visita`, `monitor_rutas`, `lista_transferencias`, `crear_transferencia`, `detalle_transferencia`, `agregar_producto_transferencia`, `enviar_transferencia`, `recibir_transferencia`, `api_cadena_frio_temperatura`, `rastrear_transferencia`

### `marketing/views.py`
- **Funciones:** `dashboard_marketing`, `api_generar_cupon`, `api_crear_campana`, `api_aplicar_cupon`, `entrenamiento_ia`, `lista_campanas`, `crear_campana`, `editar_campana`, `dashboard_campanas`, `lista_cupones`, `generar_cupon`, `lista_contactos`, `importar_contactos`, `api_detectar_pacientes_inactivos`, `dashboard_reactivacion_ia`

### `marketing/views_tracking.py`
- **Funciones:** `_hash_ip`, `_hash_ua`, `_compact_meta`, `_schedule_persist`, `track_pixel_204`

### `contabilidad/views.py`
- **Funciones:** `lista_clientes`, `crear_cliente`, `lista_facturas`, `crear_factura`, `detalle_factura`, `timbrar_factura`, `descargar_xml`, `descargar_pdf`, `api_buscar_cliente`

### `seguridad/views.py`
- **Funciones:** `configuracion_2fa`, `activar_totp`, `confirmar_totp`, `desactivar_totp`, `mostrar_codigos_backup`, `regenerar_codigos_backup`, `generar_codigos_backup`, `verificar_2fa_login`, `sesiones_activas`, `cerrar_sesion_remota`, `cerrar_todas_las_sesiones`, `registrar_sesion_activa`, `dashboard_auditoria`, `logs_auditoria`, `api_verificar_codigo_2fa`, `api_estadisticas_seguridad`, `panic_button`, `_parse_fecha`, `rastro_paciente`

### `iot/views.py`
- **Funciones:** `dashboard_kioscos`, `api_crear_kiosco`, `api_toggle_kiosco`, `api_kiosco_heartbeat`, `api_kiosco_confirmar`, `api_kiosco_rechazar`, `api_enviar_a_kiosco`

### `ia/views.py`
- **Funciones:** `dashboard_ia`, `procesar_receta_ocr`, `resultados_ocr`, `crear_orden_desde_ocr`, `transcribir_audio`, `resultados_transcripcion`, `asistente_medico`, `api_consultar_asistente`, `analizar_sintomas`, `verificar_interacciones`, `_extraer_texto_con_vision_api`, `_extraer_texto_fallback`, `_transcribir_audio_con_speech_api`, `_transcribir_audio_fallback`, `_extraer_entidades_con_gemini`, `_extraer_entidades_fallback`, `_consultar_gemini_asistente`, `_consultar_asistente_fallback`, `_analizar_sintomas_con_gemini`, `_verificar_interacciones_con_gemini`

### `bienestar/views.py`
- **Funciones:** `dashboard_bienestar`, `calcular_racha`, `chat_bienestar`, `api_chat_bienestar`, `detectar_riesgo_emocional`, `diario_emocional`, `nueva_entrada_diario`, `estadisticas_diario`, `recursos_bienestar`, `detalle_recurso`, `agendar_consultorio_bienestar`

### `pacientes/views.py`
- **Funciones:** `historial_360_paciente`, `timeline_consultas`, `graficas_signos_vitales`, `historia_clinica_completa`, `lista_pacientes`, `api_datos_graficas_signos`, `preparar_datos_graficas`, `generar_alertas_clinicas`

### `pacientes/portal_views.py`
- **Funciones:** `portal_login`, `portal_logout`, `solicitar_acceso`, `portal_login_required`, `portal_dashboard`, `portal_mis_consultas`, `portal_mis_estudios`, `portal_mis_recetas`, `portal_descargar_resultado`, `portal_mi_perfil`, `portal_cambiar_password`

---

Levantamiento topográfico completado. Esperando la orden del Director para iniciar la Fase 2: Auditoría Sistemática Módulo por Módulo.
