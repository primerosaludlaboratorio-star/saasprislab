from django.http import HttpResponse
from django.core.cache import cache
from django.test import RequestFactory, SimpleTestCase, override_settings

from core.middleware.rate_limit import RateLimitMiddleware


class RateLimitMiddlewareTests(SimpleTestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.middleware = RateLimitMiddleware(lambda request: HttpResponse("ok"))
        cache.clear()

    @override_settings(
        PRISLAB_TRUSTED_PROXY_COUNT=1,
        PRISLAB_TRUSTED_PROXY_CIDRS=('127.0.0.0/8',),
    )
    def test_x_forwarded_for_uses_last_proxy_added_ip_from_trusted_proxy(self):
        request = self.factory.post(
            "/login/",
            HTTP_X_FORWARDED_FOR="203.0.113.9, 198.51.100.77",
            REMOTE_ADDR="127.0.0.1",
        )

        client_ip = self.middleware._get_client_ip(request)

        self.assertEqual(client_ip, "198.51.100.77")

    @override_settings(
        PRISLAB_TRUSTED_PROXY_COUNT=1,
        PRISLAB_TRUSTED_PROXY_CIDRS=('127.0.0.0/8',),
    )
    def test_untrusted_peer_cannot_spoof_forwarded_for(self):
        request = self.factory.post(
            "/login/",
            HTTP_X_FORWARDED_FOR="198.51.100.77",
            REMOTE_ADDR="198.51.100.55",
        )

        client_ip = self.middleware._get_client_ip(request)

        self.assertEqual(client_ip, "198.51.100.55")

    def test_api_limit_applies_to_get_and_returns_retry_after(self):
        self.middleware.API_LIMIT = {'max_requests': 1, 'window_seconds': 60}
        first = self.middleware(self.factory.get('/api/catalogo/', REMOTE_ADDR='198.51.100.55'))
        second = self.middleware(self.factory.get('/api/catalogo/', REMOTE_ADDR='198.51.100.55'))
        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 429)
        self.assertEqual(second['Retry-After'], '60')

    def test_counter_does_not_allow_more_than_configured_requests(self):
        key = 'rl:test:198.51.100.55'
        self.assertFalse(self.middleware._is_rate_limited(key, 2, 60))
        self.assertFalse(self.middleware._is_rate_limited(key, 2, 60))
        self.assertTrue(self.middleware._is_rate_limited(key, 2, 60))

    def test_remote_addr_used_when_forwarded_for_missing(self):
        request = self.factory.post("/login/", REMOTE_ADDR="198.51.100.55")

        client_ip = self.middleware._get_client_ip(request)

        self.assertEqual(client_ip, "198.51.100.55")
