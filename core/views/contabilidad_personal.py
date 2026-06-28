"""
Área privada de Contabilidad Personal — exclusiva del Director/Dueño.

Separada del dashboard de contabilidad general (visible al personal).
Controla compras a proveedores (OrdenDeCompra) con evidencia
fotográfica y factura OBLIGATORIAS antes de marcarse como pagadas,
y gastos de caja chica (GastoCaja).
"""
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.paginator import Paginator
from django.db.models import Q, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from core.utils.empresa_request import empresa_efectiva_request
from inventario.models import OrdenDeCompra
import logging


def _solo_director(user):
    """Acceso exclusivo: superuser o rol DIRECTOR. No visible para el resto del personal."""
    return user.is_authenticated and (
        user.is_superuser or getattr(user, 'rol', None) == 'DIRECTOR'
    )


@login_required
@user_passes_test(_solo_director, login_url='home')
def contabilidad_personal_dashboard(request):
    empresa = empresa_efectiva_request(request)
    if not empresa:
        messages.error(request, 'Usuario no tiene empresa asignada.')
        return redirect('home')

    hoy = timezone.localtime(timezone.now()).date()
    mes_inicio = hoy.replace(day=1)

    ordenes_mes = OrdenDeCompra.objects.filter(
        empresa=empresa, fecha_generacion__date__gte=mes_inicio,
    ).select_related('proveedor').order_by('-fecha_generacion')

    from core.models import GastoCaja
    gastos_caja_mes = GastoCaja.objects.filter(
        empresa=empresa, fecha__date__gte=mes_inicio,
    ).order_by('-fecha')

    total_compras = ordenes_mes.aggregate(t=Sum('total'))['t'] or Decimal('0')
    total_gastos_caja = gastos_caja_mes.aggregate(t=Sum('monto'))['t'] or Decimal('0')
    ordenes_pendientes_pago = ordenes_mes.filter(pagada=False)

    return render(request, 'core/contabilidad_personal/dashboard.html', {
        'ordenes_mes': ordenes_mes,
        'gastos_caja_mes': gastos_caja_mes,
        'total_compras': total_compras,
        'total_gastos_caja': total_gastos_caja,
        'ordenes_pendientes_pago': ordenes_pendientes_pago,
        'mes_nombre': mes_inicio.strftime('%B %Y'),
        'forma_pago_choices': OrdenDeCompra.FORMA_PAGO_CHOICES,
    })


@login_required
@user_passes_test(_solo_director, login_url='home')
@require_http_methods(['POST'])
def marcar_orden_pagada(request, orden_id):
    empresa = empresa_efectiva_request(request)
    orden = get_object_or_404(OrdenDeCompra, id=orden_id, empresa=empresa)

    factura_nueva = request.FILES.get('factura_adjunta')
    foto_nueva = request.FILES.get('foto_evidencia')
    tiene_factura = bool(factura_nueva or orden.factura_adjunta)
    tiene_foto = bool(foto_nueva or orden.foto_evidencia)

    if not tiene_factura or not tiene_foto:
        faltantes = []
        if not tiene_factura:
            faltantes.append('la factura del proveedor')
        if not tiene_foto:
            faltantes.append('la foto de evidencia de recepción del material')
        messages.error(
            request,
            f'No se puede marcar como pagada: falta subir {" y ".join(faltantes)}. '
            'Toda compra debe respaldarse con factura y evidencia fotográfica '
            'antes de registrarse como pagada — esto protege tu control financiero.'
        )
        return redirect('contabilidad_personal_dashboard')

    orden.pagada = True
    orden.fecha_pago = timezone.now()
    orden.forma_pago = request.POST.get('forma_pago', orden.forma_pago)
    orden.referencia_transferencia = request.POST.get('referencia_transferencia', '')
    if factura_nueva:
        orden.factura_adjunta = factura_nueva
    if foto_nueva:
        orden.foto_evidencia = foto_nueva
    orden.save()

    try:
        from core.utils.trazabilidad import registrar_trazabilidad
        registrar_trazabilidad(
            tipo_operacion='MARCAR_PAGADA',
            modulo='CONTABILIDAD_PERSONAL',
            referencia_id=orden.id,
            referencia_tipo='OrdenDeCompra',
            accion='MODIFICAR',
            descripcion=f'Orden de compra {orden.folio} marcada como pagada con evidencia completa.',
            usuario=request.user,
            empresa=empresa,
            request=request,
        )
    except Exception:
        logging.getLogger(__name__).exception("Error inesperado en marcar_orden_pagada (contabilidad_personal.py)")
        pass

    messages.success(request, f'Orden {orden.folio} marcada como pagada con evidencia completa.')
    return redirect('contabilidad_personal_dashboard')


@login_required
@user_passes_test(_solo_director, login_url='home')
def historial_pagos_proveedores(request):
    empresa = empresa_efectiva_request(request)
    ordenes = OrdenDeCompra.objects.filter(
        empresa=empresa, pagada=True,
    ).select_related('proveedor').order_by('-fecha_pago')

    q = request.GET.get('q', '').strip()
    if q:
        ordenes = ordenes.filter(
            Q(proveedor__razon_social__icontains=q) | Q(folio__icontains=q)
        )

    paginator = Paginator(ordenes, 30)
    page = paginator.get_page(request.GET.get('page'))
    return render(request, 'core/contabilidad_personal/historial_pagos.html', {
        'page_obj': page, 'q': q,
    })