"""
Vista para Gestión de Envíos a Maquila.
"""
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from django.utils import timezone

from core.models import OrdenDeServicio, Empresa


@login_required
def maquila_envios(request):
    """Vista para gestionar envíos de muestras a maquila."""
    empresa = getattr(request.user, 'empresa', None)
    
    # Órdenes pendientes de envío a maquila
    # NOTA: Campo 'requiere_maquila' no existe en modelo actual, mostrando todas las órdenes
    ordenes_pendientes = OrdenDeServicio.objects.filter(
        empresa=empresa,
        estado__in=['PAGADO', 'EN_PROCESO']
        # requiere_maquila=True  # Campo pendiente de agregar al modelo OrdenDeServicio.
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
def enviar_a_maquila(request, orden_id):
    """Marca una orden como enviada a maquila."""
    orden = get_object_or_404(OrdenDeServicio, id=orden_id, empresa=getattr(request.user, 'empresa', None))
    
    if orden.estado not in ['PAGADO', 'EN_PROCESO']:
        messages.error(request, 'Solo se pueden enviar órdenes pagadas o en proceso.')
        return redirect('maquila_envios')
    
    # Campo 'requiere_maquila' no existe - comentado temporalmente
    # if not orden.requiere_maquila:
    #     messages.warning(request, 'Esta orden no está marcada como que requiere maquila.')
    
    orden.estado = 'EN_MAQUILA'
    # Campo 'fecha_envio_maquila' no existe - comentado temporalmente
    # orden.fecha_envio_maquila = timezone.now()
    orden.save()
    
    messages.success(request, f'Orden {orden.folio_orden} enviada a maquila.')
    return redirect('maquila_envios')
