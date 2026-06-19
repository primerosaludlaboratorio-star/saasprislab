"""Webhook externo para Prisci (WhatsApp/Facebook/generic JSON)."""
from __future__ import annotations

import json
import logging
import re

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from core.views.pris_ia import procesar_pregunta_con_ia

logger = logging.getLogger("core.prisci_webhook")


def _webhook_token_ok(request) -> bool:
    expected = (getattr(settings, "PRISCI_WEBHOOK_TOKEN", "") or "").strip()
    if not expected:
        return bool(getattr(settings, "DEBUG", False))
    provided = (
        request.headers.get("X-Prisci-Webhook-Token")
        or request.GET.get("token")
        or ""
    ).strip()
    return provided == expected


def _safe_external_id(value: str) -> str:
    clean = re.sub(r"[^A-Za-z0-9_.-]+", "_", value or "").strip("_")
    return clean[:80] or "anon"


def _default_empresa():
    try:
        from core.utils.default_empresa import resolve_default_empresa_sistema

        return resolve_default_empresa_sistema()
    except Exception:
        return None


def obtener_o_crear_usuario_externo(plataforma: str, id_externo: str, nombre: str = ""):
    """Vincula un contacto externo a un usuario interno con permisos minimos."""
    Usuario = get_user_model()
    plataforma = _safe_external_id(plataforma.lower())
    ext = _safe_external_id(id_externo)
    username = f"{plataforma}_{ext}"[:150]
    grupo, _ = Group.objects.get_or_create(name="PACIENTE_EXTERNO")
    usuario, created = Usuario.objects.get_or_create(
        username=username,
        defaults={
            "first_name": (nombre or f"Usuario {plataforma}")[:150],
            "email": f"{ext}@externo.prisci.local",
            "is_active": True,
            "puede_usar_ia": True,
            "empresa": _default_empresa(),
        },
    )
    if created:
        usuario.set_unusable_password()
        usuario.save()
    if not usuario.groups.filter(name=grupo.name).exists():
        usuario.groups.add(grupo)
    return usuario


def _extraer_payload(data: dict) -> tuple[str, str, str, str]:
    """Soporta payload generico y el formato comun de webhooks Meta."""
    plataforma = data.get("plataforma") or data.get("object") or "whatsapp"
    remitente = data.get("remitente_id") or data.get("from") or data.get("sender_id")
    mensaje = data.get("mensaje") or data.get("text") or ""
    nombre = data.get("nombre") or data.get("profile_name") or ""

    if not remitente or not mensaje:
        try:
            value = data["entry"][0]["changes"][0]["value"]
            msg = (value.get("messages") or [{}])[0]
            contact = (value.get("contacts") or [{}])[0]
            remitente = remitente or msg.get("from")
            text = msg.get("text") or {}
            mensaje = mensaje or text.get("body") or ""
            profile = contact.get("profile") or {}
            nombre = nombre or profile.get("name") or ""
            plataforma = data.get("object") or plataforma
        except (KeyError, IndexError, TypeError):
            pass
    return str(plataforma), str(remitente or ""), str(mensaje or ""), str(nombre or "")


@require_http_methods(["GET"])
def verify(request):
    expected = (getattr(settings, "PRISCI_WEBHOOK_VERIFY_TOKEN", "") or "").strip()
    token = (request.GET.get("hub.verify_token") or "").strip()
    challenge = request.GET.get("hub.challenge") or ""
    if expected and token == expected:
        return HttpResponse(challenge)
    return HttpResponse("", status=403)


@csrf_exempt
@require_http_methods(["POST"])
def webhook(request):
    if not _webhook_token_ok(request):
        return JsonResponse({"ok": False, "error": "No autorizado"}, status=401)
    try:
        data = json.loads(request.body.decode("utf-8") or "{}")
    except json.JSONDecodeError:
        return JsonResponse({"ok": False, "error": "JSON invalido"}, status=400)

    plataforma, remitente, mensaje, nombre = _extraer_payload(data)
    if not remitente or not mensaje:
        return JsonResponse({"ok": False, "error": "Faltan remitente o mensaje"}, status=400)

    usuario = obtener_o_crear_usuario_externo(plataforma, remitente, nombre)
    respuesta = procesar_pregunta_con_ia(
        mensaje,
        usuario,
        contexto_pagina=f"canal_externo:{plataforma}",
        external_channel=True,
    )
    logger.info("Prisci webhook %s usuario=%s", plataforma, usuario.pk)
    return JsonResponse({"ok": True, "respuesta": respuesta})
