import json
from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import Mock, patch

from django.test import RequestFactory, SimpleTestCase, override_settings
from django.utils import timezone

from core.views.laboratorio.calidad import api_finalizar_toma


class AudioTomaSecurityTests(SimpleTestCase):
    @override_settings(FERNET_KEY=None)
    def test_audio_never_persists_in_plaintext_when_key_is_missing(self):
        ahora = timezone.now()
        toma = Mock(
            hora_inicio_extraccion=ahora - timedelta(seconds=30),
            identidad_verificada=False,
            ayuno_confirmado=False,
            consentimiento_firmado=False,
        )
        orden = Mock(
            toma_muestra=toma,
            detalles=Mock(),
            estado_clinico='EN_TOMA',
        )
        request = RequestFactory().post(
            '/laboratorio/toma/1/finalizar/',
            data=json.dumps({'audio_b64': 'YQ=='}),
            content_type='application/json',
        )
        request.user = SimpleNamespace(username='quimica', empresa=object())

        audio_manager = Mock()
        with patch(
            'core.views.laboratorio.calidad.get_object_or_404',
            return_value=orden,
        ), patch(
            'core.models.AudioTomaMuestra',
            SimpleNamespace(objects=audio_manager),
        ), patch(
            'core.views.laboratorio.calidad.transaction.atomic',
        ) as atomic:
            atomic.return_value.__enter__.return_value = None
            response = api_finalizar_toma.__wrapped__(request, 1)

        self.assertEqual(response.status_code, 200)
        payload = json.loads(response.content)
        self.assertTrue(payload['ok'])
        self.assertFalse(payload['audio_guardado'])
        self.assertIn('advertencia_audio', payload)
        audio_manager.get_or_create.assert_not_called()
