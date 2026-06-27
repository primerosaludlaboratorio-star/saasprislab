"""
core.agent.tools - Herramientas operativas de PRIS (split por dominio).
Re-exporta todas las herramientas para compatibilidad con pris_ia.py.
"""
from .pacientes import tool_crear_paciente, tool_buscar_o_crear_paciente, tool_modificar_paciente, tool_consultar_expediente_paciente
from .laboratorio import tool_crear_orden_laboratorio, tool_cobrar_orden, tool_cancelar_orden, tool_actualizar_resultado_laboratorio, tool_aplicar_descuento_orden, tool_cambiar_estado_orden
from .ventas import tool_registrar_venta_farmacia, tool_crear_cotizacion
from .operaciones import tool_programar_cita, tool_enviar_notificacion_paciente, tool_consultar_indicadores_kpi, tool_gestionar_usuario
from .registry import TOOLS_OPERATIVOS

__all__ = [
    'tool_crear_paciente',
    'tool_buscar_o_crear_paciente',
    'tool_modificar_paciente',
    'tool_consultar_expediente_paciente',
    'tool_crear_orden_laboratorio',
    'tool_cobrar_orden',
    'tool_cancelar_orden',
    'tool_actualizar_resultado_laboratorio',
    'tool_aplicar_descuento_orden',
    'tool_cambiar_estado_orden',
    'tool_registrar_venta_farmacia',
    'tool_crear_cotizacion',
    'tool_programar_cita',
    'tool_enviar_notificacion_paciente',
    'tool_consultar_indicadores_kpi',
    'tool_gestionar_usuario',
    'TOOLS_OPERATIVOS',
]
