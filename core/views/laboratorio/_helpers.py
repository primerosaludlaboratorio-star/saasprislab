"""
Utilidades internas compartidas del paquete laboratorio.
Lógica pura — sin except Exception.
"""
from decimal import Decimal

from core.models import Convenio
from core.lims_cart import detalle_orden_etiqueta


def _convenio_desde_tarifa(orden, empresa):
    t = (getattr(orden, 'tarifa', '') or '')
    if not t.startswith('CONVENIO_'):
        return None
    try:
        cid = int(t.split('_', 1)[1])
    except (ValueError, IndexError):
        return None
    return Convenio.objects.filter(id=cid, empresa=empresa).first()


def _lims_line_key_detalle(detail):
    if getattr(detail, 'analito_id', None):
        return ('analito', detail.analito_id)
    if getattr(detail, 'perfil_lims_id', None):
        return ('perfil', detail.perfil_lims_id)
    if getattr(detail, 'paquete_lims_id', None):
        return ('paquete', detail.paquete_lims_id)
    return (None, None)


def _lims_line_key_row(row):
    if row.get('analito'):
        return ('analito', row['analito'].id)
    if row.get('perfil_lims'):
        return ('perfil', row['perfil_lims'].id)
    if row.get('paquete_lims'):
        return ('paquete', row['paquete_lims'].id)
    return (None, None)


def _detalle_codigo_lista(detail):
    if getattr(detail, 'analito_id', None) and detail.analito:
        return (detail.analito.codigo or detail.analito.abreviatura or '')[:30]
    if getattr(detail, 'perfil_lims_id', None):
        return f'PF{detail.perfil_lims_id}'
    if getattr(detail, 'paquete_lims_id', None):
        return f'PQ{detail.paquete_lims_id}'
    return (getattr(detail, 'descripcion_linea', '') or '?')[:30]
