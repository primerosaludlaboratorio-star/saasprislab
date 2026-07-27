import json
import logging
import uuid
from decimal import Decimal
from django.core.exceptions import ValidationError
from django.db import transaction
from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_POST
from core.models import OrdenDeServicio, Usuario
from contabilidad.models import ClienteFacturacion, FacturaCFDI, ConceptoFactura
from contabilidad.validators_cfdi40 import (
    clean_nombre_fiscal,
    validate_codigo_postal_sat40,
    validate_rfc_sat40,
)
# APIFacturama removed for now

logger = logging.getLogger(__name__)


ALLOWED_REGIMENES = {code for code, _ in ClienteFacturacion.REGIMEN_CHOICES}
ALLOWED_USOS_CFDI = {code for code, _ in ClienteFacturacion.USO_CFDI_CHOICES}


def _json_public(payload, status=200):
    response = JsonResponse(payload, status=status)
    response['Cache-Control'] = 'no-store'
    return response


def _json_error_publico(status=400):
    return _json_public({'error': 'No fue posible procesar la solicitud.'}, status=status)


def _resolver_orden_por_token(ticket):
    try:
        token = uuid.UUID(str(ticket or '').strip())
    except (TypeError, ValueError, AttributeError):
        return None
    return (
        OrdenDeServicio.objects_all
        .select_related('empresa', 'responsable_ingreso')
        .filter(token_acceso=token)
        .first()
    )


def _usuario_sistema_autofactura(orden):
    if orden.responsable_ingreso_id:
        return orden.responsable_ingreso
    return (
        Usuario.objects
        .filter(empresa=orden.empresa, is_active=True)
        .order_by('-is_superuser', '-is_staff', 'id')
        .first()
    )

def autofactura_portal(request):
    """
    Portal público donde el paciente ingresa con token UUID de autofactura.
    y su RFC para auto-facturarse.
    """
    ticket_id = request.GET.get('ticket', '')
    context = {'ticket_id': ticket_id}
    return render(request, 'contabilidad/public/autofactura.html', context)

@require_POST
@csrf_protect
def api_generar_autofactura(request):
    """
    API pública para generar la factura desde el portal.
    Se espera POST con JSON: { 'ticket': '<uuid token_acceso>', 'rfc': 'XAXX010101000', 'razon_social': 'PUBLICO EN GENERAL', 'cp': '00000', 'regimen': '616', 'uso': 'S01' }
    """
    try:
        data = json.loads(request.body)
        if not isinstance(data, dict):
            return _json_public({'error': 'JSON inválido'}, status=400)

        ticket_id = data.get('ticket')
        rfc = data.get('rfc', '').strip().upper()
        razon_social = clean_nombre_fiscal(data.get('razon_social', ''))
        cp = data.get('cp', '').strip()
        regimen = data.get('regimen', '').strip()
        uso = data.get('uso', '').strip()
        email = str(data.get('email', '')).strip() or 'autofactura@prislab.local'

        if not all([ticket_id, rfc, razon_social, cp, regimen, uso]):
            return _json_public({'error': 'Todos los campos son obligatorios'}, status=400)

        try:
            validate_rfc_sat40(rfc)
            validate_codigo_postal_sat40(cp)
        except ValidationError:
            return _json_public({'error': 'Datos fiscales inválidos.'}, status=400)

        if regimen not in ALLOWED_REGIMENES or uso not in ALLOWED_USOS_CFDI:
            return _json_public({'error': 'Datos fiscales inválidos.'}, status=400)

        orden = _resolver_orden_por_token(ticket_id)
        if not orden:
            return _json_error_publico(status=404)
        usuario_sistema = _usuario_sistema_autofactura(orden)
        if not usuario_sistema:
            logger.warning("Autofactura sin usuario sistema para empresa_id=%s orden_id=%s", orden.empresa_id, orden.id)
            return _json_error_publico(status=500)
        
        # Validar si ya está facturada
        if FacturaCFDI.objects.filter(
            orden_laboratorio=orden,
            estado__in=['BORRADOR', 'PENDIENTE', 'FACTURANDO', 'TIMBRADO'],
        ).exists():
            return _json_public({'error': 'Este ticket ya fue facturado previamente.'}, status=400)

        with transaction.atomic():
            # Buscar o crear ClienteFacturacion
            cliente, created = ClienteFacturacion.objects.get_or_create(
                rfc=rfc,
                empresa=orden.empresa,
                defaults={
                    'razon_social': razon_social,
                    'email': email,
                    'codigo_postal': cp,
                    'regimen_fiscal': regimen,
                    'uso_cfdi_default': uso,
                }
            )
            if not created:
                # Actualizar datos fiscales si cambiaron
                cliente.razon_social = razon_social
                cliente.codigo_postal = cp
                cliente.regimen_fiscal = regimen
                cliente.uso_cfdi_default = uso
                cliente.save()

            # Crear Borrador de Factura
            factura = FacturaCFDI.objects.create(
                empresa=orden.empresa,
                cliente=cliente,
                forma_pago='01',  # Efectivo (simplificado para autofactura pública)
                metodo_pago='PUE',
                subtotal=orden.total,
                total_impuestos_trasladados=Decimal('0.00'), # Lógica real extraería impuestos de la orden
                total=orden.total,
                orden_laboratorio=orden,
                usuario_creo=usuario_sistema,
            )

            ConceptoFactura.objects.create(
                factura=factura,
                numero_linea=1,
                clave_producto_servicio='85121800',  # Laboratorios médicos
                descripcion=f"Servicios de Laboratorio (Orden {orden.folio_orden or orden.id})",
                cantidad=Decimal('1.00'),
                valor_unitario=orden.total,
                importe=orden.total
            )

        # Dejar la factura como BORRADOR para timbrado manual o por celery
        return _json_public({'mensaje': 'Factura generada y encolada para timbrado exitosamente.', 'factura_id': factura.id})

    except json.JSONDecodeError:
        return _json_public({'error': 'JSON inválido'}, status=400)
    except Exception:
        logger.exception("Error inesperado en api_generar_autofactura")
        return _json_error_publico(status=500)
