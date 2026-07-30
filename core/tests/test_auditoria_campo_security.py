from types import SimpleNamespace
from unittest.mock import patch

from django.test import RequestFactory, SimpleTestCase

from core.views.auditoria_campo import api_auditoria_campo


class AuditoriaCampoSecurityTests(SimpleTestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.empresa = SimpleNamespace(pk=7)
        self.user = SimpleNamespace(is_authenticated=True, empresa=self.empresa)

    def _request(self, payload):
        request = self.factory.post(
            '/api/auditoria/campo/',
            data=payload,
            content_type='application/json',
        )
        request.user = self.user
        return request

    def test_rejects_arbitrary_model_and_object(self):
        response = api_auditoria_campo(self._request({
            'campo_id': 'Paciente_999',
            'campo_nombre': 'nombre_completo',
            'valor_anterior': 'real',
            'valor_nuevo': 'falso',
        }))

        self.assertEqual(response.status_code, 400)

    @patch('core.views.auditoria_campo.empresa_efectiva_request')
    @patch('core.views.auditoria_campo.DetalleOrden.objects.get')
    @patch('core.views.auditoria_campo.auditar_cambio_campo')
    def test_resolves_previous_value_from_server(self, audit, get_detail, effective_empresa):
        effective_empresa.return_value = self.empresa
        get_detail.return_value = SimpleNamespace(resultado='100', id=12)

        response = api_auditoria_campo(self._request({
            'campo_id': 'resultado_12_0',
            'campo_nombre': 'campo_falso',
            'valor_anterior': '999',
            'valor_nuevo': '110',
        }))

        self.assertEqual(response.status_code, 200)
        audit.assert_called_once()
        self.assertEqual(audit.call_args.kwargs['valor_anterior'], '100')
        self.assertEqual(audit.call_args.kwargs['valor_nuevo'], '110')

    @patch('core.views.auditoria_campo.empresa_efectiva_request')
    @patch('core.views.auditoria_campo.DetalleOrden.objects.get')
    def test_missing_result_is_not_written_as_generic_audit(self, get_detail, effective_empresa):
        from core.models import DetalleOrden

        effective_empresa.return_value = self.empresa
        get_detail.side_effect = DetalleOrden.DoesNotExist

        response = api_auditoria_campo(self._request({
            'campo_id': 'resultado_999_0',
            'valor_nuevo': '110',
        }))

        self.assertEqual(response.status_code, 404)

