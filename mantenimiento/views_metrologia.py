"""
CMMS V8.3 — Vistas de Metrología e IoT
========================================
CertificadoMetrologia: repositorio legal de calibraciones/IQ/OQ/PQ
LecturaSensorIoT: telemetría de temperatura/humedad con alertas automáticas
SensorIoT: gestión del catálogo de sensores
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q, Avg, Max, Min, Count
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.http import require_POST, require_http_methods
from datetime import date, timedelta
import logging

from .models import (
    ExpedienteEquipo, CertificadoMetrologia,
    LecturaSensorIoT, SensorIoT, TicketMantenimientoCMMS,
)
from .views import _req_empresa, _empresa

logger = logging.getLogger(__name__)


# =============================================================================
# CERTIFICADOS DE METROLOGÍA
# =============================================================================

@_req_empresa
def lista_certificados(request, empresa):
    hoy = date.today()
    qs = (
        CertificadoMetrologia.objects
        .filter(empresa=empresa)
        .select_related('expediente__equipo', 'registrado_por')
        .order_by('fecha_vencimiento')
    )

    estado_f = request.GET.get('estado', '')
    if estado_f:
        qs = qs.filter(estado=estado_f)

    # KPIs
    vencidos    = qs.filter(estado='VENCIDO').count()
    por_vencer  = qs.filter(estado='POR_VENCER').count()
    vigentes    = qs.filter(estado='VIGENTE').count()

    ctx = {
        'titulo': 'Repositorio de Metrología (ISO 15189 §6.4)',
        'certificados': qs[:100],
        'estado_f': estado_f,
        'estado_choices': CertificadoMetrologia.ESTADO_CHOICES,
        'vencidos': vencidos,
        'por_vencer': por_vencer,
        'vigentes': vigentes,
        'hoy': hoy,
    }
    return render(request, 'mantenimiento/metrologia/lista_certificados.html', ctx)


@_req_empresa
def subir_certificado(request, empresa, expediente_pk=None):
    expediente = None
    if expediente_pk:
        expediente = get_object_or_404(ExpedienteEquipo, pk=expediente_pk, empresa=empresa)

    if request.method == 'POST':
        d = request.POST
        f = request.FILES
        try:
            exp_id = d.get('expediente') or expediente_pk
            exp = get_object_or_404(ExpedienteEquipo, pk=exp_id, empresa=empresa)
            cert = CertificadoMetrologia.objects.create(
                empresa=empresa,
                expediente=exp,
                tipo=d['tipo'],
                numero_certificado=d.get('numero_certificado', '').strip() or None,
                laboratorio_emisor=d.get('laboratorio_emisor', '').strip() or None,
                fecha_emision=d['fecha_emision'],
                fecha_vencimiento=d['fecha_vencimiento'],
                archivo_pdf=f.get('archivo_pdf'),
                observaciones=d.get('observaciones', ''),
                registrado_por=request.user,
                estado='VIGENTE',
            )
            messages.success(request, f'Certificado {cert.get_tipo_display()} registrado.')
            if expediente_pk:
                return redirect('mantenimiento:detalle_expediente', pk=expediente_pk)
            return redirect('mantenimiento:lista_certificados')
        except Exception as exc:
            logger.error('Error subir certificado: %s', exc, exc_info=True)
            messages.error(request, f'Error: {exc}')

    expedientes = ExpedienteEquipo.objects.filter(empresa=empresa).select_related('equipo').order_by('equipo__nombre')
    ctx = {
        'titulo': 'Subir Certificado de Metrología',
        'expediente': expediente,
        'expedientes': expedientes,
        'tipo_choices': CertificadoMetrologia.TIPO_CHOICES,
    }
    return render(request, 'mantenimiento/metrologia/form_certificado.html', ctx)


@_req_empresa
@require_POST
def eliminar_certificado(request, empresa, pk):
    cert = get_object_or_404(CertificadoMetrologia, pk=pk, empresa=empresa)
    cert.estado = 'RENOVADO'
    cert.save(update_fields=['estado'])
    messages.warning(request, 'Certificado marcado como renovado/sustituido.')
    return redirect('mantenimiento:lista_certificados')


# =============================================================================
# SENSORES IoT — CATÁLOGO Y LECTURAS
# =============================================================================

@_req_empresa
def lista_sensores(request, empresa):
    sensores = (
        SensorIoT.objects
        .filter(empresa=empresa)
        .select_related('expediente__equipo')
        .order_by('activo', 'codigo')
    )
    ctx = {
        'titulo': 'Sensores IoT — Telemetría',
        'sensores': sensores,
    }
    return render(request, 'mantenimiento/metrologia/lista_sensores.html', ctx)


@_req_empresa
def crear_sensor(request, empresa):
    if request.method == 'POST':
        d = request.POST
        try:
            exp_id = d.get('expediente') or None
            SensorIoT.objects.create(
                empresa=empresa,
                codigo=d['codigo'].strip(),
                nombre=d.get('nombre', d['codigo']),
                tipo=d['tipo'],
                expediente_id=exp_id,
                temp_min_aceptable=d.get('temp_min_aceptable') or 2.0,
                temp_max_aceptable=d.get('temp_max_aceptable') or 8.0,
                hum_min_aceptable=d.get('hum_min_aceptable') or None,
                hum_max_aceptable=d.get('hum_max_aceptable') or None,
                notas=d.get('notas', ''),
            )
            messages.success(request, 'Sensor registrado.')
            return redirect('mantenimiento:lista_sensores')
        except Exception as exc:
            messages.error(request, f'Error: {exc}')

    expedientes = ExpedienteEquipo.objects.filter(empresa=empresa).select_related('equipo')
    ctx = {
        'titulo': 'Nuevo Sensor IoT',
        'expedientes': expedientes,
        'tipo_choices': SensorIoT.TIPO_CHOICES,
    }
    return render(request, 'mantenimiento/metrologia/form_sensor.html', ctx)


@_req_empresa
def dashboard_sensores(request, empresa):
    """Dashboard de telemetría en tiempo real."""
    sensores = (
        SensorIoT.objects
        .filter(empresa=empresa, activo=True)
        .select_related('expediente__equipo')
        .prefetch_related('lecturas')
        .order_by('codigo')
    )

    # Última lectura de cada sensor
    alertas_activas = []
    datos_sensores = []
    for s in sensores:
        ultima = s.lecturas.order_by('-timestamp').first()
        fuera = ultima.fuera_de_rango if ultima else False
        if fuera:
            alertas_activas.append({'sensor': s, 'lectura': ultima})
        datos_sensores.append({'sensor': s, 'ultima': ultima, 'fuera': fuera})

    # Lecturas de las últimas 24h con alertas
    alertas_24h = (
        LecturaSensorIoT.objects
        .filter(empresa=empresa, fuera_de_rango=True,
                timestamp__gte=timezone.now() - timedelta(hours=24))
        .select_related('sensor', 'ticket_generado')
        .order_by('-timestamp')[:20]
    )

    ctx = {
        'titulo': 'Dashboard Telemetría IoT',
        'datos_sensores': datos_sensores,
        'alertas_activas': alertas_activas,
        'alertas_24h': alertas_24h,
        'total_sensores': sensores.count(),
        'total_alertas': len(alertas_activas),
    }
    return render(request, 'mantenimiento/metrologia/dashboard_sensores.html', ctx)


@_req_empresa
def registrar_lectura_manual(request, empresa):
    """Captura manual de temperatura/humedad (simulador de telemetría)."""
    if request.method == 'POST':
        d = request.POST
        try:
            sensor = get_object_or_404(SensorIoT, pk=d['sensor'], empresa=empresa)
            temp = float(d['temperatura']) if d.get('temperatura') else None
            hum  = float(d['humedad'])     if d.get('humedad')     else None

            lectura = LecturaSensorIoT.objects.create(
                sensor=sensor,
                empresa=empresa,
                temperatura=temp,
                humedad=hum,
                origen='MANUAL',
            )
            # El signal post_save en mantenimiento/signals.py evalúa la lectura
            # y crea el ticket crítico si hay desviación — ver signals.py
            if lectura.fuera_de_rango:
                messages.error(
                    request,
                    f'⚠ ALERTA: Lectura fuera de rango en {sensor.codigo}. '
                    f'Se generó un Ticket Crítico automáticamente.'
                )
            else:
                messages.success(request, f'Lectura registrada: T={temp}°C H={hum}%')
            return redirect('mantenimiento:dashboard_sensores')
        except Exception as exc:
            messages.error(request, f'Error: {exc}')

    sensores = SensorIoT.objects.filter(empresa=empresa, activo=True).order_by('codigo')
    ctx = {'titulo': 'Registrar Lectura Manual', 'sensores': sensores}
    return render(request, 'mantenimiento/metrologia/form_lectura.html', ctx)


# =============================================================================
# API IoT — Endpoint para sensores reales (REST)
# =============================================================================

@login_required
@require_http_methods(['POST'])
def api_iot_lectura(request):
    """
    Endpoint REST para recibir lecturas de sensores físicos.
    Autenticación: Header X-SENSOR-TOKEN = sensor.token_api
    """
    token = request.headers.get('X-SENSOR-TOKEN', '')
    if not token:
        return JsonResponse({'error': 'Token requerido'}, status=401)

    try:
        sensor = SensorIoT.objects.select_related('empresa').get(codigo=token, activo=True)
    except SensorIoT.DoesNotExist:
        return JsonResponse({'error': 'Sensor no reconocido'}, status=401)

    import json
    try:
        data = json.loads(request.body)
    except Exception:
        return JsonResponse({'error': 'JSON inválido'}, status=400)

    temp = data.get('temperatura')
    hum  = data.get('humedad')

    lectura = LecturaSensorIoT.objects.create(
        sensor=sensor,
        empresa=sensor.empresa,
        temperatura=temp,
        humedad=hum,
        origen='API',
    )

    return JsonResponse({
        'status': 'ok',
        'lectura_id': lectura.pk,
        'fuera_de_rango': lectura.fuera_de_rango,
        'ticket_id': lectura.ticket_generado_id,
    })
