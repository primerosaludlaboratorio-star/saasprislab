import json
from unittest.mock import patch

from django.test import RequestFactory, SimpleTestCase, override_settings

from core.services.lims.interfaces_lims_service import (
    _empresa_hl7_autoritativa,
    _empresa_id_por_api_key,
)


class Hl7TenantBindingTests(SimpleTestCase):
    def setUp(self):
        self.factory = RequestFactory()

    @override_settings(HL7_IP_EMPRESA_MAP={})
    @patch.dict('os.environ', {'HL7_API_KEY_EMPRESA_MAP': json.dumps({'clave-a': 7})}, clear=False)
    @patch('core.services.lims.interfaces_lims_service._resolver_empresa_hl7')
    def test_api_key_map_binds_tenant(self, resolver):
        resolver.return_value = object()
        request = self.factory.post(
            '/api/iot/hl7/',
            HTTP_X_PRISLAB_API_KEY='clave-a',
            HTTP_X_EMPRESA_ID='999',
        )

        self.assertIsNotNone(_empresa_hl7_autoritativa(request, '10.0.0.1'))
        resolver.assert_called_once_with(7)

    @override_settings(HL7_IP_EMPRESA_MAP={})
    @patch.dict('os.environ', {'HL7_API_KEY_EMPRESA_MAP': json.dumps({'clave-a': 7})}, clear=False)
    def test_unbound_key_and_header_cannot_select_tenant(self):
        request = self.factory.post(
            '/api/iot/hl7/',
            HTTP_X_PRISLAB_API_KEY='otra-clave',
            HTTP_X_EMPRESA_ID='7',
        )

        self.assertIsNone(_empresa_hl7_autoritativa(request, '10.0.0.1'))

    @patch.dict('os.environ', {'HL7_API_KEY_EMPRESA_MAP': json.dumps({'clave-a': 7})}, clear=False)
    def test_api_key_lookup_uses_constant_time_comparison(self):
        self.assertEqual(_empresa_id_por_api_key('clave-a'), 7)
        self.assertIsNone(_empresa_id_por_api_key('clave-b'))

