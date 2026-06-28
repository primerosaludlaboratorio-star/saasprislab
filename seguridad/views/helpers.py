"""
Seguridad V8.0 — Helpers compartidos
"""
from django.contrib import messages
from django.http import JsonResponse
from django.shortcuts import redirect
from core.utils.empresa_request import get_empresa_usuario


def _empresa_staff_o_redirect(request):
    if not request.user.is_staff:
        messages.error(request, "No tienes permisos para acceder a esta sección.")
        return None, redirect('dashboard')
    empresa = get_empresa_usuario(request.user)
    if not empresa:
        messages.error(request, "Usuario sin empresa asignada.")
        return None, redirect('dashboard')
    return empresa, None


def _empresa_staff_o_json(request):
    if not request.user.is_staff:
        return None, JsonResponse({'error': 'No autorizado'}, status=403)
    empresa = get_empresa_usuario(request.user)
    if not empresa:
        return None, JsonResponse({'error': 'Usuario sin empresa asignada'}, status=403)
    return empresa, None


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


def _empresa_staff_o_redirect(request):
    if not request.user.is_staff:
        messages.error(request, "No tienes permisos para acceder a esta sección.")
        return None, redirect('dashboard')
    empresa = get_empresa_usuario(request.user)
    if not empresa:
        messages.error(request, "Usuario sin empresa asignada.")
        return None, redirect('dashboard')
    return empresa, None


def _empresa_staff_o_json(request):
    if not request.user.is_staff:
        return None, JsonResponse({'error': 'No autorizado'}, status=403)
    empresa = get_empresa_usuario(request.user)
    if not empresa:
        return None, JsonResponse({'error': 'Usuario sin empresa asignada'}, status=403)
    return empresa, None


