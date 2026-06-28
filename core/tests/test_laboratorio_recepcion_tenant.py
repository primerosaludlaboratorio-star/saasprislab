from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from core.models import Empresa, Sucursal
from lims.models import Analito


Usuario = get_user_model()


class RecepcionLaboratorioTenantTest(TestCase):
    def setUp(self):
        self.empresa = Empresa.objects.create(nombre="PRISLAB Tenant", rfc="TEN260621A1")
        self.sucursal = Sucursal.objects.create(
            empresa=self.empresa,
            nombre="Matriz",
            codigo_sucursal="TEN-MTZ",
            activa=True,
        )
        self.usuario = Usuario.objects.create_user(
            username="auditor_tenant_lab",
            password="Test2026!PRIS",
            empresa=self.empresa,
            sucursal=self.sucursal,
            rol="ADMIN",
        )
        self.client.force_login(self.usuario)

    def test_recepcion_lab_no_expone_departamentos_analitos_de_otra_empresa(self):
        otra_empresa = Empresa.objects.create(nombre="Otro Laboratorio", rfc="OTR260621B2")
        Analito.objects.create(
            empresa=self.empresa,
            codigo="AUD-TEN-GLU",
            abreviatura="GLU",
            nombre="Glucosa Auditoria",
            departamento="QUIMICA PRISLAB",
            activo=True,
        )
        Analito.objects.create(
            empresa=otra_empresa,
            codigo="AUD-TEN-EXT",
            abreviatura="EXT",
            nombre="Externo Auditoria",
            departamento="SECRETO OTRO TENANT",
            activo=True,
        )

        response = self.client.get(reverse("recepcion_lab"))

        self.assertEqual(response.status_code, 200)
        categorias = {item["nombre"] for item in response.context["categorias"]}
        self.assertIn("QUIMICA PRISLAB", categorias)
        self.assertNotIn("SECRETO OTRO TENANT", categorias)
