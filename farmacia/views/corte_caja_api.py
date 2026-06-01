"""
farmacia/views/corte_caja_api.py
FASE 8 — API de corte de caja unificado (Farmacia + Lab).
"""
import json
from decimal import Decimal
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.conf import settings


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
        body = json.loads(request.body) if request.body else {}
    except json.JSONDecodeError:
        body = {}

    efectivo = Decimal(str(body.get('efectivo_declarado', '0')))
    imprimir = body.get('imprimir_ticket', False)
    host_imp = body.get('host_impresora', '') or getattr(settings, 'THERMAL_PRINTER_HOST', '')

    try:
        from farmacia.services.corte_caja_unificado import cerrar_turno_unificado
        corte = cerrar_turno_unificado(
            cajero=request.user,
            empresa=empresa,
            sucursal=getattr(request.user, 'sucursal', None),
            efectivo_declarado=efectivo,
            imprimir_ticket=imprimir,
            host_impresora=host_imp,
        )
        return JsonResponse({'ok': True, 'corte': corte})
    except Exception as exc:
        return JsonResponse({'ok': False, 'error': str(exc)}, status=500)
