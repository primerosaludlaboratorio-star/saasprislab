import json
import uuid
from decimal import Decimal

from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

from core.models import OrdenDeServicio
from contabilidad.models import ClienteFacturacion, FacturaCFDI, ConceptoFactura


def autofactura_portal(request):
    """
    Portal público donde el paciente ingresa con el token UUID de su orden
    (impreso en ticket/QR) y su RFC para auto-facturarse.
    """
    ticket_id = request.GET.get('ticket', '')
    context = {'ticket_id': ticket_id}
    return render(request, 'contabilidad/public/autofactura.html', context)


@csrf_exempt
def api_generar_autofactura(request):
    """
    API pública para generar la factura desde el portal.
    Se espera POST con JSON:
    {
      'ticket': '<token UUID de OrdenDeServicio.token_acceso>',
      'rfc': 'XAXX010101000',
      'razon_social': 'PUBLICO EN GENERAL',
      'cp': '00000',
      'regimen': '616',
      'uso': 'S01'
    }
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'Método no permitido'}, status=405)

    try:
        data = json.loads(request.body)
        ticket_raw = str(data.get('ticket', '')).strip()
        rfc = data.get('rfc', '').strip().upper()
        razon_social = data.get('razon_social', '').strip().upper()
        cp = data.get('cp', '').strip()
        regimen = data.get('regimen', '').strip()
        uso = data.get('uso', '').strip()

        if not all([ticket_raw, rfc, razon_social, cp, regimen, uso]):
            return JsonResponse({'error': 'Todos los campos son obligatorios'}, status=400)

        try:
            ticket_token = uuid.UUID(ticket_raw)
        except ValueError:
            return JsonResponse({'error': 'Ticket inválido: use el token UUID del ticket/QR.'}, status=400)

        # Seguridad multi-tenant: lookup por token secreto, no por ID incremental.
        orden = get_object_or_404(
            OrdenDeServicio.objects_all.select_related('empresa'),
            token_acceso=ticket_token,
        )

        # Validar si ya está facturada para esta orden
        if FacturaCFDI.objects.filter(
            empresa=orden.empresa,
            referencia_origen=f"ORDEN_{orden.id}",
            estado__in=['TIMBRADO', 'PROCESANDO', 'FACTURANDO'],
        ).exists():
            return JsonResponse({'error': 'Este ticket ya fue facturado previamente.'}, status=400)

        cliente, created = ClienteFacturacion.objects.get_or_create(
            rfc=rfc,
            empresa=orden.empresa,
            defaults={
                'razon_social': razon_social,
                'codigo_postal': cp,
                'regimen_fiscal': regimen,
                'email': 'autofactura@sin-email.local',
            }
        )
        if not created:
            cliente.razon_social = razon_social
            cliente.codigo_postal = cp
            cliente.regimen_fiscal = regimen
            if not cliente.email:
                cliente.email = 'autofactura@sin-email.local'
            cliente.save()

        factura = FacturaCFDI.objects.create(
            empresa=orden.empresa,
            cliente=cliente,
            forma_pago='01',
            metodo_pago='PUE',
            uso_cfdi=uso,
            moneda='MXN',
            subtotal=orden.total,
            total_impuestos_trasladados=Decimal('0.00'),
            total=orden.total,
            referencia_origen=f"ORDEN_{orden.id}",
        )

        ConceptoFactura.objects.create(
            factura=factura,
            clave_prod_serv='85121800',
            descripcion=f"Servicios de Laboratorio (Ticket {orden.id})",
            cantidad=Decimal('1.00'),
            valor_unitario=orden.total,
            importe=orden.total,
        )

        return JsonResponse({'mensaje': 'Factura generada y encolada para timbrado exitosamente.', 'factura_id': factura.id})

    except json.JSONDecodeError:
        return JsonResponse({'error': 'JSON inválido'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
