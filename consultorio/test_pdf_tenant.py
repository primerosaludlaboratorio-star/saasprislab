from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import RequestFactory, TestCase

from consultorio.pdf_views import imprimir_expediente_forense
from consultorio.pdf_views_prislab import api_generar_receta_pdf, imprimir_receta_profesional
from core.models import ConsultaMedica, Empresa, Medico, Paciente, Receta


User = get_user_model()


class ConsultorioPdfTenantRequestContextTest(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.empresa_usuario = Empresa.objects.create(
            nombre="Empresa Usuario PDF",
            rfc="USR260625AAA",
        )
        self.empresa_actual = Empresa.objects.create(
            nombre="Empresa Actual PDF",
            rfc="ACT260625AAA",
        )
        self.user = User.objects.create_user(
            username="doctor_pdf_ctx",
            password="test123456789",
            empresa=self.empresa_usuario,
            rol="DIRECTOR",
        )
        self.medico = Medico.objects.create(
            empresa=self.empresa_actual,
            nombre_completo="Dr Tenant PDF",
            cedula_profesional="PDF-TENANT-001",
            especialidad="General",
        )
        self.paciente = Paciente.objects.create(
            empresa=self.empresa_actual,
            nombres="Paula",
            apellido_paterno="Tenant",
            nombre_completo="Paula Tenant",
            fecha_nacimiento="1990-01-01",
            sexo="F",
        )
        self.receta = Receta.objects.create(
            empresa=self.empresa_actual,
            paciente=self.paciente,
            medico_nombre_completo="Dr Tenant PDF",
            medico_cedula="PDF-TENANT-001",
            indicaciones="Paracetamol 500 mg cada 8 horas",
        )
        self.consulta = ConsultaMedica.objects.create(
            empresa=self.empresa_actual,
            paciente=self.paciente,
            medico=self.medico,
            receta=self.receta,
            folio_consulta="CONS-PDF-TENANT-0001",
            motivo_consulta="Seguimiento",
            exploracion_fisica="Sin hallazgos",
            diagnostico_principal="Control",
            plan_tratamiento="Observacion",
            estado="FINALIZADA",
        )

    @patch("consultorio.pdf_views_prislab.generar_receta_pdf", return_value=b"%PDF-1.4 test")
    def test_imprimir_receta_profesional_usa_empresa_actual_del_request(self, generar_mock):
        request = self.factory.get(f"/consultorio/pdf/receta/{self.consulta.id}/")
        request.user = self.user
        request.empresa_actual = self.empresa_actual

        response = imprimir_receta_profesional(request, self.consulta.id)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/pdf")
        generar_mock.assert_called_once()

    @patch("consultorio.pdf_views_prislab.generar_receta_pdf", return_value=b"%PDF-1.4 test")
    def test_api_generar_receta_pdf_usa_empresa_actual_del_request(self, generar_mock):
        request = self.factory.get(f"/consultorio/api/receta-pdf/{self.consulta.id}/")
        request.user = self.user
        request.empresa_actual = self.empresa_actual

        response = api_generar_receta_pdf(request, self.consulta.id)

        self.assertEqual(response.status_code, 200)
        self.assertIn('"status": "success"', response.content.decode("utf-8"))
        generar_mock.assert_called_once()

    def test_imprimir_expediente_forense_usa_empresa_actual_del_request(self):
        self.user.is_superuser = True
        self.user.save(update_fields=["is_superuser"])

        request = self.factory.get(f"/consultorio/pdf/forense/{self.consulta.id}/")
        request.user = self.user
        request.empresa_actual = self.empresa_actual

        response = imprimir_expediente_forense(request, self.consulta.id)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/pdf")
