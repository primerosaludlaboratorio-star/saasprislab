"""
Tests para core.views.bienestar_mejorado.
Cubre alertas_bienestar_director, marcar_alerta_vista y aislamiento cross-tenant.
"""
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
import json

from core.models import Empresa, ConversacionBienestar, AlertaBienestar

Usuario = get_user_model()


class BienestarMejoradoAlertasTest(TestCase):
    """Pruebas de alertas silenciosas de PRIS (core.views.bienestar_mejorado)."""

    def setUp(self):
        self.client = Client()
        self.empresa_a = Empresa.objects.create(nombre='Empresa A', rfc='RFCA000000A')
        self.empresa_b = Empresa.objects.create(nombre='Empresa B', rfc='RFCB000000B')

        self.empleado_a = Usuario.objects.create_user(
            username='empleado_a',
            password='testpass123',
            empresa=self.empresa_a,
            rol='RECEPCION',
        )
        self.director_a = Usuario.objects.create_user(
            username='director_a',
            password='testpass123',
            empresa=self.empresa_a,
            rol='DIRECTOR',
        )
        self.director_b = Usuario.objects.create_user(
            username='director_b',
            password='testpass123',
            empresa=self.empresa_b,
            rol='DIRECTOR',
        )
        self.user_sin_empresa = Usuario.objects.create_user(
            username='sin_empresa',
            password='testpass123',
        )

    def test_alertas_director_requiere_rol(self):
        """Empleado normal es redirigido a home."""
        self.client.force_login(self.empleado_a)
        response = self.client.get(reverse('alertas_bienestar_director'))
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('home'), target_status_code=302)

    def test_alertas_director_filtra_por_empresa(self):
        """Director de empresa A no ve alertas de empresa B."""
        AlertaBienestar.objects.create(
            usuario=self.empleado_a,
            empresa=self.empresa_a,
            nivel=AlertaBienestar.NIVEL_CRITICO,
            descripcion='Alerta A',
        )
        AlertaBienestar.objects.create(
            usuario=self.director_b,
            empresa=self.empresa_b,
            nivel=AlertaBienestar.NIVEL_ALTO,
            descripcion='Alerta B',
        )
        self.client.force_login(self.director_a)
        response = self.client.get(reverse('alertas_bienestar_director'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'bienestar/alertas_director.html')
        alertas = response.context['alertas']
        self.assertEqual(len(alertas), 1)
        self.assertEqual(alertas[0].empresa, self.empresa_a)

    def test_marcar_alerta_vista_exito(self):
        """Director marca alerta de su empresa como vista."""
        alerta = AlertaBienestar.objects.create(
            usuario=self.empleado_a,
            empresa=self.empresa_a,
            nivel=AlertaBienestar.NIVEL_CRITICO,
            descripcion='Alerta crítica',
        )
        self.client.force_login(self.director_a)
        response = self.client.post(
            reverse('marcar_alerta_vista', args=[alerta.id]),
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(data['status'], 'success')
        alerta.refresh_from_db()
        self.assertEqual(alerta.estado, AlertaBienestar.ESTADO_VISTA)
        self.assertEqual(alerta.visto_por, self.director_a)

    def test_marcar_alerta_vista_cross_tenant_bloqueado(self):
        """Director de empresa B obtiene 404 al marcar alerta de empresa A."""
        alerta = AlertaBienestar.objects.create(
            usuario=self.empleado_a,
            empresa=self.empresa_a,
            nivel=AlertaBienestar.NIVEL_CRITICO,
            descripcion='Alerta crítica',
        )
        self.client.force_login(self.director_b)
        response = self.client.post(
            reverse('marcar_alerta_vista', args=[alerta.id]),
        )
        self.assertEqual(response.status_code, 404)
        alerta.refresh_from_db()
        self.assertEqual(alerta.estado, AlertaBienestar.ESTADO_NUEVA)

    def test_marcar_alerta_vista_requiere_post(self):
        """GET a marcar_alerta_vista devuelve 405."""
        alerta = AlertaBienestar.objects.create(
            usuario=self.empleado_a,
            empresa=self.empresa_a,
            nivel=AlertaBienestar.NIVEL_CRITICO,
            descripcion='Alerta crítica',
        )
        self.client.force_login(self.director_a)
        response = self.client.get(reverse('marcar_alerta_vista', args=[alerta.id]))
        self.assertEqual(response.status_code, 405)

    def test_marcar_alerta_vista_requiere_rol(self):
        """Empleado normal recibe 403 al intentar marcar alerta."""
        alerta = AlertaBienestar.objects.create(
            usuario=self.empleado_a,
            empresa=self.empresa_a,
            nivel=AlertaBienestar.NIVEL_CRITICO,
            descripcion='Alerta crítica',
        )
        self.client.force_login(self.empleado_a)
        response = self.client.post(reverse('marcar_alerta_vista', args=[alerta.id]))
        self.assertEqual(response.status_code, 403)
