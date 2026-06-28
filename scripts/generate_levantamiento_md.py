# -*- coding: utf-8 -*-
"""Genera docs/LEVANTAMIENTO_TOPOGRAFICO_PRISLAB_SAAS.md (ejecutar desde raíz del repo)."""
import ast
from pathlib import Path

SKIP_DIR_PARTS = frozenset({"venv", ".venv-gate", ".git", "__pycache__", "node_modules", "migrations"})

MD = r"""# Levantamiento topográfico — PRISLAB SaaS

**Fecha del inventario:** 2 de abril de 2026.  
**Alcance:** código de aplicación (se excluyen `venv/`, `.venv-gate/` y plantillas empaquetadas en site-packages).  
**Nota:** Paciente canónico: `core.models.pacientes.Paciente` (`TenantModel`). La tabla legacy `pacientes_paciente` fue retirada.

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
"""

CLOSING = (
    "\n\n---\n\nLevantamiento topográfico completado. Esperando la orden del Director "
    "para iniciar la Fase 2: Auditoría Sistemática Módulo por Módulo.\n"
)


def _list_management_commands(root: Path) -> list[str]:
    cmds: list[str] = []
    for p in root.glob("**/management/commands/**/*.py"):
        if any(x in p.parts for x in SKIP_DIR_PARTS):
            continue
        if p.name == "__init__.py":
            continue
        cmds.append(p.relative_to(root).as_posix())
    return sorted(cmds)


def _list_html_templates(root: Path) -> list[str]:
    htmls: list[str] = []
    for p in root.rglob("*.html"):
        if any(x in p.parts for x in SKIP_DIR_PARTS):
            continue
        htmls.append(p.relative_to(root).as_posix())
    return sorted(htmls)


def _format_ast_module(f: Path, rel_root: Path) -> str:
    rel = f.relative_to(rel_root).as_posix()
    try:
        tree = ast.parse(f.read_text(encoding="utf-8", errors="replace"))
    except SyntaxError as e:
        return f"### `{rel}`\n- **Error de sintaxis:** {e}"
    funcs: list[str] = []
    classes: list[str] = []
    for node in tree.body:
        if isinstance(node, ast.FunctionDef):
            funcs.append(node.name)
        elif isinstance(node, ast.AsyncFunctionDef):
            funcs.append(f"{node.name} (async)")
        elif isinstance(node, ast.ClassDef):
            classes.append(node.name)
    parts: list[str] = [f"### `{rel}`"]
    if classes:
        parts.append("- **Clases:** " + ", ".join(f"`{c}`" for c in classes))
    if funcs:
        parts.append("- **Funciones:** " + ", ".join(f"`{n}`" for n in funcs))
    if not classes and not funcs:
        parts.append("- *(sin defs de módulo)*")
    return "\n".join(parts)


def _scan_dir_py(root: Path, directory: Path) -> list[str]:
    if not directory.is_dir():
        return []
    blocks: list[str] = []
    for f in sorted(directory.rglob("*.py")):
        if f.name == "__init__.py":
            continue
        if any(x in f.parts for x in SKIP_DIR_PARTS):
            continue
        blocks.append(_format_ast_module(f, root))
    return blocks


def main():
    root = Path(__file__).resolve().parents[1]
    out = root / "docs" / "LEVANTAMIENTO_TOPOGRAFICO_PRISLAB_SAAS.md"

    cmds = _list_management_commands(root)
    htmls = _list_html_templates(root)
    core_blocks = _scan_dir_py(root, root / "core" / "views")

    extra_view_dirs = [
        root / "lims" / "views",
        root / "laboratorio" / "views",
        root / "farmacia" / "views",
    ]
    extra_single_files = [
        root / "inventario" / "views.py",
        root / "inventario" / "views_consultorio.py",
        root / "inventario" / "views_generales.py",
        root / "inventario" / "views_compras.py",
        root / "inventario" / "views_traspasos.py",
        root / "mantenimiento" / "views.py",
        root / "mantenimiento" / "views_metrologia.py",
        root / "consultorio" / "views.py",
        root / "consultorio" / "pdf_views.py",
        root / "consultorio" / "pdf_views_prislab.py",
        root / "consultorio" / "api_views.py",
        root / "laboratorio" / "views_admin.py",
        root / "recepcion" / "views.py",
        root / "enfermeria" / "views.py",
        root / "logistica" / "views.py",
        root / "marketing" / "views.py",
        root / "marketing" / "views_tracking.py",
        root / "contabilidad" / "views.py",
        root / "seguridad" / "views.py",
        root / "iot" / "views.py",
        root / "ia" / "views.py",
        root / "bienestar" / "views.py",
        root / "pacientes" / "views.py",
        root / "pacientes" / "portal_views.py",
    ]

    annex_a = "## Anexo A — Comandos de gestión (exhaustivo)\n\n" + "\n".join(
        f"- `{c}`" for c in cmds
    )
    annex_a += f"\n\n**Total:** {len(cmds)} módulos de comando.\n"

    annex_b = "## Anexo B — Plantillas HTML (exhaustivo)\n\n" + "\n".join(f"- `{h}`" for h in htmls)
    annex_b += f"\n\n**Total:** {len(htmls)} archivos `.html`.\n"

    annex_c = "## Anexo C — `core/views/`: funciones y clases por archivo (AST)\n\n" + "\n\n".join(
        core_blocks
    )

    annex_d_parts: list[str] = ["## Anexo D — Vistas fuera de `core/views/` (AST)\n"]
    for d in extra_view_dirs:
        blocks = _scan_dir_py(root, d)
        if not blocks:
            continue
        annex_d_parts.append(f"\n### Directorio `{d.relative_to(root).as_posix()}/`\n\n")
        annex_d_parts.append("\n\n".join(blocks))
    singles: list[str] = []
    for fp in extra_single_files:
        if fp.is_file():
            singles.append(_format_ast_module(fp, root))
    if singles:
        annex_d_parts.append("\n### Archivos sueltos\n\n")
        annex_d_parts.append("\n\n".join(singles))
    annex_d = "\n".join(annex_d_parts)

    body = MD.rstrip() + "\n\n" + annex_a + "\n\n" + annex_b + "\n\n" + annex_c + "\n\n" + annex_d + CLOSING
    out.write_text(body, encoding="utf-8")
    print("Wrote", out, "| commands:", len(cmds), "html:", len(htmls), "core view files:", len(core_blocks))


if __name__ == "__main__":
    main()
