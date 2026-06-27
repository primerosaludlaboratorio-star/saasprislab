"""
Registro central de herramientas operativas de PRIS.
Mapea nombre_tool -> {ejecutor, grupos, descripcion} para despacho en pris_ia.py.
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
        "grupos": [],
        "descripcion": "Crea un paciente nuevo en el sistema.",
    },
    "crear_orden_laboratorio": {
        "ejecutor": tool_crear_orden_laboratorio,
        "grupos": [],
        "descripcion": "Crea una orden de laboratorio con estudios para un paciente.",
    },
    "cobrar_orden": {
        "ejecutor": tool_cobrar_orden,
        "grupos": [],
        "descripcion": "Cobra/paga una orden de laboratorio.",
    },
    "registrar_venta_farmacia": {
        "ejecutor": tool_registrar_venta_farmacia,
        "grupos": [],
        "descripcion": "Registra una venta de productos en farmacia.",
    },
    "crear_cotizacion": {
        "ejecutor": tool_crear_cotizacion,
        "grupos": [],
        "descripcion": "Crea una cotizacion de estudios.",
    },
    "buscar_o_crear_paciente": {
        "ejecutor": tool_buscar_o_crear_paciente,
        "grupos": [],
        "descripcion": "Busca un paciente y lo crea si no existe.",
    },
    "actualizar_resultado_laboratorio": {
        "ejecutor": tool_actualizar_resultado_laboratorio,
        "grupos": [],
        "descripcion": "Guarda o actualiza el resultado de un parametro de laboratorio.",
    },
    "cancelar_orden": {
        "ejecutor": tool_cancelar_orden,
        "grupos": [],
        "descripcion": "Cancela una orden de laboratorio.",
    },
    "consultar_expediente_paciente": {
        "ejecutor": tool_consultar_expediente_paciente,
        "grupos": [],
        "descripcion": "Consulta el expediente completo de un paciente.",
    },
    "aplicar_descuento_orden": {
        "ejecutor": tool_aplicar_descuento_orden,
        "grupos": [],
        "descripcion": "Aplica un descuento a una orden de laboratorio.",
    },
    "cambiar_estado_orden": {
        "ejecutor": tool_cambiar_estado_orden,
        "grupos": [],
        "descripcion": "Cambia el estado de una orden de laboratorio.",
    },
    "programar_cita": {
        "ejecutor": tool_programar_cita,
        "grupos": [],
        "descripcion": "Programa una cita medica o de laboratorio.",
    },
    "enviar_notificacion_paciente": {
        "ejecutor": tool_enviar_notificacion_paciente,
        "grupos": [],
        "descripcion": "Envia una notificacion a un paciente por SMS/Email/WhatsApp.",
    },
    "consultar_indicadores_kpi": {
        "ejecutor": tool_consultar_indicadores_kpi,
        "grupos": [],
        "descripcion": "KPIs del dia/semana/mes para el director.",
    },
    "modificar_paciente": {
        "ejecutor": tool_modificar_paciente,
        "grupos": [],
        "descripcion": "Modifica datos de un paciente existente.",
    },
    "gestionar_usuario": {
        "ejecutor": tool_gestionar_usuario,
        "grupos": [],
        "descripcion": "Crea, modifica o desactiva usuarios del sistema (solo Director/Admin).",
    },
}
