from django.core.cache import cache
from django.http import HttpResponse
from django.test import RequestFactory, SimpleTestCase

from core.decorators import rate_limit


class RateLimitDecoratorTests(SimpleTestCase):
    def setUp(self):
        cache.clear()
        self.factory = RequestFactory()

    def test_counter_is_enforced_for_repeated_requests(self):
        @rate_limit("decorator-regression", limit=1, window_seconds=60)
        def view(request):
            return HttpResponse("ok")

        first = view(self.factory.get("/", REMOTE_ADDR="198.51.100.10"))
        second = view(self.factory.get("/", REMOTE_ADDR="198.51.100.10"))

        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 429)
        self.assertEqual(second["Retry-After"], "60")

