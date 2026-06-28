"""
Módulo CRM — PRISLAB v5
Gestión de prospectos, seguimientos y embudo de ventas.
"""
import json
import logging
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.db.models import Q, Count, Sum
from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.views.decorators.http import require_POST
from django.core.paginator import Paginator
from django.utils import timezone

from marketing.models import ProspectoCRM, SeguimientoCRM

logger = logging.getLogger('core')


def _empresa(request):
    """Retorna la empresa del usuario con verificación de pertenencia."""
    empresa = getattr(request.user, 'empresa', None)
    if empresa is None:
        raise PermissionDenied("Usuario no tiene empresa asignada.")
    return empresa


def _verificar_empresa(request, empresa_obj):
    """Verifica que el objeto pertenezca a la empresa del usuario."""
    empresa_usuario = getattr(request.user, 'empresa', None)
    if empresa_obj.empresa != empresa_usuario:
        raise PermissionDenied("No tiene permiso para acceder a este recurso.")
    return True


@login_required
def dashboard_crm(request):
    """Dashboard del módulo CRM con embudo y KPIs."""
    empresa = _empresa(request)
    # Lista de (estado, etiqueta, count) para el template
    estados = [
        (e, lbl, ProspectoCRM.objects.filter(empresa=empresa, estado=e).count())
        for e, lbl in ProspectoCRM.ESTADO_CHOICES
    ]

    proximos = ProspectoCRM.objects.filter(
        empresa=empresa,
        fecha_proximo_contacto__lte=timezone.now().date() + timezone.timedelta(days=3),
        estado__in=['NUEVO', 'CONTACTADO', 'INTERESADO', 'COTIZADO'],
    ).order_by('fecha_proximo_contacto')[:10]

    valor_pipeline = ProspectoCRM.objects.filter(
        empresa=empresa,
        estado__in=['INTERESADO', 'COTIZADO'],
    ).aggregate(total=Sum('valor_estimado'))['total'] or 0

    return render(request, 'core/crm/dashboard.html', {
        'estados':        estados,
        'proximos':       proximos,
        'valor_pipeline': valor_pipeline,
    })


@login_required
def lista_prospectos(request):
    """Listado de prospectos con filtros."""
    empresa = _empresa(request)
    qs = ProspectoCRM.objects.filter(empresa=empresa).select_related('asignado_a')

    estado = request.GET.get('estado', '')
    origen = request.GET.get('origen', '')
    q      = request.GET.get('q', '').strip()

    if estado:
        qs = qs.filter(estado=estado)
    if origen:
        qs = qs.filter(origen=origen)
    if q:
        qs = qs.filter(Q(nombre__icontains=q) | Q(telefono__icontains=q) | Q(email__icontains=q))

    paginator = Paginator(qs.order_by('-creado'), 20)
    return render(request, 'core/crm/lista_prospectos.html', {
        'prospectos':     paginator.get_page(request.GET.get('page')),
        'ESTADO_CHOICES': ProspectoCRM.ESTADO_CHOICES,
        'ORIGEN_CHOICES': ProspectoCRM.ORIGEN_CHOICES,
    })


@login_required
def crear_prospecto(request):
    """Formulario para crear un nuevo prospecto."""
    empresa = _empresa(request)
    if request.method == 'POST':
        try:
            prospecto = ProspectoCRM.objects.create(
                empresa=empresa,
                nombre=request.POST['nombre'],
                telefono=request.POST.get('telefono', ''),
                email=request.POST.get('email', ''),
                empresa_prospecto=request.POST.get('empresa_prospecto', ''),
                origen=request.POST.get('origen', 'OTRO'),
                estado='NUEVO',
                servicio_interes=request.POST.get('servicio_interes', ''),
                notas=request.POST.get('notas', ''),
                asignado_a=request.user,
                fecha_proximo_contacto=request.POST.get('fecha_proximo_contacto') or None,
            )
            messages.success(request, f'Prospecto "{prospecto.nombre}" creado correctamente.')
            return redirect('crm_detalle_prospecto', pk=prospecto.pk)
        except Exception as exc:
            logger.error("Error creando prospecto: %s", exc)
            messages.error(request, f'Error: {exc}')

    return render(request, 'core/crm/crear_prospecto.html', {
        'ORIGEN_CHOICES': ProspectoCRM.ORIGEN_CHOICES,
    })


@login_required
def detalle_prospecto(request, pk):
    """Detalle de un prospecto con historial de seguimientos."""
    empresa = _empresa(request)
    prospecto = get_object_or_404(ProspectoCRM, pk=pk, empresa=empresa)
    seguimientos = prospecto.seguimientos.select_related('realizado_por').order_by('-fecha')

    return render(request, 'core/crm/detalle_prospecto.html', {
        'prospecto':      prospecto,
        'seguimientos':   seguimientos,
        'ESTADO_CHOICES': ProspectoCRM.ESTADO_CHOICES,
        'TIPO_CHOICES':   SeguimientoCRM.TIPO_CHOICES,
    })


@login_required
@require_POST
def agregar_seguimiento(request, pk):
    """Agrega un registro de seguimiento al prospecto."""
    empresa = _empresa(request)
    prospecto = get_object_or_404(ProspectoCRM, pk=pk, empresa=empresa)
    try:
        seguimiento = SeguimientoCRM.objects.create(
            prospecto=prospecto,
            realizado_por=request.user,
            tipo=request.POST.get('tipo', 'NOTA'),
            descripcion=request.POST['descripcion'],
            resultado=request.POST.get('resultado', ''),
            nuevo_estado=request.POST.get('nuevo_estado', ''),
            fecha_proximo=request.POST.get('fecha_proximo') or None,
        )
        messages.success(request, 'Seguimiento registrado.')
    except Exception as exc:
        logger.error("Error agregando seguimiento: %s", exc)
        messages.error(request, f'Error: {exc}')
    return redirect('crm_detalle_prospecto', pk=pk)


# ── Clientes CRM (prospectos convertidos) ──────────────────────────────────────
@login_required
def lista_clientes_crm(request):
    """Clientes activos = prospectos convertidos."""
    empresa = _empresa(request)
    qs = ProspectoCRM.objects.filter(empresa=empresa, estado='CONVERTIDO').select_related('asignado_a')

    q = request.GET.get('q', '').strip()
    if q:
        qs = qs.filter(Q(nombre__icontains=q) | Q(telefono__icontains=q) | Q(email__icontains=q))

    paginator = Paginator(qs.order_by('-actualizado'), 20)
    return render(request, 'core/crm/lista_clientes.html', {
        'clientes': paginator.get_page(request.GET.get('page')),
        'q':        q,
    })


def crear_cliente_crm(request):
    return crear_prospecto(request)


def ver_cliente_crm(request, cliente_id):
    return detalle_prospecto(request, pk=cliente_id)


def crear_interaccion_crm(request, cliente_id):
    return agregar_seguimiento(request, pk=cliente_id)


# ── Oportunidades CRM (prospectos en el embudo activo) ────────────────────────
@login_required
def lista_oportunidades_crm(request):
    """Oportunidades = prospectos en etapas activas del embudo."""
    empresa = _empresa(request)
    estados_activos = ['NUEVO', 'CONTACTADO', 'INTERESADO', 'COTIZADO']
    qs = ProspectoCRM.objects.filter(
        empresa=empresa, estado__in=estados_activos
    ).select_related('asignado_a').order_by('fecha_proximo_contacto', '-creado')

    estado  = request.GET.get('estado', '')
    q       = request.GET.get('q', '').strip()

    if estado:
        qs = qs.filter(estado=estado)
    if q:
        qs = qs.filter(Q(nombre__icontains=q) | Q(servicio_interes__icontains=q))

    valor_total = qs.aggregate(total=Sum('valor_estimado'))['total'] or 0
    paginator   = Paginator(qs, 20)

    return render(request, 'core/crm/lista_oportunidades.html', {
        'oportunidades':  paginator.get_page(request.GET.get('page')),
        'ESTADO_CHOICES': [(e, l) for e, l in ProspectoCRM.ESTADO_CHOICES if e in estados_activos],
        'valor_total':    valor_total,
        'estado_filtro':  estado,
        'q':              q,
        'today':          timezone.now().date(),
    })


def crear_oportunidad_crm(request):
    return crear_prospecto(request)


def ver_oportunidad_crm(request, oportunidad_id):
    return detalle_prospecto(request, pk=oportunidad_id)


@login_required
@require_POST
def cerrar_oportunidad(request, oportunidad_id):
    """Cierra una oportunidad como GANADA o PERDIDA."""
    empresa = _empresa(request)
    prospecto = get_object_or_404(ProspectoCRM, pk=oportunidad_id, empresa=empresa)
    accion    = request.POST.get('accion', 'PERDIDO')

    if accion == 'GANADO':
        prospecto.estado = 'CONVERTIDO'
        msg = f'Oportunidad "{prospecto.nombre}" cerrada como GANADA.'
    else:
        prospecto.estado = 'PERDIDO'
        msg = f'Oportunidad "{prospecto.nombre}" cerrada como PERDIDA.'

    prospecto.save()

    SeguimientoCRM.objects.create(
        prospecto=prospecto,
        realizado_por=request.user,
        tipo='NOTA',
        descripcion=f'Oportunidad cerrada como {accion} por {request.user.get_full_name()}.',
        resultado=request.POST.get('motivo', ''),
    )
    messages.success(request, msg)
    return redirect('crm_dashboard')


@login_required
def api_kanban_crm(request):
    """Retorna datos para el tablero Kanban del CRM."""
    empresa = _empresa(request)
    columnas = []
    for estado, etiqueta in ProspectoCRM.ESTADO_CHOICES:
        prospectos = ProspectoCRM.objects.filter(empresa=empresa, estado=estado).order_by('-creado')[:20]
        columnas.append({
            'estado': estado,
            'etiqueta': etiqueta,
            'count': ProspectoCRM.objects.filter(empresa=empresa, estado=estado).count(),
            'items': [
                {
                    'id': p.pk,
                    'nombre': p.nombre,
                    'origen': p.get_origen_display(),
                    'telefono': p.telefono,
                    'servicio': p.servicio_interes[:50] if p.servicio_interes else '',
                    'valor': float(p.valor_estimado or 0),
                    'proximo': p.fecha_proximo_contacto.strftime('%d/%m') if p.fecha_proximo_contacto else '',
                }
                for p in prospectos
            ],
        })
    return JsonResponse({'ok': True, 'columnas': columnas})
