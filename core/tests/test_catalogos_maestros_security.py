import json
from types import SimpleNamespace

from django.test import RequestFactory, SimpleTestCase

from core.views.catalogos_maestros import api_actualizar_metodo, api_actualizar_muestra


class CatalogosMaestrosSecurityTests(SimpleTestCase):
    def _request(self, payload):
        request = RequestFactory().post(
            '/catalogos-maestros/api/actualizar/',
            data=json.dumps(payload),
            content_type='application/json',
        )
        request.user = SimpleNamespace(
            is_authenticated=True,
            is_superuser=False,
            rol='ADMIN',
            username='admin-empresa',
        )
        return request

    def test_company_admin_cannot_mutate_global_method_catalog(self):
        response = api_actualizar_metodo.__wrapped__(
            self._request({
                'metodo_anterior': 'Colorimetría',
                'metodo_nuevo': 'Colorimetría validada',
                'actualizar_estudios': True,
            })
        )

        self.assertEqual(response.status_code, 403)

    def test_company_admin_cannot_mutate_global_sample_catalog(self):
        response = api_actualizar_muestra.__wrapped__(
            self._request({
                'muestra_anterior': 'Suero',
                'muestra_nueva': 'Suero validado',
                'actualizar_estudios': True,
            })
        )

        self.assertEqual(response.status_code, 403)
