"""
DEPRECATED: Este archivo sera eliminado en version 2.0
Usar modelos de core en su lugar.
"""

import warnings
warnings.warn(
    f"{__name__} is deprecated. Use core models instead.",
    DeprecationWarning,
    stacklevel=2
)

"""
Metrología / calibración de equipos de laboratorio (Bastión 3).
Usado por el receptor HL7 cuando el equipo se identifica por IP.
"""
import logging
from datetime import date

logger = logging.getLogger('laboratorio.metrologia')

DIAS_VENTANA_BLANDA = 30


def evaluar_metrologia_equipo(equipo):
    """
    Retorna ('ok', None) | ('soft', mensaje) | ('hard', mensaje).
    Sin fecha de vencimiento configurada → ok (compatibilidad con equipos legacy).
    """
    if not equipo:
        return 'ok', None
    v = getattr(equipo, 'fecha_vencimiento_calibracion', None)
    if not v:
        return 'ok', None
    today = date.today()
    if v >= today:
        return 'ok', None
    dias = (today - v).days
    if dias > DIAS_VENTANA_BLANDA:
        return 'hard', f'Calibración vencida hace {dias} días (límite duro {DIAS_VENTANA_BLANDA} d).'
    return 'soft', f'Calibración vencida hace {dias} días (ventana blanda; revise metrología).'
