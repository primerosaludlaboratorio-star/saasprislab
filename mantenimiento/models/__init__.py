"""
CMMS V8.0 — Paquete de modelos
"""
from .base import (
    SILO_ORIGEN_CHOICES,
    TIPO_EQUIPO_CHOICES,
    NIVEL_AUTORIZACION_CHOICES,
    TIPO_VALIDACION_PASO_CHOICES,
    TIPO_PROTOCOLO_CHOICES,
    TIPO_NODO_CHOICES,
    NIVEL_ESCALAMIENTO_CHOICES,
    TIPO_COMPONENTE_CHOICES,
    ESTADO_TICKET_CHOICES,
)
from .gemelo import ExpedienteEquipo
from .biblioteca import (
    ProtocoloEquipo,
    PasoProtocolo,
    ArbolDiagnostico,
    ProcedimientoReparacion,
    PasoReparacion,
    NodoDiagnostico,
)
from .ejecucion import (
    EjecucionProtocolo,
    RespuestaPasoProtocolo,
    BypassChecklistAutorizacion,
)
from .tickets import TicketMantenimientoCMMS, SalidaRefaccionMantenimiento
from .tco import RegistroTCO
from .metrologia import CertificadoMetrologia
from .iot import SensorIoT, LecturaSensorIoT
from .incca import InCCAInterfaceConfig, InCCAFileEvent, InCCAOutputRowStaging

__all__ = [
    'SILO_ORIGEN_CHOICES',
    'TIPO_EQUIPO_CHOICES',
    'NIVEL_AUTORIZACION_CHOICES',
    'TIPO_VALIDACION_PASO_CHOICES',
    'TIPO_PROTOCOLO_CHOICES',
    'TIPO_NODO_CHOICES',
    'NIVEL_ESCALAMIENTO_CHOICES',
    'TIPO_COMPONENTE_CHOICES',
    'ESTADO_TICKET_CHOICES',
    'ExpedienteEquipo',
    'ProtocoloEquipo',
    'PasoProtocolo',
    'ArbolDiagnostico',
    'ProcedimientoReparacion',
    'PasoReparacion',
    'NodoDiagnostico',
    'EjecucionProtocolo',
    'RespuestaPasoProtocolo',
    'BypassChecklistAutorizacion',
    'TicketMantenimientoCMMS',
    'SalidaRefaccionMantenimiento',
    'RegistroTCO',
    'CertificadoMetrologia',
    'SensorIoT',
    'LecturaSensorIoT',
    'InCCAInterfaceConfig',
    'InCCAFileEvent',
    'InCCAOutputRowStaging',
]
