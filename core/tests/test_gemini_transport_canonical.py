from unittest.mock import patch
from unittest.mock import Mock
import urllib.request

from django.test import SimpleTestCase

from core.views.pris_ia import _gemini_rest_call as legacy_call
from core.views.pris_ia._gemini import _gemini_rest_call as package_call
from core.utils.gemini_transport import generate_gemini_content


class GeminiTransportCanonicalTests(SimpleTestCase):
    @patch('core.utils.gemini_transport.generate_gemini_content', return_value='OK')
    def test_legacy_and_package_adapters_share_one_transport(self, transport):
        self.assertEqual(legacy_call('key', 'hola', 'img', 0.3, 100), 'OK')
        self.assertEqual(package_call('key', 'hola', 'img', 0.3, 100), 'OK')
        self.assertEqual(transport.call_count, 2)
        transport.assert_any_call(
            'hola', api_key='key', image_b64='img', temperature=0.3, max_tokens=100
        )

    @patch('core.utils.gemini_transport.urllib.request.urlopen')
    def test_api_key_uses_header_not_query_string(self, urlopen):
        response = Mock()
        response.read.return_value = b'{"candidates":[{"content":{"parts":[{"text":"OK"}]}}]}'
        response.__enter__ = Mock(return_value=response)
        response.__exit__ = Mock(return_value=False)
        urlopen.return_value = response

        self.assertEqual(generate_gemini_content('hola', api_key='secret-key'), 'OK')
        request = urlopen.call_args.args[0]
        self.assertNotIn('secret-key', request.full_url)
        self.assertNotIn('?', request.full_url)
        self.assertEqual(request.headers['X-goog-api-key'], 'secret-key')
