"""
PRISLAB - Modulo de Cuentas por Cobrar y Convenios
====================================================
Gestion de creditos a empresas/aseguradoras con seguimiento
de pagos, vencimientos y conciliacion.

Blindaje H-004: Aislamiento multi-tenant estricto y roles de acceso.
Todas las consultas filtran por empresa=request.user.empresa.
"""

import json
import logging
from datetime import timedelta
from decimal import Decimal

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db.models import Sum, Q, Count
from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.utils import timezone
from django.views.decorators.http import require_POST

from core.decorators import role_required
from core.models import (
    CuentaPorCobrar, PagoCuentaPorCobrar, Convenio,
    NotaCredito, OrdenDeServicio,
)

logger = logging.getLogger('core')


def _empresa(request):
    """Retorna la empresa del usuario con validación de pertenencia."""
    empresa = getattr(request.user, 'empresa', None)
    if empresa is None:
        raise PermissionDenied("Usuario no tiene empresa asignada.")
    return empresa


# =============================================================================
# DASHBOARD DE CUENTAS POR COBRAR
# =============================================================================

@login_required
@role_required('DIRECTOR', 'ADMIN', 'GERENTE', 'FINANZAS')
def cuentas_por_cobrar_dashboard(request):
    """Dashboard principal de cuentas por cobrar."""
    empresa = _empresa(request)
    hoy = timezone.localdate()

    cuentas = CuentaPorCobrar.objects.filter(empresa=empresa)

    # Metricas
    pendientes = cuentas.filter(estado='PENDIENTE')
    vencidas = pendientes.filter(fecha_vencimiento__lt=hoy)
    parciales = cuentas.filter(estado='PARCIAL')

    total_pendiente = pendientes.aggregate(s=Sum('saldo_pendiente'))['s'] or 0
    total_vencido = vencidas.aggregate(s=Sum('saldo_pendiente'))['s'] or 0
    total_parcial = parciales.aggregate(s=Sum('saldo_pendiente'))['s'] or 0

    # Marcar vencidas automaticamente
    vencidas.update(estado='VENCIDO')

    # Listado con filtros
    filtro = request.GET.get('estado', '')
    filtro_convenio = request.GET.get('convenio', '')

    qs = cuentas.select_related('convenio', 'orden', 'creado_por')
    if filtro:
        qs = qs.filter(estado=filtro)
    if filtro_convenio:
        qs = qs.filter(convenio_id=filtro_convenio)

    convenios = Convenio.objects.filter(empresa=empresa, activo=True)

    context = {
        'cuentas': qs[:50],
        'total_pendiente': total_pendiente,
        'total_vencido': total_vencido,
        'total_parcial': total_parcial,
        'count_pendientes': pendientes.count(),
        'count_vencidas': vencidas.count(),
        'convenios': convenios,
        'filtro': filtro,
        'filtro_convenio': filtro_convenio,
    }
    return render(request, 'core/cuentas_por_cobrar.html', context)


# ======================================================================
# API: REGISTRAR PAGO A CxC
# ======================================================================

@login_required
@require_POST
def api_registrar_pago_cxc(request):
    """Registra un pago (parcial o total) a una cuenta por cobrar."""
    try:
        empresa = getattr(request.user, 'empresa', None)
        if not empresa:
            return JsonResponse({'status': 'error', 'mensaje': 'Usuario sin empresa asignada'}, status=403)
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({'status': 'error', 'mensaje': 'JSON inválido'}, status=400)
        cuenta_id = data.get('cuenta_id')
        monto = Decimal(str(data.get('monto', 0)))
        metodo = data.get('metodo_pago', 'TRANSFERENCIA')
        referencia = data.get('referencia', '')
        notas = data.get('notas', '')

        cuenta = CuentaPorCobrar.objects.get(
            id=cuenta_id, empresa=empresa
        )

        if monto <= 0:
            return JsonResponse({'status': 'error', 'mensaje': 'Monto debe ser mayor a 0'}, status=400)
        if monto > cuenta.saldo_pendiente:
            return JsonResponse({'status': 'error', 'mensaje': 'Monto excede el saldo pendiente'}, status=400)

        from django.db import transaction as _dbt
        with _dbt.atomic():
            PagoCuentaPorCobrar.objects.create(
                cuenta=cuenta,
                monto=monto,
                metodo_pago=metodo,
                referencia=referencia,
                notas=notas,
                registrado_por=request.user,
            )
            cuenta.monto_pagado += monto
            cuenta.saldo_pendiente -= monto
            if cuenta.saldo_pendiente <= 0:
                cuenta.estado = 'COBRADO'
                cuenta.fecha_cobro = timezone.localdate()
            else:
                cuenta.estado = 'PARCIAL'
            cuenta.save()

        # AuditLog
        try:
            from core.services.audit_service import registrar_auditoria
            registrar_auditoria(
                accion='UPDATE',
                modelo='CuentaPorCobrar',
                objeto_id=str(cuenta.id),
                datos_nuevos={'pago': str(monto), 'estado': cuenta.estado},
                request=request,
            )
        except Exception:
            pass

        return JsonResponse({
            'status': 'success',
            'mensaje': f'Pago de ${monto} registrado. Saldo: ${cuenta.saldo_pendiente}',
            'saldo_pendiente': str(cuenta.saldo_pendiente),
            'estado': cuenta.estado,
        })

    except CuentaPorCobrar.DoesNotExist:
        return JsonResponse({'status': 'error', 'mensaje': 'Cuenta no encontrada'}, status=404)
    except Exception as e:
        return JsonResponse({'status': 'error', 'mensaje': str(e)}, status=500)


# ======================================================================
# API: CREAR CUENTA POR COBRAR (desde una orden)
# ======================================================================

@login_required
@require_POST
def api_crear_cxc(request):
    """Crea una cuenta por cobrar para una orden con pago a credito."""
    try:
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({'status': 'error', 'mensaje': 'JSON inválido'}, status=400)
        orden_id = data.get('orden_id')
        convenio_id = data.get('convenio_id')

        empresa = getattr(request.user, 'empresa', None)
        if not empresa:
            return JsonResponse({'status': 'error', 'mensaje': 'Usuario sin empresa asignada'}, status=403)
        orden = get_object_or_404(OrdenDeServicio, id=orden_id, empresa=empresa)
        convenio = get_object_or_404(Convenio, id=convenio_id, empresa=empresa, activo=True)

        # Generar folio
        count = CuentaPorCobrar.objects.filter(empresa=empresa).count() + 1
        folio = f'CXC-{timezone.now().year}-{count:05d}'

        # Calcular vencimiento
        fecha_venc = timezone.localdate() + timedelta(days=convenio.dias_credito)

        # Concepto — compatible con LIMS puro y legacy.
        from core.utils.detalle_orden import get_detalle_nombre
        detalles_qs = orden.detalles.select_related('analito', 'perfil_lims', 'paquete_lims').all()[:5]
        estudios = ', '.join(get_detalle_nombre(d) for d in detalles_qs)
        concepto = f'Orden {orden.folio_orden} - {orden.paciente.nombre_completo} - {estudios}'

        from django.db import transaction as _dbt
        with _dbt.atomic():
            cxc = CuentaPorCobrar.objects.create(
                empresa=empresa,
                convenio=convenio,
                orden=orden,
                folio=folio,
                concepto=concepto[:500],
                monto_total=orden.total,
                saldo_pendiente=orden.total,
                fecha_vencimiento=fecha_venc,
                estado='PENDIENTE',
                creado_por=request.user,
            )
            # Marcar orden como pagada a crédito
            orden.estado_pago = 'PAGADO'
            orden.estado = 'PAGADO'
            orden.save(update_fields=['estado_pago', 'estado'])

        return JsonResponse({
            'status': 'success',
            'mensaje': f'Cuenta por cobrar {folio} creada. Vence: {fecha_venc}',
            'cxc_id': cxc.id,
            'folio': folio,
        })

    except OrdenDeServicio.DoesNotExist:
        return JsonResponse({'status': 'error', 'mensaje': 'Orden no encontrada'}, status=404)
    except Convenio.DoesNotExist:
        return JsonResponse({'status': 'error', 'mensaje': 'Convenio no encontrado o inactivo'}, status=404)
    except Exception as e:
        return JsonResponse({'status': 'error', 'mensaje': str(e)}, status=500)


# ======================================================================
# GESTION DE CONVENIOS
# ======================================================================

@login_required
def convenios_lista(request):
    """Lista de convenios activos con metricas."""
    empresa = getattr(request.user, 'empresa', None)
    if not empresa:
        from django.contrib import messages
        messages.error(request, 'Usuario no tiene empresa asignada.')
        return redirect('home')
    convenios = Convenio.objects.filter(empresa=empresa).annotate(
        cuentas_pendientes=Count('cuentas', filter=Q(cuentas__estado__in=['PENDIENTE', 'VENCIDO'])),
        saldo_total=Sum('cuentas__saldo_pendiente', filter=Q(cuentas__estado__in=['PENDIENTE', 'PARCIAL', 'VENCIDO'])),
    )

    return render(request, 'core/convenios_lista.html', {
        'convenios': convenios,
    })


@login_required
@require_POST
def api_crear_convenio(request):
    """Crea un nuevo convenio."""
    try:
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({'status': 'error', 'mensaje': 'JSON inválido'}, status=400)
        empresa = getattr(request.user, 'empresa', None)
        if not empresa:
            return JsonResponse({'status': 'error', 'mensaje': 'Usuario sin empresa asignada'}, status=403)
        convenio = Convenio.objects.create(
            empresa=empresa,
            nombre=data.get('nombre', ''),
            rfc=data.get('rfc', ''),
            contacto=data.get('contacto', ''),
            telefono=data.get('telefono', ''),
            email=data.get('email', ''),
            tipo=data.get('tipo', 'EMPRESA'),
            dias_credito=int(data.get('dias_credito', 15)),
            descuento_porcentaje=Decimal(str(data.get('descuento', 0))),
            limite_credito=Decimal(str(data.get('limite_credito', 0))),
        )
        return JsonResponse({
            'status': 'success',
            'mensaje': f'Convenio "{convenio.nombre}" creado',
            'convenio_id': convenio.id,
        })
    except Exception as e:
        return JsonResponse({'status': 'error', 'mensaje': str(e)}, status=500)


# ======================================================================
# REPORTES FISCALES BASICO
# ======================================================================

@login_required
def reporte_fiscal_mensual(request):
    """Reporte fiscal mensual: ingresos, egresos, CxC, notas de credito."""
    empresa = getattr(request.user, 'empresa', None)
    if not empresa:
        from django.contrib import messages
        messages.error(request, 'Usuario no tiene empresa asignada.')
        return redirect('home')
    hoy = timezone.localdate()
    mes = int(request.GET.get('mes', hoy.month))
    anio = int(request.GET.get('anio', hoy.year))

    from core.models import Venta, GastoCaja
    from datetime import date

    inicio_mes = date(anio, mes, 1)
    if mes == 12:
        fin_mes = date(anio + 1, 1, 1)
    else:
        fin_mes = date(anio, mes + 1, 1)

    # Ingresos por ventas
    ventas = Venta.objects.filter(
        empresa=empresa, fecha__date__gte=inicio_mes, fecha__date__lt=fin_mes,
        estado='COMPLETADA'
    )
    total_ventas = ventas.aggregate(s=Sum('total'))['s'] or 0
    count_ventas = ventas.count()

    # Ingresos por ordenes de laboratorio
    ordenes = OrdenDeServicio.objects.filter(
        empresa=empresa, fecha_creacion__date__gte=inicio_mes, fecha_creacion__date__lt=fin_mes,
        estado_pago='PAGADO',
    )
    total_ordenes = ordenes.aggregate(s=Sum('total'))['s'] or 0
    count_ordenes = ordenes.count()

    # Gastos
    gastos = GastoCaja.objects.filter(
        empresa=empresa, fecha__date__gte=inicio_mes, fecha__date__lt=fin_mes,
    )
    total_gastos = gastos.aggregate(s=Sum('monto'))['s'] or 0

    # CxC emitidas en el mes
    cxc = CuentaPorCobrar.objects.filter(
        empresa=empresa, fecha_emision__gte=inicio_mes, fecha_emision__lt=fin_mes,
    )
    total_cxc = cxc.aggregate(s=Sum('monto_total'))['s'] or 0

    # Notas de credito
    nc = NotaCredito.objects.filter(
        empresa=empresa, fecha_emision__date__gte=inicio_mes, fecha_emision__date__lt=fin_mes,
    )
    total_nc = nc.aggregate(s=Sum('monto'))['s'] or 0

    context = {
        'mes': mes,
        'anio': anio,
        'total_ventas': total_ventas,
        'count_ventas': count_ventas,
        'total_ordenes': total_ordenes,
        'count_ordenes': count_ordenes,
        'total_gastos': total_gastos,
        'total_cxc': total_cxc,
        'total_notas_credito': total_nc,
        'ingreso_bruto': total_ventas + total_ordenes,
        'ingreso_neto': total_ventas + total_ordenes - total_gastos - total_nc,
    }
    return render(request, 'core/reporte_fiscal.html', context)
