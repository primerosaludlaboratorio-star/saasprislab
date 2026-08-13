from django.test import TestCase

from core.models import Empresa, Usuario
from laboratorio.models import ResponsableSanitario


class ResponsableSanitarioTenantTests(TestCase):
    def setUp(self):
        self.empresa_a = Empresa.objects.create(nombre='Laboratorio A', rfc='RSA260813A1')
        self.empresa_b = Empresa.objects.create(nombre='Laboratorio B', rfc='RSB260813B2')
        self.user_a = Usuario.objects.create_user(
            username='responsable_a', password='Test2026!A', empresa=self.empresa_a
        )
        self.user_b = Usuario.objects.create_user(
            username='responsable_b', password='Test2026!B', empresa=self.empresa_b
        )

    def _crear(self, usuario, empresa, cedula):
        return ResponsableSanitario.objects.create(
            usuario=usuario,
            empresa=empresa,
            cedula_profesional=cedula,
            universidad_titulo='Universidad de Prueba',
        )

    def test_same_cedula_is_allowed_in_different_tenants(self):
        self._crear(self.user_a, self.empresa_a, 'CED-001')
        self._crear(self.user_b, self.empresa_b, 'CED-001')
        self.assertEqual(ResponsableSanitario.objects.filter(cedula_profesional='CED-001').count(), 2)

    def test_active_responsible_is_rotated_only_inside_tenant(self):
        first = self._crear(self.user_a, self.empresa_a, 'CED-002')
        other_tenant = self._crear(self.user_b, self.empresa_b, 'CED-002')

        user_a_2 = Usuario.objects.create_user(
            username='responsable_a_2', password='Test2026!A2', empresa=self.empresa_a
        )
        second = self._crear(user_a_2, self.empresa_a, 'CED-003')

        first.refresh_from_db()
        other_tenant.refresh_from_db()
        self.assertFalse(first.activo)
        self.assertTrue(other_tenant.activo)
        self.assertTrue(second.activo)

