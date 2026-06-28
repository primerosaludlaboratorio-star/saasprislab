import json
from unittest.mock import patch

from django.contrib.auth.models import Group
from django.test import Client, TestCase, override_settings

from core.models import Empresa, Usuario


class AIProviderViewsTests(TestCase):
    def setUp(self):
        self.empresa = Empresa.objects.create(nombre="IA Views Test")
        self.user = Usuario.objects.create_user(
            username="ia_views",
            password="x",
            empresa=self.empresa,
            rol="ADMIN",
        )
        self.client = Client()
        self.client.force_login(self.user)

    @override_settings(AI_PROVIDER="deepseek", DEEPSEEK_API_KEY="sk-test")
    @patch("core.utils.gemini_client.generate_content", return_value="Respuesta ejecutiva")
    def test_coach_uses_central_text_provider(self, mock_generate):
        response = self.client.post(
            "/director/coach/api/preguntar/",
            data=json.dumps({"pregunta": "Como mejoro el turno?"}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["respuesta"], "Respuesta ejecutiva")
        mock_generate.assert_called_once()

    @override_settings(AI_PROVIDER="deepseek", DEEPSEEK_API_KEY="sk-test")
    @patch("core.utils.gemini_client.generate_content", return_value="Te escucho.")
    def test_bienestar_chat_uses_central_text_provider(self, mock_generate):
        response = self.client.post(
            "/bienestar/api/chat/",
            data=json.dumps({"mensaje": "Me siento abrumado"}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["ok"])
        self.assertEqual(data["mensaje"], "Te escucho.")
        mock_generate.assert_called_once()
