from unittest.mock import MagicMock, patch

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import Client, TestCase
from django.test import override_settings
from django.urls import reverse

from core.models import DocumentoCapacitacion, Empresa, PushSubscription
from core.push_service import _push_block_key, enviar_notificacion_push


User = get_user_model()


class FakeWebPushException(Exception):
    def __init__(self, response):
        super().__init__('rate limited')
        self.response = response


class TestBlindajeCapacitacion(TestCase):
    def setUp(self):
        self.client = Client()
        self.empresa = Empresa.objects.create(
            nombre='PRISLAB Test Blindaje',
            rfc='TST123456AAA',
        )
        self.usuario = User.objects.create_user(
            username='director_blindaje',
            email='director@test.com',
            password='TestPass123!',
            empresa=self.empresa,
            rol='ADMIN',
            is_staff=True,
        )
        self.client.force_login(self.usuario)
        self.documento = DocumentoCapacitacion.objects.create(
            empresa=self.empresa,
            titulo='Manual Interno',
            tipo=DocumentoCapacitacion.TIPO_MANUAL,
            modulo_relacionado=DocumentoCapacitacion.MODULO_GENERAL,
            archivo='capacitacion/manual.pdf',
            estado_rag=DocumentoCapacitacion.ESTADO_SUBIDO,
            subido_por=self.usuario,
        )

    def test_estado_documento_resuelve_por_uuid(self):
        response = self.client.get(
            reverse('estado_documento_rag', kwargs={'documento_id': self.documento.token_acceso})
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['estado_rag'], self.documento.estado_rag)


class TestCircuitBreakerPush(TestCase):
    def setUp(self):
        cache.clear()
        self.empresa = Empresa.objects.create(
            nombre='PRISLAB Push Test',
            rfc='PUS123456AAA',
        )
        self.usuario = User.objects.create_user(
            username='push_admin',
            email='push@test.com',
            password='TestPass123!',
            empresa=self.empresa,
            rol='ADMIN',
        )
        self.subscription = PushSubscription.objects.create(
            usuario=self.usuario,
            endpoint='https://example.com/push/123',
            p256dh='test-p256dh',
            auth='test-auth',
            nombre_dispositivo='Chrome Test',
            activa=True,
        )

    @override_settings(VAPID_PRIVATE_KEY='test-private-key', VAPID_CLAIMS={'sub': 'mailto:test@example.com'})
    @patch('core.push_service.WebPushException', new=FakeWebPushException)
    @patch('core.push_service.webpush')
    def test_429_retry_after_activa_circuit_breaker(self, mock_webpush):
        response = MagicMock()
        response.status_code = 429
        response.headers = {'Retry-After': '120'}

        mock_webpush.side_effect = FakeWebPushException(response)

        resultado = enviar_notificacion_push(self.subscription, 'Titulo', 'Cuerpo')

        self.assertFalse(resultado)
        self.assertTrue(cache.get(_push_block_key(self.subscription)))

    @override_settings(VAPID_PRIVATE_KEY='test-private-key', VAPID_CLAIMS={'sub': 'mailto:test@example.com'})
    def test_suscripcion_bloqueada_omite_envio(self):
        cache.set(_push_block_key(self.subscription), True, timeout=60)
        with patch('core.push_service.webpush') as mock_webpush:
            resultado = enviar_notificacion_push(self.subscription, 'Titulo', 'Cuerpo')
        self.assertFalse(resultado)
        mock_webpush.assert_not_called()
