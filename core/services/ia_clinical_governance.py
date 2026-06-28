"""
Punto 18 — Ética IA / human-in-the-loop.
Constantes y helpers para que valores sugeridos por PRIS no equivalgan a validación clínica.
"""
from __future__ import annotations

# ResultadoParametro.metodo_captura — sugerencia IA pendiente de validación formal en captura
METODO_IA_BORRADOR = 'IA_BORRADOR'


def defaults_resultado_ia_borrador():
    """Defaults al persistir desde herramientas PRIS (sin escritura autónoma a validado)."""
    return {
        'metodo_captura': METODO_IA_BORRADOR,
        'validado': False,
        'aprobado_por_humano': False,
    }
