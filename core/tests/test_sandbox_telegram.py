"""Punto 23 — supresión Telegram en modo training_sandbox."""
from unittest.mock import patch

from django.test import SimpleTestCase, override_settings


class SandboxTelegramOutboundTests(SimpleTestCase):
    @override_settings(IS_SANDBOX=True)
    def test_sandbox_suppresses_http_returns_true(self):
        from core.services.telegram_outbound import send_telegram_message

        with patch('core.services.telegram_outbound.requests.post') as post:
            ok = send_telegram_message('tok', '12345', 'Hola prueba')
        post.assert_not_called()
        self.assertTrue(ok)

    @override_settings(IS_SANDBOX=False)
    @patch('core.services.telegram_outbound.requests.post')
    def test_production_calls_api(self, post):
        post.return_value.ok = True
        from core.services.telegram_outbound import send_telegram_message

        ok = send_telegram_message('tok', '999', 'Msg')
        post.assert_called_once()
        self.assertTrue(ok)
