"""
CMMS V8.0 — Api
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
from .helpers import _empresa, _req_empresa
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


def api_checklist_bloqueado(request):
    """
    Verifica si el usuario tiene checklists de arranque pendientes hoy.
    Llamado por la Worklist antes de permitir el acceso.
    Retorna: {'bloqueado': bool, 'protocolos_pendientes': [...]}
    """
    empresa = _empresa(request)
    if not empresa:
        return JsonResponse({'bloqueado': False})

    hoy = timezone.now().date()
    pendientes = []

    protocolos_bloqueantes = ProtocoloEquipo.objects.filter(
        Q(empresa=empresa) | Q(empresa__isnull=True),
        bloquea_worklist=True,
        activo=True,
    ).select_related('equipo__equipo')

    for protocolo in protocolos_bloqueantes:
        completado_hoy = EjecucionProtocolo.objects.filter(
            protocolo=protocolo,
            empresa=empresa,
            ejecutado_por=request.user,
            fecha_inicio__date=hoy,
            estado__in=['COMPLETADO', 'BYPASS'],
        ).exists()
        if not completado_hoy:
            pendientes.append({
                'protocolo_id': protocolo.pk,
                'protocolo_nombre': protocolo.nombre,
                'expediente_id': protocolo.equipo_id,
                'equipo': str(protocolo.equipo.equipo) if protocolo.equipo else '',
                'url': f'/mantenimiento/checklist/{protocolo.pk}/{protocolo.equipo_id or 0}/',
            })

    return JsonResponse({
        'bloqueado': len(pendientes) > 0,
        'protocolos_pendientes': pendientes,
    })


@login_required
def api_stock_lote_para_refaccion(request):
    """
    Retorna el stock disponible de un lote genérico dado su silo y lote_id.
    Parámetros GET: silo, lote_id
    """
    empresa = _empresa(request)
    silo    = request.GET.get('silo', '')
    lote_id = request.GET.get('lote_id')

    if not all([empresa, silo, lote_id]):
        return JsonResponse({'error': 'Parámetros incompletos'}, status=400)

    from mantenimiento.services.consumo_refacciones_service import _get_lote_model, SiloNoSoportadoError
    try:
        LoteModel = _get_lote_model(silo)
    except SiloNoSoportadoError:
        return JsonResponse({'error': f'Silo inválido: {silo}'}, status=400)

    try:
        lote = LoteModel.objects.get(pk=lote_id, empresa=empresa)
        return JsonResponse({
            'lote_id': lote.pk,
            'cantidad_actual': float(lote.cantidad_actual),
            'estado': getattr(lote, 'estado', None),
            'content_type_id': ContentType.objects.get_for_model(LoteModel).pk,
        })
    except LoteModel.DoesNotExist:
        return JsonResponse({'error': 'Lote no encontrado'}, status=404)
