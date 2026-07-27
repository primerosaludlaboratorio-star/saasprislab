from unittest.mock import patch

from django.test import SimpleTestCase

from core.views.pris_ia import _gemini_rest_call as legacy_call
from core.views.pris_ia._gemini import _gemini_rest_call as package_call


class GeminiTransportCanonicalTests(SimpleTestCase):
    @patch('core.utils.gemini_transport.generate_gemini_content', return_value='OK')
    def test_legacy_and_package_adapters_share_one_transport(self, transport):
        self.assertEqual(legacy_call('key', 'hola', 'img', 0.3, 100), 'OK')
        self.assertEqual(package_call('key', 'hola', 'img', 0.3, 100), 'OK')
        self.assertEqual(transport.call_count, 2)
        transport.assert_any_call(
            'hola', api_key='key', image_b64='img', temperature=0.3, max_tokens=100
        )
