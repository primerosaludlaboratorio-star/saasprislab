from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta
import json
import os

from core.models import Empresa, OrdenDeServicio, Paciente
from iot.models import Kiosco, VerificacionKiosco

Usuario = get_user_model()

class IoTKioscoSecurityTests(TestCase):
    def setUp(self):
        # Configure test environment variables for API token authentication
        self.original_token = os.environ.get("PRISLAB_KIOSCO_API_TOKEN")
        os.environ["PRISLAB_KIOSCO_API_TOKEN"] = "test-kiosco-token-123"

        self.empresa_a = Empresa.objects.create(nombre="Empresa A", rfc="RFC111111AAA")
        self.empresa_b = Empresa.objects.create(nombre="Empresa B", rfc="RFC222222BBB")

        self.user_con_empresa = Usuario.objects.create_user(
            username="iot_user_a",
            password="password123",
            empresa=self.empresa_a,
            rol="RECEPCION"
        )
        self.user_sin_empresa = Usuario.objects.create_user(
            username="iot_user_sin_emp",
            password="password123",
            empresa=None,
            rol="RECEPCION"
        )

        self.paciente_a = Paciente.objects.create(
            empresa=self.empresa_a,
            nombres="Juan",
            apellido_paterno="Perez",
            nombre_completo="Juan Perez"
        )
        
        self.orden_a = OrdenDeServicio.objects.create(
            empresa=self.empresa_a,
            paciente=self.paciente_a,
            folio_orden="FOLIO-A",
            total=0
        )

        self.kiosco_a = Kiosco.objects.create(
            empresa=self.empresa_a,
            nombre="Kiosco A",
            ip_address="192.168.1.100",
            activo=True
        )

        self.verificacion_a = VerificacionKiosco.objects.create(
            orden=self.orden_a,
            kiosco=self.kiosco_a,
            datos_mostrar={"paciente": "Juan Perez", "estudios": []},
            fecha_expiracion=timezone.now() + timedelta(minutes=10)
        )

        self.client = Client()

    def tearDown(self):
        if self.original_token is not None:
            os.environ["PRISLAB_KIOSCO_API_TOKEN"] = self.original_token
        else:
            os.environ.pop("PRISLAB_KIOSCO_API_TOKEN", None)

    def test_dashboard_kioscos_enforces_empresa(self):
        self.client.login(username="iot_user_sin_emp", password="password123")
        response = self.client.get(reverse("iot:dashboard_kioscos"))
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse("home"), target_status_code=302)

        self.client.login(username="iot_user_a", password="password123")
        response = self.client.get(reverse("iot:dashboard_kioscos"))
        self.assertEqual(response.status_code, 200)

    def test_api_crear_kiosco_enforces_empresa(self):
        self.client.login(username="iot_user_sin_emp", password="password123")
        response = self.client.post(
            reverse("iot:api_crear_kiosco"),
            data=json.dumps({"nombre": "Nuevo Kiosco", "ip_address": "192.168.1.150"}),
            content_type="application/json"
        )
        self.assertEqual(response.status_code, 403)

        self.client.login(username="iot_user_a", password="password123")
        response = self.client.post(
            reverse("iot:api_crear_kiosco"),
            data=json.dumps({"nombre": "Nuevo Kiosco", "ip_address": "192.168.1.150"}),
            content_type="application/json"
        )
        self.assertEqual(response.status_code, 200)
        k = Kiosco.objects.get(nombre="Nuevo Kiosco")
        self.assertEqual(k.empresa, self.empresa_a)

    def test_api_toggle_kiosco_cross_tenant(self):
        kiosco_b = Kiosco.objects.create(
            empresa=self.empresa_b,
            nombre="Kiosco B",
            activo=True
        )
        self.client.login(username="iot_user_a", password="password123")
        response = self.client.post(reverse("iot:api_toggle_kiosco", args=[kiosco_b.id]))
        self.assertEqual(response.status_code, 404)

    def test_api_enviar_a_kiosco_cross_tenant(self):
        kiosco_b = Kiosco.objects.create(
            empresa=self.empresa_b,
            nombre="Kiosco B",
            activo=True
        )
        self.client.login(username="iot_user_a", password="password123")
        response = self.client.post(
            reverse("iot:api_enviar"),
            data=json.dumps({"orden_id": self.orden_a.id, "kiosco_id": kiosco_b.id, "estudios": []}),
            content_type="application/json"
        )
        self.assertEqual(response.status_code, 500)

    def test_api_kiosco_heartbeat_ip_whitelist(self):
        # 1. Invalid API token -> 401 Unauthorized
        response = self.client.get(
            reverse("iot:api_heartbeat", args=[self.kiosco_a.id]),
            HTTP_AUTHORIZATION="Bearer wrong-token",
            REMOTE_ADDR="192.168.1.100"
        )
        self.assertEqual(response.status_code, 401)

        # 2. Valid token but incorrect IP -> 403 Forbidden
        response = self.client.get(
            reverse("iot:api_heartbeat", args=[self.kiosco_a.id]),
            HTTP_AUTHORIZATION="Bearer test-kiosco-token-123",
            REMOTE_ADDR="192.168.1.200"
        )
        self.assertEqual(response.status_code, 403)

        # 3. Valid token and correct IP -> 200 OK
        response = self.client.get(
            reverse("iot:api_heartbeat", args=[self.kiosco_a.id]),
            HTTP_AUTHORIZATION="Bearer test-kiosco-token-123",
            REMOTE_ADDR="192.168.1.100"
        )
        self.assertEqual(response.status_code, 200)

    def test_api_kiosco_confirmar_ip_whitelist(self):
        # 1. Incorrect IP -> 403 Forbidden
        response = self.client.post(
            reverse("iot:api_confirmar", args=[self.verificacion_a.id]),
            data=json.dumps({"datos": {}}),
            content_type="application/json",
            HTTP_AUTHORIZATION="Bearer test-kiosco-token-123",
            REMOTE_ADDR="192.168.1.200"
        )
        self.assertEqual(response.status_code, 403)

        # 2. Correct IP -> 200 OK
        response = self.client.post(
            reverse("iot:api_confirmar", args=[self.verificacion_a.id]),
            data=json.dumps({"datos": {}}),
            content_type="application/json",
            HTTP_AUTHORIZATION="Bearer test-kiosco-token-123",
            REMOTE_ADDR="192.168.1.100"
        )
        self.assertEqual(response.status_code, 200)

    def test_api_kiosco_rechazar_ip_whitelist(self):
        # 1. Incorrect IP -> 403 Forbidden
        response = self.client.post(
            reverse("iot:api_rechazar", args=[self.verificacion_a.id]),
            HTTP_AUTHORIZATION="Bearer test-kiosco-token-123",
            REMOTE_ADDR="192.168.1.200"
        )
        self.assertEqual(response.status_code, 403)

        # 2. Correct IP -> 200 OK
        response = self.client.post(
            reverse("iot:api_rechazar", args=[self.verificacion_a.id]),
            HTTP_AUTHORIZATION="Bearer test-kiosco-token-123",
            REMOTE_ADDR="192.168.1.100"
        )
        self.assertEqual(response.status_code, 200)
