import json
from types import SimpleNamespace
from unittest.mock import patch

from django.test import RequestFactory, SimpleTestCase

from core.services.motor_recetas import _safe
from core.services.motor_reportes_lab import _safe_str
from core.views.medico.receta import verificar_qr_receta


class PdfAndQrSecurityTests(SimpleTestCase):
    def test_reportlab_values_are_escaped(self):
        payload = '<b>Paciente</b> & texto'
        self.assertEqual(_safe(payload), '&lt;b&gt;Paciente&lt;/b&gt; &amp; texto')
        self.assertEqual(_safe_str(payload), '&lt;b&gt;Paciente&lt;/b&gt; &amp; texto')

    def test_qr_hash_is_required_before_patient_data_is_returned(self):
        receta = SimpleNamespace(
            folio_receta='REC-202607-00001',
            hash_verificacion='hash-real',
        )
        request = RequestFactory().post(
            '/medico/receta/verificar-qr/',
            data=json.dumps({'qr_data': {'folio': receta.folio_receta, 'hash': 'hash-falso'}}),
            content_type='application/json',
        )
        request.user = SimpleNamespace(is_authenticated=True)

        with patch('core.views.medico.receta.empresa_efectiva_request', return_value=object()), \
             patch('core.views.medico.receta.Receta.objects.filter') as filter_mock, \
             patch('core.views.medico.receta.calcular_hash_verificacion_receta', return_value='hash-real'):
            filter_mock.return_value.first.return_value = receta
            response = verificar_qr_receta.__wrapped__(request)

        self.assertEqual(response.status_code, 403)
        body = json.loads(response.content)
        self.assertNotIn('receta', body)
        self.assertFalse(body['autentica'])
