"""DRP Punto 14 — ReadOnlyMiddleware (PRISLAB_READ_ONLY)."""
from django.test import Client, TestCase, override_settings


class ReadOnlyMiddlewareTests(TestCase):
    @override_settings(PRISLAB_READ_ONLY=False)
    def test_disabled_allows_post(self):
        c = Client(enforce_csrf_checks=False)
        r = c.post('/home/', {})
        self.assertNotEqual(r.status_code, 405)

    @override_settings(PRISLAB_READ_ONLY=True)
    def test_blocks_post_outside_allowlist(self):
        c = Client(enforce_csrf_checks=False)
        r = c.post(
            '/home/',
            {},
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )
        self.assertEqual(r.status_code, 405)
        data = r.json()
        self.assertEqual(data.get('modo'), 'READ_ONLY')

    @override_settings(PRISLAB_READ_ONLY=True)
    def test_allows_get(self):
        c = Client()
        r = c.get('/login/')
        self.assertIn(r.status_code, (200, 302))

    @override_settings(PRISLAB_READ_ONLY=True)
    def test_allows_post_login_path(self):
        c = Client(enforce_csrf_checks=False)
        r = c.post('/login/', {'username': 'nouser', 'password': 'bad'})
        self.assertNotEqual(r.status_code, 405)

    @override_settings(PRISLAB_READ_ONLY=True)
    def test_blocks_admin_login_post(self):
        c = Client(enforce_csrf_checks=False)
        r = c.post(
            '/admin/login/',
            {'username': 'x', 'password': 'y', 'next': '/'},
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )
        self.assertEqual(r.status_code, 405)
        self.assertEqual(r.json().get('modo'), 'READ_ONLY')
