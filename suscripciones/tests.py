from django.test import TestCase, RequestFactory
from django.contrib.auth import get_user_model
from django.utils import timezone
from core.models import Empresa
from suscripciones.models import PlanSaaS, SuscripcionTenant
from core.middleware.suscripciones import SuscripcionMiddleware
from django.http import HttpResponse

User = get_user_model()

class SuscripcionMiddlewareTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.empresa = Empresa.objects.create(nombre="Test Empresa", rfc="TEST010101T1")
        self.plan = PlanSaaS.objects.create(nombre="Pro", precio_mensual=100.00)
        self.user = User.objects.create_user(username="testuser", password="password", empresa=self.empresa)
        self.suscripcion = SuscripcionTenant.objects.create(
            empresa=self.empresa,
            plan=self.plan,
            estado=SuscripcionTenant.ESTADO_ACTIVA
        )

        def dummy_get_response(request):
            return HttpResponse("OK")
        self.middleware = SuscripcionMiddleware(dummy_get_response)

    def test_acceso_permitido_activa(self):
        request = self.factory.get('/dashboard/')
        request.user = self.user
        response = self.middleware(request)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b"OK")

    def test_acceso_bloqueado_vencida(self):
        self.suscripcion.estado = SuscripcionTenant.ESTADO_VENCIDA
        self.suscripcion.save()
        
        request = self.factory.get('/dashboard/')
        request.user = self.user
        response = self.middleware(request)
        self.assertEqual(response.status_code, 403)
        self.assertIn(b"Payment Required", response.content)

    def test_acceso_permitido_admin_sin_suscripcion(self):
        self.suscripcion.delete()
        admin_user = User.objects.create_superuser(username="admin", password="pwd")
        request = self.factory.get('/dashboard/')
        request.user = admin_user
        response = self.middleware(request)
        self.assertEqual(response.status_code, 200)
