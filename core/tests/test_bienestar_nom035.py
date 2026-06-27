"""
Tests para el módulo de Bienestar Staff NOM-035 (core.views.bienestar).
Cubre rutas NOM-035, diario emocional, alertas_rrhh y aislamiento cross-tenant.
"""
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone

from core.models import Empresa, EvaluacionNOM035, DiarioEmocionalStaff, AlertaBurnout

Usuario = get_user_model()


class BienestarNOM035URLTest(TestCase):
    """Verifica que las URLs NOM-035 resuelven correctamente."""

    def test_urls_nom035_resuelven_ok(self):
        urls = [
            'bienestar_dashboard',
            'diario_emocional',
            'evaluacion_nom035',
            'bienestar_alertas_rrhh',
        ]
        for url_name in urls:
            with self.subTest(url=url_name):
                url = reverse(url_name)
                self.assertIsNotNone(url)


class BienestarNOM035VistaTest(TestCase):
    """Pruebas funcionales de core.views.bienestar."""

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

    def test_dashboard_bienestar_requiere_empresa(self):
        """Usuario sin empresa es redirigido a home."""
        self.client.force_login(self.user_sin_empresa)
        response = self.client.get(reverse('bienestar_dashboard'))
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('home'), target_status_code=302)

    def test_dashboard_bienestar_muestra_metricas(self):
        """Empleado con empresa ve dashboard y métricas."""
        DiarioEmocionalStaff.objects.create(
            empleado=self.empleado_a,
            fecha=timezone.now().date(),
            humor_general=3,
            nivel_estres=5,
        )
        self.client.force_login(self.empleado_a)
        response = self.client.get(reverse('bienestar_dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'core/bienestar/dashboard.html')
        self.assertEqual(response.context['entradas_mes'], 1)
        # El empleado normal no ve contador de alertas RRHH
        self.assertIsNone(response.context['alertas_rrhh'])

    def test_evaluacion_nom035_crea_alerta(self):
        """POST a NOM-035 con score alto genera AlertaBurnout."""
        self.client.force_login(self.empleado_a)
        data = {f'item_{i}': '5' for i in range(1, 21)}
        response = self.client.post(reverse('evaluacion_nom035'), data)
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('bienestar_dashboard'), target_status_code=200)
        self.assertTrue(
            AlertaBurnout.objects.filter(
                empleado=self.empleado_a,
                empresa=self.empresa_a,
                tipo='NOM035_RIESGO',
            ).exists()
        )

    def test_alertas_rrhh_requiere_rol_directivo(self):
        """Empleado normal no puede acceder a alertas_rrhh."""
        self.client.force_login(self.empleado_a)
        response = self.client.get(reverse('bienestar_alertas_rrhh'))
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('bienestar_dashboard'), target_status_code=200)

    def test_alertas_rrhh_filtra_por_empresa(self):
        """Director de empresa A no ve alertas de empresa B."""
        AlertaBurnout.objects.create(
            empleado=self.empleado_a,
            empresa=self.empresa_a,
            tipo='HUMOR_BAJO',
            nivel_riesgo=4,
        )
        AlertaBurnout.objects.create(
            empleado=self.director_b,
            empresa=self.empresa_b,
            tipo='ESTRES_ALTO',
            nivel_riesgo=4,
        )
        self.client.force_login(self.director_a)
        response = self.client.get(reverse('bienestar_alertas_rrhh'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'core/bienestar/alertas_rrhh.html')
        alertas = response.context['alertas']
        self.assertEqual(len(alertas), 1)
        self.assertEqual(alertas[0].empresa, self.empresa_a)
        self.assertEqual(response.context['total_pendientes'], 1)

    def test_alertas_rrhh_marcar_atendida(self):
        """Director puede marcar una alerta como atendida vía POST."""
        alerta = AlertaBurnout.objects.create(
            empleado=self.empleado_a,
            empresa=self.empresa_a,
            tipo='ESTRES_ALTO',
            nivel_riesgo=4,
        )
        self.client.force_login(self.director_a)
        response = self.client.post(
            reverse('bienestar_alertas_rrhh'),
            {'alerta_id': alerta.id, 'notas': 'Atendida'},
        )
        # La vista procesa el POST y vuelve a renderizar la página
        self.assertEqual(response.status_code, 200)
        alerta.refresh_from_db()
        self.assertTrue(alerta.atendida)
        self.assertEqual(alerta.atendida_por, self.director_a)
        self.assertEqual(alerta.notas_rrhh, 'Atendida')

    def test_diario_emocional_guarda_entrada(self):
        """POST al diario emocional guarda entrada cifrada."""
        self.client.force_login(self.empleado_a)
        data = {
            'humor_general': '4',
            'nivel_estres': '3',
            'contenido': 'Hoy me siento bien',
            'fecha': timezone.now().date().isoformat(),
        }
        response = self.client.post(reverse('diario_emocional'), data)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            DiarioEmocionalStaff.objects.filter(empleado=self.empleado_a).count(),
            1,
        )

    def test_alertas_rrhh_marcar_atendida_cross_tenant_bloqueado(self):
        """Director de empresa B no puede marcar alerta de empresa A."""
        alerta = AlertaBurnout.objects.create(
            empleado=self.empleado_a,
            empresa=self.empresa_a,
            tipo='ESTRES_ALTO',
            nivel_riesgo=4,
        )
        self.client.force_login(self.director_b)
        response = self.client.post(
            reverse('bienestar_alertas_rrhh'),
            {'alerta_id': alerta.id, 'notas': 'Atendida'},
        )
        # La vista muestra error y renderiza; la alerta permanece sin atender
        self.assertEqual(response.status_code, 200)
        alerta.refresh_from_db()
        self.assertFalse(alerta.atendida)
