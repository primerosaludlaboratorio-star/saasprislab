from unittest.mock import patch

from django.test import TestCase, override_settings
from django.urls import reverse


class CronTaskSecurityTests(TestCase):
    @override_settings(DEBUG=False)
    def test_cron_rejects_scheduler_headers_without_secret_in_production(self):
        from core.views import cron_tasks

        with patch.object(cron_tasks, '_CRON_SECRET', ''):
            response = self.client.get(
                reverse('cron_check_metrologia'),
                HTTP_X_CLOUDSCHEDULER_JOBNAME='daily-job',
            )
        self.assertEqual(response.status_code, 403)

    @override_settings(DEBUG=False)
    def test_cron_accepts_matching_secret(self):
        from core.views import cron_tasks

        with patch.object(cron_tasks, '_CRON_SECRET', 'top-secret'):
            with patch('django.core.management.call_command'):
                response = self.client.get(
                    reverse('cron_check_metrologia'),
                    HTTP_X_CRON_SECRET='top-secret',
                )
        self.assertNotEqual(response.status_code, 403)

    @override_settings(DEBUG=False)
    def test_cron_rejects_wrong_secret(self):
        from core.views import cron_tasks

        with patch.object(cron_tasks, '_CRON_SECRET', 'top-secret'):
            response = self.client.get(
                reverse('cron_check_metrologia'),
                HTTP_X_CRON_SECRET='wrong-secret',
            )
        self.assertEqual(response.status_code, 403)
