from datetime import timedelta
import os
import tempfile

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from core.models import Empresa, Paciente, Producto, Sucursal
from core.models import Lote


Usuario = get_user_model()


class AuditoriaFuncionalJunio21Test(TestCase):
    def setUp(self):
        self.empresa = Empresa.objects.create(nombre="PRISLAB Auditoria", rfc="AUD260621TST")
        self.sucursal = Sucursal.objects.create(
            empresa=self.empresa,
            nombre="Matriz",
            codigo_sucursal="AUD-MTZ",
            activa=True,
        )
        self.usuario = Usuario.objects.create_user(
            username="auditor_funcional",
            password="Test2026!PRIS",
            empresa=self.empresa,
            sucursal=self.sucursal,
            rol="ADMIN",
        )
        self.usuario.is_staff = True
        self.usuario.is_superuser = True
        self.usuario.save(update_fields=["is_staff", "is_superuser"])
        self.client.login(username="auditor_funcional", password="Test2026!PRIS")

    def test_laboratorio_pacientes_busqueda_no_consulta_curp_inexistente(self):
        Paciente.objects.create(
            empresa=self.empresa,
            sucursal=self.sucursal,
            nombre_completo="Testaudit Prueba Auditoria",
            nombres="Testaudit",
            apellido_paterno="Prueba",
            apellido_materno="Auditoria",
            telefono="5551234567",
            activo=True,
        )

        response = self.client.get("/laboratorio/pacientes/", {"q": "Prueba"})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Testaudit Prueba Auditoria")
        self.assertNotContains(response, "está reparando")
        self.assertNotContains(response, "esta reparando")

    def test_consultorio_agendar_fecha_tiene_rango_operativo(self):
        response = self.client.get(reverse("consultorio:agendar_cita"))

        hoy = timezone.localdate()
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'type="date"')
        self.assertContains(response, f'min="{hoy.isoformat()}"')
        self.assertContains(response, f'max="{(hoy + timedelta(days=365)).isoformat()}"')
        self.assertContains(response, "Seleccione una fecha entre hoy y los próximos 365 días.")

    def test_pdv_devuelve_productos_cuando_catalogo_tiene_datos(self):
        Producto.objects.create(
            empresa=self.empresa,
            sucursal=self.sucursal,
            nombre="Paracetamol 500mg",
            sustancia_activa="Paracetamol",
            codigo_barras="AUD-PARA-500",
            forma_farmaceutica="Tableta",
            concentracion="500mg",
            presentacion="Caja",
            precio_compra="10.00",
            precio_publico="25.00",
            stock=10,
            stock_minimo=1,
            categoria="GENERICO",
            clasificacion_sanitaria="VI",
        )

        response = self.client.get("/farmacia/api/buscar-producto-pdv/", {"q": "paracetamol"})

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data["productos"]), 1)
        self.assertEqual(data["productos"][0]["nombre_comercial"], "Paracetamol 500mg")

    def test_importar_excel_inventario_crea_lote_con_empresa(self):
        from openpyxl import Workbook

        wb = Workbook()
        ws = wb.active
        ws.append([])
        ws.append([])
        ws.append([
            "Nombre del Producto",
            "Identificador (No Cambiar)",
            "Es un Servicio",
            "Categoría",
            "Marca",
            "Unidad de Venta",
            "Código de Barras",
            "Descripción",
            "Precio Público",
            "Costo",
            "IVA",
            "Stock Mínimo ",
            "Receta Médica",
            "Usa Lotes",
            "Lote",
            "Fabricación del Lote",
            "Caducidad del Lote",
            "Stock Total ",
        ])
        ws.append([
            "Ibuprofeno Auditoria 400mg",
            "IBU-AUD-400",
            "No",
            "GENERICO",
            "GENERICO",
            "Tableta",
            "AUD-IBU-400",
            "Ibuprofeno",
            35,
            12,
            0,
            1,
            "No",
            "Si",
            "LOT-AUD-1",
            "2026-01-01",
            "2099-12-31",
            7,
        ])

        tmp = tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False)
        tmp.close()
        try:
            wb.save(tmp.name)
            wb.close()
            call_command(
                "importar_excel_inventario",
                tmp.name,
                empresa_id=self.empresa.pk,
                reset_stock=True,
                verbosity=0,
            )
        finally:
            try:
                os.unlink(tmp.name)
            except PermissionError:
                pass

        producto = Producto.objects.get(codigo_barras="AUD-IBU-400", empresa=self.empresa)
        lote = Lote.objects.get(producto=producto, numero_lote="LOT-AUD-1")
        self.assertEqual(lote.empresa_id, self.empresa.pk)
        self.assertEqual(lote.cantidad, 7)
        producto.refresh_from_db()
        self.assertEqual(producto.stock, 7)
