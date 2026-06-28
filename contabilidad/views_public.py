import json
from decimal import Decimal
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from core.models import OrdenDeServicio, Empresa
from contabilidad.models import ClienteFacturacion, FacturaCFDI, ConceptoFactura
# APIFacturama removed for now

def autofactura_portal(request):
    """
    Portal público donde el paciente ingresa con el folio de su ticket (orden_id o uuid)
    y su RFC para auto-facturarse.
    """
    ticket_id = request.GET.get('ticket', '')
    context = {'ticket_id': ticket_id}
    return render(request, 'contabilidad/public/autofactura.html', context)

@csrf_exempt
def api_generar_autofactura(request):
    """
    API pública para generar la factura desde el portal.
    Se espera POST con JSON: { 'ticket': '123', 'rfc': 'XAXX010101000', 'razon_social': 'PUBLICO EN GENERAL', 'cp': '00000', 'regimen': '616', 'uso': 'S01' }
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'Método no permitido'}, status=405)
    
    try:
        data = json.loads(request.body)
        ticket_id = data.get('ticket')
        rfc = data.get('rfc', '').strip().upper()
        razon_social = data.get('razon_social', '').strip().upper()
        cp = data.get('cp', '').strip()
        regimen = data.get('regimen', '').strip()
        uso = data.get('uso', '').strip()

        if not all([ticket_id, rfc, razon_social, cp, regimen, uso]):
            return JsonResponse({'error': 'Todos los campos son obligatorios'}, status=400)

        orden = get_object_or_404(OrdenDeServicio, id=ticket_id)
        
        # Validar si ya está facturada
        if FacturaCFDI.objects.filter(referencia_origen=f"ORDEN_{orden.id}", estado__in=['TIMBRADO', 'PROCESANDO']).exists():
            return JsonResponse({'error': 'Este ticket ya fue facturado previamente.'}, status=400)

        # Buscar o crear ClienteFacturacion
        cliente, created = ClienteFacturacion.objects.get_or_create(
            rfc=rfc,
            empresa=orden.empresa,
            defaults={
                'razon_social': razon_social,
                'codigo_postal': cp,
                'regimen_fiscal': regimen
            }
        )
        if not created:
            # Actualizar datos fiscales si cambiaron
            cliente.razon_social = razon_social
            cliente.codigo_postal = cp
            cliente.regimen_fiscal = regimen
            cliente.save()

        # Crear Borrador de Factura
        factura = FacturaCFDI.objects.create(
            empresa=orden.empresa,
            cliente=cliente,
            forma_pago='01',  # Efectivo (simplificado para autofactura pública)
            metodo_pago='PUE',
            uso_cfdi=uso,
            moneda='MXN',
            subtotal=orden.total,
            total_impuestos_trasladados=Decimal('0.00'), # Lógica real extraería impuestos de la orden
            total=orden.total,
            referencia_origen=f"ORDEN_{orden.id}"
        )

        ConceptoFactura.objects.create(
            factura=factura,
            clave_prod_serv='85121800',  # Laboratorios médicos
            descripcion=f"Servicios de Laboratorio (Ticket {orden.id})",
            cantidad=Decimal('1.00'),
            valor_unitario=orden.total,
            importe=orden.total
        )

        # Dejar la factura como BORRADOR para timbrado manual o por celery
        return JsonResponse({'mensaje': 'Factura generada y encolada para timbrado exitosamente.', 'factura_id': factura.id})

    except json.JSONDecodeError:
        return JsonResponse({'error': 'JSON inválido'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
