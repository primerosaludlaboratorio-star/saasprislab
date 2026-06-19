"""
INVENTARIO V8.0 — Vistas del Silo de Laboratorio
Gestión de Reactivos, Lotes (FEFO), Consumo por Estudio y Dashboard Director
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.db import transaction
from django.db.models import Sum, F, Q, Count, Value, DecimalField
from decimal import Decimal
from django.db.models.functions import Coalesce
from django.utils import timezone
from django.views.decorators.http import require_POST
from datetime import date, timedelta
import logging

from lims.models import Analito as AnalitoLims
from core.utils.tenant_strict import empresa_desde_request
from .models import (
    CatalogoReactivoLab, LoteReactivoLab, ConsumoEstudioReactivo,
    SalidaAnaliticaLab, SalidaTecnicaLab, UNIDAD_CHOICES,
)

logger = logging.getLogger(__name__)


# ── Helper: empresa del request (tenant estricto; sin fallback a «primera» empresa) ──
def _get_empresa(request):
    """Retorna la Empresa del usuario activo. None si no hay tenant resoluble."""
    return empresa_desde_request(request)


def _empresa_required(view_fn):
    """Decorator: requiere login + empresa válida."""
    from functools import wraps

    @login_required
    @wraps(view_fn)
    def wrapper(request, *args, **kwargs):
        empresa = _get_empresa(request)
        if not empresa:
            messages.error(request, "No tienes una empresa asignada.")
            return redirect('home')
        return view_fn(request, empresa, *args, **kwargs)
    return wrapper


# =============================================================================
# 1. DASHBOARD PRINCIPAL — Stock Crítico + Valor + Semáforos
# =============================================================================

@_empresa_required
def dashboard_reactivos(request, empresa):
    """
    Dashboard del Silo Laboratorio.
    Muestra stock crítico, valor total del inventario y alertas de caducidad.
    Acceso: Químico Jefe / Director / Admin
    """
    hoy = date.today()
    dias_alerta = 30

    # Stock por reactivo: suma de cantidad_actual de lotes ACTIVOS
    reactivos_qs = (
        CatalogoReactivoLab.objects
        .filter(empresa=empresa, activo=True)
        .prefetch_related('lotes')
        .annotate(
            stock_total=Coalesce(
                Sum('lotes__cantidad_actual',
                    filter=Q(lotes__estado='ACTIVO'),
                    output_field=DecimalField()),
                Value(Decimal('0'), output_field=DecimalField())
            )
        )
    )

    # Clasificar semáforos
    criticos   = [r for r in reactivos_qs if r.stock_total <= float(r.stock_minimo)]
    sin_stock  = [r for r in reactivos_qs if r.stock_total == 0]

    # Lotes próximos a caducar
    limite_alerta = hoy + timedelta(days=dias_alerta)
    lotes_por_caducar = (
        LoteReactivoLab.objects
        .filter(empresa=empresa, estado='ACTIVO',
                fecha_caducidad__lte=limite_alerta,
                fecha_caducidad__gte=hoy)
        .select_related('reactivo')
        .order_by('fecha_caducidad')[:20]
    )

    lotes_vencidos = (
        LoteReactivoLab.objects
        .filter(empresa=empresa, estado='ACTIVO', fecha_caducidad__lt=hoy)
        .select_related('reactivo')[:10]
    )

    # Lotes en Cuarentena pendientes de aprobación
    en_cuarentena = (
        LoteReactivoLab.objects
        .filter(empresa=empresa, estado='CUARENTENA')
        .select_related('reactivo', 'recibido_por')
        .order_by('-fecha_recepcion')[:10]
    )

    # Valor total del inventario (lotes ACTIVOS)
    valor_inventario = (
        LoteReactivoLab.objects
        .filter(empresa=empresa, estado='ACTIVO')
        .aggregate(total=Coalesce(Sum(F('cantidad_actual') * F('precio_unitario_compra'),
                                     output_field=DecimalField()), Value(Decimal('0.00'))))
        ['total'] or 0
    )

    # Últimas salidas analíticas (feed de actividad)
    ultimas_salidas = (
        SalidaAnaliticaLab.objects
        .filter(empresa=empresa)
        .select_related('lote__reactivo', 'validado_por', 'orden')
        .order_by('-fecha')[:10]
    )

    ctx = {
        'titulo': 'Inventario de Laboratorio',
        'empresa': empresa,
        'reactivos_total': reactivos_qs.count(),
        'criticos': criticos,
        'sin_stock': sin_stock,
        'lotes_por_caducar': lotes_por_caducar,
        'lotes_vencidos': lotes_vencidos,
        'en_cuarentena': en_cuarentena,
        'valor_inventario': valor_inventario,
        'ultimas_salidas': ultimas_salidas,
        'hoy': hoy,
        'dias_alerta': dias_alerta,
    }
    return render(request, 'inventario/dashboard_reactivos.html', ctx)


# =============================================================================
# 2. CATÁLOGO DE REACTIVOS — CRUD
# =============================================================================

@_empresa_required
def lista_reactivos(request, empresa):
    tipo_filtro = request.GET.get('tipo', '')
    busqueda    = request.GET.get('q', '')

    qs = (
        CatalogoReactivoLab.objects
        .filter(empresa=empresa)
        .prefetch_related('lotes')
        .annotate(
            stock_total=Coalesce(
                Sum('lotes__cantidad_actual',
                    filter=Q(lotes__estado='ACTIVO')),
                Value(0.0)
            )
        )
        .order_by('tipo', 'nombre')
    )

    if tipo_filtro:
        qs = qs.filter(tipo=tipo_filtro)
    if busqueda:
        qs = qs.filter(
            Q(nombre__icontains=busqueda) |
            Q(codigo_interno__icontains=busqueda) |
            Q(fabricante__icontains=busqueda)
        )

    ctx = {
        'titulo': 'Catálogo de Reactivos',
        'reactivos': qs,
        'tipo_filtro': tipo_filtro,
        'busqueda': busqueda,
        'tipo_choices': CatalogoReactivoLab.TIPO_CHOICES,
    }
    return render(request, 'inventario/lista_reactivos.html', ctx)


@_empresa_required
def crear_reactivo(request, empresa):
    if request.method == 'POST':
        d = request.POST
        try:
            reactivo = CatalogoReactivoLab.objects.create(
                empresa=empresa,
                codigo_interno=d['codigo_interno'].strip(),
                nombre=d['nombre'].strip(),
                descripcion=d.get('descripcion', ''),
                tipo=d['tipo'],
                fabricante=d.get('fabricante', ''),
                referencia_fabricante=d.get('referencia_fabricante', ''),
                unidad_medida=d['unidad_medida'],
                temperatura_almacenamiento=d.get('temperatura_almacenamiento', ''),
                requiere_cadena_frio=bool(d.get('requiere_cadena_frio')),
                stock_minimo=d.get('stock_minimo') or 0,
                stock_maximo=d.get('stock_maximo') or None,
                notas=d.get('notas', ''),
            )
            messages.success(request, f'Reactivo "{reactivo.nombre}" creado correctamente.')
            return redirect('inventario:lista_reactivos')
        except Exception as exc:
            logger.error("Error al crear reactivo: %s", exc, exc_info=True)
            messages.error(request, f'Error al guardar: {exc}')

    ctx = {
        'titulo': 'Nuevo Reactivo',
        'accion': 'Crear',
        'tipo_choices': CatalogoReactivoLab.TIPO_CHOICES,
        'unidad_choices': UNIDAD_CHOICES,
    }
    return render(request, 'inventario/form_reactivo.html', ctx)


@_empresa_required
def editar_reactivo(request, empresa, pk):
    reactivo = get_object_or_404(CatalogoReactivoLab, pk=pk, empresa=empresa)
    if request.method == 'POST':
        d = request.POST
        try:
            reactivo.codigo_interno         = d['codigo_interno'].strip()
            reactivo.nombre                  = d['nombre'].strip()
            reactivo.descripcion             = d.get('descripcion', '')
            reactivo.tipo                    = d['tipo']
            reactivo.fabricante              = d.get('fabricante', '')
            reactivo.referencia_fabricante   = d.get('referencia_fabricante', '')
            reactivo.unidad_medida           = d['unidad_medida']
            reactivo.temperatura_almacenamiento = d.get('temperatura_almacenamiento', '')
            reactivo.requiere_cadena_frio    = bool(d.get('requiere_cadena_frio'))
            reactivo.stock_minimo            = d.get('stock_minimo') or 0
            reactivo.stock_maximo            = d.get('stock_maximo') or None
            reactivo.notas                   = d.get('notas', '')
            reactivo.activo                  = bool(d.get('activo', True))
            reactivo.save()
            messages.success(request, f'Reactivo "{reactivo.nombre}" actualizado.')
            return redirect('inventario:lista_reactivos')
        except Exception as exc:
            logger.error("Error al editar reactivo pk=%s: %s", pk, exc, exc_info=True)
            messages.error(request, f'Error: {exc}')

    ctx = {
        'titulo': 'Editar Reactivo',
        'accion': 'Guardar Cambios',
        'reactivo': reactivo,
        'tipo_choices': CatalogoReactivoLab.TIPO_CHOICES,
        'unidad_choices': UNIDAD_CHOICES,
    }
    return render(request, 'inventario/form_reactivo.html', ctx)


@_empresa_required
@require_POST
def eliminar_reactivo(request, empresa, pk):
    reactivo = get_object_or_404(CatalogoReactivoLab, pk=pk, empresa=empresa)
    if reactivo.lotes.exists():
        messages.error(request, 'No se puede eliminar: tiene lotes asociados. Desactívalo en cambio.')
    else:
        reactivo.delete()
        messages.success(request, 'Reactivo eliminado.')
    return redirect('inventario:lista_reactivos')


# =============================================================================
# 3. LOTES (FEFO + CUARENTENA)
# =============================================================================

@_empresa_required
def lista_lotes(request, empresa):
    hoy = date.today()
    reactivo_id = request.GET.get('reactivo')
    estado_filtro = request.GET.get('estado', '')

    qs = (
        LoteReactivoLab.objects
        .filter(empresa=empresa)
        .select_related('reactivo', 'recibido_por', 'aprobado_por')
        .order_by('fecha_caducidad')
    )
    if reactivo_id:
        qs = qs.filter(reactivo_id=reactivo_id)
    if estado_filtro:
        qs = qs.filter(estado=estado_filtro)

    # Semáforos para template
    for lote in qs:
        dias = (lote.fecha_caducidad - hoy).days if lote.fecha_caducidad else 9999
        if lote.estado in ('VENCIDO', 'AGOTADO', 'BAJA') or dias < 0:
            lote._semaforo = 'rojo'
        elif dias <= 30:
            lote._semaforo = 'amarillo'
        else:
            lote._semaforo = 'verde'

    reactivos = CatalogoReactivoLab.objects.filter(empresa=empresa, activo=True).order_by('nombre')
    ctx = {
        'titulo': 'Lotes de Reactivos',
        'lotes': qs,
        'reactivos': reactivos,
        'reactivo_id': reactivo_id,
        'estado_filtro': estado_filtro,
        'estado_choices': LoteReactivoLab.ESTADO_CHOICES,
        'hoy': hoy,
    }
    return render(request, 'inventario/lista_lotes.html', ctx)


@_empresa_required
def crear_lote(request, empresa):
    if request.method == 'POST':
        d = request.POST
        try:
            reactivo = get_object_or_404(CatalogoReactivoLab, pk=d['reactivo'], empresa=empresa)
            try:
                cantidad = float(d['cantidad_inicial'])
            except (ValueError, TypeError):
                messages.error(request, 'Cantidad inicial inválida.')
                return redirect('inventario:crear_lote')
            with transaction.atomic():
                lote = LoteReactivoLab.objects.create(
                    empresa=empresa,
                    reactivo=reactivo,
                    numero_lote=d['numero_lote'].strip(),
                    fecha_caducidad=d['fecha_caducidad'],
                    cantidad_inicial=cantidad,
                    cantidad_actual=cantidad,
                    precio_unitario_compra=d.get('precio_unitario_compra') or 0,
                    estado='CUARENTENA',   # Siempre inicia en cuarentena
                    recibido_por=request.user,
                    observaciones_qc=d.get('observaciones_qc', ''),
                )
                # Actualizar precio última compra en catálogo
                reactivo.precio_ultima_compra = lote.precio_unitario_compra
                reactivo.save(update_fields=['precio_ultima_compra'])

            messages.success(request, f'Lote {lote.numero_lote} creado en CUARENTENA. Pendiente de liberación técnica (QC).')
            return redirect('inventario:lista_lotes')
        except Exception as exc:
            logger.error("Error al crear lote: %s", exc, exc_info=True)
            messages.error(request, f'Error: {exc}')

    reactivos = CatalogoReactivoLab.objects.filter(empresa=empresa, activo=True).order_by('nombre')
    ctx = {
        'titulo': 'Registrar Nuevo Lote',
        'reactivos': reactivos,
    }
    return render(request, 'inventario/form_lote.html', ctx)


@_empresa_required
def detalle_lote(request, empresa, pk):
    lote = get_object_or_404(LoteReactivoLab, pk=pk, empresa=empresa)
    salidas_analiticas = lote.salidas_analiticas.select_related('orden__paciente', 'validado_por').order_by('-fecha')
    salidas_tecnicas   = lote.salidas_tecnicas.select_related('registrado_por').order_by('-fecha')
    ctx = {
        'titulo': f'Lote: {lote.numero_lote}',
        'lote': lote,
        'salidas_analiticas': salidas_analiticas,
        'salidas_tecnicas': salidas_tecnicas,
        'hoy': date.today(),
    }
    return render(request, 'inventario/detalle_lote.html', ctx)


@_empresa_required
@require_POST
def liberar_lote_qc(request, empresa, pk):
    """
    Liberación Técnica: cambia estado de CUARENTENA → ACTIVO.
    Solo Químico Jefe / Director / Admin.
    """
    warn_msg = None
    numero_ok = None
    with transaction.atomic():
        lote = get_object_or_404(
            LoteReactivoLab.objects.select_for_update(),
            pk=pk,
            empresa=empresa,
        )
        if lote.estado != 'CUARENTENA':
            warn_msg = f'El lote ya está en estado: {lote.get_estado_display()}'
        else:
            lote.estado = 'ACTIVO'
            lote.lote_aprobado_qc = True
            lote.aprobado_por = request.user
            lote.fecha_aprobacion_qc = timezone.now()
            lote.observaciones_qc = request.POST.get('observaciones_qc', lote.observaciones_qc)
            if request.POST.get('fecha_apertura'):
                lote.fecha_apertura = request.POST['fecha_apertura']
            lote.save()
            numero_ok = lote.numero_lote
    if warn_msg:
        messages.warning(request, warn_msg)
    else:
        messages.success(request, f'✅ Lote {numero_ok} liberado. Estado: ACTIVO.')
    return redirect('inventario:detalle_lote', pk=pk)


@_empresa_required
@require_POST
def baja_lote(request, empresa, pk):
    """Da de baja un lote (merma, vencimiento, incidente)."""
    motivo = request.POST.get('motivo', 'Sin motivo especificado')
    with transaction.atomic():
        lote = get_object_or_404(
            LoteReactivoLab.objects.select_for_update(),
            pk=pk,
            empresa=empresa,
        )
        if lote.cantidad_actual > 0:
            SalidaTecnicaLab.objects.create(
                empresa=empresa,
                lote=lote,
                tipo='MERMA',
                cantidad=lote.cantidad_actual,
                motivo=f'Baja de lote — {motivo}',
                registrado_por=request.user,
            )
            lote.cantidad_actual = 0
        lote.estado = 'BAJA'
        lote.save()
    messages.warning(request, f'Lote {lote.numero_lote} dado de baja.')
    return redirect('inventario:lista_lotes')


# =============================================================================
# 4. SALIDAS TÉCNICAS (Mantenimiento / Merma)
# =============================================================================

@_empresa_required
def lista_salidas_tecnicas(request, empresa):
    qs = (
        SalidaTecnicaLab.objects
        .filter(empresa=empresa)
        .select_related('lote__reactivo', 'registrado_por', 'ticket_mantenimiento')
        .order_by('-fecha')[:100]
    )
    ctx = {'titulo': 'Descuentos Técnicos', 'salidas': qs}
    return render(request, 'inventario/lista_salidas_tecnicas.html', ctx)


@_empresa_required
def crear_salida_tecnica(request, empresa):
    if request.method == 'POST':
        d = request.POST
        try:
            try:
                cantidad = float(d['cantidad'])
            except (ValueError, TypeError):
                messages.error(request, 'Cantidad inválida.')
                return redirect('inventario:crear_salida_tecnica')
            err = None
            with transaction.atomic():
                lote = get_object_or_404(
                    LoteReactivoLab.objects.select_for_update(),
                    pk=d['lote'],
                    empresa=empresa,
                )
                if lote.estado in ('CUARENTENA', 'VENCIDO'):
                    err = (
                        'No se puede consumir un lote en CUARENTENA o VENCIDO. Use solo lotes ACTIVOS.'
                    )
                elif lote.estado != 'ACTIVO':
                    err = f'Estado de lote no permitido para consumo: {lote.get_estado_display()}'
                elif cantidad > float(lote.cantidad_actual):
                    err = (
                        f'Cantidad ({cantidad}) supera el stock del lote ({lote.cantidad_actual}).'
                    )
                else:
                    SalidaTecnicaLab.objects.create(
                        empresa=empresa,
                        lote=lote,
                        tipo=d['tipo'],
                        cantidad=cantidad,
                        motivo=d['motivo'],
                        registrado_por=request.user,
                    )
                    lote.cantidad_actual = float(lote.cantidad_actual) - cantidad
                    if lote.cantidad_actual <= 0:
                        lote.cantidad_actual = 0
                        lote.estado = 'AGOTADO'
                    lote.save(update_fields=['cantidad_actual', 'estado'])
            if err:
                messages.error(request, err)
                return redirect('inventario:crear_salida_tecnica')
            messages.success(request, f'Salida técnica de {cantidad} registrada.')
            return redirect('inventario:lista_salidas_tecnicas')
        except Exception as exc:
            logger.error("Error salida técnica: %s", exc, exc_info=True)
            messages.error(request, f'Error: {exc}')

    lotes = (
        LoteReactivoLab.objects
        .filter(empresa=empresa, estado='ACTIVO')
        .select_related('reactivo')
        .order_by('reactivo__nombre', 'fecha_caducidad')
    )
    ctx = {
        'titulo': 'Registrar Descuento Técnico',
        'lotes': lotes,
        'tipo_choices': SalidaTecnicaLab.TIPO_CHOICES,
    }
    return render(request, 'inventario/form_salida_tecnica.html', ctx)


# =============================================================================
# 5. CONFIGURADOR DE CONSUMO POR ESTUDIO
# =============================================================================

@_empresa_required
def lista_consumo(request, empresa):
    qs = (
        ConsumoEstudioReactivo.objects
        .filter(empresa=empresa)
        .select_related('analito', 'reactivo')
        .order_by('analito__nombre', 'reactivo__nombre')
    )
    ctx = {
        'titulo': 'Fórmulas de Consumo por Analito (LIMS)',
        'consumos': qs,
    }
    return render(request, 'inventario/lista_consumo.html', ctx)


@_empresa_required
def crear_consumo(request, empresa):
    if request.method == 'POST':
        d = request.POST
        try:
            get_object_or_404(AnalitoLims, pk=d['analito'], empresa=empresa, activo=True)
            get_object_or_404(CatalogoReactivoLab, pk=d['reactivo'], empresa=empresa, activo=True)
            ConsumoEstudioReactivo.objects.create(
                empresa=empresa,
                analito_id=d['analito'],
                reactivo_id=d['reactivo'],
                cantidad_por_prueba=d['cantidad_por_prueba'],
                unidad=d['unidad'],
                incluye_overhead_qc=bool(d.get('incluye_overhead_qc')),
            )
            messages.success(request, 'Fórmula de consumo guardada.')
            return redirect('inventario:lista_consumo')
        except Exception as exc:
            logger.error("Error crear consumo: %s", exc, exc_info=True)
            messages.error(request, f'Error: {exc}')

    analitos = AnalitoLims.objects.filter(empresa=empresa, activo=True).order_by('nombre')
    reactivos = CatalogoReactivoLab.objects.filter(empresa=empresa, activo=True).order_by('nombre')
    ctx = {
        'titulo': 'Nueva Fórmula de Consumo',
        'analitos': analitos,
        'reactivos': reactivos,
        'unidad_choices': UNIDAD_CHOICES,
    }
    return render(request, 'inventario/form_consumo.html', ctx)


@_empresa_required
def editar_consumo(request, empresa, pk):
    consumo = get_object_or_404(ConsumoEstudioReactivo, pk=pk, empresa=empresa)
    if request.method == 'POST':
        d = request.POST
        try:
            get_object_or_404(AnalitoLims, pk=d['analito'], empresa=empresa, activo=True)
            get_object_or_404(CatalogoReactivoLab, pk=d['reactivo'], empresa=empresa, activo=True)
            consumo.analito_id = d['analito']
            consumo.reactivo_id        = d['reactivo']
            consumo.cantidad_por_prueba = d['cantidad_por_prueba']
            consumo.unidad             = d['unidad']
            consumo.incluye_overhead_qc = bool(d.get('incluye_overhead_qc'))
            consumo.activo             = bool(d.get('activo', True))
            consumo.save()
            messages.success(request, 'Fórmula actualizada.')
            return redirect('inventario:lista_consumo')
        except Exception as exc:
            messages.error(request, f'Error: {exc}')

    analitos = AnalitoLims.objects.filter(empresa=empresa, activo=True).order_by('nombre')
    reactivos = CatalogoReactivoLab.objects.filter(empresa=empresa, activo=True).order_by('nombre')
    ctx = {
        'titulo': 'Editar Fórmula de Consumo',
        'consumo': consumo,
        'analitos': analitos,
        'reactivos': reactivos,
        'unidad_choices': UNIDAD_CHOICES,
    }
    return render(request, 'inventario/form_consumo.html', ctx)


@_empresa_required
@require_POST
def eliminar_consumo(request, empresa, pk):
    consumo = get_object_or_404(ConsumoEstudioReactivo, pk=pk, empresa=empresa)
    consumo.delete()
    messages.success(request, 'Fórmula eliminada.')
    return redirect('inventario:lista_consumo')


# =============================================================================
# 6. TRAZABILIDAD FORENSE
# =============================================================================

@_empresa_required
def trazabilidad_lote(request, empresa):
    """Busca todas las órdenes donde se usó un lote específico."""
    numero_lote = request.GET.get('lote', '').strip()
    reactivo_id = request.GET.get('reactivo', '')
    resultados   = None
    lote_obj     = None

    if numero_lote or reactivo_id:
        qs_lotes = LoteReactivoLab.objects.filter(empresa=empresa)
        if numero_lote:
            qs_lotes = qs_lotes.filter(numero_lote__icontains=numero_lote)
        if reactivo_id:
            qs_lotes = qs_lotes.filter(reactivo_id=reactivo_id)

        if qs_lotes.count() == 1:
            lote_obj = qs_lotes.first()

        resultados = (
            SalidaAnaliticaLab.objects
            .filter(empresa=empresa, lote__in=qs_lotes)
            .select_related(
                'lote__reactivo',
                'orden__paciente',
                'validado_por',
                'analito',
            )
            .order_by('-fecha')
        )

    reactivos = CatalogoReactivoLab.objects.filter(empresa=empresa, activo=True).order_by('nombre')
    ctx = {
        'titulo': 'Trazabilidad Forense de Lotes',
        'resultados': resultados,
        'lote_obj': lote_obj,
        'numero_lote': numero_lote,
        'reactivo_id': reactivo_id,
        'reactivos': reactivos,
        'total': resultados.count() if resultados is not None else 0,
    }
    return render(request, 'inventario/trazabilidad_lote.html', ctx)


# =============================================================================
# 7. APIs JSON
# =============================================================================

@login_required
def api_stock_critico(request):
    """Devuelve reactivos en stock crítico para widgets del dashboard."""
    empresa = _get_empresa(request)
    if not empresa:
        return JsonResponse({'error': 'Sin empresa'}, status=403)

    data = []
    reactivos = (
        CatalogoReactivoLab.objects
        .filter(empresa=empresa, activo=True)
        .annotate(
            stock_total=Coalesce(
                Sum('lotes__cantidad_actual', filter=Q(lotes__estado='ACTIVO')),
                Value(0.0)
            )
        )
        .filter(stock_total__lte=F('stock_minimo'))
        .order_by('nombre')[:20]
    )
    for r in reactivos:
        data.append({
            'id': r.pk,
            'nombre': r.nombre,
            'codigo': r.codigo_interno,
            'stock': float(r.stock_total),
            'minimo': float(r.stock_minimo),
            'unidad': r.unidad_medida,
        })
    return JsonResponse({'criticos': data, 'total': len(data)})


@login_required
def api_lotes_por_reactivo(request, reactivo_id):
    """Devuelve lotes ACTIVOS de un reactivo (para formularios de descuento técnico)."""
    empresa = _get_empresa(request)
    if not empresa:
        return JsonResponse({'error': 'Sin empresa'}, status=403)

    get_object_or_404(CatalogoReactivoLab, pk=reactivo_id, empresa=empresa)
    lotes = (
        LoteReactivoLab.objects
        .filter(empresa=empresa, reactivo_id=reactivo_id, estado='ACTIVO')
        .order_by('fecha_caducidad')
        .values('id', 'numero_lote', 'fecha_caducidad', 'cantidad_actual')
    )
    return JsonResponse({'lotes': list(lotes)})
