"""
Handshake HL7 — Punto 13 v7.5: unidades vs catálogo LIMS y precisión Decimal.
"""
from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Optional, Tuple

# Sustituciones cosméticas UCUM comunes (no convierten magnitud física)
_UNIDAD_ALIASES = {
    'MG/DL': 'MG/DL',
    'MG%2FDL': 'MG/DL',
    'MMOL/L': 'MMOL/L',
    'UI/L': 'U/L',
    'U/L': 'U/L',
    'µUI/ML': 'µUI/ML',
    'µIU/ML': 'µUI/ML',
}


def normalizar_unidad(u: str) -> str:
    """Normaliza para comparación estricta catálogo ↔ equipo."""
    if not u:
        return ''
    s = ' '.join(str(u).strip().split())
    s = s.replace('μ', 'µ').upper()
    s = re.sub(r'\s*/\s*', '/', s)
    return _UNIDAD_ALIASES.get(s, s)


def unidad_equipo_vs_catalogo(
    unidades_catalogo: str,
    unidad_payload: str,
) -> Tuple[bool, str]:
    """
    Si el catálogo declara unidades, el payload debe traer la misma (normalizada).
    Catálogo vacío: no se exige unidad del equipo (compatibilidad legado).
    """
    cat = normalizar_unidad(unidades_catalogo or '')
    pay = normalizar_unidad(unidad_payload or '')
    if not cat:
        return True, ''
    if not pay:
        return False, 'unidad_equipo_vacia'
    if cat != pay:
        return False, 'unidad_distinta'
    return True, ''


def decimal_desde_valor_hl7(valor_str: str) -> Tuple[Optional[Decimal], Optional[str]]:
    """
    Convierte valor HL7 a Decimal (coma decimal, sin float intermedio de magnitud).
    Rechaza marcadores no numéricos típicos (> < texto).
    """
    raw = (valor_str or '').strip()
    if not raw:
        return None, 'vacio'
    # Quitar comparadores de desigualdad al inicio para intentar parseo
    core = raw
    if core[0] in '><≥≤':
        core = core[1:].strip()
    core = core.replace(',', '.')
    # Solo dígitos, punto, signo y exponente mínimo
    if not re.match(r'^[+-]?(\d+\.?\d*|\.\d+)([eE][+-]?\d+)?$', core):
        return None, 'no_decimal'
    try:
        d = Decimal(core)
    except InvalidOperation:
        return None, 'invalid_operation'
    return d, None


def formatear_decimal_para_rp(d: Decimal, decimales: int) -> str:
    """Cadena estable para ResultadoParametro (ISO / informe)."""
    if decimales is None or decimales < 0:
        decimales = 2
    if decimales > 12:
        decimales = 12
    q = Decimal('1.' + '0' * decimales) if decimales else Decimal('1')
    return str(d.quantize(q, rounding=ROUND_HALF_UP))
