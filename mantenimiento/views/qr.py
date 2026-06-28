"""
CMMS V8.0 — Qr
"""
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
from datetime import date, timedelta
import hashlib
import logging

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

logger = logging.getLogger(__name__)


def qr_equipo_publico(request, uid):
    """
    Landing del Gemelo Digital accesible por QR/NFC.
    Muestra info del equipo. Si el usuario está logueado,
    muestra accesos rápidos a protocolos y tickets.
    """
    exp = get_object_or_404(ExpedienteEquipo, qr_uid=uid)
    protocolos = exp.protocolos.filter(activo=True).order_by('tipo_protocolo')
    ultimo_ticket = exp.tickets.order_by('-fecha_apertura').first()
    ctx = {
        'titulo': f'Equipo: {exp.equipo}',
        'exp': exp,
        'protocolos': protocolos,
        'ultimo_ticket': ultimo_ticket,
        'usuario_logueado': request.user.is_authenticated and getattr(request.user, 'empresa', None) == exp.empresa,
    }
    return render(request, 'mantenimiento/qr_equipo.html', ctx)


# =============================================================================
