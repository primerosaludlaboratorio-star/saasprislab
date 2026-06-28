"""
core/views/pris_ia/views.py

Vistas públicas y helpers de Prisci (PRIS-Jarvis).
"""

import json
import logging
import time
import traceback

from django.contrib.auth.decorators import login_required
from django.db import IntegrityError, OperationalError
from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from core.models import AccionPRIS

from ._constants import _TOOL_TO_TIPO
from ._dispatcher import _ejecutar_herramienta
from ._gemini import _gemini_rest_call
from ._prompts import _build_system_prompt
from ._tools_lectura import _resumir_resultado_tool

logger = logging.getLogger('core')


@login_required
def asistente_page(request):
    return render(request, 'core/pris_ia_assistant.html')


@login_required
@require_http_methods(["POST"])
def asistente_chat(request):
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
                except (IntegrityError, OperationalError) as _pris_err:
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
                except (IntegrityError, OperationalError) as _pris_err:
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
        # Broad catch intencional: handler de último recurso del endpoint principal de chat.
        # Clasifica errores conocidos (rate limit, API key) antes de devolver respuesta genérica.
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
    except (json.JSONDecodeError, UnicodeDecodeError):
        return {
            "status": "error",
            "respuesta": "Prisci no pudo procesar la respuesta del canal.",
        }


@login_required
@require_http_methods(["POST"])
def asistente_reset(request):
    for k in ('pris_ia_empresa_id', 'pris_ia_chat_bucket'):
        request.session.pop(k, None)
    request.session.modified = True
    return JsonResponse({'status': 'success', 'mensaje': 'Historial limpiado'})


# AccionPRIS: Auditoría y confirmación externa

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
    except (ImportError, RuntimeError, OperationalError) as exc:
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
    except (json.JSONDecodeError, UnicodeDecodeError):
        motivo = ''
    accion.rechazar(request.user, motivo)
    logger.info(f"AccionPRIS #{accion_id} RECHAZADA por {request.user.username}")
    return JsonResponse({'ok': True, 'estado': accion.get_estado_display()})


# Helpers

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
    except (json.JSONDecodeError, ValueError, KeyError):
        pass
    return None
