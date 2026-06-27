"""
core/views/pris_ia/_dispatcher.py

Despachador centralizado de herramientas de Prisci.
"""

import logging

from ._constants import _PRISCI_EXTERNAL_ALLOWED_TOOLS
from ._rbac import _verificar_rbac, _rol_aliases_usuario
from ._tools_lectura import (
    _tool_analizar_imagen_documento,
    _tool_auditar_errores_recientes,
    _tool_auditoria_sistema_completa,
    _tool_buscar_estudio,
    _tool_buscar_medicamento,
    _tool_buscar_paciente,
    _tool_buscar_ordenes,
    _tool_consultar_inventario,
    _tool_generar_corte_caja,
    _tool_guardar_resultado,
    _tool_ordenes_pendientes,
    _tool_resultados_orden,
    _tool_saldo_caja,
    _tool_estadisticas_dia,
)
from ._tools_lab import (
    _tool_buscar_reactivo_lab,
    _tool_consultar_manual_lab,
    _tool_consultar_stock_silos,
    _tool_notificar_resultados_whatsapp,
    _tool_validar_orden_laboratorio,
)

logger = logging.getLogger('core')


def _ejecutar_herramienta(nombre_tool, args, request, jarvis_mode=True):
    """Punto de entrada centralizado de Prisci para ejecutar herramientas con RBAC."""
    user = request.user
    empresa = getattr(user, 'empresa', None)

    if getattr(request, 'prisci_external_channel', False) and nombre_tool not in _PRISCI_EXTERNAL_ALLOWED_TOOLS:
        return {
            "denegado_rbac": True,
            "error": "No tienes autorizacion para hacer eso. Contacta a tu supervisor.",
        }

    # Verificar permiso real del usuario humano que invoca Prisci.
    permitido, msg_rbac = _verificar_rbac(nombre_tool, user, jarvis_mode=jarvis_mode)
    if not permitido:
        return {"denegado_rbac": True, "error": msg_rbac}

    try:
        # Herramientas de consulta (read-only)
        if nombre_tool == "buscar_paciente":
            return _tool_buscar_paciente(args, empresa)
        elif nombre_tool == "obtener_estadisticas_dia":
            return _tool_estadisticas_dia(args, empresa)
        elif nombre_tool == "buscar_ordenes":
            return _tool_buscar_ordenes(args, empresa)
        elif nombre_tool == "obtener_resultados_orden":
            return _tool_resultados_orden(args, empresa)
        elif nombre_tool == "guardar_resultado":
            return _tool_guardar_resultado(args, empresa, user)
        elif nombre_tool == "buscar_medicamento":
            return _tool_buscar_medicamento(args, empresa)
        elif nombre_tool == "buscar_estudio":
            return _tool_buscar_estudio(args, empresa)
        elif nombre_tool == "obtener_saldo_caja":
            return _tool_saldo_caja(args, empresa, user)
        elif nombre_tool == "listar_ordenes_pendientes":
            return _tool_ordenes_pendientes(args, empresa)
        elif nombre_tool == "consultar_inventario":
            return _tool_consultar_inventario(args, empresa)
        elif nombre_tool == "auditar_errores_recientes":
            return _tool_auditar_errores_recientes(args, empresa)
        elif nombre_tool == "generar_corte_caja":
            return _tool_generar_corte_caja(args, empresa, user)
        elif nombre_tool == "auditoria_sistema_completa":
            return _tool_auditoria_sistema_completa(args, empresa, user)
        elif nombre_tool == "analizar_imagen_documento":
            return _tool_analizar_imagen_documento(args, empresa, request)
        elif nombre_tool == "buscar_reactivo_laboratorio":
            return _tool_buscar_reactivo_lab(args, empresa)
        elif nombre_tool == "consultar_stock_silos":
            return _tool_consultar_stock_silos(args, empresa)
        elif nombre_tool == "validar_orden_laboratorio":
            return _tool_validar_orden_laboratorio(args, empresa, user)
        elif nombre_tool == "notificar_resultados_whatsapp":
            return _tool_notificar_resultados_whatsapp(args, empresa, user)
        elif nombre_tool == "consultar_manual_lab":
            return _tool_consultar_manual_lab(args, empresa)
        # Herramientas operativas (escritura + nuevas Jarvis)
        else:
            from core.agent.pris_tools_operativos import TOOLS_OPERATIVOS
            if nombre_tool in TOOLS_OPERATIVOS:
                entry = TOOLS_OPERATIVOS[nombre_tool]
                # Capa adicional para herramientas operativas que declaren grupos propios.
                grupos_req = entry.get("grupos", [])
                if grupos_req and not user.is_superuser:
                    grupos_usuario = set(user.groups.values_list('name', flat=True))
                    roles_usuario = _rol_aliases_usuario(user)
                    permitidos = set(grupos_req)
                    if not (grupos_usuario.intersection(permitidos) or roles_usuario.intersection(permitidos)):
                        return {
                            "denegado_rbac": True,
                            "error": (
                                f"Su rol no tiene autorización para '{nombre_tool}'. "
                                f"Se requiere uno de: {', '.join(grupos_req)}."
                            ),
                        }
                return entry["ejecutor"](args, empresa, user)
            return {"error": f"Herramienta '{nombre_tool}' no disponible. Herramientas disponibles: {', '.join(TOOLS_OPERATIVOS.keys())}"}
    except Exception as e:
        # Broad catch intencional: el despachador no puede predecir todos los fallos
        # de herramientas externas (inventario, RAG, Drive, WhatsApp).
        logger.error(f"PRIS tool '{nombre_tool}' error: {e}", exc_info=True)
        return {"error": str(e)}
