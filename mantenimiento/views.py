"""
CMMS V8.2 — Vistas
==================
Sección A: Wizard Visual del Director (construcción de protocolos y árboles)
Sección B: Operativas del Químico (checklist, bypass, diagnóstico, tickets)
Sección C: Dashboard TCO y War Room
Sección D: QR Gemelo Digital
Sección E: APIs JSON
"""
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
from .models import (
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


# =============================================================================
# SECCIÓN A — WIZARD VISUAL DEL DIRECTOR
# =============================================================================

@_req_empresa
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
        except Exception as exc:
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
        except Exception as exc:
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
            except Exception as exc:
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
            except Exception as exc:
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
# SECCIÓN B — VISTAS OPERATIVAS (QUÍMICO / TÉCNICO)
# =============================================================================

@_req_empresa
def lista_equipos_operativo(request, empresa):
    """Pantalla de inicio operativo: equipos con semáforo de estado."""
    expedientes = (
        ExpedienteEquipo.objects
        .filter(empresa=empresa, en_servicio=True)
        .select_related('equipo')
        .annotate(
            tickets_abiertos=Count('tickets', filter=Q(tickets__estado__in=['ABIERTO', 'EN_PROCESO'])),
        )
        .order_by('equipo__nombre')
    )
    ctx = {
        'titulo': 'Equipos — Panel Operativo',
        'expedientes': expedientes,
    }
    return render(request, 'mantenimiento/lista_equipos_operativo.html', ctx)


@_req_empresa
def ejecutar_checklist(request, empresa, protocolo_pk, expediente_pk):
    """
    Ejecución del checklist de arranque/diario.
    Pilar 1: Si el protocolo bloquea la Worklist, el usuario debe
             completar esto primero.
    """
    protocolo  = get_object_or_404(ProtocoloEquipo, pk=protocolo_pk)
    expediente = get_object_or_404(ExpedienteEquipo, pk=expediente_pk, empresa=empresa)
    pasos      = protocolo.pasos.order_by('orden')

    # ¿Ya fue completado hoy?
    hoy = timezone.now().date()
    ya_completado = EjecucionProtocolo.objects.filter(
        protocolo=protocolo,
        expediente=expediente,
        empresa=empresa,
        ejecutado_por=request.user,
        fecha_inicio__date=hoy,
        estado__in=['COMPLETADO', 'BYPASS'],
    ).exists()

    if ya_completado:
        messages.info(request, 'Ya completaste este checklist hoy.')
        return redirect('mantenimiento:lista_equipos_operativo')

    # Obtener o crear ejecución en progreso
    ejecucion, _ = EjecucionProtocolo.objects.get_or_create(
        protocolo=protocolo,
        expediente=expediente,
        empresa=empresa,
        ejecutado_por=request.user,
        estado='EN_PROGRESO',
        defaults={'ip_address': _get_ip(request)},
    )

    if request.method == 'POST':
        d = request.POST
        errores_criticos = []
        with transaction.atomic():
            for paso in pasos:
                validado       = bool(d.get(f'paso_{paso.pk}_check'))
                respuesta_texto = d.get(f'paso_{paso.pk}_texto', '')
                respuesta_valor = d.get(f'paso_{paso.pk}_valor') or None

                RespuestaPasoProtocolo.objects.update_or_create(
                    ejecucion=ejecucion, paso=paso,
                    defaults={
                        'validado': validado,
                        'respuesta_texto': respuesta_texto,
                        'respuesta_valor': respuesta_valor or None,
                        'observacion': d.get(f'paso_{paso.pk}_obs', ''),
                    }
                )
                if paso.es_critico and not validado:
                    errores_criticos.append(paso.titulo)

            if errores_criticos:
                messages.error(
                    request,
                    f'Pasos críticos sin completar: {", ".join(errores_criticos)}. '
                    'No puedes avanzar.'
                )
            else:
                ejecucion.completar()
                messages.success(request, f'✅ Checklist "{protocolo.nombre}" completado.')
                return redirect('mantenimiento:lista_equipos_operativo')

    # Respuestas ya guardadas en esta sesión
    respuestas_map = {
        r.paso_id: r
        for r in ejecucion.respuestas.select_related('paso')
    }
    ctx = {
        'titulo': f'Checklist: {protocolo.nombre}',
        'protocolo': protocolo,
        'expediente': expediente,
        'ejecucion': ejecucion,
        'pasos': pasos,
        'respuestas_map': respuestas_map,
        'total_pasos': pasos.count(),
    }
    return render(request, 'mantenimiento/ejecutar_checklist.html', ctx)


@_req_empresa
@require_POST
def bypass_checklist(request, empresa, ejecucion_pk):
    """
    ── Ajuste 3: BOTÓN DE EMERGENCIA / SUPERVISIÓN DIRECTA ──
    El supervisor introduce su PIN para autorizar que el novato
    omita el checklist completo.
    """
    ejecucion = get_object_or_404(EjecucionProtocolo, pk=ejecucion_pk, empresa=empresa)
    d = request.POST

    supervisor_username = d.get('supervisor_username', '').strip()
    supervisor_pin      = d.get('supervisor_pin', '').strip()
    motivo              = d.get('motivo', '').strip()

    if not motivo:
        messages.error(request, 'Debes indicar el motivo de la omisión.')
        return redirect('mantenimiento:ejecutar_checklist',
                        protocolo_pk=ejecucion.protocolo_id,
                        expediente_pk=ejecucion.expediente_id)

    # Verificar que el supervisor existe y su PIN es correcto
    from core.models import Usuario
    try:
        supervisor = Usuario.objects.get(username=supervisor_username, empresa=empresa)
    except Usuario.DoesNotExist:
        messages.error(request, 'Usuario supervisor no encontrado.')
        return redirect('mantenimiento:ejecutar_checklist',
                        protocolo_pk=ejecucion.protocolo_id,
                        expediente_pk=ejecucion.expediente_id)

    # Verificar PIN: usamos el PIN de validación del sistema (LAB_VALIDATION_PIN)
    # o el password hasheado del supervisor
    from django.conf import settings
    pin_correcto = False
    lab_pin = getattr(settings, 'LAB_VALIDATION_PIN', None)
    if lab_pin and supervisor_pin == str(lab_pin):
        pin_correcto = True
    elif supervisor.check_password(supervisor_pin):
        pin_correcto = True

    if not pin_correcto:
        messages.error(request, 'PIN incorrecto. No se puede autorizar el bypass.')
        return redirect('mantenimiento:ejecutar_checklist',
                        protocolo_pk=ejecucion.protocolo_id,
                        expediente_pk=ejecucion.expediente_id)

    pasos_omitidos = ejecucion.protocolo.pasos.count() - ejecucion.respuestas.filter(validado=True).count()

    with transaction.atomic():
        ejecucion.estado    = 'BYPASS'
        ejecucion.fecha_fin = timezone.now()
        ejecucion.save(update_fields=['estado', 'fecha_fin'])

        BypassChecklistAutorizacion.objects.create(
            ejecucion=ejecucion,
            ejecutado_por=request.user,
            autorizado_por=supervisor,
            motivo=motivo,
            pin_verificado=True,
            ip_autorizacion=_get_ip(request),
            pasos_omitidos=pasos_omitidos,
        )

    messages.warning(
        request,
        f'⚠️ Bypass autorizado por {supervisor.get_full_name() or supervisor.username}. '
        f'{pasos_omitidos} pasos omitidos. Queda registro forense.'
    )
    return redirect('mantenimiento:lista_equipos_operativo')


@_req_empresa
def diagnostico_inicio(request, empresa, expediente_pk):
    """Inicia el árbol de diagnóstico: muestra las fallas disponibles para el equipo."""
    expediente = get_object_or_404(ExpedienteEquipo, pk=expediente_pk, empresa=empresa)
    arboles = ArbolDiagnostico.objects.filter(
        Q(empresa=empresa) | Q(empresa__isnull=True),
        Q(expediente=expediente) | Q(expediente__isnull=True),
        activo=True,
    ).order_by('falla_descripcion')

    ctx = {
        'titulo': f'Diagnóstico — {expediente.equipo}',
        'expediente': expediente,
        'arboles': arboles,
    }
    return render(request, 'mantenimiento/diagnostico_inicio.html', ctx)


@_req_empresa
def diagnostico_nodo(request, empresa, arbol_pk, nodo_pk=None):
    """Navega el árbol de diagnóstico nodo por nodo (wizard de preguntas)."""
    arbol = get_object_or_404(ArbolDiagnostico, pk=arbol_pk)
    if nodo_pk:
        nodo = get_object_or_404(NodoDiagnostico, pk=nodo_pk, arbol=arbol)
    else:
        nodo = arbol.get_nodo_raiz()
        if not nodo:
            messages.warning(request, 'Este árbol de diagnóstico no tiene nodos configurados.')
            return redirect('mantenimiento:lista_equipos_operativo')

    hijos = nodo.get_hijos_ordenados() if nodo else []

    # Si el nodo lleva a un procedimiento, mostramos sus pasos
    procedimiento = nodo.lleva_a_procedimiento if nodo else None
    pasos_procedimiento = procedimiento.pasos.order_by('orden') if procedimiento else []

    # Si es nodo tipo ESCALAMIENTO y nivel=PROVEEDOR, verificar autorización director
    puede_escalar_proveedor = False
    if (nodo and nodo.tipo_nodo == 'ESCALAMIENTO'
            and nodo.nivel_escalamiento == 'PROVEEDOR'):
        from core.auth_extras import is_role
        puede_escalar_proveedor = request.user.is_superuser or (
            hasattr(request.user, 'rol') and request.user.rol in ('DIRECTOR', 'ADMIN')
        )

    ctx = {
        'titulo': f'Diagnóstico: {arbol.falla_descripcion}',
        'arbol': arbol,
        'nodo': nodo,
        'hijos': hijos,
        'procedimiento': procedimiento,
        'pasos_procedimiento': pasos_procedimiento,
        'puede_escalar_proveedor': puede_escalar_proveedor,
    }
    return render(request, 'mantenimiento/diagnostico_nodo.html', ctx)


# ── Tickets CMMS ──────────────────────────────────────────────────────────────

@_req_empresa
def lista_tickets(request, empresa):
    estado_f = request.GET.get('estado', '')
    qs = (
        TicketMantenimientoCMMS.objects
        .filter(empresa=empresa)
        .select_related('expediente__equipo', 'creado_por', 'asignado_a')
        .order_by('-fecha_apertura')
    )
    if estado_f:
        qs = qs.filter(estado=estado_f)

    ctx = {
        'titulo': 'Tickets de Mantenimiento',
        'tickets': qs[:100],
        'estado_f': estado_f,
        'estado_choices': ESTADO_TICKET_CHOICES,
    }
    return render(request, 'mantenimiento/lista_tickets.html', ctx)


@_req_empresa
def crear_ticket(request, empresa, expediente_pk=None):
    expediente = None
    if expediente_pk:
        expediente = get_object_or_404(ExpedienteEquipo, pk=expediente_pk, empresa=empresa)

    if request.method == 'POST':
        d = request.POST
        try:
            exp_id = d.get('expediente') or (expediente.pk if expediente else None)
            ticket = TicketMantenimientoCMMS.objects.create(
                empresa=empresa,
                expediente_id=exp_id,
                tipo_origen=d.get('tipo_origen', 'MANUAL'),
                titulo=d['titulo'],
                descripcion=d.get('descripcion', ''),
                creado_por=request.user,
            )
            messages.success(request, f'Ticket #{ticket.pk} creado.')
            return redirect('mantenimiento:detalle_ticket', pk=ticket.pk)
        except Exception as exc:
            logger.error("Error crear ticket: %s", exc, exc_info=True)
            messages.error(request, f'Error: {exc}')

    expedientes = ExpedienteEquipo.objects.filter(empresa=empresa).select_related('equipo')
    ctx = {
        'titulo': 'Nuevo Ticket de Mantenimiento',
        'expediente': expediente,
        'expedientes': expedientes,
        'tipo_origen_choices': TicketMantenimientoCMMS.TIPO_ORIGEN_CHOICES,
    }
    return render(request, 'mantenimiento/form_ticket.html', ctx)


@_req_empresa
def detalle_ticket(request, empresa, pk):
    ticket = get_object_or_404(TicketMantenimientoCMMS, pk=pk, empresa=empresa)
    salidas = ticket.salidas_refaccion.select_related('registrado_por').order_by('-fecha')

    if request.method == 'POST':
        accion = request.POST.get('accion')
        if accion == 'cerrar':
            desc = request.POST.get('resolucion', '')
            ticket.cerrar(descripcion_resolucion=desc)
            messages.success(request, f'Ticket #{ticket.pk} cerrado.')
            return redirect('mantenimiento:lista_tickets')
        elif accion == 'escalar':
            nuevo_nivel = request.POST.get('nuevo_nivel', '')
            if nuevo_nivel == 'PROVEEDOR' and not ticket.autorizado_por_director_id:
                ticket.autorizado_por_director = request.user
            ticket.nivel_escalamiento_actual = nuevo_nivel
            ticket.estado = 'ESCALADO'
            ticket.save(update_fields=['nivel_escalamiento_actual', 'estado', 'autorizado_por_director'])
            messages.warning(request, f'Ticket escalado a: {nuevo_nivel}')
            return redirect('mantenimiento:detalle_ticket', pk=pk)
        elif accion == 'agregar_refaccion':
            try:
                silo    = request.POST.get('silo_origen', 'LAB')
                lote_id = request.POST.get('lote_object_id')
                cantidad = float(request.POST.get('cantidad_usada', 0))
                if not lote_id or cantidad <= 0:
                    raise ValueError('Lote y cantidad son requeridos.')
                registrar_consumo_refaccion(
                    ticket=ticket,
                    empresa=empresa,
                    silo_origen=silo,
                    lote_object_id=int(lote_id),
                    cantidad_usada=cantidad,
                    unidad=request.POST.get('unidad', ''),
                    registrado_por=request.user,
                    observacion=request.POST.get('observacion', ''),
                )
                messages.success(request, 'Refacción registrada y stock descontado.')
            except Exception as exc:
                logger.error("Error agregar refacción ticket %s: %s", pk, exc, exc_info=True)
                messages.error(request, f'Error al registrar refacción: {exc}')
            return redirect('mantenimiento:detalle_ticket', pk=pk)

    ctx = {
        'titulo': f'Ticket #{ticket.pk}',
        'ticket': ticket,
        'salidas': salidas,
        'nivel_choices': NIVEL_ESCALAMIENTO_CHOICES,
        'estado_choices': ESTADO_TICKET_CHOICES,
    }
    return render(request, 'mantenimiento/detalle_ticket.html', ctx)


# =============================================================================
# SECCIÓN C — DASHBOARD TCO Y WAR ROOM
# =============================================================================

@_req_empresa
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


# =============================================================================
# SECCIÓN D — QR GEMELO DIGITAL (acceso público con UUID)
# =============================================================================

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
        'usuario_logueado': request.user.is_authenticated,
    }
    return render(request, 'mantenimiento/qr_equipo.html', ctx)


# =============================================================================
# SECCIÓN E — APIs JSON
# =============================================================================

@login_required
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

    from mantenimiento.signals import _get_lote_model
    LoteModel = _get_lote_model(silo)
    if not LoteModel:
        return JsonResponse({'error': f'Silo inválido: {silo}'}, status=400)

    try:
        lote = LoteModel.objects.get(pk=lote_id)
        return JsonResponse({
            'lote_id': lote.pk,
            'cantidad_actual': float(lote.cantidad_actual),
            'estado': lote.estado,
            'content_type_id': ContentType.objects.get_for_model(LoteModel).pk,
        })
    except LoteModel.DoesNotExist:
        return JsonResponse({'error': 'Lote no encontrado'}, status=404)
