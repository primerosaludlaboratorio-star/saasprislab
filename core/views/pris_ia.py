import os
"""
PRIS — Sistema Nervioso Central v2 (Jarvis-Level)
==================================================
Asistente omnipresente con acciones reales en PRISLAB.
Usa el REST API de Gemini v1 directamente (sin dependencia del SDK)
para máxima compatibilidad y control del endpoint.

Endpoint:
    POST /ia/asistente/chat/
    Body: { "mensaje", "historial", "contexto_pagina", "imagen_b64" }
"""
import json
import re
import logging
import time
import base64
import traceback
import urllib.request
import urllib.error
from datetime import datetime

from django.conf import settings
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.shortcuts import render, get_object_or_404
from django.utils import timezone
from django.db.models import Q, Sum

from core.models import AccionPRIS

logger = logging.getLogger('core')

# Mapeo de tool_name → tipo AccionPRIS
_TOOL_TO_TIPO = {
    "crear_paciente":                   AccionPRIS.TIPO_CREAR_REGISTRO,
    "buscar_o_crear_paciente":          AccionPRIS.TIPO_CREAR_REGISTRO,
    "crear_orden_laboratorio":          AccionPRIS.TIPO_CREAR_REGISTRO,
    "cobrar_orden":                     AccionPRIS.TIPO_CREAR_REGISTRO,
    "registrar_venta_farmacia":         AccionPRIS.TIPO_CREAR_REGISTRO,
    "crear_cotizacion":                 AccionPRIS.TIPO_GENERAR_REPORTE,
    "cancelar_orden":                   AccionPRIS.TIPO_MODIFICAR_REGISTRO,
    "actualizar_resultado_laboratorio": AccionPRIS.TIPO_VALIDAR_RESULTADO,
    "guardar_resultado":                AccionPRIS.TIPO_VALIDAR_RESULTADO,
}

# ─── REST API de Gemini v1 ─────────────────────────────────────────────────────

_GEMINI_REST_URL = "https://generativelanguage.googleapis.com/v1/models/{model}:generateContent?key={key}"
_DEFAULT_GEMINI_MODEL = "gemini-2.0-flash"
_FALLBACK_MODELS = ["gemini-2.0-flash", "gemini-2.0-flash-lite", "gemini-2.5-flash-lite"]


def _gemini_rest_call(api_key: str, prompt_text: str, imagen_b64: str = "",
                      temperatura: float = 0.4, max_tokens: int = 1200) -> str:
    """
    Llama al REST API de Gemini v1 directamente.
    Soporta texto y una imagen opcional en base64.
    Retorna el texto de la respuesta.
    """
    if not imagen_b64:
        try:
            from core.utils.gemini_client import generate_content
            return generate_content(
                prompt_text,
                model_name=_DEFAULT_GEMINI_MODEL,
                temperature=temperatura,
                max_tokens=max_tokens,
            ).strip()
        except Exception as provider_error:
            logger.warning("PRIS proveedor IA texto no disponible, intentando REST Gemini: %s", provider_error)

    parts = [{"text": prompt_text}]

    if imagen_b64:
        try:
            raw = imagen_b64.split(',', 1)[1] if ',' in imagen_b64 else imagen_b64
            # Detectar mime_type del header de data URI
            mime_type = "image/jpeg"
            if imagen_b64.startswith("data:"):
                mime_type = imagen_b64.split(';')[0].split(':')[1]
            parts.append({
                "inline_data": {
                    "mime_type": mime_type,
                    "data": raw,
                }
            })
        except Exception as img_err:
            logger.warning(f"PRIS: imagen inválida, se omite: {img_err}")

    payload = {
        "contents": [{"role": "user", "parts": parts}],
        "generationConfig": {
            "temperature": temperatura,
            "maxOutputTokens": max_tokens,
        },
    }
    body = json.dumps(payload).encode("utf-8")

    last_error = None
    for model in _FALLBACK_MODELS:
        url = _GEMINI_REST_URL.format(model=model, key=api_key)
        req = urllib.request.Request(
            url, data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        # Reintentos con backoff para 429/503 (rate limit / sobrecarga)
        for intento in range(3):
            try:
                with urllib.request.urlopen(req, timeout=45) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                candidates = data.get("candidates", [])
                if candidates:
                    parts_resp = candidates[0].get("content", {}).get("parts", [])
                    text = "".join(p.get("text", "") for p in parts_resp)
                    logger.info(f"PRIS Gemini REST OK — modelo: {model}")
                    return text.strip()
                logger.warning(f"PRIS Gemini '{model}': sin candidatos")
                break
            except urllib.error.HTTPError as e:
                err_body = e.read().decode("utf-8", errors="ignore")
                logger.warning(f"PRIS Gemini '{model}' HTTP {e.code} intento {intento+1}: {err_body[:200]}")
                if e.code == 403:
                    raise PermissionError(
                        "Gemini REST devolvió 403/Forbidden. "
                        "Verifica que la API key esté autorizada para generativelanguage.googleapis.com "
                        "y que el modelo solicitado esté habilitado."
                    ) from e
                if e.code in (429, 503) and intento < 2:
                    # Espera escalonada: 2s, 5s
                    time.sleep(2 + intento * 3)
                    continue
                last_error = f"HTTP {e.code}: {err_body[:150]}"
                break
            except Exception as e:
                logger.warning(f"PRIS Gemini '{model}' error: {e}")
                last_error = str(e)
                break

    raise Exception(last_error or "Gemini no respondió con ningún modelo.")

# ─── Tools disponibles ─────────────────────────────────────────────────────────

TOOLS_DESCRIPCION = """
HERRAMIENTAS DISPONIBLES (PRIS-Jarvis — Acceso Irrestricto) — responde con JSON puro:
{"tool": "nombre_herramienta", "args": {"arg1": "valor1"}}

═══ CONSULTA (solo lectura — sin confirmación) ═══
1.  buscar_paciente — args: nombre, telefono — Busca pacientes registrados
2.  obtener_estadisticas_dia — args: fecha (YYYY-MM-DD) — Estadísticas del día
3.  buscar_ordenes — args: folio, paciente_nombre, estado, hoy (bool) — Busca órdenes
4.  obtener_resultados_orden — args: folio — Resultados de laboratorio de un folio
5.  buscar_medicamento — args: nombre — Busca medicamentos en farmacia con stock
6.  buscar_estudio — args: nombre — Busca estudios clínicos y su precio
7.  obtener_saldo_caja — args: {} — Saldo y ventas del día
8.  listar_ordenes_pendientes — args: area, limite — Órdenes pendientes de procesar
9.  consultar_inventario — args: producto, limite — Stock real en lotes de productos
10. auditar_errores_recientes — args: modulo, limite — Errores activos en Sentinel
11. generar_corte_caja — args: fecha — Resumen de corte de caja
12. auditoria_sistema_completa — args: {} — Diagnóstico completo [SOLO SUPERUSUARIO]
13. consultar_expediente_paciente — args: paciente_id O nombre, limite_ordenes — Historial completo del paciente
14. consultar_indicadores_kpi — args: periodo (HOY/SEMANA/MES), categoria (LABORATORIO/FARMACIA/GENERAL) — KPIs para el director

═══ ESCRITURA — Acciones reales (REQUIEREN CONFIRMACIÓN HUMANA) ═══
15. crear_paciente — args: nombres, apellido_paterno, apellido_materno, telefono, fecha_nacimiento (YYYY-MM-DD), sexo (M/F/O), confirmado
    → Registra un paciente nuevo
16. crear_orden_laboratorio — args: paciente_id O paciente_nombre, estudios_ids ([int]) O estudios_nombres ([str]), metodo_pago, descuento_monto, confirmado
    → Crea una orden de laboratorio con estudios
17. cobrar_orden — args: folio_orden, metodo_pago (EFECTIVO/TARJETA/TRANSFERENCIA), monto_pagado, confirmado
    → Cobra y marca como PAGADA una orden
18. registrar_venta_farmacia — args: productos ([{nombre, cantidad}]), metodo_pago, paciente_nombre, confirmado
    → Registra una venta en farmacia POS
19. crear_cotizacion — args: paciente_nombre, estudios_nombres ([str]) O estudios_ids ([int]), descuento_porcentaje
    → Genera una cotización (sin confirmación — solo cálculo)
20. buscar_o_crear_paciente — args: nombres, apellido_paterno, telefono, fecha_nacimiento, sexo
    → Busca paciente y lo crea si no existe (flujo automático)
21. actualizar_resultado_laboratorio — args: folio_orden, nombre_parametro, valor, confirmado
    → Sugiere resultado (borrador IA); NO valida; el QFB debe validar en captura
22. guardar_resultado — args: folio_orden, nombre_parametro, valor — alias; mismo borrador IA
23. cancelar_orden — args: folio_orden, motivo, confirmado
    → Cancela una orden de laboratorio
24. aplicar_descuento_orden — args: folio_orden, descuento_monto O descuento_porcentaje, motivo, confirmado
    → Aplica o modifica el descuento de una orden
25. cambiar_estado_orden — args: folio_orden, nuevo_estado (PENDIENTE_PAGO/PAGADO/EN_PROCESO/CANCELADA), confirmado
    → Cambia estado operativo; PROHIBIDO: RESULTADOS_LISTOS y ENTREGADO (solo validación humana en captura)
26. programar_cita — args: paciente_id O paciente_nombre, fecha (YYYY-MM-DD), hora (HH:MM), tipo_cita (LABORATORIO/CONSULTORIO), motivo, confirmado
    → Programa una cita médica o de laboratorio
27. enviar_notificacion_paciente — args: paciente_id O paciente_nombre, canal (SMS/EMAIL/WHATSAPP), mensaje, confirmado
    → Envía una notificación al paciente
28. modificar_paciente — args: paciente_id, [telefono, email, sexo], confirmado
    → Actualiza datos de un paciente existente
29. gestionar_usuario — args: accion (CREAR/DESACTIVAR), username, nombres, apellido_paterno, email, rol, password (para CREAR), confirmado
    → Administra usuarios del sistema [DIRECTOR/ADMIN]
30. analizar_imagen_documento — args: imagen_b64 — Clasifica INE/receta/orden y pre-llena formulario de recepción
31. buscar_reactivo_laboratorio — args: nombre, limite — Busca reactivos/consumibles en el Silo de Laboratorio con stock disponible
32. consultar_stock_silos — args: silo (LAB/CONSULTORIO/GENERAL), nombre — Consulta stock en cualquier silo de inventario
33. validar_orden_laboratorio — args: folio_orden, confirmado — Valida y libera resultados de una orden (REQUIERE PIN del QFB en panel)
34. notificar_resultados_whatsapp — args: folio_orden, confirmado — Genera enlace WhatsApp para notificar al paciente que sus resultados están listos
35. consultar_manual_lab — args: pregunta — Consulta la biblioteca de manuales/protocolos del laboratorio (RAG). Responde preguntas como "¿cuál es el tubo para coagulación?", "tiempo de ayuno para glucosa", "protocolo de calibración"

PROTOCOLO OBLIGATORIO PARA ESCRITURAS:
- SIEMPRE usa confirmado:false primero → el resumen del plan aparece y el usuario confirma con "sí"/"confirmo"/"dale"
- SOLO ejecuta con confirmado:true cuando el usuario dice "sí", "confirmo", "procede" o equivalente
- Para flujos compuestos (registrar paciente + crear orden + cobrar), ejecuta UNA herramienta a la vez y espera confirmación
- NUNCA inventes datos. Si algo no existe, dilo claramente y ofrece buscar alternativas

FLUJO EJEMPLO — "necesito crear una orden de laboratorio":
1. Pregunta: "¿Para qué paciente? ¿Tiene registro en el sistema?"
2. buscar_paciente → si no existe: crear_paciente (con confirmación)
3. buscar_estudio para cada estudio mencionado
4. crear_orden_laboratorio con confirmado:false → muestra resumen → espera "sí"
5. crear_orden_laboratorio con confirmado:true → crea la orden y da el folio
6. Pregunta: "¿La cobro ahora?"

EJEMPLOS RÁPIDOS:
- "registra a Juan López tel 555-1234" → {"tool":"crear_paciente","args":{"nombres":"Juan","apellido_paterno":"López","telefono":"555-1234","confirmado":false}}
- "crea orden de BH y QS para María García" → primero buscar_paciente, luego crear_orden_laboratorio
- "cobra el folio F-001 en efectivo" → {"tool":"cobrar_orden","args":{"folio_orden":"F-001","metodo_pago":"EFECTIVO","confirmado":false}}
- "¿cuántas órdenes hay hoy?" → {"tool":"obtener_estadisticas_dia","args":{}}
- "expediente de Juan" → {"tool":"consultar_expediente_paciente","args":{"nombre":"Juan"}}
- "KPIs de hoy" → {"tool":"consultar_indicadores_kpi","args":{"periodo":"HOY","categoria":"GENERAL"}}
"""


def _build_system_prompt(request, contexto_pagina=""):
    """Construye el prompt del sistema con contexto del usuario."""
    user = request.user
    empresa = getattr(user, 'empresa', None)

    nombre_empresa = getattr(empresa, 'nombre', 'PRISLAB') if empresa else 'PRISLAB'
    nombre_usuario = user.get_full_name() or user.username
    rol_usuario = getattr(user, 'rol', 'ADMIN')
    es_superuser = user.is_superuser

    fecha_hora = timezone.localtime(timezone.now()).strftime("%A %d de %B de %Y, %H:%M")

    modulo_actual = "Sistema general"
    if contexto_pagina:
        if '/laboratorio' in contexto_pagina or '/captura' in contexto_pagina:
            modulo_actual = "Laboratorio - Captura de resultados"
        elif '/recepcion' in contexto_pagina:
            modulo_actual = "Recepción"
        elif '/farmacia' in contexto_pagina:
            modulo_actual = "Farmacia"
        elif '/consultorio' in contexto_pagina or '/medico' in contexto_pagina:
            modulo_actual = "Consultorio médico"
        elif '/dashboard' in contexto_pagina:
            modulo_actual = "Dashboard"
        elif '/cotizacion' in contexto_pagina:
            modulo_actual = "Cotizador"

    grupos_usuario = list(request.user.groups.values_list('name', flat=True)) if request.user.is_authenticated else []
    grupos_str = ', '.join(grupos_usuario) if grupos_usuario else 'Sin grupos asignados'

    _eid = getattr(empresa, "id", None)
    _tenant_line = (
        f"CONTEXTO TENANT (obligatorio): empresa_id={_eid}. "
        f"No uses ni reveles datos de otras empresas o sucursales. "
        f"Todas las herramientas deben limitarse a empresa_id={_eid}.\n"
        if _eid is not None
        else "CONTEXTO TENANT: sin empresa asignada; no inventes ni asumas otra empresa.\n"
    )

    return f"""Eres PRIS-Jarvis — Agente Operativo Integral del laboratorio clínico {nombre_empresa}.
Eres el copiloto del sistema: ejecutas cualquier acción en el sistema en nombre del usuario.
No tienes restricciones de módulo. Tu única restricción es la confirmación humana obligatoria para escrituras.

{_tenant_line}
OPERADOR: {nombre_usuario} | Rol: {'SUPERUSUARIO' if es_superuser else rol_usuario} | Grupos: {grupos_str}
EMPRESA: {nombre_empresa} | MÓDULO ACTIVO: {modulo_actual} | {fecha_hora}

FILOSOFÍA JARVIS:
- Cuando te piden algo, LO HACES. No rediriges al usuario a una pantalla.
- Para acciones de escritura: primero muestras el plan (confirmado:false), luego ejecutas (confirmado:true).
- Para consultas: respondes directamente sin pedir confirmación.
- Puedes encadenar múltiples herramientas para completar una tarea compuesta.
- Eres proactivo: si el usuario dice "crea una orden", preguntas el paciente, los estudios, y lo haces todo.

FLUJO MAESTRO para "necesito crear una orden de laboratorio" (o similar):
1. Pregunta por el paciente → buscar_paciente → si no existe: crear_paciente con confirmación
2. Pregunta por los estudios → buscar_estudio para verificar
3. crear_orden_laboratorio (confirmado:false) → presentas resumen → esperas "sí"
4. crear_orden_laboratorio (confirmado:true) → das el folio generado
5. Preguntas proactivamente: "¿La cobro ahora? ¿Imprimimos etiquetas?"

CONTEXTO DE MÓDULO: Estás en "{modulo_actual}". Usa ese contexto para respuestas más relevantes.

TONO: Profesional, cálido, directo. Sin tecnicismos innecesarios. Responde en español.

NUNCA:
- Inventes datos que no existen en el sistema
- Des diagnósticos médicos definitivos ni recomendaciones de tratamiento
- Ejecutes escrituras sin mostrar plan y pedir confirmación
- Compartas información de pacientes más allá de lo necesario para la tarea
- Marques una orden como RESULTADOS_LISTOS ni ENTREGADO (solo el químico en pantalla de captura)
- Trates una sugerencia tuya de resultado como «validada»: siempre es borrador hasta que el QFB valide

{TOOLS_DESCRIPCION}

Responde en texto natural. Para usar una herramienta, responde SOLO el JSON. Sin texto adicional cuando uses herramienta."""


# ─── Escudo RBAC: mapeo de herramienta → grupos permitidos ─────────────────────
# None = sin restricción (cualquier usuario autenticado puede usar).
# Lista de grupos = requiere pertenecer al menos a uno de ellos.
_TOOL_RBAC = {
    # ── Consulta (sin restricción) ──────────────────────────────────────────
    "buscar_paciente":                    None,
    "obtener_estadisticas_dia":           None,
    "buscar_ordenes":                     None,
    "obtener_resultados_orden":           None,
    "buscar_medicamento":                 None,
    "buscar_estudio":                     None,
    "listar_ordenes_pendientes":          None,
    "consultar_inventario":               None,
    # ── Consulta restringida ────────────────────────────────────────────────
    "guardar_resultado":                  ["LABORATORIO", "GERENCIA_OPERATIVA", "Administrador"],
    "obtener_saldo_caja":                 ["FARMACIA", "GERENCIA_OPERATIVA", "GERENCIA", "Administrador"],
    "auditar_errores_recientes":          ["GERENCIA_OPERATIVA", "GERENCIA", "Administrador"],
    "generar_corte_caja":                 ["FARMACIA", "GERENCIA_OPERATIVA", "GERENCIA", "Administrador"],
    "auditoria_sistema_completa":         [],   # Solo superusuario
    # ── Escritura — Recepción / Laboratorio ─────────────────────────────────
    "crear_paciente":                     ["RECEPCION", "LABORATORIO", "ADMIN", "Administrador", "GERENCIA"],
    "crear_orden_laboratorio":            ["RECEPCION", "LABORATORIO", "ADMIN", "Administrador", "GERENCIA"],
    "cobrar_orden":                       ["RECEPCION", "FARMACIA", "ADMIN", "Administrador", "GERENCIA", "LABORATORIO"],
    "buscar_o_crear_paciente":            ["RECEPCION", "LABORATORIO", "ADMIN", "Administrador", "GERENCIA"],
    "actualizar_resultado_laboratorio":   ["LABORATORIO", "ADMIN", "Administrador", "GERENCIA"],
    "cancelar_orden":                     ["RECEPCION", "ADMIN", "Administrador", "GERENCIA"],
    # ── Escritura — Farmacia ─────────────────────────────────────────────────
    "registrar_venta_farmacia":           ["FARMACIA", "ADMIN", "Administrador", "GERENCIA"],
    # ── Escritura — Cotizaciones (acceso amplio) ─────────────────────────────
    "crear_cotizacion":                   ["RECEPCION", "LABORATORIO", "FARMACIA", "ADMIN", "Administrador", "GERENCIA"],
    "consultar_expediente_paciente":      ["MEDICOS", "MEDICO", "LABORATORIO", "ADMIN", "Administrador", "GERENCIA"],
    "aplicar_descuento_orden":            ["RECEPCION", "ADMIN", "Administrador", "GERENCIA"],
    "cambiar_estado_orden":               ["RECEPCION", "LABORATORIO", "ADMIN", "Administrador", "GERENCIA"],
    "programar_cita":                     ["RECEPCION", "MEDICOS", "MEDICO", "ADMIN", "Administrador", "GERENCIA"],
    "enviar_notificacion_paciente":       ["RECEPCION", "MEDICOS", "MEDICO", "LABORATORIO", "ADMIN", "Administrador", "GERENCIA"],
    "consultar_indicadores_kpi":          ["GERENCIA_OPERATIVA", "GERENCIA", "GERENTE", "ADMIN", "Administrador"],
    "modificar_paciente":                 ["RECEPCION", "MEDICOS", "MEDICO", "ADMIN", "Administrador", "GERENCIA"],
    "gestionar_usuario":                  ["DIRECTOR", "ADMIN", "Administrador", "GERENCIA"],
}

_SUPERUSER_ONLY_TOOLS = {"auditoria_sistema_completa"}

# PRIS/Prisci: cada herramienta respeta el rol del usuario en sesion.
# La confirmacion humana es una capa adicional, no la unica defensa.
_PRISCI_EXTERNAL_ALLOWED_TOOLS = {
    "buscar_estudio",
    "crear_cotizacion",
    "consultar_manual_lab",
    "buscar_medicamento",
}


def _rol_aliases_usuario(user) -> set[str]:
    rol = (getattr(user, 'rol', '') or '').upper()
    aliases = {rol} if rol else set()
    mapa = {
        'GERENTE': {'GERENCIA', 'GERENCIA_OPERATIVA'},
        'QUIMICO': {'LABORATORIO'},
        'MEDICO': {'MEDICOS'},
        'ADMIN': {'Administrador'},
        'DIRECTOR': {'GERENCIA', 'Administrador'},
    }
    aliases.update(mapa.get(rol, set()))
    return {a for a in aliases if a}


def _verificar_rbac(tool_name: str, user, jarvis_mode: bool = False) -> tuple:
    """
    Retorna (permitido, mensaje_denegacion).
    El RBAC se aplica SIEMPRE, incluso en modo Jarvis.
    La confirmacion humana es una capa ADICIONAL, no el unico mecanismo de seguridad.
    """
    if not user or not getattr(user, 'is_authenticated', False):
        return False, "No tienes autorizacion para hacer eso. Inicia sesion primero."
    if user.is_superuser:
        return True, ""

    if tool_name in _SUPERUSER_ONLY_TOOLS:
        return False, "Disculpe, esta acción requiere nivel de Superusuario (Director)."
    grupos_req = _TOOL_RBAC.get(tool_name)
    if grupos_req is None:
        return True, ""
    if not grupos_req:
        return False, "Disculpe, esta acción está reservada para el Director del sistema."
    grupos_usuario = set(user.groups.values_list('name', flat=True))
    roles_usuario = _rol_aliases_usuario(user)
    permitidos = set(grupos_req)
    if grupos_usuario.intersection(permitidos) or roles_usuario.intersection(permitidos):
        return True, ""
    return False, (
        "Disculpe, pero su rol no tiene autorización para esta acción. "
        f"Grupos permitidos: {', '.join(grupos_req)}."
    )


# ─── Ejecutores de herramientas ────────────────────────────────────────────────

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
        # ── Herramientas de consulta (read-only) ─────────────────────────────
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
        # ── Herramientas operativas (escritura + nuevas Jarvis) ──────────────
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
        logger.error(f"PRIS tool '{nombre_tool}' error: {e}", exc_info=True)
        return {"error": str(e)}


def _tool_buscar_paciente(args, empresa):
    from core.models import Paciente
    nombre = args.get("nombre", "")
    telefono = args.get("telefono", "")
    limite = min(int(args.get("limite", 5)), 10)
    qs = Paciente.objects.filter(empresa=empresa, activo=True)
    if nombre:
        qs = qs.filter(
            Q(nombre_completo__icontains=nombre) |
            Q(apellido_paterno__icontains=nombre) |
            Q(nombres__icontains=nombre)
        )
    if telefono:
        qs = qs.filter(telefono__icontains=telefono)
    qs = qs.order_by('-fecha_registro')[:limite]
    resultados = list(qs)
    return {
        "total": len(resultados),
        "pacientes": [{"id": p.id, "nombre": p.nombre_completo or "",
                       "telefono": p.telefono or "",
                       "fecha_nacimiento": p.fecha_nacimiento.isoformat() if p.fecha_nacimiento else ""} for p in resultados]
    }


def _tool_estadisticas_dia(args, empresa):
    from core.models import OrdenDeServicio, Venta
    fecha_str = args.get("fecha", "")
    try:
        fecha = datetime.strptime(fecha_str, "%Y-%m-%d").date() if fecha_str else timezone.localdate()
    except ValueError:
        fecha = timezone.localdate()
    ordenes = OrdenDeServicio.objects.filter(empresa=empresa, fecha_creacion__date=fecha)
    ventas = 0
    try:
        # Venta usa 'fecha' (no fecha_creacion) y estado 'COMPLETADA'
        ventas = Venta.objects.filter(
            empresa=empresa, fecha__date=fecha, estado='COMPLETADA'
        ).aggregate(t=Sum('total'))['t'] or 0
    except Exception:
        pass
    return {
        "fecha": fecha.isoformat(),
        "ordenes_total": ordenes.count(),
        "ordenes_pendientes": ordenes.filter(estado__in=["PENDIENTE_PAGO", "PAGADO", "EN_PROCESO"]).count(),
        "ordenes_completadas": ordenes.filter(estado__in=["RESULTADOS_LISTOS", "ENTREGADO"]).count(),
        "ventas_farmacia_mxn": float(ventas),
    }


def _tool_buscar_ordenes(args, empresa):
    from core.models import OrdenDeServicio
    folio = args.get("folio", "")
    paciente_nombre = args.get("paciente_nombre", "")
    estado = args.get("estado", "")
    hoy = args.get("hoy", False)
    qs = OrdenDeServicio.objects.filter(empresa=empresa).select_related('paciente')
    if folio:
        qs = qs.filter(folio_orden__icontains=folio)
    if paciente_nombre:
        qs = qs.filter(Q(paciente__nombre_completo__icontains=paciente_nombre) |
                       Q(paciente_nombre_snapshot__icontains=paciente_nombre))
    if estado:
        qs = qs.filter(estado=estado.upper())
    if hoy:
        qs = qs.filter(fecha_creacion__date=timezone.localdate())
    qs = qs.order_by('-fecha_creacion')[:10]
    return {
        "total": qs.count(),
        "ordenes": [{"id": o.id, "folio": o.folio_orden,
                     "paciente": o.paciente.nombre_completo if o.paciente else (o.paciente_nombre_snapshot or ""),
                     "estado": o.estado,
                     "fecha": timezone.localtime(o.fecha_creacion).strftime("%d/%m/%Y %H:%M"),
                     "total": float(o.total or 0)} for o in qs]
    }


def _tool_resultados_orden(args, empresa):
    from core.models import OrdenDeServicio, DetalleOrden, ResultadoParametro
    folio = args.get("folio", "")
    try:
        orden = OrdenDeServicio.objects.filter(empresa=empresa).filter(
            Q(folio_orden=folio) | Q(folio_orden__icontains=folio)).first()
        if not orden:
            return {"error": f"No se encontró la orden '{folio}'"}
        detalles = DetalleOrden.objects.filter(orden=orden).select_related(
            'analito', 'perfil_lims', 'paquete_lims',
        )
        estudios = []
        for d in detalles:
            label = (
                d.descripcion_linea
                or (d.analito.nombre if d.analito_id else '')
                or (d.perfil_lims.nombre if d.perfil_lims_id else '')
                or (d.paquete_lims.nombre if d.paquete_lims_id else '')
                or ''
            )
            params = []
            if d.analito_id:
                for rp in ResultadoParametro.objects.filter(
                    orden=orden, analito=d.analito,
                ).select_related('analito'):
                    params.append({
                        "parametro": rp.analito.nombre if rp.analito else "",
                        "valor": str(rp.valor or ""),
                        "unidades": (rp.analito.unidades if rp.analito else "") or "",
                        "validado": rp.validado,
                    })
            estudios.append({
                "estudio": label,
                "estado": d.estado_procesamiento,
                "parametros": params,
            })
        return {"folio": orden.folio_orden,
                "paciente": orden.paciente.nombre_completo if orden.paciente else "",
                "estado": orden.estado, "estudios": estudios}
    except Exception as e:
        return {"error": str(e)}


def _tool_guardar_resultado(args, empresa, user):
    from core.models import OrdenDeServicio, ResultadoParametro, DetalleOrden
    from core.services.ia_clinical_governance import METODO_IA_BORRADOR, defaults_resultado_ia_borrador
    from lims.models import Analito
    folio = args.get("folio_orden", "")
    nombre_param = args.get("nombre_parametro", "")
    valor = args.get("valor", "")
    try:
        orden = OrdenDeServicio.objects.filter(empresa=empresa, folio_orden__icontains=folio).first()
        if not orden:
            return {"error": f"Orden '{folio}' no encontrada"}
        analitos_ids = list(
            DetalleOrden.objects.filter(orden=orden, analito__isnull=False).values_list(
                'analito_id', flat=True,
            )
        )
        analito = Analito.objects.filter(id__in=analitos_ids).filter(
            Q(nombre__icontains=nombre_param)
            | Q(codigo__icontains=nombre_param)
            | Q(abreviatura__icontains=nombre_param)
        ).first()
        if not analito:
            return {"error": f"Analito '{nombre_param}' no encontrado en orden '{folio}'"}
        if getattr(analito, "es_calculado", False):
            return {
                "error": (
                    f"El analito '{analito.abreviatura}' es calculado por fórmula; "
                    "debe capturarse vía laboratorio (motor clínico), no por voz."
                )
            }
        _ia_def = defaults_resultado_ia_borrador()
        rp, created = ResultadoParametro.objects.get_or_create(
            orden=orden,
            analito=analito,
            defaults={
                'valor': valor,
                'capturado_por': user,
                **_ia_def,
            },
        )
        if not created:
            rp.valor = valor
            rp.capturado_por = user
            rp.metodo_captura = METODO_IA_BORRADOR
            rp.validado = False
            rp.aprobado_por_humano = False
            rp.validado_por = None
            rp.fecha_validacion = None
            rp.save(
                update_fields=[
                    'valor', 'capturado_por', 'metodo_captura', 'validado',
                    'aprobado_por_humano', 'validado_por', 'fecha_validacion',
                ]
            )
        return {
            "exito": True,
            "accion": "creado" if created else "actualizado",
            "parametro": analito.nombre,
            "valor": valor,
            "unidades": analito.unidades or "",
            "aprobado_por_humano": False,
            "metodo_captura": METODO_IA_BORRADOR,
            "aviso_etico": (
                "Borrador IA: el QFB debe revisar y pulsar Validar en captura; "
                "la IA no libera resultados clínicos."
            ),
        }
    except Exception as e:
        return {"error": str(e)}


def _tool_buscar_medicamento(args, empresa):
    from core.models import Producto
    nombre = args.get("nombre", "")
    # Producto no tiene campo 'activo', se filtra solo por empresa y nombre/sustancia
    qs = Producto.objects.filter(empresa=empresa).filter(
        Q(nombre__icontains=nombre) | Q(sustancia_activa__icontains=nombre)
    ).order_by('nombre')[:8]
    resultados = list(qs)
    return {"total": len(resultados),
            "medicamentos": [{"id": p.id, "nombre": p.nombre,
                               "sustancia": p.sustancia_activa or "",
                               "presentacion": p.presentacion or "",
                               "concentracion": p.concentracion or "",
                               "precio": float(p.precio_publico or 0),
                               "stock": p.stock or 0} for p in resultados]}


def _tool_buscar_estudio(args, empresa):
    from laboratorio.models import Estudio
    try:
        from laboratorio.models import RangoReferenciaParametro
    except ImportError:
        RangoReferenciaParametro = None
    nombre = args.get("nombre", "")
    if not nombre:
        return {"error": "Especifica el nombre del estudio a buscar (ej: 'Glucosa', 'BH')."}

    qs = Estudio.objects.filter(activo=True).filter(
        Q(nombre__icontains=nombre) | Q(codigo__icontains=nombre) |
        Q(abreviatura__icontains=nombre)
    ).prefetch_related('parametros').order_by('nombre')[:8]

    resultados = list(qs)
    if not resultados:
        return {"total": 0, "estudios": [],
                "sugerencia": f"No encontré estudios con '{nombre}'. Verifica el nombre o usa términos como 'glucosa', 'BH', 'QS'."}

    estudios_out = []
    for e in resultados:
        # Obtener rangos de referencia de los parámetros del estudio
        rangos_resumen = []
        try:
            if RangoReferenciaParametro is not None:
                for param in e.parametros.all().order_by('orden_impresion', 'nombre')[:5]:
                    rango = RangoReferenciaParametro.objects.filter(
                        parametro=param, activo=True, sexo='A'
                    ).first()
                    if rango:
                        rangos_resumen.append({
                            "parametro": param.nombre,
                            "min": float(rango.valor_minimo) if rango.valor_minimo else None,
                            "max": float(rango.valor_maximo) if rango.valor_maximo else None,
                            "unidad": rango.unidad or param.unidades or "",
                        })
        except Exception:
            pass

        _dias = (e.dias_entrega or e.tiempo_proceso or "") or "1"
        estudios_out.append({
            "id": e.id,
            "nombre": e.nombre,
            "codigo": e.codigo or "",
            "abreviatura": e.abreviatura or "",
            "precio": float(e.precio_base or 0),
            "muestra": e.muestra_requerida or "Suero",
            "tubo": "",
            "indicaciones": e.indicaciones or "",
            "dias_entrega": _dias,
            "es_perfil": e.es_perfil,
            "rangos_referencia": rangos_resumen,
        })

    return {"total": len(estudios_out), "estudios": estudios_out}


def _tool_saldo_caja(args, empresa, user):
    from core.models import Venta
    hoy = timezone.localdate()
    # Venta usa campo 'fecha' (DateTimeField) y estado 'COMPLETADA'
    ventas = Venta.objects.filter(empresa=empresa, fecha__date=hoy, estado='COMPLETADA')
    total = ventas.aggregate(t=Sum('total'))['t'] or 0
    return {"fecha": hoy.isoformat(), "total_ventas": float(total),
            "numero_ventas": ventas.count()}


def _tool_ordenes_pendientes(args, empresa):
    from core.models import OrdenDeServicio
    area = args.get("area", "")
    limite = min(int(args.get("limite", 10)), 20)
    # Todos los estados que aún no están entregados ni cancelados
    qs = OrdenDeServicio.objects.filter(
        empresa=empresa,
        estado__in=["PENDIENTE_PAGO", "PAGADO", "EN_PROCESO", "RESULTADOS_LISTOS"]
    ).select_related('paciente').order_by('fecha_creacion')
    if area:
        qs = qs.filter(detalles__analito__departamento__icontains=area).distinct()
    resultados = list(qs[:limite])
    return {
        "total": len(resultados),
        "pendientes": [{"folio": o.folio_orden,
                        "paciente": o.paciente.nombre_completo if o.paciente else (o.paciente_nombre_snapshot or ""),
                        "estado": o.get_estado_display() if hasattr(o, 'get_estado_display') else o.estado,
                        "hora": timezone.localtime(o.fecha_creacion).strftime("%H:%M")} for o in resultados]
    }


def _tool_consultar_inventario(args, empresa):
    """Consulta stock de productos por nombre, sustancia o categoría."""
    from core.models import Producto
    from django.db.models import Sum as DjSum
    nombre = args.get("producto", args.get("nombre", ""))
    sucursal = args.get("sucursal", "")  # reservado para multi-sucursal
    limite = min(int(args.get("limite", 10)), 20)
    qs = Producto.objects.filter(empresa=empresa)
    if nombre:
        qs = qs.filter(
            Q(nombre__icontains=nombre) |
            Q(sustancia_activa__icontains=nombre) |
            Q(categoria__nombre__icontains=nombre)
        )
    qs = qs.order_by('nombre')[:limite]
    items = []
    for p in qs:
        # Stock real desde lotes
        try:
            from farmacia.models import Lote
            stock_lotes = Lote.objects.filter(producto=p, cantidad__gt=0).aggregate(
                total=DjSum('cantidad'))['total'] or 0
        except Exception:
            stock_lotes = p.stock or 0
        items.append({
            "id": p.id,
            "nombre": p.nombre,
            "sustancia": p.sustancia_activa or "",
            "presentacion": p.presentacion or "",
            "precio_publico": float(p.precio_publico or 0),
            "precio_compra": float(p.precio_compra or 0),
            "stock": int(stock_lotes),
        })
    return {"total": len(items), "productos": items}


def _tool_auditar_errores_recientes(args, empresa):
    """Escanea los últimos errores del sistema Sentinel y da un diagnóstico."""
    modulo = args.get("modulo", "")
    limite = min(int(args.get("limite", 10)), 30)
    try:
        from consultorio.models import IncidenciaSentinel
        qs = IncidenciaSentinel.objects.filter(
            estado__in=["PENDIENTE", "EN_REPARACION"]
        )
        if empresa:
            qs = qs.filter(empresa=empresa)
        if modulo:
            qs = qs.filter(
                Q(url_afectada__icontains=modulo) |
                Q(namespace__icontains=modulo)
            )
        qs = qs.order_by('-fecha_creacion')[:limite]
        errores = []
        for inc in qs:
            errores.append({
                "id": inc.id,
                "fecha": timezone.localtime(inc.fecha_creacion).strftime("%d/%m %H:%M") if inc.fecha_creacion else "",
                "tipo": inc.tipo_excepcion or "Desconocido",
                "url": (inc.url_afectada or "")[:120],
                "severidad": inc.severidad,
                "resumen": (inc.resumen_para_director or inc.tipo_excepcion or "")[:200],
            })
        criticos = sum(1 for e in errores if e["severidad"] == "CRITICA")
        return {
            "total_pendientes": len(errores),
            "criticos": criticos,
            "errores": errores,
            "diagnostico": (
                f"Hay {len(errores)} incidencias pendientes, {criticos} críticas."
                if errores else "No hay errores pendientes. Sistema limpio."
            ),
        }
    except Exception as e:
        return {"error": str(e)}


def _tool_generar_corte_caja(args, empresa, user):
    """Genera un resumen de corte de caja del día (o fecha indicada)."""
    from core.models import Venta
    fecha_str = args.get("fecha", "")
    try:
        from datetime import datetime as _dt
        fecha = _dt.strptime(fecha_str, "%Y-%m-%d").date() if fecha_str else timezone.localdate()
    except ValueError:
        fecha = timezone.localdate()

    qs = Venta.objects.filter(empresa=empresa, fecha__date=fecha, estado="COMPLETADA")
    total_ventas = qs.aggregate(t=Sum('total'))['t'] or 0

    # Desglose por método de pago
    try:
        from django.db.models import Sum as DjSum
        from core.models import Venta as V
        metodos = {}
        for venta in qs:
            for pago in getattr(venta, 'pagos', V.objects.none()).filter(pk__isnull=True):
                mp = getattr(pago, 'metodo_pago', 'OTRO')
                metodos[mp] = metodos.get(mp, 0) + float(getattr(pago, 'monto', 0))
    except Exception:
        metodos = {}

    # Devoluciones del día
    canceladas = Venta.objects.filter(empresa=empresa, fecha__date=fecha, estado="CANCELADA")
    total_dev = canceladas.aggregate(t=Sum('total'))['t'] or 0

    return {
        "fecha": fecha.isoformat(),
        "total_ventas": float(total_ventas),
        "num_ventas": qs.count(),
        "total_devoluciones": float(total_dev),
        "neto": float(total_ventas - total_dev),
        "desglose_pago": metodos,
        "generado_por": user.get_full_name() or user.username,
    }


def _tool_auditoria_sistema_completa(args, empresa, user):
    """
    Auditoría completa del sistema: BD, modelos críticos, incidencias, Drive.
    Solo disponible para superusuarios.
    """
    from django.db import connection as _conn
    reporte = {
        "timestamp": timezone.now().isoformat(),
        "usuario": user.username,
        "checks": {},
    }

    # 1. Conexión BD
    try:
        with _conn.cursor() as c:
            c.execute("SELECT 1")
        reporte["checks"]["base_datos"] = {"ok": True, "msg": "Conexión activa"}
    except Exception as e:
        reporte["checks"]["base_datos"] = {"ok": False, "msg": str(e)[:100]}

    # 2. Modelos críticos
    modelos_check = {
        "Pacientes": ("core", "Paciente"),
        "Ordenes": ("core", "OrdenDeServicio"),
        "Productos": ("core", "Producto"),
        "Estudios": ("laboratorio", "Estudio"),
    }
    from django.apps import apps as django_apps
    counts = {}
    for label, (app, model) in modelos_check.items():
        try:
            m = django_apps.get_model(app, model)
            counts[label] = m.objects.count()
        except Exception as e:
            counts[label] = f"ERROR: {e}"
    reporte["checks"]["modelos"] = counts

    # 3. Incidencias Sentinel
    try:
        from consultorio.models import IncidenciaSentinel
        qs_pend = IncidenciaSentinel.objects.filter(
            estado__in=["PENDIENTE", "EN_REPARACION"]
        )
        if empresa:
            qs_pend = qs_pend.filter(empresa=empresa)
        reporte["checks"]["sentinel"] = {
            "ok": qs_pend.count() == 0,
            "pendientes": qs_pend.count(),
            "criticos": qs_pend.filter(severidad="CRITICA").count(),
        }
    except Exception as e:
        reporte["checks"]["sentinel"] = {"ok": False, "error": str(e)[:100]}

    # 4. Google Drive
    drive_activo = getattr(settings, '_DRIVE_STORAGE_ACTIVO', False)
    reporte["checks"]["drive"] = {"activo": drive_activo}

    # Veredicto global
    errores = [k for k, v in reporte["checks"].items()
               if isinstance(v, dict) and not v.get("ok", True)]
    reporte["veredicto"] = "SISTEMA OPERATIVO" if not errores else f"ATENCION: {', '.join(errores)}"
    reporte["ok"] = len(errores) == 0
    return reporte


def _resumir_resultado_tool(tool_name, resultado):
    if not isinstance(resultado, dict):
        return "Herramienta ejecutada"
    if resultado.get("denegado_rbac"):
        return f"RBAC denegado: {resultado.get('error', '')}"
    if resultado.get("necesita_confirmacion"):
        return "Pendiente de confirmación del usuario"
    if resultado.get("necesita_aclaracion"):
        return "Necesita aclaración del usuario"
    if resultado.get("aviso"):
        return resultado.get("mensaje", "Aviso generado")
    if resultado.get("error"):
        return f"Error: {resultado['error']}"
    # Herramientas de consulta
    if tool_name == "buscar_paciente":
        return f"{resultado.get('total', 0)} paciente(s) encontrado(s)"
    elif tool_name == "obtener_estadisticas_dia":
        return (f"Hoy: {resultado.get('ordenes_total', 0)} ordenes, "
                f"{resultado.get('ordenes_pendientes', 0)} pendientes, "
                f"${resultado.get('ventas_farmacia_mxn', 0):.2f} en farmacia")
    elif tool_name == "buscar_ordenes":
        return f"{resultado.get('total', 0)} orden(es) encontrada(s)"
    elif tool_name in ("guardar_resultado", "actualizar_resultado_laboratorio"):
        return f"Guardado: {resultado.get('parametro')} = {resultado.get('valor')}" if resultado.get("exito") else "No guardado"
    elif tool_name == "obtener_saldo_caja":
        return f"Ventas hoy: ${resultado.get('total_ventas', 0):.2f} ({resultado.get('numero_ventas', 0)} tickets)"
    elif tool_name == "listar_ordenes_pendientes":
        return f"{resultado.get('total', 0)} orden(es) pendiente(s)"
    elif tool_name == "consultar_inventario":
        return f"{resultado.get('total', 0)} producto(s) encontrado(s) en inventario"
    elif tool_name == "auditar_errores_recientes":
        return resultado.get("diagnostico", "Auditoria ejecutada")
    elif tool_name == "generar_corte_caja":
        return (f"Corte {resultado.get('fecha', '')}: "
                f"${resultado.get('total_ventas', 0):.2f} ventas, "
                f"neto ${resultado.get('neto', 0):.2f}")
    elif tool_name == "auditoria_sistema_completa":
        return resultado.get("veredicto", "Auditoria ejecutada")
    # Herramientas operativas
    elif tool_name == "crear_paciente":
        return resultado.get("mensaje", "Paciente creado" if resultado.get("exito") else "Error al crear paciente")
    elif tool_name == "crear_orden_laboratorio":
        return resultado.get("mensaje", f"Orden {resultado.get('folio_orden', '')} creada" if resultado.get("exito") else "Error al crear orden")
    elif tool_name == "cobrar_orden":
        return resultado.get("mensaje", f"Orden cobrada ${resultado.get('total', 0):.2f}" if resultado.get("exito") else "Error al cobrar")
    elif tool_name == "registrar_venta_farmacia":
        return resultado.get("mensaje", f"Venta ${resultado.get('total', 0):.2f}" if resultado.get("exito") else "Error en venta")
    elif tool_name == "crear_cotizacion":
        return resultado.get("mensaje", f"Cotización #{resultado.get('cotizacion_id', '')} creada" if resultado.get("exito") else "Error al cotizar")
    elif tool_name == "buscar_o_crear_paciente":
        return resultado.get("mensaje", "Paciente procesado")
    elif tool_name == "cancelar_orden":
        return resultado.get("mensaje", "Orden cancelada" if resultado.get("exito") else "Error al cancelar")
    elif tool_name == "analizar_imagen_documento":
        tipo = resultado.get('tipo_documento', 'OTRO')
        prefill = resultado.get('prefill', {})
        sug = resultado.get('sugerencias_negocio', [])
        resumen = f"Documento: {tipo}"
        if prefill.get('nombre_paciente'):
            resumen += f" — Paciente: {prefill['nombre_paciente']}"
        if sug:
            resumen += f" — {len(sug)} sugerencia(s) de perfil"
        return resumen
    elif tool_name == "consultar_expediente_paciente":
        total = resultado.get('total_ordenes', 0)
        nombre = resultado.get('nombre', '')
        return f"Expediente de {nombre}: {total} órdenes totales"
    elif tool_name == "consultar_indicadores_kpi":
        lab = resultado.get('laboratorio', {})
        farm = resultado.get('farmacia', {})
        return (f"KPIs {resultado.get('periodo','')}: "
                f"{lab.get('ordenes_total',0)} órdenes lab, "
                f"${farm.get('ingresos_farmacia',0):.2f} farmacia")
    elif tool_name == "aplicar_descuento_orden":
        return resultado.get("mensaje", f"Descuento aplicado ${resultado.get('descuento_monto',0):.2f}" if resultado.get("exito") else "Error al aplicar descuento")
    elif tool_name == "cambiar_estado_orden":
        return resultado.get("mensaje", f"Estado cambiado a {resultado.get('nuevo_estado','')}" if resultado.get("exito") else "Error al cambiar estado")
    elif tool_name == "programar_cita":
        return resultado.get("mensaje", f"Cita programada el {resultado.get('fecha','')}" if resultado.get("exito") else "Error al programar cita")
    elif tool_name == "enviar_notificacion_paciente":
        return resultado.get("mensaje", f"Notificación {resultado.get('canal','')} enviada" if resultado.get("exito") else "Error al enviar notificación")
    elif tool_name == "modificar_paciente":
        return resultado.get("mensaje", "Paciente modificado" if resultado.get("exito") else "Error al modificar paciente")
    elif tool_name == "gestionar_usuario":
        return resultado.get("mensaje", "Usuario gestionado" if resultado.get("exito") else "Error al gestionar usuario")
    return "Herramienta ejecutada"


def _tool_analizar_imagen_documento(args, empresa, request):
    """
    Capa 4: Clasificación y extracción de documento con el Motor OCR.
    Usa la imagen que ya viene adjunta al request (imagen_b64 en el body).
    """
    try:
        from core.services.ocr_documental import analizar_documento
        imagen_b64 = args.get('imagen_b64', '')
        if not imagen_b64:
            # Intentar obtener del body del request
            try:
                body = json.loads(request.body)
                imagen_b64 = body.get('imagen_b64', '')
            except Exception:
                pass
        if not imagen_b64:
            return {'error': 'No se adjuntó imagen para analizar.'}
        resultado = analizar_documento(imagen_b64, empresa=empresa, usuario=request.user)
        return resultado
    except Exception as exc:
        return {'error': f'Error en análisis de documento: {exc}'}


# ─── Endpoint principal ────────────────────────────────────────────────────────

@login_required
def asistente_page(request):
    return render(request, 'core/pris_ia_assistant.html')


@login_required
@require_http_methods(["POST"])

def asistente_chat(request):
    import json
    from core.utils.gemini_client import _get_ai_provider
    try:
        data = json.loads(request.body)
        mensaje = (data.get('mensaje') or '').strip()
        historial = data.get('historial', [])
        contexto_pagina = (data.get('contexto_pagina') or '').strip()
        imagen_b64 = (data.get('imagen_b64') or '').strip()

        empresa_ia = getattr(request.user, 'empresa', None)
        if empresa_ia:
            request.session['pris_ia_empresa_id'] = empresa_ia.id
            request.session['pris_ia_chat_bucket'] = f"ia:e{empresa_ia.id}:u{request.user.id}"
            request.session.modified = True

        if not mensaje and not imagen_b64:
            return JsonResponse({'status': 'error', 'mensaje': 'Mensaje vacío'}, status=400)
        if not mensaje and imagen_b64:
            mensaje = "Analiza esta imagen y dime qué ves con detalle."

        start = time.time()

        # Ruta legacy opcional: DeepSeek si el entorno lo pide explícitamente.
        # Por defecto, PRIS ejecuta el flujo real con Gemini + function calling.
        if _get_ai_provider() == 'deepseek':
            from core.utils.deepseek_client import generate_content as _deepseek_generate
            respuesta = _deepseek_generate(mensaje, max_tokens=300)
            return JsonResponse({
                'status': 'success',
                'respuesta': respuesta,
                'tiempo_ms': int((time.time() - start) * 1000),
                'herramientas_ejecutadas': [],
            })

        from core.utils.gemini_client import _get_api_key
        api_key = _get_api_key()
        if imagen_b64 and not api_key:
            raise ValueError("GOOGLE_API_KEY no configurada para analizar imagenes.")

        system_prompt = _build_system_prompt(request, contexto_pagina)
        herramientas_ejecutadas = []

        # Construir prompt completo con historial
        partes_prompt = [system_prompt, "\n\n"]
        for msg in historial[-12:]:
            rol = "Usuario" if msg.get('rol') == 'user' else "PRIS"
            texto = msg.get('texto', '')
            if texto:
                partes_prompt.append(f"{rol}: {texto}\n")
        partes_prompt.append(f"\nUsuario: {mensaje}\nPRIS:")

        prompt_texto = ''.join(partes_prompt)

        # Primera llamada via REST API v1
        respuesta_raw = _gemini_rest_call(api_key, prompt_texto, imagen_b64=imagen_b64)

        # Ciclo de function calling manual (hasta 8 iteraciones para tareas multi-paso)
        for iteracion in range(8):
            tool_match = _detectar_tool_call(respuesta_raw)
            if not tool_match:
                break

            tool_name, tool_args = tool_match
            logger.info(f"PRIS tool '{tool_name}' args={tool_args} iter={iteracion}")
            resultado = _ejecutar_herramienta(tool_name, tool_args, request)

            resumen = _resumir_resultado_tool(tool_name, resultado)
            herramientas_ejecutadas.append({
                "herramienta": tool_name,
                "args": tool_args,
                "resultado_resumen": resumen,
            })

            # RBAC denegado: terminar ciclo
            if isinstance(resultado, dict) and resultado.get("denegado_rbac"):
                respuesta_raw = resultado.get("error", "No tiene permiso para esta acción.")
                break

            # Confirmación pendiente: registrar AccionPRIS PENDIENTE y detener ciclo
            if isinstance(resultado, dict) and resultado.get("necesita_confirmacion"):
                tipo_accion = _TOOL_TO_TIPO.get(tool_name, AccionPRIS.TIPO_PRELLENAR_FORMULARIO)
                try:
                    empresa_obj = getattr(request.user, 'empresa', None)
                    if empresa_obj:
                        AccionPRIS.objects.create(
                            empresa=empresa_obj,
                            usuario_solicitante=request.user,
                            tipo=tipo_accion,
                            modulo_destino=tool_name,
                            instruccion_original=mensaje,
                            payload=tool_args,
                            resultado=resultado,
                        )
                except Exception as _pris_err:
                    logger.warning(f"AccionPRIS no pudo guardarse: {_pris_err}")

                resultado_txt = json.dumps(resultado, ensure_ascii=False, default=str)
                partes_prompt.append(
                    f"\n[Sistema: la herramienta '{tool_name}' requiere confirmación. "
                    f"Resultado: {resultado_txt}]\n"
                    f"Presenta el resumen del plan al usuario en español, de forma clara y amigable, "
                    f"y pide que confirme con 'sí' para proceder:\nPRIS:"
                )
                respuesta_raw = _gemini_rest_call(api_key, ''.join(partes_prompt))
                break

            # Aclaración necesaria: usuario debe proporcionar más info
            if isinstance(resultado, dict) and resultado.get("necesita_aclaracion"):
                resultado_txt = json.dumps(resultado, ensure_ascii=False, default=str)
                partes_prompt.append(
                    f"\n[Sistema: herramienta '{tool_name}' necesita aclaración. "
                    f"Resultado: {resultado_txt}]\n"
                    f"Pide al usuario la información necesaria para continuar:\nPRIS:"
                )
                respuesta_raw = _gemini_rest_call(api_key, ''.join(partes_prompt))
                break

            # Añadir resultado y continuar ciclo (tool ejecutada correctamente)
            # Registrar AccionPRIS CONFIRMADO para herramientas de escritura
            if tool_name in _TOOL_TO_TIPO:
                try:
                    empresa_obj = getattr(request.user, 'empresa', None)
                    if empresa_obj:
                        AccionPRIS.objects.create(
                            empresa=empresa_obj,
                            usuario_solicitante=request.user,
                            usuario_confirmador=request.user,
                            tipo=_TOOL_TO_TIPO[tool_name],
                            estado=AccionPRIS.ESTADO_CONFIRMADO,
                            modulo_destino=tool_name,
                            instruccion_original=mensaje,
                            payload=tool_args,
                            resultado=resultado if isinstance(resultado, dict) else {},
                            fecha_resolucion=timezone.now(),
                        )
                except Exception as _pris_err:
                    logger.warning(f"AccionPRIS confirmada no pudo guardarse: {_pris_err}")

            resultado_txt = json.dumps(resultado, ensure_ascii=False, default=str)
            partes_prompt.append(
                f"\n[Sistema: herramienta '{tool_name}' ejecutada exitosamente. "
                f"Resultado: {resultado_txt}]\n"
                f"Continúa con el siguiente paso si lo hay, o responde al usuario de forma natural y concisa:\nPRIS:"
            )
            respuesta_raw = _gemini_rest_call(api_key, ''.join(partes_prompt))

        respuesta_texto = respuesta_raw or "No pude procesar tu solicitud. Intenta de nuevo."

        from core.utils.ia_output_sanitize import sanitizar_salida_ia

        _eid = getattr(empresa_ia, 'id', None)
        respuesta_texto, _ok = sanitizar_salida_ia(respuesta_texto, empresa_id=_eid)
        if not _ok:
            logger.warning("PRIS: respuesta filtrada por sanitizador (PII / tenant) user=%s", request.user.pk)

        elapsed_ms = int((time.time() - start) * 1000)
        logger.info(f"PRIS: {request.user.username} | {elapsed_ms}ms | tools={len(herramientas_ejecutadas)}")

        return JsonResponse({
            'status': 'success',
            'respuesta': respuesta_texto,
            'tiempo_ms': elapsed_ms,
            'herramientas_ejecutadas': herramientas_ejecutadas,
        })

    except json.JSONDecodeError:
        return JsonResponse({'status': 'error', 'mensaje': 'JSON inválido'}, status=400)
    except Exception as e:
        error_msg = str(e)
        logger.error(f"PRIS Error: {e}\n{traceback.format_exc()}")
        if '429' in error_msg or 'Resource exhausted' in error_msg or 'quota' in error_msg.lower():
            return JsonResponse({
                'status': 'error',
                'respuesta': 'Demasiadas consultas en este momento. Espera 30 segundos e intenta de nuevo.',
            }, status=200)
        if 'API key' in error_msg or 'api_key' in error_msg.lower():
            return JsonResponse({
                'status': 'error',
                'respuesta': 'La clave de Gemini no está configurada. Contacta al administrador.',
            }, status=200)
        return JsonResponse({
            'status': 'error',
            'mensaje': type(e).__name__,
            'respuesta': f'Tuve un problema técnico: {error_msg[:120]}. Intenta de nuevo.',
        }, status=200)


class _PrisciSession(dict):
    modified = False


def procesar_pregunta_con_ia(
    mensaje: str,
    user,
    historial=None,
    contexto_pagina: str = "",
    external_channel: bool = False,
) -> dict:
    """Ejecuta el mismo asistente Prisci para canales internos o externos."""
    from django.http import HttpRequest

    req = HttpRequest()
    req.method = "POST"
    req.path = "/ia/asistente/chat/"
    req.META = {"CONTENT_TYPE": "application/json", "REMOTE_ADDR": "127.0.0.1"}
    req.user = user
    req.session = _PrisciSession()
    req.prisci_external_channel = external_channel
    payload = {
        "mensaje": mensaje,
        "historial": historial or [],
        "contexto_pagina": contexto_pagina,
    }
    req._body = json.dumps(payload).encode("utf-8")
    response = asistente_chat(req)
    try:
        return json.loads(response.content.decode("utf-8"))
    except Exception:
        return {
            "status": "error",
            "respuesta": "Prisci no pudo procesar la respuesta del canal.",
        }


def _tool_buscar_reactivo_lab(args, empresa):
    """Busca reactivos y consumibles analíticos en el Silo de Laboratorio (solo lotes ACTIVOS)."""
    nombre = args.get("nombre", "")
    limite = min(int(args.get("limite", 8)), 20)
    try:
        from inventario.models import LoteReactivoLab
        from django.db.models import Q
        qs = LoteReactivoLab.objects.filter(
            empresa=empresa,
            cantidad_actual__gt=0,
            estado='ACTIVO',
        ).select_related('reactivo')
        if nombre:
            qs = qs.filter(Q(reactivo__nombre__icontains=nombre) | Q(reactivo__codigo_interno__icontains=nombre))
        qs = qs.order_by('fecha_caducidad')[:limite]
        lotes = [
            {
                'lote': l.numero_lote or '—',
                'reactivo': l.reactivo.nombre if l.reactivo else '—',
                'stock': float(l.cantidad_actual),
                'unidad': l.reactivo.unidad_medida if l.reactivo else '',
                'caducidad': l.fecha_caducidad.strftime('%d/%m/%Y') if l.fecha_caducidad else '—',
                'estado': l.estado,
            }
            for l in qs
        ]
        return {"total": len(lotes), "lotes": lotes}
    except Exception as e:
        logger.warning(f"PRIS buscar_reactivo_lab: {e}")
        return {"error": str(e), "lotes": []}


def _tool_consultar_stock_silos(args, empresa):
    """Consulta stock en cualquier silo de inventario (LAB/CONSULTORIO/GENERAL)."""
    silo = args.get("silo", "LAB").upper()
    nombre = args.get("nombre", "")
    try:
        from django.db.models import Q
        if silo == "LAB":
            from inventario.models import LoteReactivoLab
            qs = LoteReactivoLab.objects.filter(
                empresa=empresa, estado='ACTIVO', cantidad_actual__gt=0,
            ).select_related('reactivo')
            if nombre:
                qs = qs.filter(Q(reactivo__nombre__icontains=nombre))
            items = [
                {
                    "nombre": l.reactivo.nombre if l.reactivo else "—",
                    "stock": float(l.cantidad_actual),
                    "lote": l.numero_lote or "—",
                    "caducidad": l.fecha_caducidad.strftime('%d/%m/%Y') if l.fecha_caducidad else "—",
                }
                for l in qs[:10]
            ]
        elif silo == "CONSULTORIO":
            from inventario.models import LoteInsumoConsultorio
            qs = LoteInsumoConsultorio.objects.filter(empresa=empresa, cantidad_disponible__gt=0).select_related('insumo')
            if nombre:
                qs = qs.filter(Q(insumo__nombre__icontains=nombre))
            items = [{"nombre": l.insumo.nombre if l.insumo else "—", "stock": float(l.cantidad_disponible), "lote": l.numero_lote or "—"} for l in qs[:10]]
        elif silo == "GENERAL":
            from inventario.models import LoteInsumoGeneral
            qs = LoteInsumoGeneral.objects.filter(empresa=empresa, cantidad_disponible__gt=0).select_related('insumo')
            if nombre:
                qs = qs.filter(Q(insumo__nombre__icontains=nombre))
            items = [{"nombre": l.insumo.nombre if l.insumo else "—", "stock": float(l.cantidad_disponible), "lote": l.numero_lote or "—"} for l in qs[:10]]
        else:
            return {"error": f"Silo '{silo}' no reconocido. Usa LAB, CONSULTORIO o GENERAL."}
        return {"silo": silo, "total": len(items), "items": items}
    except Exception as e:
        logger.warning(f"PRIS consultar_stock_silos: {e}")
        return {"error": str(e), "items": []}


def _tool_validar_orden_laboratorio(args, empresa, user):
    """
    Crea una AccionPRIS para validar y liberar resultados de una orden.
    El QFB debe confirmar en el panel de Pendientes.
    """
    from core.models import AccionPRIS, OrdenDeServicio
    folio = args.get("folio_orden", "")
    confirmado = args.get("confirmado", False)

    orden = OrdenDeServicio.objects.filter(empresa=empresa).filter(
        Q(folio_orden=folio) | Q(id__icontains=folio)
    ).first() if folio else None

    if not orden:
        return {"error": f"No se encontró la orden con folio '{folio}'."}

    if orden.estado == "RESULTADOS_LISTOS":
        return {"info": f"La orden {folio} ya está validada (RESULTADOS_LISTOS)."}

    if not confirmado:
        return {
            "requiere_confirmacion": True,
            "resumen": f"PRIS validará la orden {orden.folio_orden or orden.id} del paciente {orden.paciente.nombre_completo if orden.paciente else '—'}. ¿Confirmar?",
        }

    # Crear AccionPRIS para auditoría y ejecución confirmada
    accion = AccionPRIS.objects.create(
        empresa=empresa,
        usuario_solicitante=user,
        tipo=AccionPRIS.TIPO_VALIDAR_RESULTADO,
        modulo_destino="laboratorio.validar_resultado",
        instruccion_original=f"Jarvis: validar orden {folio}",
        payload={"orden_id": orden.id, "folio": orden.folio_orden or str(orden.id)},
    )
    return {
        "accion_id": accion.id,
        "mensaje": f"Acción de validación creada (#{accion.id}). Confirma en el panel de Pendientes para liberar los resultados.",
    }


def _tool_notificar_resultados_whatsapp(args, empresa, user):
    """Genera el enlace WhatsApp para notificar al paciente sobre sus resultados listos."""
    from core.models import OrdenDeServicio
    from core.utils.whatsapp_sender import generar_enlace_whatsapp
    folio = args.get("folio_orden", "")
    confirmado = args.get("confirmado", False)

    orden = OrdenDeServicio.objects.filter(empresa=empresa).filter(
        Q(folio_orden=folio) | Q(id__icontains=folio)
    ).select_related("paciente", "empresa").first() if folio else None

    if not orden:
        return {"error": f"Orden '{folio}' no encontrada."}

    telefono = ""
    nombre_paciente = "Paciente"
    if orden.paciente:
        telefono = orden.paciente.telefono or ""
        nombre_paciente = orden.paciente.nombre_completo or "Paciente"

    if not telefono:
        return {"error": f"El paciente {nombre_paciente} no tiene teléfono registrado. Agrégalo en su expediente."}

    if not orden.paciente:
        return {"error": "La orden no tiene paciente asociado."}

    from core.utils.lfpdppp_resultados import paciente_autorizado_canal_digital_resultados

    if not paciente_autorizado_canal_digital_resultados(orden.paciente):
        return {
            "error": (
                "LFPDPPP: sin consentimiento informado (privacidad y tratamiento) para comunicación digital. "
                "Regularizar en recepción antes de notificar resultados por WhatsApp."
            )
        }

    if not confirmado:
        return {
            "requiere_confirmacion": True,
            "resumen": f"Enviar WhatsApp a {nombre_paciente} ({telefono}) notificando que sus resultados del folio {folio} están listos.",
        }

    empresa_nombre = getattr(empresa, 'nombre', 'PRISLAB')
    mensaje = (
        f"Hola {nombre_paciente.split()[0]}, tus resultados de laboratorio ({folio}) "
        f"de {empresa_nombre} están listos. "
        f"Puedes recogerlos en sucursal o solicitarlos por este medio. "
        f"¡Que te encuentres muy bien! 🧬"
    )
    enlace = generar_enlace_whatsapp(telefono, mensaje)
    return {
        "enlace_whatsapp": enlace,
        "mensaje_preview": mensaje,
        "instruccion": "Haz clic en el enlace para abrir WhatsApp y enviar el mensaje al paciente.",
    }


def _tool_consultar_manual_lab(args, empresa):
    """
    Micro-Learning RAG — consulta la biblioteca de manuales/protocolos de laboratorio.
    Responde preguntas clínicas basadas en documentos cargados por el Director.
    Fallback inteligente: si no hay docs en el RAG, responde con conocimiento base.
    """
    pregunta = str(args.get('pregunta', '')).strip()
    if not pregunta:
        return {'error': 'Proporciona una pregunta para consultar los manuales.'}

    categoria = args.get('categoria', 'LABORATORIO')
    empresa_id = getattr(empresa, 'id', 0)

    try:
        from core.utils.rag_engine import consultar_cerebro
        resultado = consultar_cerebro(
            pregunta=pregunta,
            empresa_id=empresa_id,
            categoria=categoria,
        )
        respuesta = resultado.get('respuesta', '')
        fuentes = resultado.get('fuentes', [])

        # Si el RAG no encontró contexto relevante, dar respuesta base
        if 'No encontré contexto' in respuesta or not respuesta:
            return {
                'respuesta': (
                    f'No tengo documentos cargados en la biblioteca RAG para responder "{pregunta}". '
                    f'El Director puede cargar manuales en /capacitacion/manuales/ para activar '
                    f'el Micro-Learning. Como referencia general: consulta el Manual de Toma de Muestra '
                    f'o los Procedimientos Normalizados de Trabajo (PNT) de tu laboratorio.'
                ),
                'fuentes': [],
                'tipo': 'sin_contexto',
            }
        return {
            'respuesta': respuesta,
            'fuentes': fuentes,
            'tipo': 'rag',
        }
    except Exception as e:
        logger.warning('_tool_consultar_manual_lab: RAG no disponible: %s', e)
        return {
            'respuesta': (
                f'El motor RAG no está disponible en este momento ({e}). '
                f'Para tu pregunta "{pregunta}", te sugiero consultar los manuales físicos '
                f'o comunicarte con el QFB responsable.'
            ),
            'fuentes': [],
            'tipo': 'fallback_error',
        }


@login_required
@require_http_methods(["POST"])
def asistente_reset(request):
    for k in ('pris_ia_empresa_id', 'pris_ia_chat_bucket'):
        request.session.pop(k, None)
    request.session.modified = True
    return JsonResponse({'status': 'success', 'mensaje': 'Historial limpiado'})


# ─── AccionPRIS: Auditoría y confirmación externa ──────────────────────────────

@login_required
@require_http_methods(["GET"])
def api_acciones_pendientes(request):
    """Retorna las AccionPRIS pendientes del usuario o empresa actual."""
    empresa = getattr(request.user, 'empresa', None)
    if not empresa:
        return JsonResponse({'acciones': []})
    # ADMIN/DIRECTOR/Superuser ven todas las pendientes de la empresa; el resto solo las suyas
    _rol = (getattr(request.user, 'rol', '') or '').upper().strip()
    _es_supervisor = (
        request.user.is_superuser or request.user.is_staff
        or _rol in ('ADMIN', 'ADMINISTRADOR', 'DIRECTOR', 'GERENTE')
        or request.user.groups.filter(name__in=['DIRECTOR', 'GERENCIA', 'GERENCIA_OPERATIVA']).exists()
    )
    base_qs = AccionPRIS.objects.filter(empresa=empresa, estado=AccionPRIS.ESTADO_PENDIENTE)
    if not _es_supervisor:
        base_qs = base_qs.filter(usuario_solicitante=request.user)
    qs = base_qs.select_related('usuario_solicitante').order_by('-fecha_propuesta')[:20]
    data = [
        {
            'id': a.id,
            'tipo': a.get_tipo_display(),
            'modulo': a.modulo_destino,
            'instruccion': a.instruccion_original[:120],
            'payload': a.payload,
            'usuario': a.usuario_solicitante.get_full_name() or a.usuario_solicitante.username if a.usuario_solicitante else '—',
            'fecha': a.fecha_propuesta.strftime('%H:%M:%S'),
        }
        for a in qs
    ]
    return JsonResponse({'acciones': data, 'total': len(data)})


@login_required
@require_http_methods(["POST"])
def api_confirmar_accion(request, accion_id):
    """Confirma y ejecuta una AccionPRIS pendiente delegando en el motor del Jarvis."""
    empresa = getattr(request.user, 'empresa', None)
    accion = get_object_or_404(AccionPRIS, id=accion_id, empresa=empresa)
    if accion.estado != AccionPRIS.ESTADO_PENDIENTE:
        return JsonResponse({'ok': False, 'error': f'La acción ya está en estado: {accion.get_estado_display()}'}, status=400)
    try:
        from core.views.pris_jarvis import _ejecutar_accion_confirmada
        resultado = _ejecutar_accion_confirmada(accion, request.user)
        # Confirmar SOLO si la ejecución no lanzó excepción
        accion.confirmar(request.user)
        logger.info(f"AccionPRIS #{accion_id} EJECUTADA+CONFIRMADA por {request.user.username}")
        return JsonResponse({'ok': True, 'estado': accion.get_estado_display(), 'resultado': resultado})
    except Exception as exc:
        logger.error(f"AccionPRIS #{accion_id} error al ejecutar: {exc}", exc_info=True)
        # No confirmar en caso de fallo — la acción queda PENDIENTE para reintento o rechazo manual
        return JsonResponse({
            'ok': False,
            'error': 'La acción no pudo ejecutarse. Permanece pendiente.',
            'detalle': str(exc),
        }, status=500)


@login_required
@require_http_methods(["POST"])
def api_rechazar_accion(request, accion_id):
    """Rechaza una AccionPRIS pendiente."""
    empresa = getattr(request.user, 'empresa', None)
    accion = get_object_or_404(AccionPRIS, id=accion_id, empresa=empresa)
    if accion.estado != AccionPRIS.ESTADO_PENDIENTE:
        return JsonResponse({'ok': False, 'error': f'La acción ya está en estado: {accion.get_estado_display()}'}, status=400)
    try:
        body = json.loads(request.body)
        motivo = body.get('motivo', '')
    except Exception:
        motivo = ''
    accion.rechazar(request.user, motivo)
    logger.info(f"AccionPRIS #{accion_id} RECHAZADA por {request.user.username}")
    return JsonResponse({'ok': True, 'estado': accion.get_estado_display()})


# ─── Helpers ───────────────────────────────────────────────────────────────────

def _detectar_tool_call(texto):
    """
    Detecta si la respuesta de PRIS es un JSON de tool call.
    Soporta objetos con args anidados como {"tool": "...", "args": {...}}.
    Retorna (tool_name, args) o None.
    """
    texto = texto.strip()
    # Extraer el primer bloque JSON balanceado que contenga "tool"
    start = texto.find('{')
    if start == -1:
        return None
    depth = 0
    end = -1
    for i in range(start, len(texto)):
        if texto[i] == '{':
            depth += 1
        elif texto[i] == '}':
            depth -= 1
            if depth == 0:
                end = i + 1
                break
    if end == -1:
        return None
    candidate = texto[start:end]
    if '"tool"' not in candidate:
        return None
    try:
        obj = json.loads(candidate)
        tool_name = obj.get("tool", "")
        tool_args = obj.get("args", {})
        if tool_name and isinstance(tool_name, str):
            return tool_name, tool_args if isinstance(tool_args, dict) else {}
    except Exception:
        pass
    return None
