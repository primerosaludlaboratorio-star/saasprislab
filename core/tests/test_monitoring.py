from django.test import TestCase


class MonitoringEndpointsTests(TestCase):
    def test_metrics_returns_200_and_prometheus_content(self):
        response = self.client.get('/metrics/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'text/plain; version=0.0.4; charset=utf-8')
        body = response.content.decode('utf-8')
        self.assertIn('prislab_info', body)
        self.assertIn('prislab_uptime_seconds', body)
        self.assertIn('prislab_health_status', body)
        self.assertIn('prislab_request_total', body)

    def test_metrics_exposes_database_and_cache_status(self):
        response = self.client.get('/metrics/')
        self.assertEqual(response.status_code, 200)
        body = response.content.decode('utf-8')
        self.assertIn('prislab_health_status{component="database"}', body)
        self.assertIn('prislab_health_status{component="cache"}', body)
