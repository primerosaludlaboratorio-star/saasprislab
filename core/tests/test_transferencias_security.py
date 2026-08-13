from types import SimpleNamespace

from django.test import RequestFactory, SimpleTestCase

from core.views.transferencias import (
    crear_transferencia,
    enviar_transferencia,
    recibir_transferencia,
)


class TransferenciasSecurityTests(SimpleTestCase):
    def setUp(self):
        self.request = RequestFactory().get('/transferencias/')
        self.request.user = SimpleNamespace(
            is_authenticated=True,
            is_superuser=False,
            rol='CAJERO',
            username='empleado',
        )

    def test_cajero_no_puede_crear_transferencia(self):
        response = crear_transferencia.__wrapped__(self.request)
        self.assertEqual(response.status_code, 403)

    def test_cajero_no_puede_enviar_transferencia(self):
        response = enviar_transferencia.__wrapped__(self.request, 1)
        self.assertEqual(response.status_code, 403)

    def test_cajero_no_puede_recibir_transferencia(self):
        response = recibir_transferencia.__wrapped__(self.request, 1)
        self.assertEqual(response.status_code, 403)
