"""
Contexto edad/sexo para `ValorReferenciaAnalito` (unidad DIAS vs ANOS).
Alineado con `ResultadoParametro.validar_contra_rango`.
"""
from __future__ import annotations

from typing import Any, Optional

from django.utils import timezone


def contexto_edad_sexo_para_lims(
    orden: Optional[Any] = None,
    paciente: Optional[Any] = None,
) -> dict:
    """
    Retorna ``{'edad': int|None, 'edad_dias': int|None, 'sexo': str|None}``.

    - Neonatos (< 365 días desde fecha_nacimiento): solo ``edad_dias``.
    - Resto con fecha de nacimiento: ``edad`` en años (mínimo 1 para filtro ANOS).
    - Sin fecha: usa ``orden.paciente_edad_snapshot`` si existe.
    """
    sexo = None
    if paciente is not None:
        sexo = getattr(paciente, 'sexo', None)
    if not sexo and orden is not None:
        sexo = getattr(orden, 'paciente_sexo_snapshot', None)

    edad_anos = None
    edad_dias = None

    if paciente is not None and getattr(paciente, 'fecha_nacimiento', None):
        fn = paciente.fecha_nacimiento
        d = (timezone.now().date() - fn).days
        if d >= 0:
            if d < 365:
                edad_dias = d
            else:
                ca = paciente.calcular_edad()
                if ca is not None:
                    edad_anos = int(ca) if int(ca) >= 1 else 1

    if edad_anos is None and edad_dias is None and orden is not None:
        snap = getattr(orden, 'paciente_edad_snapshot', None)
        if snap is not None:
            try:
                edad_anos = int(snap) if int(snap) >= 1 else 1
            except (TypeError, ValueError):
                pass

    return {'edad': edad_anos, 'edad_dias': edad_dias, 'sexo': sexo}
