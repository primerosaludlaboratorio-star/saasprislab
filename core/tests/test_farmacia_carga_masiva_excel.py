from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.contrib.auth.models import Group
from django.test import TestCase
from django.urls import reverse

from core.models import Empresa, Lote, Producto, Sucursal


Usuario = get_user_model()


class FarmaciaCargaMasivaExcelTest(TestCase):
    def setUp(self):
        self.empresa = Empresa.objects.create(nombre="Empresa Farmacia Excel", rfc="FEX260507TST")
        Sucursal.objects.create(
            empresa=self.empresa,
            nombre="Sucursal Central",
            codigo_sucursal="FEX-CENTRAL",
        )
        self.usuario = Usuario.objects.create_user(
            username="farmacia_excel_user",
            password="test123456789",
            empresa=self.empresa,
            rol="ADMIN",
        )
        self.usuario.is_staff = True
        self.usuario.is_superuser = True
        self.usuario.save(update_fields=["is_staff", "is_superuser"])
        self.client.login(username="farmacia_excel_user", password="test123456789")

    def test_carga_csv_crea_producto_y_lote(self):
        csv_data = (
            "codigo_barras,nombre,descripcion,marca,precio_publico,costo,stock,numero_lote,caducidad,stock_lote\n"
            "ABC123,Paracetamol 500mg,Paracetamol,Generico,50.00,20.00,10,L-001,2027-12-31,10\n"
        ).encode("utf-8")
        archivo = SimpleUploadedFile("catalogo.csv", csv_data, content_type="text/csv")

        response = self.client.post(reverse("carga_masiva_excel"), data={"archivo": archivo})

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["status"], "success")
        self.assertEqual(body["procesados_archivo"], 1)
        producto = Producto.objects.get(codigo_barras="ABC123", empresa=self.empresa)
        self.assertEqual(producto.nombre, "Paracetamol 500mg")
        lote = Lote.objects.get(producto=producto, numero_lote="L-001")
        self.assertEqual(lote.cantidad, 10)

    def test_carga_rechaza_archivo_sin_nombre(self):
        csv_data = "codigo_barras,nombre\nABC124,\n".encode("utf-8")
        archivo = SimpleUploadedFile("catalogo.csv", csv_data, content_type="text/csv")

        response = self.client.post(reverse("carga_masiva_excel"), data={"archivo": archivo})

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["status"], "error")
