"""
CMMS V8.0 — Director
"""
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.contenttypes.models import ContentType
from django.db import transaction
from django.db.models import Count, Q, Sum
from django.db.utils import DatabaseError
from django.core.exceptions import ValidationError
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

from .helpers import _req_empresa, _empresa



def wizard_dashboard(request, empresa):
    """Dashboard del Wizard: lista de protocolos y árboles de diagnóstico."""
    protocolos = (
        ProtocoloEquipo.objects
        .filter(Q(empresa=empresa) | Q(empresa__isnull=True))
        .select_related('equipo__equipo')
        .annotate(total_pasos=Count('pasos'))
        .order_by('tipo_protocolo', 'nombre')
    )
    arboles = (
        ArbolDiagnostico.objects
        .filter(Q(empresa=empresa) | Q(empresa__isnull=True))
        .select_related('expediente__equipo')
        .annotate(total_nodos=Count('nodos'))
        .order_by('falla_descripcion')
    )
    expedientes = ExpedienteEquipo.objects.filter(empresa=empresa).select_related('equipo')
    ctx = {
        'titulo': 'Wizard — Biblioteca Técnica',
        'protocolos': protocolos,
        'arboles': arboles,
        'expedientes': expedientes,
    }
    return render(request, 'mantenimiento/wizard_dashboard.html', ctx)


# ── CRUD Expediente Equipo ─────────────────────────────────────────────────────

@_req_empresa
def lista_expedientes(request, empresa):
    qs = (
        ExpedienteEquipo.objects
        .filter(empresa=empresa)
        .select_related('equipo')
        .annotate(total_tickets=Count('tickets'))
        .order_by('equipo__nombre')
    )
    ctx = {
        'titulo': 'Equipos Registrados',
        'expedientes': qs,
        'tipo_choices': TIPO_EQUIPO_CHOICES,
    }
    return render(request, 'mantenimiento/lista_expedientes.html', ctx)


@_req_empresa
def crear_expediente(request, empresa):
    equipos_sin_expediente = (
        Equipo.objects
        .exclude(expediente_cmms__empresa=empresa)
        .order_by('nombre')
    )
    if request.method == 'POST':
        d = request.POST
        try:
            with transaction.atomic():
                exp = ExpedienteEquipo.objects.create(
                    empresa=empresa,
                    equipo_id=d['equipo'],
                    tipo_equipo=d.get('tipo_equipo', 'ANALIZADOR'),
                    silo_refacciones=d.get('silo_refacciones', 'LAB'),
                    numero_serie=d.get('numero_serie', ''),
                    modelo=d.get('modelo', ''),
                    fabricante=d.get('fabricante', ''),
                    fecha_instalacion=d.get('fecha_instalacion') or None,
                    garantia_hasta=d.get('garantia_hasta') or None,
                    notas=d.get('notas', ''),
                )
                if 'foto_equipo' in request.FILES:
                    exp.foto_equipo = request.FILES['foto_equipo']
                if 'manual_pdf' in request.FILES:
                    exp.manual_pdf = request.FILES['manual_pdf']
                exp.save()
            messages.success(request, f'Expediente de {exp.equipo} creado. QR generado.')
            return redirect('mantenimiento:detalle_expediente', pk=exp.pk)
        except (DatabaseError, ValidationError) as exc:
            logger.error("Error crear expediente: %s", exc, exc_info=True)
            messages.error(request, f'Error: {exc}')

    ctx = {
        'titulo': 'Registrar Equipo en CMMS',
        'equipos': equipos_sin_expediente,
        'tipo_choices': TIPO_EQUIPO_CHOICES,
        'silo_choices': SILO_ORIGEN_CHOICES,
    }
    return render(request, 'mantenimiento/form_expediente.html', ctx)


@_req_empresa
def detalle_expediente(request, empresa, pk):
    exp = get_object_or_404(ExpedienteEquipo, pk=pk, empresa=empresa)
    tickets_recientes = (
        exp.tickets.select_related('creado_por', 'asignado_a')
        .order_by('-fecha_apertura')[:10]
    )
    tco_reciente = (
        RegistroTCO.objects
        .filter(empresa=empresa, expediente=exp)
        .order_by('-periodo_anio', '-periodo_mes')[:6]
    )
    protocolos = exp.protocolos.filter(activo=True).annotate(total_pasos=Count('pasos'))
    arboles    = exp.arboles_diagnostico.filter(activo=True).annotate(total_nodos=Count('nodos'))
    ctx = {
        'titulo': f'Expediente: {exp.equipo}',
        'exp': exp,
        'tickets_recientes': tickets_recientes,
        'tco_reciente': tco_reciente,
        'protocolos': protocolos,
        'arboles': arboles,
    }
    return render(request, 'mantenimiento/detalle_expediente.html', ctx)


# ── CRUD Protocolos (Wizard Pasos) ────────────────────────────────────────────

@_req_empresa
def wizard_protocolo(request, empresa, pk=None):
    """Crea o edita un ProtocoloEquipo con sus pasos en una sola página."""
    protocolo = None
    if pk:
        protocolo = get_object_or_404(
            ProtocoloEquipo,
            pk=pk,
        )
        # Verificar pertenencia
        if protocolo.empresa and protocolo.empresa != empresa:
            messages.error(request, 'Acceso denegado.')
            return redirect('mantenimiento:wizard_dashboard')

    if request.method == 'POST':
        d = request.POST
        try:
            with transaction.atomic():
                if protocolo:
                    protocolo.nombre            = d['nombre']
                    protocolo.tipo_protocolo     = d['tipo_protocolo']
                    protocolo.descripcion        = d.get('descripcion', '')
                    protocolo.nivel_requerido    = d.get('nivel_requerido', 'TODOS')
                    protocolo.aplica_a_perfil    = d.get('aplica_a_perfil', 'TODOS')
                    protocolo.bloquea_worklist   = bool(d.get('bloquea_worklist'))
                    protocolo.periodicidad_dias  = int(d.get('periodicidad_dias', 1))
                    protocolo.version            = d.get('version', '1.0')
                    expediente_id = d.get('expediente')
                    protocolo.equipo_id = expediente_id if expediente_id else None
                    protocolo.save()
                else:
                    expediente_id = d.get('expediente')
                    protocolo = ProtocoloEquipo.objects.create(
                        empresa=empresa,
                        equipo_id=expediente_id if expediente_id else None,
                        nombre=d['nombre'],
                        tipo_protocolo=d['tipo_protocolo'],
                        descripcion=d.get('descripcion', ''),
                        nivel_requerido=d.get('nivel_requerido', 'TODOS'),
                        aplica_a_perfil=d.get('aplica_a_perfil', 'TODOS'),
                        bloquea_worklist=bool(d.get('bloquea_worklist')),
                        periodicidad_dias=int(d.get('periodicidad_dias', 1)),
                        version=d.get('version', '1.0'),
                    )

                # Procesar pasos (prefijo: paso_orden_X, paso_titulo_X, …)
                ordenes = [k.replace('paso_orden_', '') for k in d if k.startswith('paso_orden_')]
                # Eliminar pasos existentes para reescribir
                protocolo.pasos.all().delete()
                for i, idx in enumerate(ordenes, start=1):
                    titulo = d.get(f'paso_titulo_{idx}', '').strip()
                    if not titulo:
                        continue
                    paso = PasoProtocolo(
                        protocolo=protocolo,
                        orden=int(d.get(f'paso_orden_{idx}', i)),
                        titulo=titulo,
                        instruccion=d.get(f'paso_instruccion_{idx}', ''),
                        tipo_validacion=d.get(f'paso_tipo_{idx}', 'CHECKBOX'),
                        valor_esperado=d.get(f'paso_valor_{idx}', ''),
                        es_critico=bool(d.get(f'paso_critico_{idx}')),
                        tiempo_estimado_seg=int(d.get(f'paso_tiempo_{idx}', 30) or 30),
                        nota_seguridad=d.get(f'paso_seguridad_{idx}', ''),
                        video_url=d.get(f'paso_video_{idx}', '') or None,
                    )
                    if f'paso_imagen_{idx}' in request.FILES:
                        paso.imagen = request.FILES[f'paso_imagen_{idx}']
                    paso.save()

            messages.success(request, f'Protocolo "{protocolo.nombre}" guardado con {len(ordenes)} pasos.')
            return redirect('mantenimiento:wizard_protocolo_editar', pk=protocolo.pk)
        except (DatabaseError, ValidationError) as exc:
            logger.error("Error wizard protocolo: %s", exc, exc_info=True)
            messages.error(request, f'Error: {exc}')

    expedientes = ExpedienteEquipo.objects.filter(empresa=empresa).select_related('equipo')
    ctx = {
        'titulo': f'Editar Protocolo: {protocolo.nombre}' if protocolo else 'Nuevo Protocolo',
        'protocolo': protocolo,
        'pasos': protocolo.pasos.order_by('orden') if protocolo else [],
        'expedientes': expedientes,
        'tipo_protocolo_choices': TIPO_PROTOCOLO_CHOICES,
        'nivel_choices': NIVEL_AUTORIZACION_CHOICES,
        'tipo_validacion_choices': [
            ('CHECKBOX','Confirmación'),('FOTO','Fotografía'),
            ('NUMERO','Valor numérico'),('TEXTO','Texto libre'),
        ],
    }
    return render(request, 'mantenimiento/wizard_protocolo.html', ctx)


# ── CRUD Árbol de Diagnóstico (Wizard) ────────────────────────────────────────

@_req_empresa
def wizard_arbol(request, empresa, pk=None):
    """Crea o edita un ArbolDiagnostico y sus nodos en wizard visual."""
    arbol = None
    if pk:
        arbol = get_object_or_404(ArbolDiagnostico, pk=pk)
        if arbol.empresa and arbol.empresa != empresa:
            messages.error(request, 'Acceso denegado.')
            return redirect('mantenimiento:wizard_dashboard')

    if request.method == 'POST':
        d = request.POST
        accion = d.get('accion', 'guardar_arbol')

        if accion == 'guardar_arbol':
            try:
                expediente_id = d.get('expediente') or None
                if arbol:
                    arbol.falla_descripcion = d['falla_descripcion']
                    arbol.falla_codigo       = d.get('falla_codigo', '')
                    arbol.expediente_id      = expediente_id
                    arbol.save()
                else:
                    arbol = ArbolDiagnostico.objects.create(
                        empresa=empresa,
                        falla_descripcion=d['falla_descripcion'],
                        falla_codigo=d.get('falla_codigo', ''),
                        expediente_id=expediente_id,
                        creado_por=request.user,
                    )
                messages.success(request, f'Árbol "{arbol.falla_descripcion}" guardado.')
                return redirect('mantenimiento:wizard_arbol_editar', pk=arbol.pk)
            except (DatabaseError, ValidationError) as exc:
                logger.error("Error wizard árbol: %s", exc, exc_info=True)
                messages.error(request, f'Error: {exc}')

        elif accion == 'agregar_nodo' and arbol:
            try:
                padre_id = d.get('padre_id') or None
                NodoDiagnostico.objects.create(
                    arbol=arbol,
                    padre_id=padre_id,
                    tipo_nodo=d.get('tipo_nodo', 'PREGUNTA'),
                    texto=d['texto'],
                    condicion_de_padre=d.get('condicion_de_padre', ''),
                    nivel_requerido=d.get('nivel_requerido', 'TODOS'),
                    nivel_escalamiento=d.get('nivel_escalamiento', ''),
                    lleva_a_procedimiento_id=d.get('procedimiento_id') or None,
                    orden=int(d.get('orden', 1)),
                )
                messages.success(request, 'Nodo agregado al árbol.')
                return redirect('mantenimiento:wizard_arbol_editar', pk=arbol.pk)
            except (DatabaseError, ValidationError) as exc:
                messages.error(request, f'Error: {exc}')

        elif accion == 'eliminar_nodo' and arbol:
            nodo_id = d.get('nodo_id')
            NodoDiagnostico.objects.filter(pk=nodo_id, arbol=arbol).delete()
            return redirect('mantenimiento:wizard_arbol_editar', pk=arbol.pk)

    expedientes   = ExpedienteEquipo.objects.filter(empresa=empresa).select_related('equipo')
    procedimientos = ProcedimientoReparacion.objects.filter(
        Q(empresa=empresa) | Q(empresa__isnull=True), activo=True
    ).order_by('titulo')
    nodos_raiz = []
    if arbol:
        nodos_raiz = arbol.nodos.filter(padre__isnull=True).order_by('orden')

    ctx = {
        'titulo': f'Árbol: {arbol.falla_descripcion}' if arbol else 'Nuevo Árbol de Diagnóstico',
        'arbol': arbol,
        'nodos_raiz': nodos_raiz,
        'expedientes': expedientes,
        'procedimientos': procedimientos,
        'tipo_nodo_choices': TIPO_NODO_CHOICES,
        'nivel_choices': NIVEL_AUTORIZACION_CHOICES,
        'escalamiento_choices': NIVEL_ESCALAMIENTO_CHOICES,
    }
    return render(request, 'mantenimiento/wizard_arbol.html', ctx)


# =============================================================================
