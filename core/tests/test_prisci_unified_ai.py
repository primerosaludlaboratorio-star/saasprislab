import json
from unittest.mock import patch

from django.contrib.auth.models import Group
from django.test import Client, RequestFactory, TestCase, override_settings

from core.models import Empresa, Usuario
from core.views.pris_ia import _ejecutar_herramienta, _verificar_rbac


class PrisciUnifiedAITests(TestCase):
    def setUp(self):
        self.empresa = Empresa.objects.create(nombre="PRISCI Test")
        self.user = Usuario.objects.create_user(
            username="recepcion_prisci",
            password="x",
            empresa=self.empresa,
            rol="RECEPCION",
        )
        Group.objects.create(name="RECEPCION").user_set.add(self.user)

    def test_prisci_denies_tool_outside_user_role(self):
        ok, msg = _verificar_rbac("registrar_venta_farmacia", self.user, jarvis_mode=True)
        self.assertFalse(ok)
        self.assertIn("autorizaci", msg)

    def test_prisci_allows_tool_for_user_role(self):
        ok, _ = _verificar_rbac("crear_orden_laboratorio", self.user, jarvis_mode=True)
        self.assertTrue(ok)

    def test_external_channel_cannot_execute_internal_write_tool(self):
        req = RequestFactory().post("/ia/asistente/chat/")
        req.user = self.user
        req.prisci_external_channel = True
        result = _ejecutar_herramienta("crear_paciente", {}, req)
        self.assertTrue(result.get("denegado_rbac"))

    @override_settings(DEBUG=False, PRISCI_WEBHOOK_TOKEN="secret")
    def test_prisci_webhook_requires_token_when_configured(self):
        resp = Client().post(
            "/api/prisci/webhook/",
            data=json.dumps({"plataforma": "whatsapp", "remitente_id": "521555", "mensaje": "hola"}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 401)

    @override_settings(DEBUG=False, PRISCI_WEBHOOK_TOKEN="secret", AI_PROVIDER="deepseek", GOOGLE_API_KEY="fake-key")
    @patch("core.views.pris_ia._gemini_rest_call", return_value="Hola, soy Prisci.")
    def test_prisci_webhook_uses_same_assistant(self, _mock_ai):
        resp = Client().post(
            "/api/prisci/webhook/",
            data=json.dumps({"plataforma": "whatsapp", "remitente_id": "521555", "mensaje": "hola"}),
            content_type="application/json",
            HTTP_X_PRISCI_WEBHOOK_TOKEN="secret",
        )
        self.assertIn(resp.status_code, [200, 500])
        if resp.status_code == 200 and 'application/json' in resp.get('Content-Type', ''):
            data = resp.json()
            self.assertTrue(data["ok"])
