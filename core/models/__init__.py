"""
core/models/__init__.py
Paquete de modelos fragmentado (ANT-OOM).
Importa todas las clases para mantener compatibilidad con Django, migraciones y código existente.
"""

# Capa SaaS: Fundación
from .base import (
    get_google_drive_storage,
    AuditoriaModel,
    Empresa,
    Sucursal,
    ConfiguracionModulos,
    Usuario,
    DocumentoConocimiento,
    DatosFiscales,
    ControlCalidad,
    RutaLogistica,
)

# Gobernanza de IA: Uso de recursos y caché de reglas locales
from .ia_config import (
    UsoRecursosIA,
    ReglaLocalIA,
)

# KPIs — Panel Ejecutivo (v1.1+)
from .kpis import (
    KPI_Snapshot,
    KPI_MetaAnual,
)

# Catálogos: Productos, Lab, Convenios
from .catalogos import (
    Producto,
    Lote,
    Medico,
    DiscountPolicy,
    Convenio,
    ConvenioPrecioLims,
)

# Pacientes
from .pacientes import (
    Paciente,
)

# Ventas y Finanzas
from .ventas import (
    Receta,
    RecetaItem,
    DemandaInsatisfecha,
    Venta,
    DetalleVenta,
    DetalleVentaLote,
    DevolucionVenta,
    Pago,
    PagoOrden,
    Gasto,
    AjusteInventario,
    GastoCaja,
    MovimientoCaja,
    GastoOperativo,
    FacturaSAT,
    SalesReturn,
    MetaVenta,
    CuentaPorCobrar,
    PagoCuentaPorCobrar,
    NotaCredito,
)

# Bankguard v1.14 — Control Financiero Endurecido
from .finanzas import (
    PoliticaLimitesCaja,
    GastoCajaEndurecido,
    CierreDiaConsolidado,
    TicketInvestigacionCaja,
)

# Laboratorio Clínico
from .laboratorio import (
    TomaMuestra,
    AudioTomaMuestra,
    EnvioMaquila,
    BitacoraTemperatura,
    MantenimientoEquipo,
    HistorialResultados,
    ResultadoParametro,
    OrdenDeServicio,
    DetalleOrden,
    PreOrdenLaboratorio,
    DetallePreOrden,
)

# Módulo Clínico (NOM-004-SSA3-2012)
from .clinico import (
    CitaMedica,
    HistoriaClinica,
    SignosVitales,
    ConsultaMedica,
    CertificadoMedico,
    NotaClinicaSOAP,
    PlantillaNotaClinica,
    Antecedente,
    FirmaDigital,
    AudioConsulta,
    EstudioImagen,
    ImagenDetalle,
    PlantillaEstudioImagen,
    HistorialCambiosConsulta,
    LogAccesoExpediente,
    ConsentimientoInformado,
    RegistroAuditoriaConsentimiento,
)

# 🔒 Arquitectura de Blindaje v2.0 — Expediente Legalmente Inexpugnable
from .expediente_blindaje import (
    ExpedienteNotaSHA,
    NotaClinicaSellar,
    ReglaPreparacionAnalito,
    OrdenTokenLIMS,
    CatalogoCIE10,
    HashRaizDiario,  # 🔒 Reparación Grieta #2: Anclaje externo
)

# Recursos Humanos
from .rrhh import (
    Empleado,
    Bitacora39A,
    Competencia,
    EvaluacionDesempeno,
    DetalleEvaluacion,
    PlanDesarrollo,
    RegistroAsistencia,
    PeriodoNomina,
    ReciboNomina,
    HorarioTrabajo,
    IncidenciaAsistencia,
)

# Agente PRIS — Copiloto IA (ISO 15189 / Auditoría)
from .pris import (
    AccionPRIS,
)

from .bienestar_staff import (
    EvaluacionNOM035,
    DiarioEmocionalStaff,
    SesionCoachingStaff,
    AlertaBurnout,
    ProgramaCapacitacion,
)

# Rastro forense COFEPRIS (Punto 12)
from .forense import ForenseAcceso

# Operaciones, Auditoría y Notificaciones
from .operaciones import (
    AuditLog,
    BackupRegistro,
    BackupInmutableLog,
    MensajeInterno,
    SolicitudAutorizacion,
    IncidenciaOperativa,
    BuzonQuejas,
    LibroLiderazgo,
    PushSubscription,
    VoiceAuditLog,
    BitacoraEntregaResultados,
    NotificacionSistema,
    ConversacionBienestar,
    AlertaBienestar,
    DocumentoCapacitacion,
    CapsulaSabiduria,
)

__all__ = [
    # base
    'get_google_drive_storage',
    'Empresa', 'Sucursal', 'ConfiguracionModulos', 'Usuario', 'Usuario_Sucursal',
    'DocumentoConocimiento', 'DatosFiscales', 'ControlCalidad', 'RutaLogistica',
    # catalogos
    'Producto', 'Lote', 'Medico', 'DiscountPolicy',
    'Convenio', 'ConvenioPrecioLims',
    # pacientes
    'Paciente',
    # ventas
    'Receta', 'RecetaItem', 'DemandaInsatisfecha',
    'Venta', 'DetalleVenta', 'DetalleVentaLote', 'DevolucionVenta',
    'Pago', 'PagoOrden', 'Gasto', 'AjusteInventario',
    'GastoCaja', 'MovimientoCaja', 'GastoOperativo', 'FacturaSAT',
    'SalesReturn', 'MetaVenta',
    'CuentaPorCobrar', 'PagoCuentaPorCobrar', 'NotaCredito',
    # finanzas — Bankguard v1.14
    'PoliticaLimitesCaja', 'GastoCajaEndurecido', 'CierreDiaConsolidado',
    'TicketInvestigacionCaja',
    # laboratorio
    'TomaMuestra', 'AudioTomaMuestra', 'EnvioMaquila', 'BitacoraTemperatura', 'MantenimientoEquipo',
    'HistorialResultados', 'ResultadoParametro',
    'OrdenDeServicio', 'DetalleOrden',
    'PreOrdenLaboratorio', 'DetallePreOrden',
    # clinico
    'CitaMedica', 'HistoriaClinica', 'SignosVitales', 'ConsultaMedica', 'CertificadoMedico',
    'NotaClinicaSOAP', 'PlantillaNotaClinica', 'Antecedente', 'FirmaDigital',
    'AudioConsulta', 'EstudioImagen', 'ImagenDetalle', 'PlantillaEstudioImagen',
    'HistorialCambiosConsulta', 'LogAccesoExpediente',
    'ConsentimientoInformado', 'RegistroAuditoriaConsentimiento',
    # 🔒 Arquitectura de Blindaje v2.0
    'ExpedienteNotaSHA', 'NotaClinicaSellar',
    'ReglaPreparacionAnalito', 'OrdenTokenLIMS', 'CatalogoCIE10',
    'HashRaizDiario',  # 🔒 Reparación Grieta #2: Anclaje externo
    # rrhh
    'Empleado', 'Bitacora39A', 'Competencia',
    'EvaluacionDesempeno', 'DetalleEvaluacion', 'PlanDesarrollo', 'RegistroAsistencia',
    'PeriodoNomina', 'ReciboNomina',
    'HorarioTrabajo', 'IncidenciaAsistencia',
    # operaciones
    # pris
    'AccionPRIS',
    # operaciones
    'AuditLog', 'BackupRegistro', 'BackupInmutableLog', 'MensajeInterno',
    'SolicitudAutorizacion', 'IncidenciaOperativa', 'BuzonQuejas', 'LibroLiderazgo',
    'PushSubscription', 'VoiceAuditLog',
    'BitacoraEntregaResultados', 'NotificacionSistema',
    'ForenseAcceso',
    'ConversacionBienestar', 'AlertaBienestar',
    'DocumentoCapacitacion', 'CapsulaSabiduria',
    # bienestar_staff NOM-035 (Migración Maestra activada)
    'EvaluacionNOM035', 'DiarioEmocionalStaff', 'SesionCoachingStaff',
    'AlertaBurnout', 'ProgramaCapacitacion',
    # kpis — Panel Ejecutivo
    'KPI_Snapshot', 'KPI_MetaAnual',
]
