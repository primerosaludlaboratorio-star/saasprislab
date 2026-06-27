"""
Seguridad V8.0 — Api
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
from user_agents import parse

from core.decorators import role_required
from core.models import ForenseAcceso, Usuario
from core.utils.empresa_request import get_empresa_usuario

from seguridad.models import (
    DispositivoTOTP, DispositivoSMS, CodigoBackup2FA,
    SesionActiva, LogAccionSensible, AlertaPanico
)


def api_verificar_codigo_2fa(request):
    """
    API para verificar un código 2FA en tiempo real.
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'Método no permitido'}, status=405)

    codigo = request.POST.get('codigo', '').strip()
    if not codigo and request.content_type == 'application/json':
        try:
            payload = json.loads(request.body.decode('utf-8') or '{}')
            codigo = str(payload.get('codigo', '')).strip()
        except (TypeError, ValueError, UnicodeDecodeError):
            return JsonResponse({'valido': False, 'mensaje': 'JSON inválido'}, status=400)
    
    if not codigo:
        return JsonResponse({'valido': False, 'mensaje': 'Código vacío'})
    
    valido, tipo = _verificar_codigo_2fa_usuario(request.user, codigo)
    if valido:
        mensaje = 'Código correcto'
        if tipo == 'backup':
            mensaje = 'Código de respaldo correcto'
        elif tipo == 'master_recovery':
            mensaje = 'Código maestro de recuperación correcto'
        return JsonResponse({'valido': True, 'mensaje': mensaje, 'tipo': tipo})
    
    return JsonResponse({'valido': False, 'mensaje': 'Código incorrecto'})


@login_required
def api_estadisticas_seguridad(request):
    """
    API que retorna estadísticas de seguridad para dashboards.
    """
    empresa, error_response = _empresa_staff_o_json(request)
    if error_response:
        return error_response
    
    hoy = timezone.now().date()
    hace_7_dias = hoy - timedelta(days=7)
    
    logs_base = LogAccionSensible.objects.filter(usuario__empresa=empresa)
    sesiones_base = SesionActiva.objects.filter(usuario__empresa=empresa)

    data = {
        'total_usuarios_2fa': DispositivoTOTP.objects.filter(usuario__empresa=empresa, activo=True).values('usuario').distinct().count(),
        'sesiones_activas': sesiones_base.filter(activa=True).count(),
        'sesiones_sospechosas': sesiones_base.filter(activa=True, es_sospechosa=True).count(),
        'logs_criticos_7dias': logs_base.filter(
            severidad=LogAccionSensible.SEVERIDAD_CRITICAL,
            fecha_hora__date__gte=hace_7_dias
        ).count(),
        'intentos_fallidos_24h': logs_base.filter(
            accion=LogAccionSensible.ACCION_LOGIN_FALLIDO,
            fecha_hora__gte=timezone.now() - timedelta(hours=24)
        ).count(),
    }
    
    return JsonResponse(data)


