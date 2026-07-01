import json

from django.core.cache import cache
from django.test import TestCase, override_settings
from django.urls import reverse

from core.models import Empresa, OrdenDeServicio, Paciente, Usuario


class PublicAutofacturaApiTests(TestCase):
    def setUp(self):
        cache.clear()
        self.empresa = Empresa.objects.create(nombre='Empresa API Autofactura')
        self.user = Usuario.objects.create_user(
            username='auto_api_user',
            password='testpass123',
            empresa=self.empresa,
            rol='CAJERO',
        )
        self.paciente = Paciente.objects.create(
            empresa=self.empresa,
            nombre_completo='Paciente API',
            nombres='Paciente',
            apellido_paterno='API',
        )
        self.orden = OrdenDeServicio.objects.create(
            empresa=self.empresa,
            paciente=self.paciente,
            total='250.00',
            anticipo='250.00',
            estado='PAGADO',
            estado_pago='PAGADO',
            responsable_ingreso=self.user,
        )
        self.url = reverse('contabilidad:api_generar_autofactura')

    def _payload(self, ticket):
        return {
            'ticket': str(ticket),
            'rfc': 'XAXX010101000',
            'razon_social': 'PUBLICO EN GENERAL',
            'cp': '12345',
            'regimen': '616',
            'uso': 'S01',
        }

    def test_rejects_incremental_ticket_id(self):
        resp = self.client.post(
            self.url,
            data=json.dumps(self._payload(self.orden.id)),
            content_type='application/json',
        )
        self.assertEqual(resp.status_code, 400)
        self.assertIn('Ticket inválido', resp.json().get('error', ''))

    def test_accepts_uuid_ticket_token(self):
        resp = self.client.post(
            self.url,
            data=json.dumps(self._payload(self.orden.token_acceso)),
            content_type='application/json',
        )
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertIn('factura_id', body)

    @override_settings(PRISLAB_AUTOFACTURA_MAX_ATTEMPTS=1, PRISLAB_AUTOFACTURA_WINDOW_SECONDS=60)
    def test_rate_limit_blocks_repeated_attempts(self):
        # first hit consumes quota
        self.client.post(
            self.url,
            data=json.dumps({'ticket': 'bad', 'rfc': '', 'razon_social': '', 'cp': '', 'regimen': '', 'uso': ''}),
            content_type='application/json',
        )
        # second hit should be blocked
        resp = self.client.post(
            self.url,
            data=json.dumps({'ticket': 'bad2', 'rfc': '', 'razon_social': '', 'cp': '', 'regimen': '', 'uso': ''}),
            content_type='application/json',
        )
        self.assertEqual(resp.status_code, 429)
