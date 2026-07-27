from django.test import TestCase
from django.urls import reverse

from core.models import Empresa
from django.contrib.auth import get_user_model


class AuditoriaRolesUiTest(TestCase):
    def setUp(self):
        self.empresa = Empresa.objects.create(nombre='Empresa Roles UI', rfc='ROLES260727')

    def _user(self, username, rol, *, superuser=False):
        return get_user_model().objects.create_user(
            username=username,
            password='Test2026!Roles',
            empresa=self.empresa,
            rol=rol,
            is_superuser=superuser,
            is_staff=superuser,
        )

    def test_farmacia_roles_no_abren_recepcion_laboratorio_por_url_directa(self):
        for username, rol in (
            ('farmacia_admin_ui', 'FARMACIA'),
            ('farmacia_cajero_ui', 'CAJERO'),
        ):
            with self.subTest(rol=rol):
                self.client.force_login(self._user(username, rol))
                response = self.client.get(reverse('recepcion_lab'))
                self.assertEqual(response.status_code, 403)

    def test_recepcion_lab_permanece_disponible_para_recepcion_y_quimico(self):
        for username, rol in (
            ('recepcion_ui', 'RECEPCION'),
            ('quimico_ui', 'QUIMICO'),
        ):
            with self.subTest(rol=rol):
                self.client.force_login(self._user(username, rol))
                response = self.client.get(reverse('recepcion_lab'))
                self.assertEqual(response.status_code, 200)
