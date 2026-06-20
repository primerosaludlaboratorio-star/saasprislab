import json
from types import SimpleNamespace
from unittest.mock import patch

from django.test import RequestFactory, SimpleTestCase

from core.views.microbiologia import api_guardar_sensibilidad


class _ResultadoFake:
    def __init__(self):
        self.sensibilidad = ''
        self.diametro_inhibicion = None
        self.cim = None
        self.saved = False

    def save(self):
        self.saved = True


class MicrobiologiaViewsTests(SimpleTestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.user = SimpleNamespace(is_authenticated=True, empresa=SimpleNamespace(id=1))

    def test_api_guardar_sensibilidad_devuelve_503_si_modelos_no_existen(self):
        request = self.factory.post(
            '/api/microbiologia/guardar-sensibilidad/1/',
            data=json.dumps({'sensibilidad': 'S'}),
            content_type='application/json',
        )
        request.user = self.user

        response = api_guardar_sensibilidad(request, 1)

        self.assertEqual(response.status_code, 503)
        payload = json.loads(response.content)
        self.assertEqual(payload['status'], 'error')
        self.assertIn('microbiología', payload['mensaje'])

    @patch('core.views.microbiologia._resolver_modelos_microbiologia')
    @patch('core.views.microbiologia.get_object_or_404')
    def test_api_guardar_sensibilidad_actualiza_resultado_desde_json(self, mock_get, mock_modelos):
        resultado = _ResultadoFake()
        mock_get.return_value = resultado
        mock_modelos.return_value = (
            object(),
            object(),
            SimpleNamespace(),
        )

        request = self.factory.post(
            '/api/microbiologia/guardar-sensibilidad/1/',
            data=json.dumps({
                'sensibilidad': 's',
                'diametro_inhibicion': '18',
                'cim': '0.5',
            }),
            content_type='application/json',
        )
        request.user = self.user

        response = api_guardar_sensibilidad(request, 1)

        self.assertEqual(response.status_code, 200)
        payload = json.loads(response.content)
        self.assertEqual(payload['status'], 'success')
        self.assertEqual(resultado.sensibilidad, 'S')
        self.assertEqual(resultado.diametro_inhibicion, 18.0)
        self.assertEqual(resultado.cim, 0.5)
        self.assertTrue(resultado.saved)
