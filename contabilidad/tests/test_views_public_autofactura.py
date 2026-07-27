import json
from decimal import Decimal

from django.test import Client, TestCase
from django.urls import reverse

from contabilidad.models import FacturaCFDI
from core.models import Empresa, OrdenDeServicio, Paciente, Usuario


class PublicAutofacturaApiTests(TestCase):
    def setUp(self):
        self.client = Client(enforce_csrf_checks=True)
        self.empresa = Empresa.objects.create(nombre='Empresa Autofactura')
        self.usuario = Usuario.objects.create_user(
            username='autofactura_user',
            password='testpass123',
            empresa=self.empresa,
        )
        self.paciente = Paciente.objects.create(
            empresa=self.empresa,
            nombre_completo='Paciente Autofactura',
            nombres='Paciente',
            apellido_paterno='Autofactura',
        )
        self.orden = OrdenDeServicio.objects.create(
            empresa=self.empresa,
            paciente=self.paciente,
            total=Decimal('250.00'),
            anticipo=Decimal('250.00'),
            estado='PAGADO',
            estado_pago='PAGADO',
            responsable_ingreso=self.usuario,
            folio_orden='ORD-AUTO-1',
        )

    def _post(self, ticket, csrf=True):
        payload = {
            'ticket': str(ticket),
            'rfc': 'XAXX010101000',
            'razon_social': 'PUBLICO EN GENERAL',
            'cp': '12345',
            'regimen': '616',
            'uso': 'S01',
        }
        self.client.get(reverse('contabilidad:autofactura_portal'), {'ticket': str(ticket)})
        headers = {}
        if csrf:
            headers['HTTP_X_CSRFTOKEN'] = self.client.cookies['csrftoken'].value
        return self.client.post(
            reverse('contabilidad:api_generar_autofactura'),
            data=json.dumps(payload),
            content_type='application/json',
            **headers,
        )

    def test_rejects_incremental_ticket_id(self):
        response = self._post(self.orden.id)

        self.assertEqual(response.status_code, 404)
        self.assertEqual(FacturaCFDI.objects.count(), 0)

    def test_rejects_request_without_csrf(self):
        response = self._post(self.orden.token_acceso, csrf=False)

        self.assertEqual(response.status_code, 403)
        self.assertEqual(FacturaCFDI.objects.count(), 0)

    def test_accepts_uuid_ticket_token(self):
        response = self._post(self.orden.token_acceso)

        self.assertEqual(response.status_code, 200)
        factura = FacturaCFDI.objects.get()
        self.assertEqual(factura.orden_laboratorio_id, self.orden.id)
        self.assertEqual(factura.empresa_id, self.empresa.id)

    def test_invalid_ticket_error_is_generic(self):
        response = self._post('no-es-uuid')
        data = json.loads(response.content.decode('utf-8'))

        self.assertEqual(response.status_code, 404)
        self.assertEqual(data['error'], 'No fue posible procesar la solicitud.')
