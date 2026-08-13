from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from core.models import ConsentimientoInformado, Empresa, OrdenDeServicio, Paciente


User = get_user_model()


class ConsentimientoDigitalSecurityTests(TestCase):
    def setUp(self):
        self.empresa_a = Empresa.objects.create(nombre='Empresa A', rfc='AAA260507TST')
        self.empresa_b = Empresa.objects.create(nombre='Empresa B', rfc='BBB260507TST')
        self.user_a = User.objects.create_user(
            username='consent-a', password='test123456789', empresa=self.empresa_a,
        )
        self.paciente_b = Paciente.objects.create(
            empresa=self.empresa_b, nombre_completo='Paciente B', sexo='F',
        )
        self.orden_b = OrdenDeServicio.objects.create(
            empresa=self.empresa_b, paciente=self.paciente_b,
            responsable_ingreso=self.user_a, total=Decimal('100.00'),
            anticipo=Decimal('100.00'), estado='PAGADO',
        )
        self.consentimiento_b = ConsentimientoInformado.objects.create(
            empresa=self.empresa_b, paciente=self.paciente_b, orden=self.orden_b,
            folio_consentimiento='CI-TENANT-B-001', firma_digital='',
        )

    def test_pdf_cannot_cross_tenant_even_for_superuser(self):
        self.user_a.is_superuser = True
        self.user_a.save(update_fields=['is_superuser'])
        self.client.login(username='consent-a', password='test123456789')

        response = self.client.get(
            reverse('descargar_pdf_consentimiento', args=[self.consentimiento_b.folio_consentimiento])
        )

        self.assertEqual(response.status_code, 404)

    def test_pdf_lookup_uses_persisted_folio(self):
        self.consentimiento_b.empresa = self.empresa_a
        self.consentimiento_b.paciente = Paciente.objects.create(
            empresa=self.empresa_a, nombre_completo='Paciente A', sexo='M',
        )
        self.consentimiento_b.save(update_fields=['empresa', 'paciente'])
        self.client.login(username='consent-a', password='test123456789')

        response = self.client.get(
            reverse('descargar_pdf_consentimiento', args=[self.consentimiento_b.folio_consentimiento])
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/pdf')
