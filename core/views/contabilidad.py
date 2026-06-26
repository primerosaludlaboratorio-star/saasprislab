"""
Módulo de Contabilidad - PRISLAB
Gestión de catálogo de cuentas, pólizas contables y movimientos.
"""
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.db import transaction
from django.db.models import Q, Sum, Count
from django.views.decorators.http import require_http_methods
from django.core.paginator import Paginator
from django.utils import timezone
from decimal import Decimal
from datetime import date, datetime

from core.models import (
    Empresa, Sucursal, Usuario
)
from core.utils.trazabilidad import registrar_trazabilidad, serializar_modelo


@login_required
def dashboard_contabilidad(request):
    """
    Dashboard de Contabilidad — muestra datos financieros reales del período actual
    mientras los modelos de pólizas/cuentas contables están en fase de desarrollo.
    """
    empresa = getattr(request.user, 'empresa', None)
    if not empresa:
        messages.error(request, 'Usuario no tiene empresa asignada.')
        return redirect('home')

    from datetime import timedelta

    hoy = timezone.localtime(timezone.now()).date()
    mes_inicio = hoy.replace(day=1)

    # ── Ingresos del mes ────────────────────────────────────────────────────────
    ingresos_mes = Decimal('0')
    ventas_count = 0
    try:
        from core.models import Venta
        # FIX conteo falso: solo ventas COMPLETADAS cuentan como ingreso del mes.
        # Las CANCELADA conservan su total tras cancelar_venta y antes inflaban ingresos.
        agg = Venta.objects.filter(
            empresa=empresa,
            fecha__date__gte=mes_inicio,
            estado='COMPLETADA',
        ).aggregate(total=Sum('total'), count=Count('id'))
        ingresos_mes = agg['total'] or Decimal('0')
        ventas_count = agg['count'] or 0
    except Exception:
        pass

    # ── Gastos del mes ──────────────────────────────────────────────────────────
    gastos_mes = Decimal('0')
    gastos_count = 0
    try:
        from core.models import Gasto
        agg_g = Gasto.objects.filter(
            empresa=empresa,
            fecha__date__gte=mes_inicio,
        ).aggregate(total=Sum('monto'), count=Count('id'))
        gastos_mes = agg_g['total'] or Decimal('0')
        gastos_count = agg_g['count'] or 0
    except Exception:
        pass

    utilidad_mes = ingresos_mes - gastos_mes

    # ── Cortes de caja farmacia del mes (modelo real: CierreTurnoFarmacia) ─────
    cortes_recientes = []
    try:
        from farmacia.models import CierreTurnoFarmacia
        inicio_dt = timezone.make_aware(datetime.combine(mes_inicio, datetime.min.time()))
        cortes_recientes = list(
            CierreTurnoFarmacia.objects.filter(
                empresa=empresa,
                fecha_cierre__gte=inicio_dt,
            ).order_by('-fecha_cierre')[:10]
        )
    except Exception:
        pass

    # ── CFDI pendientes ─────────────────────────────────────────────────────────
    cfdi_pendientes = 0
    try:
        from core.models import FacturaSAT
        cfdi_pendientes = FacturaSAT.objects.filter(
            empresa=empresa, estatus=FacturaSAT.ESTATUS_BORRADOR
        ).count()
    except Exception:
        pass

    return render(request, 'core/contabilidad/dashboard.html', {
        'empresa': empresa,
        'ingresos_mes': ingresos_mes,
        'gastos_mes': gastos_mes,
        'utilidad_mes': utilidad_mes,
        'ventas_count': ventas_count,
        'gastos_count': gastos_count,
        'cortes_recientes': cortes_recientes,
        'cfdi_pendientes': cfdi_pendientes,
        'mes_nombre': mes_inicio.strftime('%B %Y'),
        # Campos legacy (en cero hasta que los modelos contables sean migrados)
        'total_cuentas': 0,
        'total_polizas': 0,
        'polizas_abiertas': 0,
        'polizas_autorizadas': 0,
        'polizas_recientes': [],
        'movimientos_mes': {'total_debe': ingresos_mes, 'total_haber': gastos_mes},
    })


@login_required
def catalogo_cuentas(request):
    """Catálogo de cuentas — redirige a reportes financieros mientras los modelos contables se migran."""
    messages.info(request, 'El catálogo de cuentas contables está en etapa de implementación. Usa los reportes financieros disponibles.')
    return redirect('reporte_ingresos_egresos')


@login_required
@require_http_methods(["GET", "POST"])
def crear_cuenta(request):
    """Crear cuenta contable — redirige a dashboard mientras se implementa."""
    messages.info(request, 'La gestión de cuentas contables estará disponible próximamente.')
    return redirect('dashboard_contabilidad')


@login_required
def lista_polizas(request):
    """Lista de pólizas — redirige a cortes de caja como sustituto funcional."""
    messages.info(request, 'Las pólizas contables están en desarrollo. Consulta los Cortes de Caja como referencia de movimientos.')
    return redirect('corte_dia')


@login_required
@require_http_methods(["GET", "POST"])
def crear_poliza(request):
    """Crear póliza — redirige al registro de gastos."""
    messages.info(request, 'El registro de pólizas contables estará disponible próximamente. Usa Registro de Gastos por ahora.')
    return redirect('registro_gasto')


@login_required
def ver_poliza(request, poliza_id):
    """Ver póliza — redirige al reporte fiscal."""
    messages.info(request, 'El detalle de pólizas contables estará disponible próximamente.')
    return redirect('reporte_fiscal')


@login_required
@require_http_methods(["POST"])
def autorizar_poliza(request, poliza_id):
    """Autorizar una póliza contable."""
    # NOTA: pendiente de migracion - Modelo PolizaContable no migrado aún
    messages.error(request, 'La autorización de pólizas está en desarrollo.')
    return redirect('dashboard_contabilidad')


@login_required
@require_http_methods(["GET"])
def api_cuentas(request):
    """API para buscar cuentas contables (AJAX)."""
    # NOTA: pendiente de migracion - Modelo CatalogoCuenta no migrado aún
    return JsonResponse({
        'cuentas': [],
        'error': 'El módulo de contabilidad está en desarrollo.'
    })
