from decimal import Decimal

from django.test import TestCase
from django.urls import reverse

from core.models import Empresa, Usuario
from inventario.models import OrdenDeCompra, ProveedorCompras


class ContabilidadPersonalAccessTests(TestCase):
    def setUp(self):
        self.empresa = Empresa.objects.create(nombre="PRISLAB Test", rfc="TES010101AAA")
        self.director = Usuario.objects.create_user(
            username="director_cp",
            password="secret123",
            empresa=self.empresa,
            rol="DIRECTOR",
        )
        self.admin = Usuario.objects.create_user(
            username="admin_cp",
            password="secret123",
            empresa=self.empresa,
            rol="ADMIN",
        )
        self.proveedor = ProveedorCompras.objects.create(
            empresa=self.empresa,
            razon_social="Proveedor Demo",
            rfc="PDE010101AAA",
        )
        self.orden = OrdenDeCompra.objects.create(
            empresa=self.empresa,
            proveedor=self.proveedor,
            folio="OC-TEST-001",
            total=Decimal("150.00"),
        )

    def test_director_puede_ver_dashboard_privado(self):
        self.client.login(username="director_cp", password="secret123")

        response = self.client.get(reverse("contabilidad_personal_dashboard"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "OC-TEST-001")

    def test_admin_no_puede_ver_dashboard_privado(self):
        self.client.login(username="admin_cp", password="secret123")

        response = self.client.get(reverse("contabilidad_personal_dashboard"))

        self.assertEqual(response.status_code, 302)

    def test_no_marca_pagada_sin_factura_y_foto(self):
        self.client.login(username="director_cp", password="secret123")

        response = self.client.post(
            reverse("marcar_orden_pagada", args=[self.orden.id]),
            {"forma_pago": "TRANSFERENCIA", "referencia_transferencia": "ABC123"},
        )

        self.assertEqual(response.status_code, 302)
        self.orden.refresh_from_db()
        self.assertFalse(self.orden.pagada)
        self.assertIsNone(self.orden.fecha_pago)
