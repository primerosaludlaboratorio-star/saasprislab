"""
Vista para Gestión de Envíos a Maquila.
"""
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from django.views.decorators.http import require_http_methods

from core.models import OrdenDeServicio, Empresa, EnvioMaquila
from core.utils.sucursal_helpers import get_request_sucursal


@login_required
def maquila_envios(request):
    """Vista para gestionar envíos de muestras a maquila."""
    empresa = getattr(request.user, 'empresa', None)
    
    # Solo deben aparecer órdenes explícitamente marcadas para maquila externa.
    ordenes_pendientes = OrdenDeServicio.objects.filter(
        empresa=empresa,
        requiere_maquila=True,
        estado__in=['PAGADO', 'EN_PROCESO']
    ).exclude(
        estado='EN_MAQUILA'
    ).select_related('paciente').order_by('-fecha_creacion')
    
    # Órdenes enviadas a maquila
    ordenes_enviadas = OrdenDeServicio.objects.filter(
        empresa=empresa,
        estado='EN_MAQUILA'
    ).select_related('paciente').order_by('-fecha_creacion')  # Cambiar 'fecha_envio_maquila' por 'fecha_creacion'
    
    # Búsqueda
    busqueda = request.GET.get('busqueda', '').strip()
    if busqueda:
        ordenes_pendientes = ordenes_pendientes.filter(
            Q(folio_orden__icontains=busqueda) |
            Q(paciente__nombre__icontains=busqueda)
        )
        ordenes_enviadas = ordenes_enviadas.filter(
            Q(folio_orden__icontains=busqueda) |
            Q(paciente__nombre__icontains=busqueda)
        )
    
    return render(request, 'core/laboratorio/maquila_envios.html', {
        'ordenes_pendientes': ordenes_pendientes,
        'ordenes_enviadas': ordenes_enviadas,
        'busqueda': busqueda
    })


@login_required
@require_http_methods(["POST"])
def enviar_a_maquila(request, orden_id):
    """Marca una orden como enviada a maquila."""
    orden = get_object_or_404(OrdenDeServicio, id=orden_id, empresa=getattr(request.user, 'empresa', None))
    
    if orden.estado not in ['PAGADO', 'EN_PROCESO']:
        messages.error(request, 'Solo se pueden enviar órdenes pagadas o en proceso.')
        return redirect('maquila_envios')
    
    if not orden.requiere_maquila:
        messages.error(request, 'La orden no está marcada para maquila externa.')
        return redirect('maquila_envios')

    laboratorio_externo = (request.POST.get('laboratorio_externo') or '').strip()
    if not laboratorio_externo:
        messages.error(request, 'Indica el laboratorio externo antes de enviar la orden.')
        return redirect('maquila_envios')

    envio = EnvioMaquila.objects.create(
        empresa=orden.empresa,
        sucursal=get_request_sucursal(request),
        laboratorio_externo=laboratorio_externo,
        guia_rastreo=(request.POST.get('guia_rastreo') or '').strip() or None,
        notas=(request.POST.get('notas') or '').strip() or None,
    )
    envio.ordenes.add(orden)

    orden.estado = 'EN_MAQUILA'
    orden.save()
    
    messages.success(request, f'Orden {orden.folio_orden} enviada a maquila.')
    return redirect('maquila_envios')
