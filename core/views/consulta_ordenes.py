"""
Vistas para Consulta de Órdenes y Detalle de Orden (edición).
Replica flujo UI/UX del sistema legacy con tablas filtrables y edición en línea.
"""
from datetime import date
from decimal import Decimal

from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.views.decorators.http import require_http_methods

from lims.models import Analito

from contabilidad.models import FacturaCFDI

from core.models import (
    OrdenDeServicio, PagoOrden, Medico,
    ResultadoParametro, DetalleOrden,
)


@login_required
def consulta_ordenes(request):
    """Pantalla 1: Listado filtrable de órdenes con paginación."""
    empresa = getattr(request.user, 'empresa', None)
    if not empresa:
        from django.contrib import messages
        messages.error(request, 'Tu usuario no tiene una empresa asignada. Contacta al administrador.')
        return redirect('home')
    hoy = date.today()

    # ── Parámetros de filtro ──
    fecha_ini = request.GET.get('fecha_ini', hoy.strftime('%Y-%m-%d'))
    fecha_fin = request.GET.get('fecha_fin', hoy.strftime('%Y-%m-%d'))
    folio = request.GET.get('folio', '').strip()
    paciente_q = request.GET.get('paciente', '').strip()
    cliente_q = request.GET.get('cliente', '').strip()
    medico_q = request.GET.get('medico', '').strip()
    estatus = request.GET.get('estatus', '')
    departamento = request.GET.get('departamento', '')
    tipo_orden = request.GET.get('tipo_orden', '')
    try:
        por_pagina = max(1, min(200, int(request.GET.get('por_pagina', 20))))
    except (ValueError, TypeError):
        por_pagina = 20

    qs = OrdenDeServicio.objects.filter(
        deleted_at__isnull=True,
        empresa=empresa,
    ).select_related('paciente', 'medico_referente', 'responsable_ingreso')

    # Filtros
    if fecha_ini:
        qs = qs.filter(fecha_creacion__date__gte=fecha_ini)
    if fecha_fin:
        qs = qs.filter(fecha_creacion__date__lte=fecha_fin)
    if folio:
        qs = qs.filter(folio_orden__icontains=folio)
    if paciente_q:
        qs = qs.filter(paciente__nombre_completo__icontains=paciente_q)
    if cliente_q:
        qs = qs.filter(tarifa__icontains=cliente_q)
    if medico_q:
        qs = qs.filter(medico_referente__nombre_completo__icontains=medico_q)
    if estatus:
        qs = qs.filter(estado=estatus)
    if tipo_orden:
        qs = qs.filter(tipo_servicio=tipo_orden)
    if departamento:
        qs = qs.filter(detalles__analito__departamento=departamento).distinct()

    qs = qs.prefetch_related(
        'detalles__analito', 'detalles__perfil_lims', 'detalles__paquete_lims'
    )
    qs = qs.order_by('-fecha_creacion')

    paginator = Paginator(qs, por_pagina)
    page = paginator.get_page(request.GET.get('page', 1))

    # Datos auxiliares para filtros
    secciones = (
        Analito.objects.filter(activo=True)
        .exclude(departamento='')
        .values_list('departamento', flat=True)
        .distinct()
        .order_by('departamento')
    )
    med_filter = {'activo': True}
    if empresa:
        med_filter['empresa'] = empresa
    medicos = Medico.objects.filter(**med_filter).order_by('nombre_completo')

    # Construir query string para paginación sin 'page'
    qs_params = request.GET.copy()
    if 'page' in qs_params:
        del qs_params['page']
    query_string = qs_params.urlencode()

    context = {
        'page': page,
        'paginator': paginator,
        'query_string': query_string,
        'filtros': {
            'fecha_ini': fecha_ini,
            'fecha_fin': fecha_fin,
            'folio': folio,
            'paciente': paciente_q,
            'cliente': cliente_q,
            'medico': medico_q,
            'estatus': estatus,
            'departamento': departamento,
            'tipo_orden': tipo_orden,
            'por_pagina': por_pagina,
        },
        'estados': OrdenDeServicio.ESTADO_CHOICES,
        'tipos_servicio': OrdenDeServicio.TIPO_SERVICIO_CHOICES,
        'secciones': secciones,
        'medicos': medicos,
    }
    return render(request, 'core/consulta_ordenes.html', context)


@login_required
def detalle_orden_view(request, orden_id):
    """Pantalla 2: Detalle completo de una orden con edición en línea."""
    empresa = getattr(request.user, 'empresa', None)
    filtro = {'id': orden_id}
    if empresa:
        filtro['empresa'] = empresa
    orden = get_object_or_404(
        OrdenDeServicio.objects.select_related('paciente', 'medico_referente', 'responsable_ingreso', 'sucursal'),
        **filtro,
    )

    detalles = orden.detalles.select_related(
        'analito', 'perfil_lims', 'paquete_lims'
    ).all()

    # Calcular pagos
    pagos = PagoOrden.objects.filter(orden=orden).order_by('-fecha_pago')
    total_pagado = sum(p.monto_total for p in pagos) if pagos.exists() else (orden.anticipo or Decimal('0'))

    subtotal = sum(d.precio_momento for d in detalles)
    descuento_monto = orden.descuento_monto or Decimal('0')
    total = orden.total or subtotal
    saldo = total - total_pagado

    # Edad del paciente
    pac = orden.paciente
    edad = pac.calcular_edad() if pac and pac.fecha_nacimiento else None

    editable = orden.estado not in ('CANCELADO', 'ENTREGADO')

    facturas_cfdi = FacturaCFDI.objects.none()
    if empresa:
        facturas_cfdi = (
            FacturaCFDI.objects.filter(
                Q(orden_laboratorio=orden) | Q(pago_orden__orden=orden),
                usuario_creo__empresa=empresa,
            )
            .select_related('cliente')
            .distinct()
            .order_by('-fecha_emision', '-id')
        )

    context = {
        'orden': orden,
        'paciente': pac,
        'edad': edad,
        'detalles': detalles,
        'pagos': pagos,
        'subtotal': subtotal,
        'descuento_monto': descuento_monto,
        'total': total,
        'total_pagado': total_pagado,
        'saldo': saldo,
        'editable': editable,
        'facturas_cfdi': facturas_cfdi,
    }
    return render(request, 'core/detalle_orden.html', context)


@login_required
@require_http_methods(["GET"])
def api_detalle_orden_completo(request, orden_id):
    """API JSON: Devuelve datos completos de la orden para refrescar sin recargar."""
    empresa = getattr(request.user, 'empresa', None)
    filtro = {'id': orden_id}
    if empresa:
        filtro['empresa'] = empresa
    orden = get_object_or_404(
        OrdenDeServicio.objects.select_related('paciente'),
        **filtro,
    )

    # Pre-cargar detalles + resultados en 2 queries (no N+1)
    detalles_qs = orden.detalles.select_related(
        'analito', 'perfil_lims', 'paquete_lims'
    ).all()
    analitos_con_resultado = set(
        ResultadoParametro.objects.filter(orden=orden)
        .exclude(valor='').exclude(valor__isnull=True).exclude(valor='Pendiente')
        .exclude(analito_id__isnull=True)
        .values_list('analito_id', flat=True)
        .distinct()
    )
    detalles = []
    for d in detalles_qs:
        aid = d.analito_id
        if aid:
            tiene_res = aid in analitos_con_resultado
        else:
            rt = (d.resultado or '').strip()
            tiene_res = bool(rt) and rt != 'Pendiente'
        codigo = d.analito.codigo if d.analito_id and d.analito else ''
        abrev = d.analito.abreviatura if d.analito_id and d.analito else ''
        nombre = (
            (d.descripcion_linea or '').strip()
            or (d.analito.nombre if d.analito_id and d.analito else '')
            or (d.perfil_lims.nombre if d.perfil_lims_id and d.perfil_lims else '')
            or (d.paquete_lims.nombre if d.paquete_lims_id and d.paquete_lims else '')
            or '—'
        )
        token = None
        if d.analito_id:
            token = f'analito:{d.analito_id}'
        elif d.perfil_lims_id:
            token = f'perfil:{d.perfil_lims_id}'
        elif d.paquete_lims_id:
            token = f'paquete:{d.paquete_lims_id}'
        detalles.append({
            'detalle_id': d.id,
            'estudio_id': token,
            'nombre': nombre,
            'codigo': codigo,
            'abreviatura': abrev,
            'precio': float(d.precio_momento),
            'tiene_resultado': tiene_res,
            'estado': d.estado_procesamiento,
        })

    pagos_qs = PagoOrden.objects.filter(orden=orden).order_by('-fecha_pago')
    total_pagado = sum(p.monto_total for p in pagos_qs) if pagos_qs.exists() else float(orden.anticipo or 0)
    pagos_list = []
    for p in pagos_qs:
        pagos_list.append({
            'id': p.id,
            'efectivo': float(p.monto_efectivo),
            'tarjeta': float(p.monto_tarjeta),
            'transferencia': float(p.monto_transferencia),
            'total': float(p.monto_total),
            'referencia': p.referencia_pago or '',
            'fecha': p.fecha_pago.strftime('%d/%m/%Y %H:%M') if p.fecha_pago else '',
            'usuario': str(p.usuario_registro) if p.usuario_registro else '',
        })

    return JsonResponse({
        'ok': True,
        'orden': {
            'id': orden.id,
            'folio': orden.folio_orden or f'ORD-{orden.id}',
            'estado': orden.estado,
            'total': float(orden.total or 0),
            'anticipo': float(total_pagado),
            'saldo': float((orden.total or 0) - Decimal(str(total_pagado))),
            'descuento_monto': float(orden.descuento_monto or 0),
            'editable': orden.estado not in ('CANCELADO', 'ENTREGADO'),
        },
        'detalles': detalles,
        'pagos': pagos_list,
    })
