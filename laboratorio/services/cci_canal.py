"""
Barrera CCI / metrología para resultados de paciente (empresa + equipo + analito).
"""
from __future__ import annotations

import logging
from decimal import Decimal
from typing import TYPE_CHECKING, Optional, Tuple

if TYPE_CHECKING:
    from lims.models import Analito

logger = logging.getLogger('laboratorio.cci_canal')

QC_CANAL_CODIGO = 'QC_CANAL_BLOQUEADO'


def mensaje_bloqueo_canal(empresa, equipo, analito) -> Optional[str]:
    """
    None si el canal permite paciente; mensaje si ALERTA_QC o BLOQUEO_METROLOGIA.

    Modo sombra (QC_WESTGARD_ACTIVO=False): no bloquea HTTP aunque el estado persista
    y War Room/UI reciban alertas.
    """
    if not empresa or not equipo or not analito:
        return None
    from core.services.feature_flags import flag_activo

    if not flag_activo('QC_WESTGARD_ACTIVO', empresa):
        return None
    from laboratorio.cci_models import EstadoCanalAnalizador

    row = (
        EstadoCanalAnalizador.objects.filter(
            empresa=empresa,
            equipo=equipo,
            analito=analito,
        )
        .only('estado_operativo', 'motivo')
        .first()
    )
    if not row:
        return None
    if row.estado_operativo == EstadoCanalAnalizador.ALERTA_QC:
        return row.motivo or 'Canal en alerta por control de calidad (Westgard).'
    if row.estado_operativo == EstadoCanalAnalizador.BLOQUEO_METROLOGIA:
        return row.motivo or 'Bloqueo metrológico del equipo para este analito.'
    return None


def persistir_bloqueo_metrologia(empresa, equipo, analito, motivo: str) -> None:
    """Marca BLOQUEO_METROLOGIA para la terna (p. ej. tras evaluar_metrologia hard)."""
    if not empresa or not equipo or not analito:
        return
    from laboratorio.cci_models import EstadoCanalAnalizador

    EstadoCanalAnalizador.objects.update_or_create(
        empresa=empresa,
        equipo=equipo,
        analito=analito,
        defaults={
            'estado_operativo': EstadoCanalAnalizador.BLOQUEO_METROLOGIA,
            'motivo': (motivo or '')[:2000],
        },
    )


def actualizar_canal_por_westgard(
    empresa,
    equipo,
    analito,
    westgard_estado: str,
    reglas: list,
) -> None:
    """Tras RECHAZO Westgard → ALERTA_QC (sin auto-limpieza: requiere actuación de laboratorio)."""
    if not empresa or not equipo or not analito:
        return
    from laboratorio.cci_models import EstadoCanalAnalizador

    if westgard_estado == 'RECHAZO':
        motivo = f"Westgard: {', '.join(reglas)}" if reglas else 'Westgard rechazo'
        EstadoCanalAnalizador.objects.update_or_create(
            empresa=empresa,
            equipo=equipo,
            analito=analito,
            defaults={
                'estado_operativo': EstadoCanalAnalizador.ALERTA_QC,
                'motivo': motivo[:2000],
            },
        )
        try:
            from inventario.models import NotificacionDiscrepancia

            NotificacionDiscrepancia.objects.create(
                empresa=empresa,
                tipo='QC_WESTGARD',
                nivel='CRITICO',
                titulo=f'CCI Westgard rechazo — {getattr(analito, "codigo", "")} / equipo {equipo.pk}',
                detalle=(motivo + f' | analito_id={analito.pk} equipo_id={equipo.pk}')[:4000],
            )
        except Exception as exc:
            logger.warning('War Room CCI Westgard: %s', exc)


def resolver_lote_control(empresa_id: int, analito_id: int):
    from laboratorio.cci_models import LoteMaterialControl

    return (
        LoteMaterialControl.objects.filter(
            material__empresa_id=empresa_id,
            material__analito_id=analito_id,
            material__activo=True,
            activo=True,
        )
        .select_related('material')
        .order_by('-pk')
        .first()
    )


def procesar_medicion_control_hl7(
    *,
    empresa,
    equipo,
    analito: 'Analito',
    valor_float: float,
    origen: str = 'HL7',
) -> Tuple[dict, str]:
    """
    Persiste MedicionControlInterno, evalúa Westgard y actualiza EstadoCanal.
    Retorna (dict detalle, estado_corto).
    """
    from decimal import Decimal

    from laboratorio.cci_models import MedicionControlInterno
    from laboratorio.services.westgard import evaluar_westgard

    detalle: dict = {'analito_id': analito.pk, 'valor': valor_float}
    if not empresa:
        detalle['error'] = 'sin_empresa'
        return detalle, 'CCI_SIN_EMPRESA'

    lote = resolver_lote_control(empresa.pk, analito.pk)
    if not lote or not lote.sd or Decimal(str(lote.sd)) == 0:
        MedicionControlInterno.objects.create(
            empresa=empresa,
            equipo=equipo,
            analito=analito,
            lote_material=lote,
            valor=Decimal(str(valor_float)),
            z_score=None,
            reglas_disparadas=[],
            westgard_estado='SIN_LOTE_SD',
            origen=origen,
        )
        detalle['warning'] = 'Sin lote CCI o SD=0; Westgard omitido'
        return detalle, 'CCI_SIN_CONFIG'

    media = float(lote.media)
    sd = float(lote.sd)
    prev = list(
        MedicionControlInterno.objects.filter(
            empresa=empresa,
            equipo=equipo,
            analito=analito,
        )
        .order_by('-fecha_medicion')[:49]
        .values_list('valor', flat=True)
    )
    prev.reverse()
    valores_hist = [float(v) for v in prev] + [valor_float]

    wg = evaluar_westgard(valores_hist, media, sd)
    z_last = wg.z_scores[-1] if wg.z_scores else None

    MedicionControlInterno.objects.create(
        empresa=empresa,
        equipo=equipo,
        analito=analito,
        lote_material=lote,
        valor=Decimal(str(valor_float)),
        z_score=Decimal(str(round(z_last, 6))) if z_last is not None else None,
        reglas_disparadas=wg.reglas_violadas,
        westgard_estado=wg.estado,
        origen=origen,
    )

    actualizar_canal_por_westgard(empresa, equipo, analito, wg.estado, wg.reglas_violadas)

    detalle['westgard'] = {
        'estado': wg.estado,
        'reglas': wg.reglas_violadas,
        'z_ultimo': z_last,
    }
    estado = 'CCI_INTEGRADO'
    if wg.estado == 'RECHAZO':
        estado = 'CCI_RECHAZO_WESTGARD'
    elif wg.estado == 'WARNING':
        estado = 'CCI_WARNING_WESTGARD'
    return detalle, estado
