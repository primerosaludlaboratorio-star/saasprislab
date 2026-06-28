"""
Seguridad V8.0 — Auditoria
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


def dashboard_auditoria(request):
    """
    Dashboard de auditoría de seguridad.
    Solo accesible para administradores.
    """
    empresa, error_response = _empresa_staff_o_redirect(request)
    if error_response:
        return error_response
    
    # Estadísticas generales
    hoy = timezone.now().date()
    hace_7_dias = hoy - timedelta(days=7)
    hace_30_dias = hoy - timedelta(days=30)
    
    # Logs recientes
    logs_base = LogAccionSensible.objects.filter(usuario__empresa=empresa)
    sesiones_base = SesionActiva.objects.filter(usuario__empresa=empresa)

    logs_recientes = logs_base.select_related('usuario').order_by('-fecha_hora')[:50]
    
    # Estadísticas por acción
    stats_por_accion = logs_base.values('accion').annotate(
        total=Count('id')
    ).order_by('-total')[:10]
    
    # Logs críticos recientes
    logs_criticos = logs_base.filter(
        severidad=LogAccionSensible.SEVERIDAD_CRITICAL,
        fecha_hora__date__gte=hace_7_dias
    ).select_related('usuario').order_by('-fecha_hora')[:20]
    
    # Intentos fallidos de login (últimas 24h)
    hace_24h = timezone.now() - timedelta(hours=24)
    intentos_fallidos = logs_base.filter(
        accion=LogAccionSensible.ACCION_LOGIN_FALLIDO,
        fecha_hora__gte=hace_24h
    ).values('ip_address').annotate(
        total=Count('id')
    ).order_by('-total')[:10]
    
    # Sesiones sospechosas
    sesiones_sospechosas = sesiones_base.filter(
        es_sospechosa=True,
        activa=True
    ).select_related('usuario')
    
    context = {
        'logs_recientes': logs_recientes,
        'stats_por_accion': stats_por_accion,
        'logs_criticos': logs_criticos,
        'intentos_fallidos': intentos_fallidos,
        'sesiones_sospechosas': sesiones_sospechosas,
        'total_logs_7dias': logs_base.filter(fecha_hora__date__gte=hace_7_dias).count(),
        'total_logs_30dias': logs_base.filter(fecha_hora__date__gte=hace_30_dias).count(),
    }
    
    return render(request, 'seguridad/auditoria/dashboard.html', context)


@login_required
def logs_auditoria(request):
    """
    Lista completa de logs con filtros.
    """
    empresa, error_response = _empresa_staff_o_redirect(request)
    if error_response:
        return error_response
    
    logs = LogAccionSensible.objects.filter(usuario__empresa=empresa).select_related('usuario').order_by('-fecha_hora')
    
    # Filtros
    accion = request.GET.get('accion')
    severidad = request.GET.get('severidad')
    usuario_id = request.GET.get('usuario')
    fecha_desde = request.GET.get('fecha_desde')
    fecha_hasta = request.GET.get('fecha_hasta')
    
    if accion:
        logs = logs.filter(accion=accion)
    
    if severidad:
        logs = logs.filter(severidad=severidad)
    
    if usuario_id:
        logs = logs.filter(usuario_id=usuario_id)
    
    if fecha_desde:
        logs = logs.filter(fecha_hora__date__gte=fecha_desde)
    
    if fecha_hasta:
        logs = logs.filter(fecha_hora__date__lte=fecha_hasta)
    
    # Paginación (100 por página)
    from django.core.paginator import Paginator
    paginator = Paginator(logs, 100)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'accion_choices': LogAccionSensible.ACCION_CHOICES,
        'severidad_choices': LogAccionSensible.SEVERIDAD_CHOICES,
        'filtros_aplicados': any([accion, severidad, usuario_id, fecha_desde, fecha_hasta]),
    }
    
    return render(request, 'seguridad/auditoria/logs.html', context)


