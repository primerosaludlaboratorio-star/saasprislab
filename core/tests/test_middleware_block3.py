from types import SimpleNamespace
from unittest.mock import patch

from django.test import RequestFactory, SimpleTestCase, override_settings

from consultorio.sentinel_service import sanitizar_datos
from core.middleware.sentinel import SentinelTelemetryMiddleware
from core.views.autenticacion_2fa import _ip_exenta_2fa
from core.middleware.tenant_subdomain import _resolve_empresa_by_slug


class MiddlewareBlock3Tests(SimpleTestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def test_sentinel_sanitiza_datos_anidados(self):
        data = sanitizar_datos({
            'perfil': {'password': 'secret', 'nombre': 'Ana'},
            'items': [{'api_key': 'secret', 'valor': 'ok'}],
        })
        self.assertEqual(data['perfil']['password'], '***REDACTED***')
        self.assertEqual(data['items'][0]['api_key'], '***REDACTED***')
        self.assertEqual(data['perfil']['nombre'], 'Ana')

    def test_database_error_no_redirige_a_la_misma_url(self):
        request = self.factory.get('/farmacia/pdv/')
        request.user = SimpleNamespace(is_authenticated=False)
        middleware = SentinelTelemetryMiddleware(lambda request: None)
        response = middleware._repair_database_error(
            request, RuntimeError('database unavailable'), 'farmacia', request.path
        )
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response['Retry-After'], '5')
        self.assertEqual(response['X-Sentinel-Degraded'], '1')
        self.assertNotIn('Location', response)

    @override_settings(DEBUG=False, IPS_INTERNAS_2FA_BYPASS=['127.0.0.1'])
    def test_loopback_no_es_bypass_2fa_en_produccion(self):
        request = self.factory.get('/')
        request.META['REMOTE_ADDR'] = '127.0.0.1'
        self.assertFalse(_ip_exenta_2fa(request))

    def test_subdominio_no_usa_nombre_comercial_como_identidad(self):
        with patch('core.models.Empresa._meta.get_fields', return_value=[]):
            self.assertIsNone(_resolve_empresa_by_slug('primero-salud'))
