"""
Módulo de Nómina — PRISLAB v5
Gestión de períodos, recibos individuales y reportes de nómina.
"""
import json
import logging
from decimal import Decimal, InvalidOperation
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from django.db.models import Sum, Count
from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.views.decorators.http import require_POST
from django.core.paginator import Paginator

from core.models import Empresa, Empleado, PeriodoNomina, ReciboNomina
from core.decorators import role_required

logger = logging.getLogger('core')


def _empresa(request):
    return getattr(request.user, 'empresa', None)


@login_required
@role_required('DIRECTOR', 'ADMIN', 'GERENTE')
def dashboard_nomina(request):
    """Dashboard principal del módulo de nómina."""
    empresa = _empresa(request)
    periodos = PeriodoNomina.objects.filter(empresa=empresa).order_by('-fecha_inicio')[:12]

    ultimo = periodos.first()
    estadisticas = {}
    if ultimo:
        recibos = ReciboNomina.objects.filter(periodo=ultimo)
        estadisticas = recibos.aggregate(
            total_percepciones=Sum('total_percepciones'),
            total_deducciones=Sum('total_deducciones'),
            total_neto=Sum('neto_pagar'),
            num_empleados=Count('id'),
        )

    return render(request, 'core/nomina/dashboard.html', {
        'periodos':     periodos,
        'ultimo':       ultimo,
        'estadisticas': estadisticas,
    })


@login_required
@role_required('DIRECTOR', 'ADMIN', 'GERENTE')
def lista_periodos(request):
    """Listado de todos los períodos de nómina."""
    empresa = _empresa(request)
    qs = PeriodoNomina.objects.filter(empresa=empresa).order_by('-fecha_inicio')
    paginator = Paginator(qs, 15)
    return render(request, 'core/nomina/lista_periodos.html', {
        'periodos': paginator.get_page(request.GET.get('page')),
    })


@login_required
@role_required('DIRECTOR', 'ADMIN', 'GERENTE')
def crear_periodo(request):
    """Crear un nuevo período de nómina."""
    empresa = _empresa(request)
    if request.method == 'POST':
        try:
            with transaction.atomic():
                periodo = PeriodoNomina.objects.create(
                    empresa=empresa,
                    nombre=request.POST['nombre'],
                    frecuencia=request.POST.get('frecuencia', 'QUINCENAL'),
                    fecha_inicio=request.POST['fecha_inicio'],
                    fecha_fin=request.POST['fecha_fin'],
                    fecha_pago=request.POST.get('fecha_pago') or None,
                    observaciones=request.POST.get('observaciones', ''),
                    creado_por=request.user,
                )
                # Auto-crear recibos para todos los empleados activos
                if request.POST.get('auto_empleados') == '1':
                    empleados = Empleado.objects.filter(empresa=empresa, activo=True)
                    recibos = [
                        ReciboNomina(periodo=periodo, empleado=emp, empresa=empresa)
                        for emp in empleados
                    ]
                    ReciboNomina.objects.bulk_create(recibos)
                    messages.success(request, f'Período creado con {len(recibos)} recibos generados.')
                else:
                    messages.success(request, 'Período de nómina creado correctamente.')
                return redirect('nomina_detalle_periodo', pk=periodo.pk)
        except Exception as exc:
            logger.error("Error creando período de nómina: %s", exc)
            messages.error(request, f'Error al crear período: {exc}')

    empleados_count = Empleado.objects.filter(empresa=empresa, activo=True).count()
    return render(request, 'core/nomina/crear_periodo.html', {
        'empleados_count': empleados_count,
    })


@login_required
@role_required('DIRECTOR', 'ADMIN', 'GERENTE')
def detalle_periodo(request, pk):
    """Detalle de un período con listado de recibos."""
    empresa = _empresa(request)
    periodo = get_object_or_404(PeriodoNomina, pk=pk, empresa=empresa)
    recibos = ReciboNomina.objects.filter(periodo=periodo).select_related('empleado__usuario')

    resumen = recibos.aggregate(
        total_percepciones=Sum('total_percepciones'),
        total_deducciones=Sum('total_deducciones'),
        total_neto=Sum('neto_pagar'),
        pagados=Count('id', filter=__import__('django.db.models', fromlist=['Q']).Q(pagado=True)),
    )

    return render(request, 'core/nomina/detalle_periodo.html', {
        'periodo': periodo,
        'recibos': recibos,
        'resumen': resumen,
    })


@login_required
@role_required('DIRECTOR', 'ADMIN', 'GERENTE')
def editar_recibo(request, pk):
    """Editar un recibo de nómina individual."""
    empresa = _empresa(request)
    recibo = get_object_or_404(ReciboNomina, pk=pk, empresa=empresa)

    if recibo.periodo.estado == 'PAGADO':
        messages.error(request, 'No se puede editar un recibo de un período ya pagado.')
        return redirect('nomina_detalle_periodo', pk=recibo.periodo.pk)

    if request.method == 'POST':
        try:
            campos_decimal = [
                'sueldo_base', 'horas_extra', 'importe_he', 'bonificacion',
                'percepciones_extras', 'imss', 'isr', 'infonavit',
                'prestamo', 'otras_deducciones',
            ]
            for campo in campos_decimal:
                valor = request.POST.get(campo, '0').replace(',', '').strip()
                try:
                    setattr(recibo, campo, Decimal(valor))
                except InvalidOperation:
                    setattr(recibo, campo, Decimal('0'))

            recibo.observaciones = request.POST.get('observaciones', '')
            recibo.save()  # calcular_totales() se llama en save()
            messages.success(request, 'Recibo actualizado correctamente.')
            return redirect('nomina_detalle_periodo', pk=recibo.periodo.pk)
        except Exception as exc:
            logger.error("Error editando recibo %s: %s", pk, exc)
            messages.error(request, f'Error: {exc}')

    return render(request, 'core/nomina/editar_recibo.html', {
        'recibo': recibo,
    })


@login_required
@role_required('DIRECTOR', 'ADMIN', 'GERENTE')
@require_POST
def marcar_periodo_pagado(request, pk):
    """Cambia el estado del período a PAGADO y marca todos los recibos."""
    empresa = _empresa(request)
    periodo = get_object_or_404(PeriodoNomina, pk=pk, empresa=empresa)
    if periodo.estado == 'PAGADO':
        messages.info(request, 'El período ya estaba marcado como pagado.')
    else:
        from django.utils import timezone
        with transaction.atomic():
            periodo.estado = 'PAGADO'
            periodo.fecha_pago = periodo.fecha_pago or timezone.now().date()
            periodo.save()
            ReciboNomina.objects.filter(periodo=periodo, pagado=False).update(
                pagado=True,
                fecha_pago=periodo.fecha_pago,
                metodo_pago=request.POST.get('metodo_pago', 'TRANSFERENCIA'),
            )
        messages.success(request, f'Período "{periodo.nombre}" marcado como PAGADO.')
    return redirect('nomina_detalle_periodo', pk=pk)


# ── Alias para rutas legacy ────────────────────────────────────────────────────
def ver_periodo(request, periodo_id):
    return detalle_periodo(request, pk=periodo_id)


def ver_nomina(request, nomina_id):
    return editar_recibo(request, pk=nomina_id)


def cerrar_periodo(request, periodo_id):
    return marcar_periodo_pagado(request, pk=periodo_id)


# ── Funciones nuevas ───────────────────────────────────────────────────────────
@login_required
@role_required('DIRECTOR', 'ADMIN', 'GERENTE')
@require_POST
def calcular_nomina(request, periodo_id):
    """Recalcula todos los recibos del período aplicando los totales guardados."""
    empresa = _empresa(request)
    periodo = get_object_or_404(PeriodoNomina, pk=periodo_id, empresa=empresa)

    if periodo.estado == 'PAGADO':
        messages.error(request, 'El período ya está pagado; no se puede recalcular.')
        return redirect('nomina_detalle_periodo', pk=periodo_id)

    try:
        recibos = ReciboNomina.objects.filter(periodo=periodo)
        recalculados = 0
        with transaction.atomic():
            for recibo in recibos:
                recibo.save()  # calcular_totales() se llama en save()
                recalculados += 1
        messages.success(request, f'{recalculados} recibos recalculados correctamente.')
    except Exception as exc:
        logger.error("Error calculando nómina %s: %s", periodo_id, exc)
        messages.error(request, f'Error al recalcular: {exc}')

    return redirect('nomina_detalle_periodo', pk=periodo_id)


@login_required
@role_required('DIRECTOR', 'ADMIN', 'GERENTE')
@require_POST
def autorizar_nomina(request, nomina_id):
    """Autoriza (marca como pagado) un recibo individual de nómina."""
    empresa = _empresa(request)
    recibo = get_object_or_404(ReciboNomina, pk=nomina_id, empresa=empresa)

    if recibo.pagado:
        messages.info(request, 'El recibo ya estaba marcado como pagado.')
    else:
        from django.utils import timezone as tz
        recibo.pagado = True
        recibo.fecha_pago = tz.now().date()
        recibo.metodo_pago = request.POST.get('metodo_pago', 'TRANSFERENCIA')
        recibo.save()
        messages.success(request, f'Recibo de {recibo.empleado.usuario.get_full_name()} autorizado.')

    return redirect('nomina_detalle_periodo', pk=recibo.periodo_id)


@login_required
@role_required('DIRECTOR', 'ADMIN', 'GERENTE')
def api_resumen_nomina(request):
    """API para gráficas del dashboard de nómina."""
    empresa = _empresa(request)
    periodos = PeriodoNomina.objects.filter(empresa=empresa).order_by('-fecha_inicio')[:6]
    data = []
    for p in reversed(list(periodos)):
        agg = ReciboNomina.objects.filter(periodo=p).aggregate(
            neto=Sum('neto_pagar'),
            percepciones=Sum('total_percepciones'),
            deducciones=Sum('total_deducciones'),
        )
        data.append({
            'nombre': p.nombre,
            'neto': float(agg['neto'] or 0),
            'percepciones': float(agg['percepciones'] or 0),
            'deducciones': float(agg['deducciones'] or 0),
        })
    return JsonResponse({'ok': True, 'data': data})
