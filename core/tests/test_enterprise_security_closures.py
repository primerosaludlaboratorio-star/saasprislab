import json
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import RequestFactory, SimpleTestCase, TestCase, override_settings

from core.models import Empresa
from core.services.feature_flags import FLAG_CATALOG
from core.views.feature_flags_admin import api_toggle_flag
from core.views.sentinel_api import api_shield_telemetry, api_sentinel_diagnostico


class WestgardGovernanceTests(SimpleTestCase):
    def test_westgard_is_on_by_default(self):
        self.assertTrue(FLAG_CATALOG['QC_WESTGARD_ACTIVO']['default'])


class WestgardProductionToggleTests(TestCase):
    def setUp(self):
        cache.clear()
        self.factory = RequestFactory()
        self.empresa = Empresa.objects.create(nombre='QC Governance', rfc='QCG260727AAA')
        self.user = get_user_model().objects.create_user(
            username='qc_director', password='strong-test-password',
            empresa=self.empresa, rol='DIRECTOR',
        )

    @override_settings(IS_PRODUCTION=True)
    @patch.dict('os.environ', {}, clear=False)
    def test_production_cannot_disable_westgard_without_explicit_exception(self):
        request = self.factory.post(
            '/api/feature-flags/QC_WESTGARD_ACTIVO/',
            data=json.dumps({'activo': False}),
            content_type='application/json',
        )
        request.user = self.user

        response = api_toggle_flag(request, 'QC_WESTGARD_ACTIVO')

        self.assertEqual(response.status_code, 409)


class SentinelTelemetryGuardTests(SimpleTestCase):
    def setUp(self):
        cache.clear()
        self.factory = RequestFactory()

    def test_rejects_oversized_payload(self):
        request = self.factory.post(
            '/api/sentinel/shield-telemetry/',
            data=b'x' * (16 * 1024 + 1),
            content_type='application/json',
            REMOTE_ADDR='127.0.0.1',
        )

        response = api_shield_telemetry(request)

        self.assertEqual(response.status_code, 413)

    def test_rejects_non_object_payload(self):
        request = self.factory.post(
            '/api/sentinel/shield-telemetry/',
            data=json.dumps(['not', 'an', 'event']),
            content_type='application/json',
            REMOTE_ADDR='127.0.0.1',
        )

        response = api_shield_telemetry(request)

        self.assertEqual(response.status_code, 400)


class SentinelDiagnosticCompatibilityTests(TestCase):
    def setUp(self):
        cache.clear()
        self.factory = RequestFactory()

    @patch.dict('os.environ', {'PRISLAB_SENTINEL_DIAGNOSTIC_TOKEN': 'diagnostic-test-token'})
    def test_diagnostic_uses_active_django_database_backend(self):
        request = self.factory.post(
            '/api/sentinel/diagnostico/',
            HTTP_X_ADMIN_TOKEN='diagnostic-test-token',
            REMOTE_ADDR='127.0.0.1',
        )

        response = api_sentinel_diagnostico(request)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(json.loads(response.content)['status'], 'success')
