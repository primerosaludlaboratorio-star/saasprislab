"""
Seguridad V8.0 — Panico
"""
import csv
import json
import logging
from datetime import datetime, timedelta

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_POST, require_http_methods
from django.core.cache import cache
from django.conf import settings
from django.utils import timezone
from django.contrib.auth import logout
from django.db.models import Q, Count
from django.db.utils import DatabaseError
from django.core.exceptions import ValidationError
from user_agents import parse

from core.decorators import role_required
from core.models import ForenseAcceso, Usuario
from core.utils.empresa_request import get_empresa_usuario

from seguridad.models import (
    DispositivoTOTP, DispositivoSMS, CodigoBackup2FA,
    SesionActiva, LogAccionSensible, AlertaPanico
)


def panic_button(request):
    """
    Registra AlertaPanico y notifica por Telegram/Push con rate-limit 30s por canal y usuario.
    """
    empresa = get_empresa_usuario(request.user)
    if not empresa:
        return JsonResponse({'ok': False, 'error': 'Sin empresa asignada'}, status=403)

    ubicacion = (request.POST.get('ubicacion') or request.META.get('REMOTE_ADDR') or '')[:255]
    alerta = AlertaPanico.objects.create(
        empresa=empresa,
        usuario=request.user,
        ubicacion=ubicacion or None,
        estado=AlertaPanico.ESTADO_PENDIENTE,
    )

    base_key = f"panic:emp{empresa.id}:u{request.user.id}"
    tg_key = f"{base_key}:telegram"
    push_key = f"{base_key}:push"

    telegram_ok = False
    push_ok = False

    if not cache.get(tg_key):
        from core.services.telegram_outbound import send_telegram_message

        token = getattr(settings, 'TELEGRAM_BOT_TOKEN', None)
        chat_id = getattr(settings, 'TELEGRAM_PANIC_CHAT_ID', None) or getattr(
            settings, 'TELEGRAM_CISO_CHAT_ID', None
        )
        if token and chat_id:
            msg = (
                f"🚨 PÁNICO PRISLAB\nEmpresa: {empresa.nombre}\n"
                f"Usuario: {request.user.get_username()}\nAlerta ID: {alerta.id}"
            )
            telegram_ok = send_telegram_message(token, chat_id, msg)
        cache.set(tg_key, 1, 30)

    if not cache.get(push_key):
        try:
            from core.push_service import enviar_notificacion_push
            from django.contrib.auth import get_user_model
            User = get_user_model()
            admins = (
                User.objects.filter(empresa=empresa, is_staff=True)
                .prefetch_related('push_subscriptions')
            )
            for admin in admins:
                for sub in admin.push_subscriptions.filter(activa=True):
                    if enviar_notificacion_push(
                        sub,
                        'Alerta de pánico',
                        f'{request.user.get_username()} activó el botón de pánico.',
                        '/',
                    ):
                        push_ok = True
        except (DatabaseError, ValidationError) as exc:
            logging.getLogger('seguridad').exception(
                'panic_button: fallo enviando notificaciones push para empresa=%s usuario=%s: %s',
                getattr(empresa, 'id', None),
                getattr(request.user, 'id', None),
                exc,
            )
        cache.set(push_key, 1, 30)

    if telegram_ok:
        alerta.telegram_enviado = True
        alerta.save(update_fields=['telegram_enviado'])

    return JsonResponse(
        {
            'ok': True,
            'alerta_id': alerta.id,
            'telegram_notificado': telegram_ok,
            'push_notificado': push_ok,
        }
    )


