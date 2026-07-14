from types import SimpleNamespace
from unittest.mock import patch

from django.test import RequestFactory, SimpleTestCase

from core.views.configuracion import configuracion_empresa


class ConfiguracionEmpresaViewTests(SimpleTestCase):
    def test_usuario_sin_empresa_redirige_home(self):
        request = RequestFactory().get("/configuracion/empresa/")
        request.user = SimpleNamespace(is_authenticated=True)

        with (
            patch("core.views.configuracion.get_empresa_usuario", return_value=None),
            patch("django.contrib.messages.error"),
        ):
            response = configuracion_empresa(request)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, "/home/")
