from unittest.mock import patch

from django.db import OperationalError
from django.test import TestCase


class HealthEndpointsTests(TestCase):
    def test_health_ok(self):
        response = self.client.get('/health/')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data.get('status'), 'ok')
        self.assertEqual(data.get('components', {}).get('database'), 'ok')
        self.assertEqual(data.get('components', {}).get('cache'), 'ok')

    def test_live_ok(self):
        response = self.client.get('/live/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json().get('status'), 'alive')

    def test_ready_503_when_db_fails(self):
        with patch('core.views.general.connection.cursor', side_effect=OperationalError('db down')):
            response = self.client.get('/ready/')
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json().get('components', {}).get('database'), 'error')
