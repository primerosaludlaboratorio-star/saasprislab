"""
Bankguard — discrepancia entre CierreDiaConsolidado y suma de MovimientoCaja.
Ticket automático si la desviación relativa supera el umbral (p. ej. 1%).
"""
from __future__ import annotations

import logging
from datetime import datetime, time
from decimal import Decimal

_bankguard_log = logging.getLogger('bankguard')

from django.db.models import Sum
from django.utils import timezone

UMBRAL_DISCREPANCIA_DEFAULT = Decimal('0.01')


def _rango_dia(fecha):
    start = timezone.make_aware(datetime.combine(fecha, time.min))
    end = timezone.make_aware(datetime.combine(fecha, time.max))
    return start, end


def sumar_movimientos_caja_dia(cierre):
    """Suma ingresos/egresos del kardex de caja para empresa/sucursal/fecha del cierre."""
    from core.models import MovimientoCaja

    day_start, day_end = _rango_dia(cierre.fecha)
    qs = MovimientoCaja.objects.filter(
        empresa_id=cierre.empresa_id,
        fecha_movimiento__gte=day_start,
        fecha_movimiento__lte=day_end,
    )
    if cierre.sucursal_id:
        qs = qs.filter(sucursal_id=cierre.sucursal_id)
    ing = qs.filter(tipo_movimiento='INGRESO').aggregate(s=Sum('monto'))['s'] or Decimal('0')
    egr = qs.filter(tipo_movimiento='EGRESO').aggregate(s=Sum('monto'))['s'] or Decimal('0')
    return ing, egr, ing - egr


def ratio_desviacion(esperado: Decimal, real: Decimal) -> Decimal:
    base = max(abs(esperado), abs(real), Decimal('1'))
    return abs(esperado - real) / base


def discrepancia_cierre_vs_kardex(cierre, umbral: Decimal = UMBRAL_DISCREPANCIA_DEFAULT):
    """
    Returns:
        (hay_discrepancia: bool, detalle: dict)
    """
    ing_db, egr_db, neto_db = sumar_movimientos_caja_dia(cierre)
    r_ing = ratio_desviacion(cierre.total_ingresos, ing_db)
    r_egr = ratio_desviacion(cierre.total_egresos, egr_db)
    r_neto = ratio_desviacion(cierre.neto_dia, neto_db)
    max_r = max(r_ing, r_egr, r_neto)
    detalle = {
        'ingresos_cierre': cierre.total_ingresos,
        'ingresos_kardex': ing_db,
        'egresos_cierre': cierre.total_egresos,
        'egresos_kardex': egr_db,
        'neto_cierre': cierre.neto_dia,
        'neto_kardex': neto_db,
        'ratio_max': max_r,
    }
    return max_r > umbral, detalle


def ticket_cierre_vs_kardex_ya_existe(cierre) -> bool:
    from core.models import TicketInvestigacionCaja

    return TicketInvestigacionCaja.objects.filter(
        cierre_dia_id=cierre.pk,
        tipo_discrepancia='DIFERENCIA_MONTO',
        estado__in=['ABIERTO', 'EN_INVESTIGACION'],
        descripcion__startswith='[CIERRE_VS_KARDEX]',
    ).exists()


def verificar_discrepancia_cierre_y_ticket(cierre, umbral: Decimal = UMBRAL_DISCREPANCIA_DEFAULT):
    """
    Tras guardar un CierreDiaConsolidado, abre ticket si kardex difiere > umbral.
    Idempotente por prefijo de descripción + cierre + estado.
    """
    if not cierre.pk:
        return None
    excede, det = discrepancia_cierre_vs_kardex(cierre, umbral)
    if not excede:
        return None
    if ticket_cierre_vs_kardex_ya_existe(cierre):
        return None

    from core.models import TicketInvestigacionCaja

    diff_ing = det['ingresos_cierre'] - det['ingresos_kardex']
    desc = (
        f'[CIERRE_VS_KARDEX] Consolidado vs suma MovimientoCaja del día. '
        f'Ingresos cierre={det["ingresos_cierre"]} kardex={det["ingresos_kardex"]} | '
        f'Egresos cierre={det["egresos_cierre"]} kardex={det["egresos_kardex"]} | '
        f'Neto cierre={det["neto_cierre"]} kardex={det["neto_kardex"]} | '
        f'Ratio máx.={det["ratio_max"]:.4f}'
    )
    t = TicketInvestigacionCaja.objects.create(
        empresa_id=cierre.empresa_id,
        cierre_dia=cierre,
        tipo_discrepancia='DIFERENCIA_MONTO',
        descripcion=desc,
        monto_esperado=det['ingresos_cierre'],
        monto_real=det['ingresos_kardex'],
        diferencia=diff_ing,
        creado_por=None,
    )
    _bankguard_log.warning(
        'TicketInvestigacionCaja CIERRE_VS_KARDEX ticket_id=%s cierre_id=%s empresa_id=%s ratio_max=%s',
        t.pk,
        cierre.pk,
        cierre.empresa_id,
        det['ratio_max'],
    )
    return t
