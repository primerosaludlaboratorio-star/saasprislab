"""Regresiones de RBAC para superficies sensibles de Consultorio."""

import json
from types import SimpleNamespace

from django.test import RequestFactory, SimpleTestCase

from consultorio.pdf_views import imprimir_receta_paciente
from consultorio.pdf_views_prislab import api_generar_receta_pdf
from consultorio.views.api_consulta import api_crear_consulta_directa
from consultorio.views.cobros import api_registrar_cobro
from consultorio.views.historial import historial_clinico_paciente
from consultorio.views.sentinel import api_sentinel_exportar_cursor


class ConsultorioRoleSecurityTests(SimpleTestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.user = SimpleNamespace(
            is_authenticated=True,
            is_superuser=False,
            is_staff=False,
            rol='CAJERO',
            username='cajero',
            groups=SimpleNamespace(
                filter=lambda **kwargs: SimpleNamespace(exists=lambda: False)
            ),
        )

    def _post_json(self, path, payload=None):
        request = self.factory.post(
            path,
            data=json.dumps(payload or {}),
            content_type='application/json',
        )
        request.user = self.user
        return request

    def _get(self, path):
        request = self.factory.get(path)
        request.user = self.user
        return request

    def test_cajero_no_puede_crear_consulta(self):
        response = api_crear_consulta_directa.__wrapped__(
            self._post_json('/consultorio/api/crear-consulta-directa/')
        )
        self.assertEqual(response.status_code, 403)

    def test_cajero_no_puede_registrar_cobro(self):
        response = api_registrar_cobro.__wrapped__(
            self._post_json('/consultorio/api/registrar-cobro/')
        )
        self.assertEqual(response.status_code, 403)

    def test_cajero_no_puede_ver_historial_clinico(self):
        response = historial_clinico_paciente.__wrapped__(
            self._get('/consultorio/historial/1/')
        , 1)
        self.assertEqual(response.status_code, 403)

    def test_cajero_no_puede_exportar_contexto_sentinel(self):
        response = api_sentinel_exportar_cursor.__wrapped__(
            self._get('/consultorio/sentinel/incidencias/1/exportar/'), 1
        )
        self.assertEqual(response.status_code, 403)

    def test_cajero_no_puede_generar_pdf_de_receta(self):
        response = imprimir_receta_paciente.__wrapped__(
            self._get('/consultorio/pdf/receta/1/'), 1
        )
        self.assertEqual(response.status_code, 403)
        response = api_generar_receta_pdf.__wrapped__(
            self._get('/consultorio/api/receta-pdf/1/'), 1
        )
        self.assertEqual(response.status_code, 403)
