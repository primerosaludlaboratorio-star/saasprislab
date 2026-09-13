from pathlib import Path

from django.test import SimpleTestCase


class ListaTrabajoCsrfRegressionTests(SimpleTestCase):
    def test_marcar_toma_usa_token_renderizado_y_credenciales_same_origin(self):
        template = Path(__file__).resolve().parents[1] / "templates" / "core" / "lista_trabajo.html"
        source = template.read_text(encoding="utf-8")

        self.assertIn("function getCsrfToken()", source)
        self.assertIn("document.querySelector('meta[name=\"csrf-token\"]')", source)
        self.assertIn("credentials: 'same-origin'", source)
        self.assertIn("X-Requested-With", source)
