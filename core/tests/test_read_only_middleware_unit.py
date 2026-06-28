"""Pruebas unitarias rápidas de ReadOnlyMiddleware sin base de datos."""
from types import SimpleNamespace

from django.http import HttpResponse
from django.test import RequestFactory, SimpleTestCase, override_settings

from core.middleware.read_only import ReadOnlyMiddleware


def _user(username='test.user', rol='CAJERO', authenticated=True, superuser=False):
    return SimpleNamespace(
        username=username,
        rol=rol,
        is_authenticated=authenticated,
        is_superuser=superuser,
    )


class ReadOnlyMiddlewareUnitTests(SimpleTestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.middleware = ReadOnlyMiddleware(lambda request: HttpResponse('ok'))

    @override_settings(PRISLAB_READ_ONLY=False)
    def test_disabled_allows_post(self):
        request = self.factory.post('/farmacia/pdv/')
        request.user = _user()
        response = self.middleware(request)
        self.assertEqual(response.status_code, 200)

    @override_settings(PRISLAB_READ_ONLY=True)
    def test_blocks_post_outside_allowlist(self):
        request = self.factory.post('/home/', HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        request.user = _user(authenticated=True)
        response = self.middleware(request)
        self.assertEqual(response.status_code, 405)
        self.assertIn('"modo": "READ_ONLY"', response.content.decode('utf-8'))

    @override_settings(PRISLAB_READ_ONLY=True)
    def test_allows_post_login_path(self):
        request = self.factory.post('/login/')
        request.user = _user(authenticated=True)
        response = self.middleware(request)
        self.assertEqual(response.status_code, 200)

    @override_settings(
        PRISLAB_READ_ONLY=True,
        PRISLAB_READ_ONLY_AUDIT_ALLOWED_PATH_PREFIXES=['/farmacia/'],
        PRISLAB_READ_ONLY_AUDIT_ALLOWED_USERNAMES=['auditor.farmacia'],
        PRISLAB_READ_ONLY_AUDIT_ALLOWED_ROLES=['ADMIN', 'DIRECTOR'],
        PRISLAB_READ_ONLY_ALLOW_SUPERUSERS=False,
    )
    def test_allows_audited_write_in_farmacia_for_allowlisted_user(self):
        request = self.factory.post('/farmacia/carga-masiva-excel/')
        request.user = _user(username='auditor.farmacia', rol='CAJERO', authenticated=True)
        response = self.middleware(request)
        self.assertEqual(response.status_code, 200)

    @override_settings(
        PRISLAB_READ_ONLY=True,
        PRISLAB_READ_ONLY_AUDIT_ALLOWED_PATH_PREFIXES=['/farmacia/'],
        PRISLAB_READ_ONLY_AUDIT_ALLOWED_USERNAMES=['auditor.farmacia'],
        PRISLAB_READ_ONLY_AUDIT_ALLOWED_ROLES=['ADMIN', 'DIRECTOR'],
        PRISLAB_READ_ONLY_ALLOW_SUPERUSERS=False,
    )
    def test_blocks_audited_write_for_non_allowlisted_user(self):
        request = self.factory.post('/farmacia/carga-masiva-excel/', HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        request.user = _user(username='otro.usuario', rol='CAJERO', authenticated=True)
        response = self.middleware(request)
        self.assertEqual(response.status_code, 405)
