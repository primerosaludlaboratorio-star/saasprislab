"""
Validadores de reglas de negocio estrictas del sistema.
Incluye la "Triple Llave" de envío y otras validaciones críticas.

Canónico: ``core.OrdenDeServicio`` + ``core.ResultadoParametro``.
Se mantiene compatibilidad con ``laboratorio.Orden`` / ``laboratorio.Resultado`` donde aún existan.
"""

from __future__ import annotations

from typing import Tuple, List


def _orden_pagada_completa(orden) -> bool:
    sp = getattr(orden, 'estado_pago', None)
    if isinstance(sp, bool):
        return sp
    if isinstance(sp, str):
        return sp == 'PAGADO'
    return False


def _llave_validacion_tecnica(orden, errores: List[str]) -> None:
    """QC: legacy usa ``usuario_valido``; ODS usa resultados LIMS con ``validado``."""
    if hasattr(orden, 'usuario_valido'):
        if not getattr(orden, 'usuario_valido_id', None):
            errores.append('❌ La orden no ha sido validada por calidad técnica.')
        return

    mgr = getattr(orden, 'resultados', None)
    if mgr is None:
        errores.append('❌ La orden no ha sido validada por calidad técnica.')
        return
    qs = mgr.all()
    if not qs.exists():
        errores.append('❌ No hay resultados validables aún (sin parámetros capturados).')
        return
    first = qs.first()
    if hasattr(first, 'validado'):
        if qs.filter(validado=False).exists():
            errores.append('❌ La orden no ha sido validada por calidad técnica (hay resultados sin validar).')
    else:
        errores.append('❌ La orden no ha sido validada por calidad técnica.')


def validar_triple_llave(orden) -> Tuple[bool, List[str]]:
    """
    Valida la "Triple Llave" antes de permitir el envío de resultados.

    1. Orden pagada (``estado_pago == 'PAGADO'`` en ODS, o booleano en legacy).
    2. Validación técnica (todos los ``ResultadoParametro.validado``, o ``usuario_valido`` en legacy).
    3. Teléfono del paciente verificado si el modelo lo expone.

    Args:
        orden: ``core.OrdenDeServicio`` o, en legacy, ``laboratorio.Orden``.

    Returns:
        (es_valida, lista_de_errores)
    """
    errores: List[str] = []

    if not _orden_pagada_completa(orden):
        errores.append('❌ La orden no está pagada completamente. Saldo pendiente.')

    _llave_validacion_tecnica(orden, errores)

    paciente = getattr(orden, 'paciente', None)
    if paciente is None:
        errores.append('⚠️ La orden no tiene paciente asociado.')
    elif hasattr(paciente, 'telefono_verificado') and not paciente.telefono_verificado:
        errores.append('❌ El teléfono del paciente no está verificado.')

    return len(errores) == 0, errores


def validar_valor_panico(resultado) -> Tuple[bool, str]:
    """
    Indica si un resultado está en rango de pánico.

    - ``core.ResultadoParametro``: usa ``es_critico`` (LIMS / validación).
    - ``laboratorio.Resultado``: ``es_critico`` o rangos en ``estudio`` si existen.

    Args:
        resultado: Instancia de ``ResultadoParametro`` o ``laboratorio.Resultado``.

    Returns:
        (es_panico, mensaje)
    """
    if getattr(resultado, 'es_critico', False):
        val = (
            getattr(resultado, 'valor', None)
            or getattr(resultado, 'valor_obtenido', None)
            or ''
        )
        return True, f'⚠️ VALOR DE PÁNICO: {val} (crítico)'

    estudio = getattr(resultado, 'estudio', None)
    if estudio is None:
        return False, ''

    if not hasattr(estudio, 'rango_panico_min') or not hasattr(estudio, 'rango_panico_max'):
        return False, ''

    if estudio.rango_panico_min is None or estudio.rango_panico_max is None:
        return False, ''

    raw = getattr(resultado, 'valor_obtenido', None) or getattr(resultado, 'valor', None) or ''
    try:
        valor_num = float(str(raw).replace(',', '').strip())
    except (ValueError, TypeError, AttributeError):
        return False, ''

    if valor_num < float(estudio.rango_panico_min) or valor_num > float(estudio.rango_panico_max):
        return (
            True,
            f'⚠️ VALOR DE PÁNICO: {raw} está fuera del rango crítico '
            f'({estudio.rango_panico_min} - {estudio.rango_panico_max})',
        )

    return False, ''


def requiere_doble_validacion(orden) -> bool:
    """
    True si hay al menos un resultado en pánico o la orden lo marca explícitamente.

    Args:
        orden: ``core.OrdenDeServicio`` o ``laboratorio.Orden``.
    """
    mgr = getattr(orden, 'resultados', None)
    if mgr is not None:
        for resultado in mgr.all()[:500]:
            es_panico, _ = validar_valor_panico(resultado)
            if es_panico:
                return True

    if hasattr(orden, 'requiere_doble_validacion'):
        return bool(getattr(orden, 'requiere_doble_validacion'))

    return False
