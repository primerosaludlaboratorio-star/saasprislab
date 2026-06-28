from datetime import timedelta
from io import StringIO

from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone

from core.models import Empresa, Lote, Producto, Sucursal, Usuario
from farmacia.models import AperturaCaja


class AuditoriaSeguraFarmaciaCommandTests(TestCase):
    def setUp(self):
        self.empresa = Empresa.objects.create(nombre="Empresa Audit", activa=True)
        self.sucursal = Sucursal.objects.create(
            empresa=self.empresa,
            nombre="Matriz Audit",
            codigo_sucursal="MAT-AUD",
            activa=True,
        )
        self.usuario = Usuario.objects.create_user(
            username="audit_farmacia",
            password="Audit12345!",
            empresa=self.empresa,
            sucursal=self.sucursal,
            rol="ADMIN",
            is_staff=True,
        )
        self.producto = Producto.objects.create(
            empresa=self.empresa,
            nombre="Paracetamol Audit",
            codigo_barras="AUDIT-001",
            marca_laboratorio="PRIS",
            precio_publico=25,
            precio_compra=10,
            stock=5,
            es_servicio=False,
        )
        self.lote = Lote.objects.create(
            empresa=self.empresa,
            producto=self.producto,
            numero_lote="L-AUD-001",
            fecha_caducidad=timezone.localdate() + timedelta(days=120),
            cantidad=5,
            costo_adquisicion=10,
        )
        self.apertura = AperturaCaja.objects.create(
            empresa=self.empresa,
            sucursal=self.sucursal,
            usuario_responsable=self.usuario,
            fondo_efectivo=100,
            fondo_vales=0,
        )

    def test_command_runs_without_mutating_counts(self):
        before = {
            "productos": Producto.objects.count(),
            "lotes": Lote.objects.count(),
            "aperturas": AperturaCaja.objects.count(),
        }
        out = StringIO()

        call_command(
            "auditoria_segura_farmacia",
            "--empresa-id",
            str(self.empresa.id),
            "--username",
            "audit_farmacia",
            "--password",
            "Audit12345!",
            stdout=out,
        )

        after = {
            "productos": Producto.objects.count(),
            "lotes": Lote.objects.count(),
            "aperturas": AperturaCaja.objects.count(),
        }

        self.assertEqual(before, after)
        output = out.getvalue()
        self.assertIn("AUDITORIA SEGURA FARMACIA", output)
        self.assertIn("snapshot_farmacia", output)
        self.assertIn("Login correcto", output)
