"""
Seguridad V8.0 — Forense
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


def _parse_fecha(s: str | None):
    if not s:
        return None
    try:
        return datetime.strptime(s.strip(), '%Y-%m-%d').date()
    except ValueError:
        return None


@login_required
@role_required('DIRECTOR', 'ADMIN', 'GERENTE')
def rastro_paciente(request):
    """
    Consulta rápida: accesos forenses por paciente_id (empresa del usuario).
    Rango de fechas obligatorio acotado a máximo 90 días.
    """
    empresa = get_empresa_usuario(request.user)
    if not empresa:
        messages.error(request, 'Usuario sin empresa asignada.')
        return redirect('home')

    paciente_raw = (request.GET.get('paciente_id') or '').strip()
    fecha_desde_s = (request.GET.get('fecha_desde') or '').strip()
    fecha_hasta_s = (request.GET.get('fecha_hasta') or '').strip()

    hoy = timezone.localdate()
    fecha_hasta = _parse_fecha(fecha_hasta_s) or hoy
    fecha_desde = _parse_fecha(fecha_desde_s) or (fecha_hasta - timedelta(days=29))

    if fecha_desde > fecha_hasta:
        fecha_desde, fecha_hasta = fecha_hasta, fecha_desde

    if (fecha_hasta - fecha_desde).days > 90:
        messages.error(request, 'El rango entre fechas no puede superar 90 días.')
        fecha_desde = fecha_hasta - timedelta(days=90)

    rows = []
    total_hits = 0
    usuarios_map: dict[int, str] = {}

    if paciente_raw:
        try:
            pid = int(paciente_raw)
        except ValueError:
            messages.error(request, 'paciente_id debe ser un número entero.')
            pid = None
        if pid is not None:
            qs = (
                ForenseAcceso.objects.filter(
                    empresa=empresa,
                    paciente_id=pid,
                    created_at__date__gte=fecha_desde,
                    created_at__date__lte=fecha_hasta,
                )
                .order_by('-created_at')
            )
            total_hits = qs.count()
            rows = list(qs[:5000])
            uids = {r.usuario_id for r in rows if r.usuario_id}
            for u in Usuario.objects.filter(pk__in=uids).only('id', 'username', 'first_name', 'last_name'):
                usuarios_map[u.pk] = (u.get_full_name() or u.username or str(u.pk))

    if request.GET.get('format') == 'csv' and paciente_raw:
        try:
            pid = int(paciente_raw)
        except ValueError:
            return HttpResponse('paciente_id inválido', status=400)
        qs = (
            ForenseAcceso.objects.filter(
                empresa=empresa,
                paciente_id=pid,
                created_at__date__gte=fecha_desde,
                created_at__date__lte=fecha_hasta,
            )
            .order_by('-created_at')[:5000]
        )
        resp = HttpResponse(content_type='text/csv; charset=utf-8')
        resp['Content-Disposition'] = f'attachment; filename="rastro_paciente_{pid}.csv"'
        w = csv.writer(resp)
        w.writerow(
            ['created_at', 'accion', 'es_publico', 'usuario_id', 'orden_id', 'ip_address', 'token_prefix', 'metadata']
        )
        for r in qs:
            w.writerow(
                [
                    timezone.localtime(r.created_at).isoformat(),
                    r.accion,
                    r.es_publico,
                    r.usuario_id or '',
                    r.orden_id or '',
                    r.ip_address or '',
                    r.token_prefix or '',
                    json.dumps(r.metadata, ensure_ascii=False) if r.metadata else '',
                ]
            )
        return resp

    for display in rows:
        display.usuario_label = (
            'Público'
            if display.es_publico
            else (usuarios_map.get(display.usuario_id) if display.usuario_id else '—')
        )
        display.metadata_json = json.dumps(display.metadata, ensure_ascii=False) if display.metadata else ''

    return render(
        request,
        'seguridad/rastro_paciente.html',
        {
            'paciente_id': paciente_raw,
            'fecha_desde': fecha_desde.isoformat(),
            'fecha_hasta': fecha_hasta.isoformat(),
            'rows': rows,
            'total_hits': total_hits,
            'accion_choices': ForenseAcceso.ACCION_CHOICES,
        },
    )
