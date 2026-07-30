"""
API para Auditoría Nativa de Campos.
Registra cambios en tiempo real desde el frontend.
"""
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required


@login_required
@require_http_methods(["POST"])
def api_auditar_campo(request):
    """
    API para registrar cambios en campos críticos desde el frontend.
    
    Payload esperado:
    {
        "modelo": "DetalleOrden",
        "objeto_id": 123,
        "campo_nombre": "resultado",
        "valor_anterior": "100",
        "valor_nuevo": "110",
        "modulo": "LABORATORIO",
        "referencia_id": 456,
        "referencia_tipo": "OrdenDeServicio"
    }
    """
    # Endpoint legacy sin rutas activas: no debe convertirse en una vía para
    # fabricar AuditLog desde datos enviados por el navegador.
    return JsonResponse(
        {
            'status': 'error',
            'codigo': 'AUDITORIA_CLIENTE_DEPRECADA',
            'mensaje': 'La auditoría se genera desde el cambio persistido en servidor.',
        },
        status=410,
    )
