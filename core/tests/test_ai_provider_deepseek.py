from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase, override_settings

from core.utils import deepseek_client
from core.utils.gemini_client import _get_ai_provider, generate_content


class DeepSeekProviderTests(SimpleTestCase):
    @override_settings(
        AI_PROVIDER="deepseek",
        DEEPSEEK_API_KEY="sk-test",
        DEEPSEEK_MODEL="deepseek-chat",
        DEEPSEEK_API_URL="https://deepseek.test/v1/chat/completions",
    )
    @patch("core.utils.deepseek_client.requests.post")
    def test_generate_content_routes_to_deepseek(self, mock_post):
        response = MagicMock()
        response.json.return_value = {
            "choices": [{"message": {"content": "respuesta deepseek"}}]
        }
        response.raise_for_status.return_value = None
        mock_post.return_value = response

        text = generate_content("hola", max_tokens=12)

        self.assertEqual(text, "respuesta deepseek")
        payload = mock_post.call_args.kwargs["json"]
        self.assertEqual(payload["model"], "deepseek-chat")
        self.assertEqual(payload["messages"][0]["content"], "hola")

    @override_settings(DEEPSEEK_API_KEY="")
    def test_deepseek_requires_key(self):
        with self.assertRaises(ValueError):
            deepseek_client.generate_content("hola")

    @override_settings(
        AI_PROVIDER="deepseek",
        DEEPSEEK_API_KEY="",
        GOOGLE_API_KEY="google-test-key",
    )
    def test_provider_falls_back_to_gemini_when_deepseek_key_missing(self):
        self.assertEqual(_get_ai_provider(), "gemini")

    @override_settings(
        AI_PROVIDER="gemini",
        GOOGLE_API_KEY="",
        DEEPSEEK_API_KEY="sk-test",
    )
    def test_provider_falls_back_to_deepseek_when_gemini_key_missing(self):
        self.assertEqual(_get_ai_provider(), "deepseek")
