from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase

from core.agent.pris_tools_operativos import tool_registrar_venta_farmacia
from core.models import Empresa, Lote, Producto, Venta

User = get_user_model()


class PRISHerramientasOperativasSecurityTests(TestCase):
    def setUp(self):
        self.empresa = Empresa.objects.create(
            nombre="Empresa Seguridad",
            rfc="SEG123456ABC",
        )
        self.user = User.objects.create_user(
            username="auditor_pris",
            password="Pruebas123!",
            email="auditor@prislab.local",
            empresa=self.empresa,
        )
        self.producto = Producto.objects.create(
            empresa=self.empresa,
            nombre="Amoxicilina 500mg",
            codigo_barras="750000000001",
            forma_farmaceutica="Capsulas",
            concentracion="500mg",
            presentacion="12 capsulas",
            precio_publico=Decimal("120.00"),
            stock=10,
        )
        self.lote = Lote.objects.create(
            producto=self.producto,
            numero_lote="LOT-SEG-001",
            fecha_caducidad=date.today() + timedelta(days=180),
            cantidad=10,
            costo_adquisicion=Decimal("50.00"),
        )

    def test_rechaza_cantidad_negativa(self):
        respuesta = tool_registrar_venta_farmacia(
            {
                "productos": [{"id": self.producto.id, "cantidad": -2}],
                "confirmado": True,
            },
            self.empresa,
            self.user,
        )

        self.assertIn("error", respuesta)
        self.assertIn("mayor a cero", respuesta["error"])
        self.lote.refresh_from_db()
        self.assertEqual(self.lote.cantidad, 10)
        self.assertEqual(Venta.objects.count(), 0)

    def test_rechaza_cantidad_cero_explicita(self):
        respuesta = tool_registrar_venta_farmacia(
            {
                "productos": [{"id": self.producto.id, "cantidad": 0}],
                "confirmado": True,
            },
            self.empresa,
            self.user,
        )

        self.assertIn("error", respuesta)
        self.assertIn("mayor a cero", respuesta["error"])
        self.lote.refresh_from_db()
        self.assertEqual(self.lote.cantidad, 10)
        self.assertEqual(Venta.objects.count(), 0)
