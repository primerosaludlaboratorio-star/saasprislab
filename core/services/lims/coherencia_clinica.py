"""Fachada canónica para la coherencia clínica de resultados LIMS.

Orquesta los motores existentes sin convertir alertas asistidas en diagnóstico
automático. La liberación siempre conserva el candado humano del servicio de
resultados.
"""
from __future__ import annotations

from typing import Any

from core.services.lims.asistente_clinico import evaluar_asistencia_clinica_orden
from core.utils.referencia_lims_edad import contexto_edad_sexo_para_lims
from laboratorio.services.iso15189 import validar_resultado_analito_lims


def evaluar_resultado_canonico(resultado, orden) -> dict[str, Any]:
    """Evalúa un resultado contra el rango LIMS sin mutar la base de datos."""
    contexto = contexto_edad_sexo_para_lims(orden, getattr(orden, 'paciente', None))
    analito_id = getattr(resultado, 'analito_id', None)
    if not analito_id:
        return {
            'fuente': 'SIN_ANALITO',
            'estado': 'SIN_ANALITO',
            'es_critico': False,
            'es_anormal': False,
            'contexto': contexto,
        }

    validacion = validar_resultado_analito_lims(
        analito_id,
        getattr(resultado, 'valor', '') or '',
        edad_paciente=contexto['edad'],
        sexo_paciente=contexto['sexo'],
        edad_dias=contexto['edad_dias'],
    )
    return {
        'fuente': 'LIMS_VALOR_REFERENCIA_ANALITO',
        'estado': validacion.nivel,
        'es_critico': bool(validacion.es_critico),
        'es_anormal': bool(validacion.es_anormal),
        'mensaje': validacion.mensaje,
        'rango_min': validacion.rango_min,
        'rango_max': validacion.rango_max,
        'critico_min': validacion.critico_min,
        'critico_max': validacion.critico_max,
        'contexto': contexto,
    }


def evaluar_orden_canonica(orden, empresa, *, usuario=None, request=None, accion='borrador') -> dict[str, Any]:
    """Punto único para la evaluación clínica asistida de una orden."""
    resultado = evaluar_asistencia_clinica_orden(
        orden,
        empresa,
        usuario=usuario,
        request=request,
        accion=accion,
    )
    resultado['capas'] = {
        'rangos_lims': True,
        'valores_improbables': True,
        'delta_check': True,
        'formulas_lims': True,
        'westgard_cci': True,
        'liberacion_humana': True,
    }
    resultado['fuente_orquestacion'] = 'core.services.lims.coherencia_clinica'
    return resultado
