from django.test import TestCase
from django.urls import reverse

from core.models import Empresa, Medico, Usuario


class CatalogoMedicosTenantTests(TestCase):
    def setUp(self):
        self.empresa_a = Empresa.objects.create(nombre='Médicos A', rfc='MED260812A1')
        self.empresa_b = Empresa.objects.create(nombre='Médicos B', rfc='MED260812B2')
        self.usuario_a = Usuario.objects.create_user(
            username='medicos_a', password='test', empresa=self.empresa_a, rol='ADMIN'
        )
        self.medico_b = Medico.objects.create(
            empresa=self.empresa_b,
            nombre_completo='Médico Empresa B',
            cedula_profesional='CED-UNICA-1',
            especialidad='Cardiología',
        )

    def test_cedula_compartida_no_reasigna_medico_de_otro_tenant(self):
        self.client.force_login(self.usuario_a)
        response = self.client.post(
            reverse('catalogo_medicos'),
            {
                'nombre_completo': 'Médico Empresa A',
                'cedula_profesional': 'CED-UNICA-1',
                'especialidad': 'Medicina General',
            },
        )

        self.assertEqual(response.status_code, 302)
        self.medico_b.refresh_from_db()
        self.assertEqual(self.medico_b.empresa_id, self.empresa_b.id)
        self.assertEqual(self.medico_b.nombre_completo, 'Médico Empresa B')
        self.assertEqual(
            Medico.objects.filter(empresa=self.empresa_a, cedula_profesional='CED-UNICA-1').count(),
            1,
        )
