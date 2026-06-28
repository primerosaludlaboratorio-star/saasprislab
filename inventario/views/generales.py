"""
INVENTARIO V8.2 — Vistas del Silo de Insumos Generales
CatalogoInsumoGeneral · LoteInsumoGeneral · ValeRequisicion · LineaValeRequisicion
Flujo: BORRADOR → PENDIENTE → APROBADO → ENTREGADO (con descuento automático FEFO)
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db import transaction
from django.db.models import Q, Sum, Value, Count, DecimalField
from django.db.utils import DatabaseError
from django.core.exceptions import ValidationError
from decimal import Decimal
from django.db.models.functions import Coalesce
from django.views.decorators.http import require_POST
from django.utils import timezone
from datetime import date
import logging

from inventario.models import (
    CatalogoInsumoGeneral, LoteInsumoGeneral,
    ValeRequisicion, LineaValeRequisicion, UNIDAD_CHOICES, AREA_CHOICES,
)
from .helpers import _get_empresa, _empresa_required

logger = logging.getLogger(__name__)

AREA_CHOICES_DISPLAY = AREA_CHOICES


# =============================================================================
# DASHBOARD GENERALES
# =============================================================================

@_empresa_required
def dashboard_generales(request, empresa):
    insumos = (
        CatalogoInsumoGeneral.objects
        .filter(empresa=empresa, activo=True)
        .annotate(
            stock_total=Coalesce(
                Sum('lotes__cantidad_actual', filter=Q(lotes__cantidad_actual__gt=0)),
                Value(Decimal('0'), output_field=DecimalField())
            )
        )
    )
    criticos = [i for i in insumos if float(i.stock_total) <= float(i.stock_minimo)]

    vales_pendientes = (
        ValeRequisicion.objects
        .filter(empresa=empresa, estado='PENDIENTE')
        .select_related('solicitado_por')
        .annotate(total_lineas=Count('lineas'))
        .order_by('fecha_solicitud')[:10]
    )
    vales_recientes = (
        ValeRequisicion.objects
        .filter(empresa=empresa)
        .select_related('solicitado_por', 'aprobado_por')
        .order_by('-fecha_solicitud')[:10]
    )

    ctx = {
        'titulo': 'Inventario — Silo Insumos Generales',
        'total_insumos': insumos.count(),
        'criticos': criticos,
        'vales_pendientes': vales_pendientes,
        'vales_recientes': vales_recientes,
    }
    return render(request, 'inventario/generales/dashboard.html', ctx)


# =============================================================================
# CRUD CATÁLOGO GENERALES
# =============================================================================

@_empresa_required
def lista_insumos_generales(request, empresa):
    q    = request.GET.get('q', '')
    cat  = request.GET.get('categoria', '')
    qs = (
        CatalogoInsumoGeneral.objects
        .filter(empresa=empresa)
        .annotate(
            stock_total=Coalesce(
                Sum('lotes__cantidad_actual', filter=Q(lotes__cantidad_actual__gt=0)),
                Value(Decimal('0'), output_field=DecimalField())
            )
        )
        .order_by('categoria', 'nombre')
    )
    if q:
        qs = qs.filter(Q(nombre__icontains=q) | Q(codigo_interno__icontains=q))
    if cat:
        qs = qs.filter(categoria=cat)
    ctx = {
        'titulo': 'Insumos Generales',
        'insumos': qs,
        'q': q, 'cat': cat,
        'categoria_choices': CatalogoInsumoGeneral.CATEGORIA_CHOICES,
    }
    return render(request, 'inventario/generales/lista_insumos.html', ctx)


@_empresa_required
def crear_insumo_general(request, empresa):
    if request.method == 'POST':
        d = request.POST
        try:
            CatalogoInsumoGeneral.objects.create(
                empresa=empresa,
                codigo_interno=d['codigo_interno'].strip(),
                nombre=d['nombre'].strip(),
                descripcion=d.get('descripcion', ''),
                categoria=d['categoria'],
                area_principal=d.get('area_principal', 'GENERAL'),
                unidad_medida=d.get('unidad_medida', 'UNIDAD'),
                stock_minimo=d.get('stock_minimo') or 0,
                stock_maximo=d.get('stock_maximo') or None,
            )
            messages.success(request, 'Insumo general creado.')
            return redirect('inventario:lista_insumos_generales')
        except (DatabaseError, ValidationError) as exc:
            messages.error(request, f'Error: {exc}')
    ctx = {
        'titulo': 'Nuevo Insumo General',
        'categoria_choices': CatalogoInsumoGeneral.CATEGORIA_CHOICES,
        'area_choices': AREA_CHOICES_DISPLAY,
    }
    return render(request, 'inventario/generales/form_insumo.html', ctx)


@_empresa_required
def editar_insumo_general(request, empresa, pk):
    insumo = get_object_or_404(CatalogoInsumoGeneral, pk=pk, empresa=empresa)
    if request.method == 'POST':
        d = request.POST
        try:
            insumo.codigo_interno = d['codigo_interno'].strip()
            insumo.nombre         = d['nombre'].strip()
            insumo.descripcion    = d.get('descripcion', '')
            insumo.categoria      = d['categoria']
            insumo.area_principal = d.get('area_principal', 'GENERAL')
            insumo.unidad_medida  = d.get('unidad_medida', 'UNIDAD')
            insumo.stock_minimo   = d.get('stock_minimo') or 0
            insumo.stock_maximo   = d.get('stock_maximo') or None
            insumo.activo         = bool(d.get('activo', True))
            insumo.save()
            messages.success(request, 'Actualizado.')
            return redirect('inventario:lista_insumos_generales')
        except (DatabaseError, ValidationError) as exc:
            messages.error(request, f'Error: {exc}')
    ctx = {
        'titulo': 'Editar Insumo General',
        'insumo': insumo,
        'categoria_choices': CatalogoInsumoGeneral.CATEGORIA_CHOICES,
        'area_choices': AREA_CHOICES_DISPLAY,
    }
    return render(request, 'inventario/generales/form_insumo.html', ctx)


# =============================================================================
# LOTES GENERALES
# =============================================================================

@_empresa_required
def lista_lotes_generales(request, empresa):
    qs = (
        LoteInsumoGeneral.objects
        .filter(empresa=empresa)
        .select_related('insumo', 'recibido_por')
        .order_by('-fecha_recepcion')
    )
    insumo_f = request.GET.get('insumo', '')
    if insumo_f:
        qs = qs.filter(insumo_id=insumo_f)

    insumos = CatalogoInsumoGeneral.objects.filter(empresa=empresa, activo=True).order_by('nombre')
    ctx = {'titulo': 'Lotes — Insumos Generales', 'lotes': qs, 'insumos': insumos, 'insumo_f': insumo_f}
    return render(request, 'inventario/generales/lista_lotes.html', ctx)


@_empresa_required
def crear_lote_general(request, empresa):
    if request.method == 'POST':
        d = request.POST
        try:
            insumo = get_object_or_404(CatalogoInsumoGeneral, pk=d['insumo'], empresa=empresa)
            cantidad = float(d['cantidad_inicial'])
            with transaction.atomic():
                lote = LoteInsumoGeneral.objects.create(
                    empresa=empresa,
                    insumo=insumo,
                    cantidad_inicial=cantidad,
                    cantidad_actual=cantidad,
                    precio_unitario_compra=d.get('precio_unitario_compra') or 0,
                    recibido_por=request.user,
                )
                insumo.precio_ultima_compra = lote.precio_unitario_compra
                insumo.save(update_fields=['precio_ultima_compra'])
            messages.success(request, f'Lote de {insumo.nombre} registrado.')
            return redirect('inventario:lista_lotes_generales')
        except (DatabaseError, ValidationError) as exc:
            messages.error(request, f'Error: {exc}')

    insumos = CatalogoInsumoGeneral.objects.filter(empresa=empresa, activo=True).order_by('nombre')
    ctx = {'titulo': 'Nuevo Lote — Generales', 'insumos': insumos}
    return render(request, 'inventario/generales/form_lote.html', ctx)


# =============================================================================
# VALES DE REQUISICIÓN — FLUJO COMPLETO
# =============================================================================

@_empresa_required
def lista_vales(request, empresa):
    estado_f = request.GET.get('estado', '')
    qs = (
        ValeRequisicion.objects
        .filter(empresa=empresa)
        .select_related('solicitado_por', 'aprobado_por')
        .annotate(total_lineas=Count('lineas'))
        .order_by('-fecha_solicitud')
    )
    if estado_f:
        qs = qs.filter(estado=estado_f)
    ctx = {
        'titulo': 'Vales de Requisición',
        'vales': qs[:100],
        'estado_f': estado_f,
        'estado_choices': ValeRequisicion.ESTADO_CHOICES,
    }
    return render(request, 'inventario/generales/lista_vales.html', ctx)


@_empresa_required
def crear_vale(request, empresa):
    if request.method == 'POST':
        d = request.POST
        insumos_ids   = request.POST.getlist('insumo_id')
        cantidades    = request.POST.getlist('cantidad_solicitada')
        observaciones = request.POST.getlist('obs_linea')

        if not insumos_ids:
            messages.error(request, 'Debes agregar al menos un artículo.')
        else:
            try:
                with transaction.atomic():
                    # Folio automático
                    ultimo = ValeRequisicion.objects.filter(empresa=empresa).count() + 1
                    folio = f"REQ-{date.today().year}-{ultimo:04d}"
                    vale = ValeRequisicion.objects.create(
                        empresa=empresa,
                        folio=folio,
                        area_solicitante=d.get('area_solicitante', 'GENERAL'),
                        solicitado_por=request.user,
                        estado='BORRADOR',
                        observaciones=d.get('observaciones', ''),
                    )
                    for i, insumo_id in enumerate(insumos_ids):
                        if not insumo_id:
                            continue
                        LineaValeRequisicion.objects.create(
                            empresa=empresa,
                            vale=vale,
                            insumo_id=insumo_id,
                            cantidad_solicitada=float(cantidades[i] or 0),
                            observaciones=observaciones[i] if i < len(observaciones) else '',
                        )
                messages.success(request, f'Vale {folio} creado en borrador.')
                return redirect('inventario:detalle_vale', pk=vale.pk)
            except (DatabaseError, ValidationError) as exc:
                logger.error("Error crear vale: %s", exc, exc_info=True)
                messages.error(request, f'Error: {exc}')

    insumos = CatalogoInsumoGeneral.objects.filter(empresa=empresa, activo=True).order_by('nombre')
    ctx = {
        'titulo': 'Nuevo Vale de Requisición',
        'insumos': insumos,
        'area_choices': AREA_CHOICES_DISPLAY,
    }
    return render(request, 'inventario/generales/form_vale.html', ctx)


@_empresa_required
def detalle_vale(request, empresa, pk):
    vale = get_object_or_404(ValeRequisicion, pk=pk, empresa=empresa)
    lineas = vale.lineas.select_related('insumo', 'lote_entregado')

    if request.method == 'POST':
        accion = request.POST.get('accion')

        if accion == 'enviar' and vale.estado == 'BORRADOR':
            vale.estado = 'PENDIENTE'
            vale.save(update_fields=['estado'])
            messages.info(request, f'Vale {vale.folio} enviado a aprobación.')

        elif accion == 'aprobar' and vale.estado == 'PENDIENTE':
            vale.estado = 'APROBADO'
            vale.aprobado_por = request.user
            vale.fecha_aprobacion = timezone.now()
            vale.save(update_fields=['estado', 'aprobado_por', 'fecha_aprobacion'])
            messages.success(request, f'Vale {vale.folio} aprobado.')

        elif accion == 'rechazar' and vale.estado == 'PENDIENTE':
            vale.estado = 'RECHAZADO'
            vale.aprobado_por = request.user
            vale.razon_rechazo = request.POST.get('razon_rechazo', '')
            vale.save(update_fields=['estado', 'aprobado_por', 'razon_rechazo'])
            messages.warning(request, f'Vale {vale.folio} rechazado.')

        elif accion == 'entregar' and vale.estado == 'APROBADO':
            # ── FEFO: despacha de los lotes que caducan primero ──
            errores = []
            with transaction.atomic():
                for linea in lineas:
                    pendiente = float(linea.cantidad_solicitada) - float(linea.cantidad_entregada)
                    if pendiente <= 0:
                        continue
                    lotes_fefo = (
                        LoteInsumoGeneral.objects
                        .filter(empresa=empresa, insumo=linea.insumo, cantidad_actual__gt=0)
                        .select_for_update()
                        .order_by('fecha_recepcion')  # Generales no siempre tienen caducidad → FIFO
                    )
                    for lote in lotes_fefo:
                        if pendiente <= 0:
                            break
                        a_dar = min(float(lote.cantidad_actual), pendiente)
                        lote.cantidad_actual = float(lote.cantidad_actual) - a_dar
                        lote.save(update_fields=['cantidad_actual'])
                        pendiente -= a_dar
                        linea.cantidad_entregada = float(linea.cantidad_entregada) + a_dar
                        linea.lote_entregado = lote
                        linea.save(update_fields=['cantidad_entregada', 'lote_entregado'])

                    if pendiente > 0:
                        errores.append(f'{linea.insumo.nombre}: faltaron {pendiente:.2f} unidades')

                vale.estado = 'ENTREGADO'
                vale.fecha_entrega = timezone.now()
                vale.save(update_fields=['estado', 'fecha_entrega'])

            if errores:
                messages.warning(request, f'Entregado con diferencias: {"; ".join(errores)}')
            else:
                messages.success(request, f'Vale {vale.folio} entregado. Stock descontado.')

        return redirect('inventario:detalle_vale', pk=pk)

    ctx = {
        'titulo': f'Vale {vale.folio}',
        'vale': vale,
        'lineas': lineas,
    }
    return render(request, 'inventario/generales/detalle_vale.html', ctx)


@_empresa_required
@require_POST
def cancelar_vale(request, empresa, pk):
    vale = get_object_or_404(ValeRequisicion, pk=pk, empresa=empresa)
    if vale.estado in ('ENTREGADO', 'CANCELADO'):
        messages.error(request, 'No se puede cancelar un vale ya entregado o cancelado.')
    else:
        vale.estado = 'CANCELADO'
        vale.save(update_fields=['estado'])
        messages.warning(request, f'Vale {vale.folio} cancelado.')
    return redirect('inventario:lista_vales')
