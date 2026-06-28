from datetime import date, datetime, time
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from core.models import CitaMedica, Empresa, Paciente

User = get_user_model()


class RecepcionViewsTests(TestCase):
    def setUp(self):
        self.empresa_a = Empresa.objects.create(nombre='Empresa A', rfc='AAA010101AAA')
        self.empresa_b = Empresa.objects.create(nombre='Empresa B', rfc='BBB010101BBB')

        self.user_a = User.objects.create_user(
            username='recep_a',
            password='testpass123',
            empresa=self.empresa_a,
            rol='RECEPCION',
        )
        self.user_b = User.objects.create_user(
            username='recep_b',
            password='testpass123',
            empresa=self.empresa_b,
            rol='RECEPCION',
        )
        self.user_sin_empresa = User.objects.create_user(
            username='recep_sin_empresa',
            password='testpass123',
            empresa=None,
            rol='RECEPCION',
        )

        self.paciente_a = Paciente.objects.create(
            empresa=self.empresa_a,
            nombre_completo='Paciente A',
            nombres='Paciente',
            apellido_paterno='A',
            tipo='GENERAL',
        )
        self.paciente_b = Paciente.objects.create(
            empresa=self.empresa_b,
            nombre_completo='Paciente B',
            nombres='Paciente',
            apellido_paterno='B',
            tipo='GENERAL',
        )

        self.cita_a = CitaMedica.objects.create(
            empresa=self.empresa_a,
            paciente=self.paciente_a,
            fecha_cita=date(2026, 6, 24),
            hora_cita=time(9, 0),
            motivo='Consulta general',
            creado_por=self.user_a,
        )
        self.cita_b = CitaMedica.objects.create(
            empresa=self.empresa_b,
            paciente=self.paciente_b,
            fecha_cita=date(2026, 6, 24),
            hora_cita=time(10, 0),
            motivo='Consulta empresa B',
            creado_por=self.user_b,
        )

    def test_dashboard_recepcion_redirects_when_user_has_no_empresa(self):
        self.client.force_login(self.user_sin_empresa)
        response = self.client.get(reverse('recepcion:dashboard_recepcion'))
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('home'), target_status_code=302)

    def test_check_in_paciente_blocks_cross_tenant_access(self):
        self.client.force_login(self.user_b)
        response = self.client.get(reverse('recepcion:check_in_paciente', args=[self.cita_a.id]))
        self.assertEqual(response.status_code, 404)

    def test_cobrar_consulta_blocks_cross_tenant_access(self):
        self.client.force_login(self.user_b)
        response = self.client.get(reverse('recepcion:cobrar_consulta', args=[self.cita_a.id]))
        self.assertEqual(response.status_code, 404)

    def test_dashboard_recepcion_uses_localdate_not_utc_date(self):
        self.client.force_login(self.user_a)
        fake_utc = timezone.make_aware(datetime(2026, 6, 25, 0, 30, 0))
        with patch('recepcion.views.timezone.now', return_value=fake_utc), patch(
            'recepcion.views.timezone.localdate',
            return_value=date(2026, 6, 24),
        ):
            response = self.client.get(reverse('recepcion:dashboard_recepcion'))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['total_citas_hoy'], 1)
        self.assertEqual(response.context['citas_pendientes'], 1)

    def test_lista_espera_uses_localdate_not_utc_date(self):
        self.client.force_login(self.user_a)
        fake_utc = timezone.make_aware(datetime(2026, 6, 25, 0, 30, 0))
        with patch('recepcion.views.timezone.now', return_value=fake_utc), patch(
            'recepcion.views.timezone.localdate',
            return_value=date(2026, 6, 24),
        ):
            response = self.client.get(reverse('recepcion:lista_espera'))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(list(response.context['pacientes_espera']), [self.cita_a])
        self.assertEqual(list(response.context['pacientes_consulta']), [])
