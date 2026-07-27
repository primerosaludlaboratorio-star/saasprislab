import json
from types import SimpleNamespace

from django.test import RequestFactory, SimpleTestCase

from pris_ai_core import views


class PrisAiApiSecurityTests(SimpleTestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.user = SimpleNamespace(is_authenticated=True)

    def test_authenticated_voice_api_is_not_csrf_exempt(self):
        self.assertFalse(getattr(views.voice_command_api, 'csrf_exempt', False))

        request = self.factory.post('/pris-ai/api/voice/', data='[]', content_type='application/json')
        request.user = self.user
        response = views.voice_command_api(request)

        self.assertEqual(response.status_code, 400)

    def test_authenticated_ocr_api_rejects_empty_payload(self):
        self.assertFalse(getattr(views.ocr_api, 'csrf_exempt', False))

        request = self.factory.post(
            '/pris-ai/api/ocr/',
            data=json.dumps({}),
            content_type='application/json',
        )
        request.user = self.user
        response = views.ocr_api(request)

        self.assertEqual(response.status_code, 400)
