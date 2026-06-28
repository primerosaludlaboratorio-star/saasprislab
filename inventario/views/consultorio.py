"""
INVENTARIO V8.2 — Vistas del Silo de Consultorio
CatalogoInsumoConsultorio · LoteInsumoConsultorio · SalidaConsumoConsultorio
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q, Sum, Value, DecimalField
from django.db.utils import DatabaseError
from django.core.exceptions import ValidationError
from decimal import Decimal
from django.db.models.functions import Coalesce
from django.views.decorators.http import require_POST
from datetime import date, timedelta
import logging

from inventario.models import (
    CatalogoInsumoConsultorio, LoteInsumoConsultorio, SalidaConsumoConsultorio,
    UNIDAD_CHOICES,
)
from .helpers import _get_empresa, _empresa_required

logger = logging.getLogger(__name__)


# =============================================================================
# DASHBOARD CONSULTORIO
# =============================================================================

@_empresa_required
def dashboard_consultorio(request, empresa):
    hoy = date.today()
    dias_alerta = 30

    insumos = (
        CatalogoInsumoConsultorio.objects
        .filter(empresa=empresa, activo=True)
        .prefetch_related('lotes')
        .annotate(
            stock_total=Coalesce(
                Sum('lotes__cantidad_actual', filter=Q(lotes__cantidad_actual__gt=0)),
                Value(Decimal('0'), output_field=DecimalField())
            )
        )
    )

    criticos  = [i for i in insumos if float(i.stock_total) <= float(i.stock_minimo)]
    sin_stock = [i for i in insumos if float(i.stock_total) == 0]

    limite = hoy + timedelta(days=dias_alerta)
    por_caducar = (
        LoteInsumoConsultorio.objects
        .filter(empresa=empresa, cantidad_actual__gt=0,
                fecha_caducidad__lte=limite, fecha_caducidad__gte=hoy)
        .select_related('insumo')
        .order_by('fecha_caducidad')[:15]
    )

    ultimas_salidas = (
        SalidaConsumoConsultorio.objects
        .filter(empresa=empresa)
        .select_related('lote__insumo', 'registrado_por', 'cita')
        .order_by('-fecha')[:10]
    )

    ctx = {
        'titulo': 'Inventario — Silo Consultorio',
        'criticos': criticos,
        'sin_stock': sin_stock,
        'por_caducar': por_caducar,
        'ultimas_salidas': ultimas_salidas,
        'total_insumos': insumos.count(),
    }
    return render(request, 'inventario/consultorio/dashboard.html', ctx)


# =============================================================================
# CRUD CATÁLOGO
# =============================================================================

@_empresa_required
def lista_insumos_consultorio(request, empresa):
    q    = request.GET.get('q', '')
    tipo = request.GET.get('tipo', '')
    qs = (
        CatalogoInsumoConsultorio.objects
        .filter(empresa=empresa)
        .annotate(
            stock_total=Coalesce(
                Sum('lotes__cantidad_actual', filter=Q(lotes__cantidad_actual__gt=0)),
                Value(Decimal('0'), output_field=DecimalField())
            )
        )
        .order_by('tipo', 'nombre')
    )
    if q:
        qs = qs.filter(Q(nombre__icontains=q) | Q(codigo_interno__icontains=q))
    if tipo:
        qs = qs.filter(tipo=tipo)
    ctx = {
        'titulo': 'Insumos de Consultorio',
        'insumos': qs,
        'q': q, 'tipo': tipo,
        'tipo_choices': CatalogoInsumoConsultorio.TIPO_CHOICES,
    }
    return render(request, 'inventario/consultorio/lista_insumos.html', ctx)


@_empresa_required
def crear_insumo_consultorio(request, empresa):
    if request.method == 'POST':
        d = request.POST
        try:
            CatalogoInsumoConsultorio.objects.create(
                empresa=empresa,
                codigo_interno=d['codigo_interno'].strip(),
                nombre=d['nombre'].strip(),
                descripcion=d.get('descripcion', ''),
                tipo=d['tipo'],
                unidad_medida=d.get('unidad_medida', 'UNIDAD'),
                stock_minimo=d.get('stock_minimo') or 0,
                stock_maximo=d.get('stock_maximo') or None,
                notas=d.get('notas', ''),
            )
            messages.success(request, 'Insumo creado.')
            return redirect('inventario:lista_insumos_consultorio')
        except (DatabaseError, ValidationError) as exc:
            messages.error(request, f'Error: {exc}')
    ctx = {
        'titulo': 'Nuevo Insumo de Consultorio',
        'tipo_choices': CatalogoInsumoConsultorio.TIPO_CHOICES,
        'unidad_choices': UNIDAD_CHOICES,
    }
    return render(request, 'inventario/consultorio/form_insumo.html', ctx)


@_empresa_required
def editar_insumo_consultorio(request, empresa, pk):
    insumo = get_object_or_404(CatalogoInsumoConsultorio, pk=pk, empresa=empresa)
    if request.method == 'POST':
        d = request.POST
        try:
            insumo.codigo_interno = d['codigo_interno'].strip()
            insumo.nombre         = d['nombre'].strip()
            insumo.descripcion    = d.get('descripcion', '')
            insumo.tipo           = d['tipo']
            insumo.unidad_medida  = d.get('unidad_medida', 'UNIDAD')
            insumo.stock_minimo   = d.get('stock_minimo') or 0
            insumo.stock_maximo   = d.get('stock_maximo') or None
            insumo.activo         = bool(d.get('activo', True))
            insumo.notas          = d.get('notas', '')
            insumo.save()
            messages.success(request, 'Insumo actualizado.')
            return redirect('inventario:lista_insumos_consultorio')
        except (DatabaseError, ValidationError) as exc:
            messages.error(request, f'Error: {exc}')
    ctx = {
        'titulo': 'Editar Insumo',
        'insumo': insumo,
        'tipo_choices': CatalogoInsumoConsultorio.TIPO_CHOICES,
        'unidad_choices': UNIDAD_CHOICES,
    }
    return render(request, 'inventario/consultorio/form_insumo.html', ctx)


# =============================================================================
# LOTES CONSULTORIO
# =============================================================================

@_empresa_required
def lista_lotes_consultorio(request, empresa):
    hoy = date.today()
    qs = (
        LoteInsumoConsultorio.objects
        .filter(empresa=empresa)
        .select_related('insumo', 'recibido_por')
        .order_by('fecha_caducidad')
    )
    insumo_f = request.GET.get('insumo', '')
    if insumo_f:
        qs = qs.filter(insumo_id=insumo_f)

    for lote in qs:
        dias = (lote.fecha_caducidad - hoy).days if lote.fecha_caducidad else 9999
        lote.semaforo = 'rojo' if dias < 0 or lote.cantidad_actual <= 0 else \
                        'amarillo' if dias <= 30 else 'verde'

    insumos = CatalogoInsumoConsultorio.objects.filter(empresa=empresa, activo=True).order_by('nombre')
    ctx = {
        'titulo': 'Lotes — Consultorio',
        'lotes': qs,
        'insumos': insumos,
        'insumo_f': insumo_f,
        'hoy': hoy,
    }
    return render(request, 'inventario/consultorio/lista_lotes.html', ctx)


@_empresa_required
def crear_lote_consultorio(request, empresa):
    if request.method == 'POST':
        d = request.POST
        try:
            insumo = get_object_or_404(CatalogoInsumoConsultorio, pk=d['insumo'], empresa=empresa)
            cantidad = float(d['cantidad_inicial'])
            with transaction.atomic():
                lote = LoteInsumoConsultorio.objects.create(
                    empresa=empresa,
                    insumo=insumo,
                    numero_lote=d.get('numero_lote', '').strip() or None,
                    fecha_caducidad=d.get('fecha_caducidad') or None,
                    cantidad_inicial=cantidad,
                    cantidad_actual=cantidad,
                    precio_unitario_compra=d.get('precio_unitario_compra') or 0,
                    recibido_por=request.user,
                )
                insumo.precio_ultima_compra = lote.precio_unitario_compra
                insumo.save(update_fields=['precio_ultima_compra'])
            messages.success(request, f'Lote de {insumo.nombre} registrado.')
            return redirect('inventario:lista_lotes_consultorio')
        except (DatabaseError, ValidationError) as exc:
            logger.error("Error crear lote consultorio: %s", exc, exc_info=True)
            messages.error(request, f'Error: {exc}')

    insumos = CatalogoInsumoConsultorio.objects.filter(empresa=empresa, activo=True).order_by('nombre')
    ctx = {'titulo': 'Nuevo Lote — Consultorio', 'insumos': insumos}
    return render(request, 'inventario/consultorio/form_lote.html', ctx)


# =============================================================================
# SALIDAS MANUALES CONSULTORIO
# =============================================================================

@_empresa_required
def lista_salidas_consultorio(request, empresa):
    qs = (
        SalidaConsumoConsultorio.objects
        .filter(empresa=empresa)
        .select_related('lote__insumo', 'registrado_por', 'cita')
        .order_by('-fecha')[:100]
    )
    ctx = {'titulo': 'Consumos de Insumos — Consultorio', 'salidas': qs}
    return render(request, 'inventario/consultorio/lista_salidas.html', ctx)


@_empresa_required
def registrar_salida_consultorio(request, empresa):
    if request.method == 'POST':
        d = request.POST
        try:
            cantidad = float(d['cantidad'])
            with transaction.atomic():
                lote = (
                    LoteInsumoConsultorio.objects.select_for_update(nowait=False)
                    .get(pk=int(d['lote']), empresa=empresa)
                )
                if cantidad > float(lote.cantidad_actual):
                    messages.error(request, f'Stock insuficiente ({lote.cantidad_actual}).')
                else:
                    SalidaConsumoConsultorio.objects.create(
                        empresa=empresa,
                        lote=lote,
                        cantidad=cantidad,
                        motivo=d['motivo'],
                        registrado_por=request.user,
                        cita_id=d.get('cita_id') or None,
                    )
                    lote.cantidad_actual = float(lote.cantidad_actual) - cantidad
                    lote.save(update_fields=['cantidad_actual'])
                    messages.success(request, f'Consumo de {cantidad} registrado.')
                    return redirect('inventario:lista_salidas_consultorio')
        except (DatabaseError, ValidationError) as exc:
            messages.error(request, f'Error: {exc}')

    lotes = (
        LoteInsumoConsultorio.objects
        .filter(empresa=empresa, cantidad_actual__gt=0)
        .select_related('insumo')
        .order_by('insumo__nombre', 'fecha_caducidad')
    )
    ctx = {'titulo': 'Registrar Consumo — Consultorio', 'lotes': lotes}
    return render(request, 'inventario/consultorio/form_salida.html', ctx)
