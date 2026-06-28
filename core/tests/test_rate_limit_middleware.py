from django.http import HttpResponse
from django.test import RequestFactory, SimpleTestCase

from core.middleware.rate_limit import RateLimitMiddleware


class RateLimitMiddlewareTests(SimpleTestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.middleware = RateLimitMiddleware(lambda request: HttpResponse("ok"))

    def test_x_forwarded_for_uses_last_proxy_added_ip(self):
        request = self.factory.post(
            "/login/",
            HTTP_X_FORWARDED_FOR="203.0.113.9, 198.51.100.77",
            REMOTE_ADDR="127.0.0.1",
        )

        client_ip = self.middleware._get_client_ip(request)

        self.assertEqual(client_ip, "198.51.100.77")

    def test_remote_addr_used_when_forwarded_for_missing(self):
        request = self.factory.post("/login/", REMOTE_ADDR="198.51.100.55")

        client_ip = self.middleware._get_client_ip(request)

        self.assertEqual(client_ip, "198.51.100.55")
