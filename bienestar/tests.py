from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
import json

from core.models import Empresa
from bienestar.models import DiarioEmocional, RecursoCrecimiento

Usuario = get_user_model()

class BienestarSecurityTests(TestCase):
    def setUp(self):
        self.empresa_a = Empresa.objects.create(nombre="Empresa A", rfc="RFC111111AAA")
        self.empresa_b = Empresa.objects.create(nombre="Empresa B", rfc="RFC222222BBB")

        self.user_con_empresa = Usuario.objects.create_user(
            username="user_con_emp",
            password="password123",
            empresa=self.empresa_a,
            rol="RECEPCION"
        )
        self.user_sin_empresa = Usuario.objects.create_user(
            username="user_sin_emp",
            password="password123",
            empresa=None,
            rol="RECEPCION"
        )
        self.director_empresa_a = Usuario.objects.create_user(
            username="director_a",
            password="password123",
            empresa=self.empresa_a,
            rol="DIRECTOR"
        )
        self.director_sin_empresa = Usuario.objects.create_user(
            username="director_sin_emp",
            password="password123",
            empresa=None,
            rol="DIRECTOR"
        )

        self.client = Client()

    def test_dashboard_bienestar_enforces_empresa(self):
        """User without company is redirected to home when accessing dashboard."""
        self.client.login(username="user_sin_emp", password="password123")
        response = self.client.get(reverse("bienestar:dashboard_bienestar"))
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse("home"), target_status_code=302)

        # User with company can access
        self.client.login(username="user_con_emp", password="password123")
        response = self.client.get(reverse("bienestar:dashboard_bienestar"))
        self.assertEqual(response.status_code, 200)

    def test_api_chat_bienestar_enforces_empresa(self):
        """AJAX chat endpoint returns 403 for user without company."""
        self.client.login(username="user_sin_emp", password="password123")
        response = self.client.post(
            reverse("bienestar:api_chat_bienestar"),
            data=json.dumps({"mensaje": "Hola PRIS"}),
            content_type="application/json",
            HTTP_X_REQUESTED_WITH="XMLHttpRequest"
        )
        self.assertEqual(response.status_code, 403)

        # User with company gets successful response
        self.client.login(username="user_con_emp", password="password123")
        response = self.client.post(
            reverse("bienestar:api_chat_bienestar"),
            data=json.dumps({"mensaje": "Hola PRIS"}),
            content_type="application/json",
            HTTP_X_REQUESTED_WITH="XMLHttpRequest"
        )
        self.assertEqual(response.status_code, 200)

    def test_chat_bienestar_mejorado_enforces_empresa(self):
        """Chat page in improved bienestar checks company assignment."""
        self.client.login(username="user_sin_emp", password="password123")
        response = self.client.get(reverse("chat_bienestar"))
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse("home"), target_status_code=302)

        self.client.login(username="user_con_emp", password="password123")
        response = self.client.get(reverse("chat_bienestar"))
        self.assertEqual(response.status_code, 200)

    def test_alertas_bienestar_director_enforces_empresa_and_role(self):
        """Only users with director role and company assigned can view director alerts."""
        # User without company is blocked
        self.client.login(username="director_sin_emp", password="password123")
        response = self.client.get(reverse("alertas_bienestar_director"))
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse("home"), target_status_code=302)

        # User with company but not director role is blocked
        self.client.login(username="user_con_emp", password="password123")
        response = self.client.get(reverse("alertas_bienestar_director"))
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse("home"), target_status_code=302)

        # Director with company is allowed
        self.client.login(username="director_a", password="password123")
        response = self.client.get(reverse("alertas_bienestar_director"))
        self.assertEqual(response.status_code, 200)
