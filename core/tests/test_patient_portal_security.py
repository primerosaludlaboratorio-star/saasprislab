from datetime import date

from django.core.exceptions import ValidationError
from django.core.cache import cache
from django.http import HttpResponse
from django.test import RequestFactory, TestCase, override_settings

from core.models import Empresa, Paciente
from core.middleware.rate_limit import RateLimitMiddleware
from pacientes.portal_models import SolicitudAccesoPortal


class PatientPortalSecurityTests(TestCase):
    def setUp(self):
        cache.clear()
        self.empresa_a = Empresa.objects.create(nombre='Empresa A')
        self.empresa_b = Empresa.objects.create(nombre='Empresa B')

    def tearDown(self):
        cache.clear()

    @override_settings(PRISLAB_TRUSTED_PROXY_CIDRS=())
    def test_portal_login_is_rate_limited(self):
        middleware = RateLimitMiddleware(lambda request: HttpResponse(status=200))
        factory = RequestFactory()

        responses = [
            middleware(factory.post('/pacientes/portal/', REMOTE_ADDR='192.0.2.10'))
            for _ in range(6)
        ]

        self.assertEqual([getattr(response, 'status_code', None) for response in responses[:5]], [200] * 5)
        self.assertEqual(responses[5].status_code, 429)

    def test_portal_request_cannot_link_patient_from_other_tenant(self):
        paciente = Paciente.objects.create(
            empresa=self.empresa_b,
            nombre_completo='Paciente B',
            fecha_nacimiento=date(1980, 1, 1),
        )
        solicitud = SolicitudAccesoPortal(
            empresa=self.empresa_a,
            paciente=paciente,
            nombre_completo='Solicitud',
            email='solicitud@example.com',
            telefono='5555555555',
            fecha_nacimiento=date(1980, 1, 1),
            numero_identificacion='ID-1',
        )

        with self.assertRaises(ValidationError):
            solicitud.full_clean()
