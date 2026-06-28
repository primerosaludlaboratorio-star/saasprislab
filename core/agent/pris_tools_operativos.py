"""
MODULO REFACTORIZADO — Shim de retrocompatibilidad.
El codigo fue dividido en el paquete core.agent.tools (split por dominio).
Este archivo solo re-exporta para no romper imports existentes.
"""
from core.agent.tools import (
    tool_crear_paciente,
    tool_crear_orden_laboratorio,
    tool_cobrar_orden,
    tool_registrar_venta_farmacia,
    tool_crear_cotizacion,
    tool_buscar_o_crear_paciente,
    tool_actualizar_resultado_laboratorio,
    tool_cancelar_orden,
    tool_consultar_expediente_paciente,
    tool_aplicar_descuento_orden,
    tool_cambiar_estado_orden,
    tool_programar_cita,
    tool_enviar_notificacion_paciente,
    tool_consultar_indicadores_kpi,
    tool_modificar_paciente,
    tool_gestionar_usuario,
    TOOLS_OPERATIVOS,
)

__all__ = [
    'tool_crear_paciente',
    'tool_crear_orden_laboratorio',
    'tool_cobrar_orden',
    'tool_registrar_venta_farmacia',
    'tool_crear_cotizacion',
    'tool_buscar_o_crear_paciente',
    'tool_actualizar_resultado_laboratorio',
    'tool_cancelar_orden',
    'tool_consultar_expediente_paciente',
    'tool_aplicar_descuento_orden',
    'tool_cambiar_estado_orden',
    'tool_programar_cita',
    'tool_enviar_notificacion_paciente',
    'tool_consultar_indicadores_kpi',
    'tool_modificar_paciente',
    'tool_gestionar_usuario',
    'TOOLS_OPERATIVOS',
]
