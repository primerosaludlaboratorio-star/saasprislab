"""
CMMS V8.0 — Tco
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


def dashboard_tco(request, empresa):
    """Dashboard de TCO para el Director. Panel del War Room."""
    expedientes = (
        ExpedienteEquipo.objects
        .filter(empresa=empresa)
        .select_related('equipo')
        .annotate(
            tickets_abiertos=Count('tickets', filter=Q(tickets__estado__in=['ABIERTO', 'EN_PROCESO'])),
            tickets_mes=Count('tickets', filter=Q(
                tickets__fecha_apertura__month=date.today().month,
                tickets__fecha_apertura__year=date.today().year,
            )),
        )
        .order_by('equipo__nombre')
    )

    tco_actual = {}
    for exp in expedientes:
        tco = RegistroTCO.objects.filter(
            empresa=empresa, expediente=exp,
        ).order_by('-periodo_anio', '-periodo_mes').first()
        tco_actual[exp.pk] = tco

    ctx = {
        'titulo': 'TCO — Salud del Parque de Equipos',
        'expedientes': expedientes,
        'tco_actual': tco_actual,
        'hoy': date.today(),
    }
    return render(request, 'mantenimiento/dashboard_tco.html', ctx)


