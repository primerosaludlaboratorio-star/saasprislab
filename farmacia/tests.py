"""
Unit tests for the farmacia module.
"""
import uuid
from copy import copy
from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import Client, TestCase
from django.urls import reverse

# Python 3.14 + Django 5.0.x: copy.copy(RenderContext) rompe en Context.__copy__;
# el Client de tests dispara template_rendered y hace copy(context) → AttributeError.
import django.test.client as _dj_test_client


def _store_rendered_templates_safe(store, signal, sender, template, context, **kwargs):
    from django.template.context import BaseContext

    store.setdefault("templates", []).append(template)
    if "context" not in store:
        store["context"] = _dj_test_client.ContextList()
    try:
        store["context"].append(copy(context))
    except AttributeError:
        if isinstance(context, BaseContext):
            store["context"].append(context)
        else:
            raise


_dj_test_client.store_rendered_templates = _store_rendered_templates_safe

from core.models import Empresa, Lote, Producto
from farmacia.models import MovimientoInventario, Proveedor

User = get_user_model()


def _codigo_barras_unico():
    return f"75{uuid.uuid4().hex[:12]}"


def _fecha_caducidad_valida():
    return date.today() + timedelta(days=180)


class FarmaciaModelTests(TestCase):
    """Test farmacia models."""

    def setUp(self):
        self.empresa = Empresa.objects.create(
            nombre="Test Empresa",
            rfc="TES123456ABC",
        )
        self.usuario = User.objects.create_user(
            username="test_farmacia",
            password="test123",
            email="farmacia@test.com",
            empresa=self.empresa,
        )
        self.producto = Producto.objects.create(
            empresa=self.empresa,
            nombre="Paracetamol 500mg",
            codigo_barras=_codigo_barras_unico(),
            forma_farmaceutica="Tabletas",
            concentracion="500mg",
            presentacion="20 tabletas",
            precio_publico=Decimal("50.00"),
            stock=0,
        )
        self.lote = Lote.objects.create(
            producto=self.producto,
            numero_lote="LOT001",
            fecha_caducidad=_fecha_caducidad_valida(),
            cantidad=100,
            costo_adquisicion=Decimal("5.00"),
        )
        self.client = Client()

    def test_proveedor_creation(self):
        proveedor = Proveedor.objects.create(
            empresa=self.empresa,
            razon_social="Farmacéutica ABC",
            rfc="ABC123456DEF",
        )
        self.assertIsNotNone(proveedor.id)
        self.assertEqual(proveedor.razon_social, "Farmacéutica ABC")
        self.assertEqual(proveedor.empresa, self.empresa)

    def test_proveedor_string_representation(self):
        proveedor = Proveedor.objects.create(
            empresa=self.empresa,
            razon_social="Farmacéutica XYZ",
            rfc="XYZ123456DEF",
        )
        str_repr = str(proveedor)
        self.assertIsInstance(str_repr, str)
        self.assertGreater(len(str_repr), 0)

    def test_movimiento_inventario_creation(self):
        movimiento = MovimientoInventario.objects.create(
            empresa=self.empresa,
            producto=self.producto,
            lote=self.lote,
            tipo_movimiento="ENTRADA_COMPRA",
            cantidad=Decimal("50"),
            costo_unitario=Decimal("10.00"),
            observaciones="Test unitario (sin proveedor)",
            usuario_responsable=self.usuario,
        )
        self.assertIsNotNone(movimiento.id)
        self.assertEqual(movimiento.producto, self.producto)
        self.assertEqual(movimiento.lote, self.lote)
        self.assertEqual(movimiento.tipo_movimiento, "ENTRADA_COMPRA")
        self.assertEqual(movimiento.cantidad, Decimal("50"))

    def test_producto_creation(self):
        producto = Producto.objects.create(
            empresa=self.empresa,
            nombre="Ibuprofeno 400mg",
            codigo_barras=_codigo_barras_unico(),
            forma_farmaceutica="Tabletas",
            concentracion="400mg",
            presentacion="10 tabletas",
            precio_publico=Decimal("75.00"),
        )
        self.assertIsNotNone(producto.id)
        self.assertEqual(producto.nombre, "Ibuprofeno 400mg")
        self.assertEqual(producto.empresa, self.empresa)

    def test_lote_creation(self):
        nuevo_lote = Lote.objects.create(
            producto=self.producto,
            numero_lote="LOT002",
            fecha_caducidad=_fecha_caducidad_valida(),
            cantidad=200,
            costo_adquisicion=Decimal("4.50"),
        )
        self.assertIsNotNone(nuevo_lote.id)
        self.assertEqual(nuevo_lote.producto, self.producto)
        self.assertEqual(nuevo_lote.numero_lote, "LOT002")

    def test_lote_empresa_denormalizada_coincide_producto(self):
        nuevo = Lote.objects.create(
            producto=self.producto,
            numero_lote="LOT-EMP",
            fecha_caducidad=_fecha_caducidad_valida(),
            cantidad=5,
            costo_adquisicion=Decimal("1.00"),
        )
        nuevo.refresh_from_db()
        self.assertEqual(nuevo.empresa_id, self.producto.empresa_id)


class FarmaciaViewTests(TestCase):
    """Test farmacia views (URLs actuales en config/urls y farmacia.urls)."""

    def setUp(self):
        self.empresa = Empresa.objects.create(
            nombre="Test Empresa",
            rfc="TES123456ABC",
        )
        self.usuario = User.objects.create_user(
            username="test_farmacia",
            password="test123",
            email="farmacia@test.com",
            empresa=self.empresa,
        )
        self.producto = Producto.objects.create(
            empresa=self.empresa,
            nombre="Paracetamol 500mg",
            codigo_barras=_codigo_barras_unico(),
            forma_farmaceutica="Tabletas",
            concentracion="500mg",
            presentacion="20 tabletas",
            precio_publico=Decimal("50.00"),
            stock=0,
        )
        Lote.objects.create(
            producto=self.producto,
            numero_lote="LOT001",
            fecha_caducidad=_fecha_caducidad_valida(),
            cantidad=100,
            costo_adquisicion=Decimal("5.00"),
        )
        self.client = Client()
        self.usuario.empresa = self.empresa
        self.usuario.rol = "CAJERO"
        self.usuario.save(update_fields=["empresa", "rol"])
        g, _ = Group.objects.get_or_create(name="FARMACIA")
        self.usuario.groups.add(g)
        self.client.force_login(self.usuario)

    def test_pdv_farmacia_view(self):
        url = reverse("pdv_farmacia")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_farmacia_inventario_general_view(self):
        url = reverse("farmacia_inventario_general")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_kardex_list_view(self):
        url = reverse("farmacia:kardex_list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_views_require_authentication(self):
        self.client.logout()
        url = reverse("pdv_farmacia")
        response = self.client.get(url)
        self.assertIn(response.status_code, (302, 403))

    def test_pdv_deniega_usuario_sin_empresa(self):
        u = User.objects.create_user(
            username="sin_empresa",
            password="x",
            email="x@test.com",
        )
        u.rol = "CAJERO"
        u.save(update_fields=["rol"])
        g, _ = Group.objects.get_or_create(name="FARMACIA")
        u.groups.add(g)
        User.objects.filter(pk=u.pk).update(empresa_id=None)
        u = User.objects.get(pk=u.pk)
        self.client.force_login(u)
        r = self.client.get(reverse("pdv_farmacia"))
        self.assertEqual(r.status_code, 302)

    def test_venta_farmacia_service_module(self):
        from farmacia.services import venta_farmacia_service

        self.assertTrue(hasattr(venta_farmacia_service, "ejecutar_venta_pdv"))
