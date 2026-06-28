from django.test import RequestFactory, SimpleTestCase

from core.services.forense_service import _client_ip


class ForenseServiceTests(SimpleTestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def test_client_ip_usa_ultima_ip_de_x_forwarded_for(self):
        request = self.factory.get(
            '/dummy/',
            HTTP_X_FORWARDED_FOR='1.1.1.1, 10.0.0.1, 216.238.89.243',
            REMOTE_ADDR='127.0.0.1',
        )

        self.assertEqual(_client_ip(request), '216.238.89.243')

    def test_client_ip_fallback_remote_addr(self):
        request = self.factory.get('/dummy/', REMOTE_ADDR='127.0.0.1')

        self.assertEqual(_client_ip(request), '127.0.0.1')
