import json
import uuid
from decimal import Decimal

from django.conf import settings
from django.core.cache import cache
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.csrf import csrf_exempt

from contabilidad.models import ClienteFacturacion, ConceptoFactura, FacturaCFDI
from core.models import OrdenDeServicio
from core.tenant import get_current_empresa, set_current_empresa


def _cliente_ip(request) -> str:
    xff = (request.META.get('HTTP_X_FORWARDED_FOR') or '').split(',')[0].strip()
    return xff or request.META.get('REMOTE_ADDR', '0.0.0.0')


def _rate_limit_exceeded(request) -> bool:
    max_attempts = int(getattr(settings, 'PRISLAB_AUTOFACTURA_MAX_ATTEMPTS', 20))
    window_sec = int(getattr(settings, 'PRISLAB_AUTOFACTURA_WINDOW_SECONDS', 60))
    ip = _cliente_ip(request)
    key = f"autofactura:api:{ip}"

    current = cache.get(key, 0)
    if current >= max_attempts:
        return True

    if current == 0:
        cache.set(key, 1, timeout=window_sec)
    else:
        try:
            cache.incr(key)
        except ValueError:
            cache.set(key, current + 1, timeout=window_sec)
    return False


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

    if _rate_limit_exceeded(request):
        return JsonResponse({'error': 'Demasiadas solicitudes. Intente nuevamente en un momento.'}, status=429)

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

        # Ejecutar escritura fiscal bajo contexto tenant explícito de la orden.
        prev_empresa = get_current_empresa()
        set_current_empresa(orden.empresa)
        try:
            if FacturaCFDI.objects.filter(
                empresa=orden.empresa,
                orden_laboratorio=orden,
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

            usuario_emisor = orden.responsable_ingreso
            if usuario_emisor is None:
                return JsonResponse({'error': 'La orden no tiene usuario responsable para emitir factura.'}, status=400)

            factura = FacturaCFDI.objects.create(
                empresa=orden.empresa,
                cliente=cliente,
                usuario_creo=usuario_emisor,
                orden_laboratorio=orden,
                forma_pago='01',
                metodo_pago='PUE',
                subtotal=orden.total,
                total_impuestos_trasladados=Decimal('0.00'),
                total=orden.total,
            )

            ConceptoFactura.objects.create(
                factura=factura,
                numero_linea=1,
                clave_producto_servicio='85121800',
                descripcion=f"Servicios de Laboratorio (Ticket {orden.id})",
                cantidad=Decimal('1.00'),
                valor_unitario=orden.total,
                importe=orden.total,
            )

            return JsonResponse({'mensaje': 'Factura generada y encolada para timbrado exitosamente.', 'factura_id': factura.id})
        finally:
            set_current_empresa(prev_empresa)

    except json.JSONDecodeError:
        return JsonResponse({'error': 'JSON inválido'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
