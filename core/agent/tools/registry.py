"""
Registro central de herramientas operativas de PRIS.
Mapea nombre_tool -> {ejecutor, descripcion} para despacho en pris_ia.py.
"""
from .pacientes import (
    tool_crear_paciente, tool_buscar_o_crear_paciente,
    tool_modificar_paciente, tool_consultar_expediente_paciente,
)
from .laboratorio import (
    tool_crear_orden_laboratorio, tool_cobrar_orden, tool_cancelar_orden,
    tool_actualizar_resultado_laboratorio, tool_aplicar_descuento_orden,
    tool_cambiar_estado_orden,
)
from .ventas import tool_registrar_venta_farmacia, tool_crear_cotizacion
from .operaciones import (
    tool_programar_cita, tool_enviar_notificacion_paciente,
    tool_consultar_indicadores_kpi, tool_gestionar_usuario,
)

TOOLS_OPERATIVOS = {
    "crear_paciente": {
        "ejecutor": tool_crear_paciente,
        "descripcion": "Crea un paciente nuevo en el sistema.",
    },
    "crear_orden_laboratorio": {
        "ejecutor": tool_crear_orden_laboratorio,
        "descripcion": "Crea una orden de laboratorio con estudios para un paciente.",
    },
    "cobrar_orden": {
        "ejecutor": tool_cobrar_orden,
        "descripcion": "Cobra/paga una orden de laboratorio.",
    },
    "registrar_venta_farmacia": {
        "ejecutor": tool_registrar_venta_farmacia,
        "descripcion": "Registra una venta de productos en farmacia.",
    },
    "crear_cotizacion": {
        "ejecutor": tool_crear_cotizacion,
        "descripcion": "Crea una cotizacion de estudios.",
    },
    "buscar_o_crear_paciente": {
        "ejecutor": tool_buscar_o_crear_paciente,
        "descripcion": "Busca un paciente y lo crea si no existe.",
    },
    "actualizar_resultado_laboratorio": {
        "ejecutor": tool_actualizar_resultado_laboratorio,
        "descripcion": "Guarda o actualiza el resultado de un parametro de laboratorio.",
    },
    "cancelar_orden": {
        "ejecutor": tool_cancelar_orden,
        "descripcion": "Cancela una orden de laboratorio.",
    },
    "consultar_expediente_paciente": {
        "ejecutor": tool_consultar_expediente_paciente,
        "descripcion": "Consulta el expediente completo de un paciente.",
    },
    "aplicar_descuento_orden": {
        "ejecutor": tool_aplicar_descuento_orden,
        "descripcion": "Aplica un descuento a una orden de laboratorio.",
    },
    "cambiar_estado_orden": {
        "ejecutor": tool_cambiar_estado_orden,
        "descripcion": "Cambia el estado de una orden de laboratorio.",
    },
    "programar_cita": {
        "ejecutor": tool_programar_cita,
        "descripcion": "Programa una cita medica o de laboratorio.",
    },
    "enviar_notificacion_paciente": {
        "ejecutor": tool_enviar_notificacion_paciente,
        "descripcion": "Envia una notificacion a un paciente por SMS/Email/WhatsApp.",
    },
    "consultar_indicadores_kpi": {
        "ejecutor": tool_consultar_indicadores_kpi,
        "descripcion": "KPIs del dia/semana/mes para el director.",
    },
    "modificar_paciente": {
        "ejecutor": tool_modificar_paciente,
        "descripcion": "Modifica datos de un paciente existente.",
    },
    "gestionar_usuario": {
        "ejecutor": tool_gestionar_usuario,
        "descripcion": "Crea, modifica o desactiva usuarios del sistema (solo Director/Admin).",
    },
}
