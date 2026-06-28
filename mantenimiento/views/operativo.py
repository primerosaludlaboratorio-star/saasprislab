"""
CMMS V8.0 — Operativo
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
        exp_id = d.get('expediente') or (expediente.pk if expediente else None)
        if exp_id:
            # Validar que el expediente pertenece a la empresa
            get_object_or_404(ExpedienteEquipo, pk=exp_id, empresa=empresa)
        try:
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
        except (DatabaseError, ValidationError) as exc:
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
            ticket.full_clean()
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
            except (DatabaseError, ValidationError) as exc:
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
