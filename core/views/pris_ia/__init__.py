"""
core/views/pris_ia/__init__.py

Shim retrocompatible: reexporta todas las funciones públicas del paquete
para que urls.py y cualquier otro import existente sigan funcionando sin cambios.
"""

# Vistas públicas (urls.py)
from .views import (
    asistente_page,
    asistente_tts,
    asistente_chat,
    asistente_reset,
    api_acciones_pendientes,
    api_confirmar_accion,
    api_rechazar_accion,
    procesar_pregunta_con_ia,
    _detectar_tool_call,
    _PrisciSession,
)

# Internals reexportados para compatibilidad (voice.py, tests, etc.)
from ._gemini import _gemini_rest_call
from ._prompts import _build_system_prompt
from ._rbac import _verificar_rbac, _rol_aliases_usuario
from ._dispatcher import _ejecutar_herramienta
from ._constants import (
    TOOLS_DESCRIPCION,
    _TOOL_TO_TIPO,
    _TOOL_RBAC,
    _SUPERUSER_ONLY_TOOLS,
    _PRISCI_EXTERNAL_ALLOWED_TOOLS,
)

# Capacidades heredadas expuestas bajo el mismo namespace de PRIS. Los paths
# antiguos siguen funcionando, pero no crean un segundo asistente.
from core.views.pris_jarvis import (
    api_dictado_resultado,
    api_dictado_inventario,
    api_dictado_busqueda,
    api_dictado_validar_orden,
    api_ocr_documento,
    api_crear_archivo_raw,
    api_consulta_voz,
    api_generar_hoja_trabajo,
    api_crear_alerta_clinica,
    api_coach_toma_muestra,
    api_confirmar_accion,
    api_rechazar_accion,
    lista_acciones_pris,
    validar_accion_pris,
)

__all__ = [
    # Públicas
    "asistente_page", "asistente_tts", "asistente_chat", "asistente_reset",
    "api_acciones_pendientes", "api_confirmar_accion", "api_rechazar_accion",
    "procesar_pregunta_con_ia",
    # Internals
    "_gemini_rest_call", "_build_system_prompt",
    "_verificar_rbac", "_rol_aliases_usuario",
    "_ejecutar_herramienta", "_detectar_tool_call",
    "TOOLS_DESCRIPCION", "_TOOL_TO_TIPO", "_TOOL_RBAC",
    "_SUPERUSER_ONLY_TOOLS", "_PRISCI_EXTERNAL_ALLOWED_TOOLS",
    "_PrisciSession",
    "api_dictado_resultado", "api_dictado_inventario", "api_dictado_busqueda",
    "api_dictado_validar_orden", "api_ocr_documento", "api_crear_archivo_raw",
    "api_consulta_voz", "api_generar_hoja_trabajo", "api_crear_alerta_clinica",
    "api_coach_toma_muestra", "api_confirmar_accion", "api_rechazar_accion",
    "lista_acciones_pris", "validar_accion_pris",
]
