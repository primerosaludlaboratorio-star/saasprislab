"""
Motor puro de reglas Westgard (ISO 15189 / CLIA) — sin acceso a base de datos.

Reglas implementadas (sobre la ventana cronológica que termina en el último punto):
  - 1_2s: un punto fuera de ±2σ → WARNING (si no aplica rechazo más severo en el mismo punto)
  - 1_3s: un punto fuera de ±3σ → RECHAZO
  - 2_2s: dos puntos consecutivos del mismo lado fuera de ±2σ → RECHAZO
  - R_4s: diferencia entre dos puntos consecutivos > 4σ → RECHAZO
  - 4_1s: cuatro puntos consecutivos del mismo lado fuera de ±1σ → RECHAZO
  - 10_x: diez puntos consecutivos del mismo lado de la media (todos z>0 o todos z<0) → RECHAZO
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Sequence


RECHAZO_RULES = frozenset({'1_3s', '2_2s', 'R_4s', '4_1s', '10_x'})
WARNING_RULES = frozenset({'1_2s'})


@dataclass
class WestgardResultado:
    z_scores: List[float] = field(default_factory=list)
    reglas_violadas: List[str] = field(default_factory=list)
    estado: str = 'OK'  # OK | WARNING | RECHAZO | ERROR


def _compute_z(valores: Sequence[float], media: float, sd: float) -> List[float]:
    if sd == 0:
        raise ValueError('SD debe ser > 0 para Westgard')
    return [float((v - media) / sd) for v in valores]


def evaluar_westgard(
    valores: Sequence[float],
    media: float,
    sd: float,
    *,
    valores_son_z: bool = False,
) -> WestgardResultado:
    """
    Args:
        valores: mediciones en orden cronológico (más antiguo → más reciente),
                 o Z-scores si valores_son_z=True.
        media: target (ignorado si valores_son_z).
        sd: desviación estándar (ignorada si valores_son_z; en ese caso z ya está en unidades σ).
        valores_son_z: si True, ``valores`` son ya Z-scores.
    """
    out = WestgardResultado()
    if not valores:
        return out
    try:
        if valores_son_z:
            z = [float(x) for x in valores]
        else:
            z = _compute_z(valores, float(media), float(sd))
    except ValueError as e:
        out.estado = 'ERROR'
        out.reglas_violadas = [f'ERROR:{e}']
        return out

    out.z_scores = z
    n = len(z)
    if n == 0:
        return out

    zn = z[-1]
    viol: List[str] = []

    # 1_3s (rechazo) — último punto
    if abs(zn) > 3:
        viol.append('1_3s')
    # 1_2s (advertencia) — solo si no hay 1_3s en el último punto
    elif abs(zn) > 2:
        viol.append('1_2s')

    # 2_2s — dos consecutivos mismo lado más allá de 2σ
    if n >= 2:
        a, b = z[-2], z[-1]
        if (a > 2 and b > 2) or (a < -2 and b < -2):
            viol.append('2_2s')

    # R_4s — salto entre dos consecutivos
    if n >= 2:
        if abs(z[-1] - z[-2]) > 4:
            viol.append('R_4s')

    # 4_1s — cuatro consecutivos mismo lado más allá de 1σ
    if n >= 4:
        w = z[-4:]
        if all(x > 1 for x in w) or all(x < -1 for x in w):
            viol.append('4_1s')

    # 10_x — diez consecutivos mismo lado de la media
    if n >= 10:
        w = z[-10:]
        if all(x > 0 for x in w) or all(x < 0 for x in w):
            viol.append('10_x')

    # Deduplicar preservando orden
    seen = set()
    ordered: List[str] = []
    for r in viol:
        if r not in seen:
            seen.add(r)
            ordered.append(r)
    out.reglas_violadas = ordered

    has_rechazo = bool(set(ordered) & RECHAZO_RULES)
    has_warn = bool(set(ordered) & WARNING_RULES)
    if has_rechazo:
        out.estado = 'RECHAZO'
    elif has_warn:
        out.estado = 'WARNING'
    else:
        out.estado = 'OK'

    return out
