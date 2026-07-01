"""
API Views — Panel Ejecutivo (Dashboard)
Endpoints para acceder a KPIs y métricas operacionales.
"""

from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.utils import timezone

from core.services.kpi_service import KPIService
from core.utils.sucursal_helpers import get_user_primary_sucursal
from core.rbac.permissions import check_permission
from core.tenant import get_current_empresa, get_current_sucursal, tenant_required


@login_required
@tenant_required
@require_http_methods(["GET"])
def dashboard_hoy(request):
    """
    GET /api/dashboard/hoy

    Retorna dashboard con KPIs de hoy para la empresa/sucursal actual.

    Permisos:
        - Requiere "finanzas:ver_reportes" (ADMIN, DIRECTOR, GERENTE)

    Respuesta (200):
        {
            "empresa": "PRISLAB S.A.",
            "sucursal": "Matriz Principal",
            "fecha": "2026-06-29",
            "ingresos_hoy": 5250.00,
            "ingresos_por_modulo": { "lab": 3000, "farmacia": 2250, "consultorio": 0 },
            "ordenes_capturadas": 12,
            "ordenes_completadas": 10,
            "tasa_cumplimiento": 83.33,
            "caja": { "ingresos": 5250, "egresos": 500, "saldo": 4750 },
            "cuentas_por_cobrar": 1200.00,
            "pacientes_nuevos": 3,
            "pacientes_atendidos": 15,
            "cambios_registrados": 42
        }
    """
    try:
        check_permission(request.user, "finanzas:ver_reportes")
    except Exception as e:
        return JsonResponse({
            'error': str(e),
            'status': 'forbidden'
        }, status=403)

    empresa = get_current_empresa() or getattr(request.user, 'empresa', None)
    sucursal = get_current_sucursal() or getattr(request, 'sucursal_actual', None)

    if not empresa:
        return JsonResponse({
            'error': 'No se pudo determinar la empresa actual',
            'status': 'error'
        }, status=400)

    kpi_service = KPIService(empresa, sucursal)
    dashboard = kpi_service.dashboard_hoy()

    return JsonResponse(dashboard, status=200)


@login_required
@tenant_required
@require_http_methods(["GET"])
def dashboard_comparativo(request):
    """
    GET /api/dashboard/comparativo?dias=30&metrica=ingresos

    Retorna histórico de KPIs para comparativa (últimos N días).

    Query Params:
        - dias: Número de días a retornar (default: 30)
        - metrica: Métrica específica (ingresos, ordenes, caja) o vacío = todas

    Respuesta (200):
        {
            "fecha_inicio": "2026-05-30",
            "fecha_fin": "2026-06-29",
            "snapshots": [
                { "fecha": "2026-06-29", "ingresos": 5250, "ordenes_completadas": 10, ... },
                ...
            ]
        }
    """
    try:
        check_permission(request.user, "finanzas:ver_reportes")
    except Exception as e:
        return JsonResponse({
            'error': str(e),
            'status': 'forbidden'
        }, status=403)

    empresa = get_current_empresa() or getattr(request.user, 'empresa', None)
    sucursal = get_current_sucursal() or getattr(request, 'sucursal_actual', None)

    if not empresa:
        return JsonResponse({
            'error': 'No se pudo determinar la empresa actual',
            'status': 'error'
        }, status=400)

    dias = int(request.GET.get('dias', 30))
    desde = timezone.now().date() - timezone.timedelta(days=dias)

    # Obtener snapshots
    from core.models import KPI_Snapshot
    snapshots = KPI_Snapshot.objects.filter(
        empresa=empresa,
        fecha__gte=desde
    )

    if sucursal:
        snapshots = snapshots.filter(sucursal=sucursal)

    snapshots = snapshots.order_by('fecha').values(
        'fecha', 'ingresos_total', 'ordenes_capturadas', 'ordenes_completadas',
        'tasa_cumplimiento', 'saldo_caja', 'cuentas_por_cobrar', 'pacientes_atendidos'
    )

    return JsonResponse({
        'empresa': empresa.nombre,
        'sucursal': sucursal.nombre if sucursal else 'Global',
        'fecha_inicio': desde.isoformat(),
        'fecha_fin': timezone.now().date().isoformat(),
        'snapshots': list(snapshots)
    }, status=200)


@login_required
@tenant_required
@require_http_methods(["POST"])
def generar_snapshot(request):
    """
    POST /api/dashboard/snapshot/generar

    Genera snapshot inmediato de KPIs para hoy.
    Requiere "finanzas:exportar" (ADMIN, DIRECTOR).

    Respuesta (201):
        {
            "success": true,
            "snapshot": { ... }
        }
    """
    try:
        check_permission(request.user, "finanzas:exportar")
    except Exception as e:
        return JsonResponse({
            'error': str(e),
            'status': 'forbidden'
        }, status=403)

    empresa = get_current_empresa() or getattr(request.user, 'empresa', None)
    sucursal = get_current_sucursal() or getattr(request, 'sucursal_actual', None)

    if not empresa:
        return JsonResponse({
            'error': 'No se pudo determinar la empresa actual',
            'status': 'error'
        }, status=400)

    kpi_service = KPIService(empresa, sucursal)
    snapshot = kpi_service.generar_snapshot_hoy()

    return JsonResponse({
        'success': True,
        'snapshot': {
            'fecha': snapshot.fecha.isoformat(),
            'ingresos_total': float(snapshot.ingresos_total),
            'ordenes_capturadas': snapshot.ordenes_capturadas,
            'ordenes_completadas': snapshot.ordenes_completadas,
            'tasa_cumplimiento': float(snapshot.tasa_cumplimiento),
            'saldo_caja': float(snapshot.saldo_caja),
            'cambios_registrados': snapshot.cambios_registrados,
        }
    }, status=201)
