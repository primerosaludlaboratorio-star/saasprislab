"""
Paquete de modelos de laboratorio.

Re-exporta todos los modelos para mantener compatibilidad con los
importadores existentes (from laboratorio.models import ...).
"""
from .catalogo import (
    CategoriaExamen,
    InsumoEstudio,
    PerfilLaboratorio,
)
from .hardware import (
    BitacoraMantenimiento,
    CodigoParametroEquipo,
    EnvioMaquila,
    Equipo,
    PrecursorCellular,
)
from .clinico import (
    DiferencialLeucocitario,
    Estudio,
    IndiceEritrocitario,
    RangoReferenciaParametro,
    ValorReferencia,
)
from .ordenes import DetalleOrden
from .resultados import (
    HistorialResultados,
    Parametro,
    Resultado,
)
from .regulatorio import (
    ControlCalidad,
    NotificacionPanico,
    ResponsableSanitario,
)
from .hl7 import (
    ResultadoHL7,
    ResultadoHL7Huerfano,
)
from laboratorio.cci_models import (
    EstadoCanalAnalizador,
    LoteMaterialControl,
    MaterialControl,
    MedicionControlInterno,
)
