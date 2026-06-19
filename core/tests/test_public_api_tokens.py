import json
import os
from unittest.mock import patch

from django.core.cache import cache
from django.test import TestCase
from django.urls import reverse

from iot.models import Kiosco


class PublicApiTokenSecurityTests(TestCase):
    def setUp(self):
        cache.clear()

    @patch.dict(os.environ, {'PRISLAB_FRONTEND_LOG_TOKEN': 'front-token'}, clear=False)
    def test_log_frontend_error_requiere_token(self):
        url = reverse('log_frontend_error')
        payload = json.dumps({'message': 'boom', 'source': 'test.js'})

        sin_token = self.client.post(url, data=payload, content_type='application/json')
        con_token = self.client.post(
            url,
            data=payload,
            content_type='application/json',
            HTTP_X_FRONTEND_LOG_TOKEN='front-token',
        )

        self.assertEqual(sin_token.status_code, 401)
        self.assertEqual(con_token.status_code, 200)

    @patch.dict(os.environ, {'PRISLAB_KIOSCO_API_TOKEN': 'kiosk-token'}, clear=False)
    def test_kiosco_heartbeat_requiere_token(self):
        kiosco = Kiosco.objects.create(nombre='Kiosco QA', activo=True, intervalo_polling=2)
        url = reverse('iot:api_heartbeat', args=[kiosco.id])

        sin_token = self.client.get(url)
        con_token = self.client.get(url, HTTP_X_PRISLAB_KIOSCO_TOKEN='kiosk-token')

        self.assertEqual(sin_token.status_code, 401)
        self.assertEqual(con_token.status_code, 200)
        self.assertEqual(con_token.json()['status'], 'ok')
