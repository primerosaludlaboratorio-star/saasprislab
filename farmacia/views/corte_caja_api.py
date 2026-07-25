"""
farmacia/views/corte_caja_api.py
FASE 8 — API de corte de caja unificado (Farmacia + Lab).
"""
import json
import logging
from decimal import Decimal, InvalidOperation
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.conf import settings

from core.utils.sucursal_helpers import get_request_sucursal

logger = logging.getLogger('farmacia.corte_caja_api')


def _parse_money(raw_value, field_name, *, allow_zero=True):
    """Valida importes de caja antes de permitir una mutacion financiera."""
    try:
        value = Decimal(str(raw_value))
    except (InvalidOperation, TypeError, ValueError):
        raise ValueError(f'{field_name} debe ser un monto válido.')
    if not value.is_finite():
        raise ValueError(f'{field_name} debe ser un monto finito.')
    if value.as_tuple().exponent < -2:
        raise ValueError(f'{field_name} admite como máximo dos decimales.')
    minimum = Decimal('0.00') if allow_zero else Decimal('0.01')
    if value < minimum:
        comparator = 'mayor o igual a' if allow_zero else 'mayor a'
        raise ValueError(f'{field_name} debe ser {comparator} {minimum:.2f}.')
    return value


@login_required
@require_http_methods(['GET'])
def api_precorte_unificado(request):
    """GET /api/caja/precorte/ - lectura del turno activo, nunca cierra la caja.

    Todo usuario con empresa puede consultar la caja activa de su sucursal,
    aunque otro usuario haya abierto el turno. La función no expone costos,
    márgenes ni ganancias.
    """
    empresa = getattr(request.user, 'empresa', None)
    if not empresa:
        return JsonResponse({'ok': False, 'error': 'Sin empresa asignada.'}, status=403)

    try:
        from farmacia.services.corte_caja_unificado import calcular_precorte_unificado
        precorte = calcular_precorte_unificado(
            cajero=request.user,
            empresa=empresa,
            sucursal=get_request_sucursal(request),
        )
        return JsonResponse({'ok': True, 'precorte': precorte})
    except Exception:
        logger.exception('Error calculando precorte unificado')
        return JsonResponse(
            {'ok': False, 'error': 'No fue posible calcular el precorte.'},
            status=500,
        )


@login_required
@require_http_methods(['POST'])
def api_corte_caja_unificado(request):
    """
    POST /api/caja/corte-unificado/
    Body: { efectivo_declarado, imprimir_ticket, host_impresora }
    """
    empresa = getattr(request.user, 'empresa', None)
    if not empresa:
        return JsonResponse({'ok': False, 'error': 'Sin empresa asignada.'}, status=403)

    try:
        body = json.loads(request.body.decode('utf-8')) if request.body else {}
    except (json.JSONDecodeError, UnicodeDecodeError):
        return JsonResponse(
            {'ok': False, 'error': 'JSON inválido en el cuerpo de la petición.'},
            status=400,
        )

    if 'efectivo_declarado' not in body:
        return JsonResponse(
            {'ok': False, 'error': 'efectivo_declarado es obligatorio.'},
            status=400,
        )

    try:
        efectivo = _parse_money(body.get('efectivo_declarado'), 'efectivo_declarado')
    except ValueError as exc:
        return JsonResponse(
            {'ok': False, 'error': str(exc)},
            status=400,
        )
    imprimir = body.get('imprimir_ticket', False)
    host_imp = body.get('host_impresora', '') or getattr(settings, 'THERMAL_PRINTER_HOST', '')

    try:
        from farmacia.services.corte_caja_unificado import cerrar_turno_unificado
        corte = cerrar_turno_unificado(
            cajero=request.user,
            empresa=empresa,
            sucursal=get_request_sucursal(request),
            efectivo_declarado=efectivo,
            imprimir_ticket=imprimir,
            host_impresora=host_imp,
        )
        if corte.get('estado') == 'SIN_APERTURA':
            return JsonResponse(
                {'ok': False, 'error': 'No existe una caja activa para cerrar.'},
                status=409,
            )
        if corte.get('estado') == 'ERROR' or corte.get('status') == 'error':
            return JsonResponse(
                {'ok': False, 'error': 'No fue posible completar el corte unificado.'},
                status=500,
            )
        return JsonResponse({'ok': True, 'corte': corte})
    except Exception as exc:
        # Justificación: Boundary top-level de API para corte unificado.
        logger.exception('Error en corte de caja unificado')
        return JsonResponse(
            {'ok': False, 'error': 'No fue posible completar el corte unificado.'},
            status=500,
        )
