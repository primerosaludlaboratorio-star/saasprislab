import base64
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase, override_settings

from core.services.pris_tts import synthesize_pris_voice


class PrisTtsTests(SimpleTestCase):
    @override_settings()
    @patch.dict("os.environ", {"GOOGLE_APPLICATION_CREDENTIALS": "/tmp/pris-test.json"}, clear=False)
    @patch("core.services.pris_tts.default")
    @patch("core.services.pris_tts.requests.post")
    def test_synthesizes_mexico_neural_voice(self, mock_post, mock_default):
        credentials = MagicMock(token="token")
        mock_default.return_value = (credentials, "test-project")
        response = MagicMock()
        response.json.return_value = {"audioContent": base64.b64encode(b"mp3").decode()}
        response.raise_for_status.return_value = None
        mock_post.return_value = response

        self.assertEqual(synthesize_pris_voice("Hola, soy PRIS."), b"mp3")
        payload = mock_post.call_args.kwargs["json"]
        self.assertEqual(payload["voice"]["languageCode"], "es-MX")
        self.assertEqual(payload["audioConfig"]["speakingRate"], 0.93)

    @patch.dict("os.environ", {"GOOGLE_APPLICATION_CREDENTIALS": ""}, clear=False)
    def test_without_credentials_uses_browser_fallback(self):
        self.assertIsNone(synthesize_pris_voice("Hola"))
