"""
CMMS V8.0 — Helpers compartidos de vistas
"""
from functools import wraps
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.shortcuts import redirect
from core.utils.tenant_strict import empresa_desde_request
import logging

logger = logging.getLogger(__name__)


def _empresa(request):
    return empresa_desde_request(request)


def _req_empresa(fn):
    @login_required
    @wraps(fn)
    def inner(request, *args, **kwargs):
        emp = _empresa(request)
        if not emp:
            messages.error(request, "Sin empresa asignada.")
            return redirect('home')
        return fn(request, emp, *args, **kwargs)
    return inner


def _get_ip(request):
    return request.META.get('REMOTE_ADDR')


import hashlib
from datetime import date, timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.contenttypes.models import ContentType
from django.db import transaction
from django.db.models import Count, Q, Sum
from django.db.models.functions import Coalesce
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from laboratorio.models import Equipo
from mantenimiento.services.consumo_refacciones_service import registrar_consumo_refaccion
from mantenimiento.models import (
    ArbolDiagnostico, BypassChecklistAutorizacion, EjecucionProtocolo,
    ExpedienteEquipo, NodoDiagnostico, PasoProtocolo, ProcedimientoReparacion,
    PasoReparacion, ProtocoloEquipo, RespuestaPasoProtocolo,
    RegistroTCO, SalidaRefaccionMantenimiento, TicketMantenimientoCMMS,
    NIVEL_AUTORIZACION_CHOICES, SILO_ORIGEN_CHOICES, TIPO_EQUIPO_CHOICES,
    TIPO_PROTOCOLO_CHOICES, TIPO_COMPONENTE_CHOICES, TIPO_NODO_CHOICES,
    NIVEL_ESCALAMIENTO_CHOICES, ESTADO_TICKET_CHOICES,
)

import logging
logger = logging.getLogger(__name__)


# ── Helpers ────────────────────────────────────────────────────────────────────

def _empresa(request):
    from core.utils.tenant_strict import empresa_desde_request

    return empresa_desde_request(request)


def _req_empresa(fn):
    from functools import wraps
    @login_required
    @wraps(fn)
    def inner(request, *args, **kwargs):
        emp = _empresa(request)
        if not emp:
            messages.error(request, "Sin empresa asignada.")
            return redirect('home')
        return fn(request, emp, *args, **kwargs)
    return inner


def _get_ip(request):
    return request.META.get('REMOTE_ADDR')


