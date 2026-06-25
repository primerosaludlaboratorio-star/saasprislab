"""
Unit tests for the farmacia module.
"""
import io
import json
import uuid
from copy import copy
from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError
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

from core.models import ConfiguracionModulos, DetalleVenta, Empresa, Lote, Producto, Sucursal, Venta
from farmacia.models import (
    AperturaCaja, DevolucionVenta, MovimientoInventario, Proveedor,
    RegistroAntibiotico,
)

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
        self.sucursal = Sucursal.objects.create(
            empresa=self.empresa,
            nombre="Matriz",
            codigo_sucursal=f"SUC-{uuid.uuid4().hex[:8]}",
            activa=True,
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
        self.usuario.sucursal = self.sucursal
        self.usuario.save(update_fields=["empresa", "rol", "sucursal"])
        g, _ = Group.objects.get_or_create(name="FARMACIA")
        self.usuario.groups.add(g)
        self.client.force_login(self.usuario)

    def test_pdv_farmacia_view(self):
        url = reverse("pdv_farmacia")
        response = self.client.get(url, follow=True)
        self.assertIn(response.status_code, [200, 301, 302])

    def test_pdv_template_exposes_active_api_urls(self):
        response = self.client.get(reverse("pdv_farmacia"), follow=True)
        self.assertContains(response, "/farmacia/api/validar-pin-neto/")
        self.assertContains(response, "/farmacia/api/validar-cupon/")
        self.assertContains(response, "/api/pacientes/buscar/")

    def test_validar_pin_precio_neto_ok(self):
        self.usuario.rol = "ADMIN"
        self.usuario.save(update_fields=["rol"])
        ConfiguracionModulos.objects.update_or_create(
            empresa=self.empresa,
            defaults={"pin_precio_neto": "1234"},
        )
        response = self.client.post(
            reverse("validar_pin_precio_neto"),
            data='{"pin":"1234"}',
            content_type="application/json",
            secure=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "success")
        self.assertTrue(response.json()["autorizado"])

    def test_validar_pin_precio_neto_rechaza_pin_incorrecto(self):
        self.usuario.rol = "ADMIN"
        self.usuario.save(update_fields=["rol"])
        ConfiguracionModulos.objects.update_or_create(
            empresa=self.empresa,
            defaults={"pin_precio_neto": "1234"},
        )
        response = self.client.post(
            reverse("validar_pin_precio_neto"),
            data='{"pin":"9999"}',
            content_type="application/json",
            secure=True,
        )
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["status"], "error")
        self.assertFalse(response.json()["autorizado"])

    def test_farmacia_inventario_general_view(self):
        url = reverse("farmacia_inventario_general")
        response = self.client.get(url, follow=True)
        self.assertIn(response.status_code, [200, 301, 302])

    def test_kardex_list_view(self):
        url = reverse("farmacia:kardex_list")
        response = self.client.get(url, follow=True)
        self.assertIn(response.status_code, [200, 301, 302])

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

    def test_buscar_venta_devolucion_precarga_venta_desde_historial(self):
        venta = Venta.objects.create(
            empresa=self.empresa,
            sucursal=self.sucursal,
            usuario=self.usuario,
            paciente_nombre="Publico General",
            total=Decimal("120.00"),
            subtotal=Decimal("120.00"),
        )
        DetalleVenta.objects.create(
            venta=venta,
            producto=self.producto,
            lote_vendido=Lote.objects.get(numero_lote="LOT001"),
            cantidad=2,
            precio_unitario=Decimal("60.00"),
            subtotal=Decimal("120.00"),
        )

        self.usuario.rol = "GERENTE"
        self.usuario.save(update_fields=["rol"])

        response = self.client.get(
            reverse("farmacia:buscar_venta_devolucion"),
            {"venta_id": venta.id},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, venta.folio_operacion)
        self.assertContains(response, "venta-prefill-data")

    def test_procesar_devolucion_parcial_rechaza_sin_detalle_por_producto(self):
        self.usuario.rol = "GERENTE"
        self.usuario.save(update_fields=["rol"])

        venta = Venta.objects.create(
            empresa=self.empresa,
            sucursal=self.sucursal,
            usuario=self.usuario,
            paciente_nombre="Publico General",
            total=Decimal("120.00"),
            subtotal=Decimal("120.00"),
        )
        DetalleVenta.objects.create(
            venta=venta,
            producto=self.producto,
            lote_vendido=Lote.objects.get(numero_lote="LOT001"),
            cantidad=2,
            precio_unitario=Decimal("60.00"),
            subtotal=Decimal("120.00"),
        )

        response = self.client.post(
            reverse("farmacia:procesar_devolucion"),
            data='{"venta_id": %d, "tipo": "PARCIAL", "monto": "60.00", "motivo": "ERROR_VENTA"}' % venta.id,
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)
        payload = response.json()
        self.assertEqual(payload["codigo"], "DEVOLUCION_PARCIAL_REQUIERE_DETALLE")
        self.assertEqual(DevolucionVenta.objects.count(), 0)
        self.assertEqual(MovimientoInventario.objects.filter(tipo_movimiento="ENTRADA_DEVOLUCION").count(), 0)

    def test_modelo_devolucion_parcial_no_procesa_stock_sin_detalle(self):
        venta = Venta.objects.create(
            empresa=self.empresa,
            sucursal=self.sucursal,
            usuario=self.usuario,
            paciente_nombre="Publico General",
            total=Decimal("80.00"),
            subtotal=Decimal("80.00"),
        )
        detalle = DetalleVenta.objects.create(
            venta=venta,
            producto=self.producto,
            lote_vendido=Lote.objects.get(numero_lote="LOT001"),
            cantidad=1,
            precio_unitario=Decimal("80.00"),
            subtotal=Decimal("80.00"),
        )
        devolucion = DevolucionVenta.objects.create(
            empresa=self.empresa,
            sucursal=self.sucursal,
            venta_original=venta,
            tipo="PARCIAL",
            motivo="ERROR_VENTA",
            motivo_detallado="Prueba de blindaje",
            monto_devolucion=Decimal("40.00"),
            reingresar_a_stock=True,
            usuario_procesa=self.usuario,
            autorizado=True,
        )

        with self.assertRaises(ValidationError):
            devolucion.procesar_devolucion(usuario=self.usuario)

        devolucion.refresh_from_db()
        self.assertFalse(devolucion.procesada)
        self.assertEqual(detalle.cantidad, 1)


class FarmaciaAperturaCajaTests(TestCase):
    """Tests para apertura y verificación de caja."""

    def setUp(self):
        self.empresa = Empresa.objects.create(
            nombre="Test Apertura", rfc="APE123456ABC",
        )
        self.sucursal = Sucursal.objects.create(
            empresa=self.empresa, nombre="Matriz",
            codigo_sucursal=f"SUC-{uuid.uuid4().hex[:8]}", activa=True,
        )
        self.usuario = User.objects.create_user(
            username="cajero_test", password="test123",
            email="cajero@test.com", empresa=self.empresa,
        )
        self.usuario.rol = "CAJERO"
        self.usuario.sucursal = self.sucursal
        self.usuario.save(update_fields=["rol", "sucursal"])
        g, _ = Group.objects.get_or_create(name="FARMACIA")
        self.usuario.groups.add(g)
        self.client = Client()
        self.client.force_login(self.usuario)

    def test_verificar_apertura_caja_sin_caja_abierta(self):
        """Verificar que responde caja_abierta=False cuando no hay caja."""
        response = self.client.get(reverse("farmacia:verificar_apertura_caja"))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["success"])
        self.assertFalse(data["caja_abierta"])

    def test_verificar_apertura_caja_con_caja_abierta(self):
        """Verificar que detecta una caja ya abierta."""
        AperturaCaja.objects.create(
            empresa=self.empresa, sucursal=self.sucursal,
            usuario_responsable=self.usuario,
            fondo_efectivo=Decimal("500.00"), activa=True,
        )
        response = self.client.get(reverse("farmacia:verificar_apertura_caja"))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["success"])
        self.assertTrue(data["caja_abierta"])

    def test_abrir_caja_crea_apertura(self):
        """Abrir caja con fondo válido crea el registro."""
        response = self.client.post(
            reverse("farmacia:abrir_caja"),
            data='{"fondo_efectivo": "500.00", "fondo_vales": "0.00", "observaciones": "Test"}',
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["success"])
        self.assertIn("folio", data)
        self.assertEqual(AperturaCaja.objects.filter(empresa=self.empresa, activa=True).count(), 1)

    def test_abrir_caja_rechaza_fondo_cero(self):
        """No permite abrir caja con fondo <= 0."""
        response = self.client.post(
            reverse("farmacia:abrir_caja"),
            data='{"fondo_efectivo": "0.00"}',
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertFalse(response.json()["success"])

    def test_abrir_caja_rechaza_duplicada(self):
        """No permite abrir una segunda caja si ya hay una activa."""
        AperturaCaja.objects.create(
            empresa=self.empresa, sucursal=self.sucursal,
            usuario_responsable=self.usuario,
            fondo_efectivo=Decimal("300.00"), activa=True,
        )
        response = self.client.post(
            reverse("farmacia:abrir_caja"),
            data='{"fondo_efectivo": "500.00"}',
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertFalse(response.json()["success"])

    def test_verificar_apertura_requiere_empresa(self):
        """Usuario sin empresa recibe 403."""
        u = User.objects.create_user(
            username="sin_emp", password="x", email="x@t.com",
        )
        u.rol = "CAJERO"
        u.save(update_fields=["rol"])
        g, _ = Group.objects.get_or_create(name="FARMACIA")
        u.groups.add(g)
        User.objects.filter(pk=u.pk).update(empresa_id=None)
        u = User.objects.get(pk=u.pk)
        self.client.force_login(u)
        response = self.client.get(reverse("farmacia:verificar_apertura_caja"))
        self.assertEqual(response.status_code, 403)


class FarmaciaCorteCajaTests(TestCase):
    """Tests para corte de caja (arqueo ciego)."""

    def setUp(self):
        self.empresa = Empresa.objects.create(
            nombre="Test Corte", rfc="COR123456ABC",
        )
        self.sucursal = Sucursal.objects.create(
            empresa=self.empresa, nombre="Matriz",
            codigo_sucursal=f"SUC-{uuid.uuid4().hex[:8]}", activa=True,
        )
        self.usuario = User.objects.create_user(
            username="cajero_corte", password="test123",
            email="corte@test.com", empresa=self.empresa,
        )
        self.usuario.rol = "CAJERO"
        self.usuario.sucursal = self.sucursal
        self.usuario.save(update_fields=["rol", "sucursal"])
        g, _ = Group.objects.get_or_create(name="FARMACIA")
        self.usuario.groups.add(g)
        self.client = Client()
        self.client.force_login(self.usuario)

    def test_corte_caja_get_muestra_formulario(self):
        """GET al corte de caja carga (puede ser 200 o redirect si falta template)."""
        response = self.client.get(reverse("farmacia:corte_caja"), follow=True)
        self.assertIn(response.status_code, [200, 301, 302])

    def test_corte_caja_post_procesa_arqueo(self):
        """POST con datos válidos procesa el corte."""
        response = self.client.post(
            reverse("farmacia:corte_caja"),
            data={
                "efectivo_declarado": "100.00",
                "tarjeta_declarada": "0.00",
                "transferencia_declarada": "0.00",
                "observaciones_corte": "Test arqueo",
            },
            follow=True,
        )
        self.assertIn(response.status_code, [200, 301, 302])

    def test_corte_caja_sin_empresa_redirige(self):
        """Usuario sin empresa es redirigido."""
        u = User.objects.create_user(
            username="sin_emp_corte", password="x", email="x@t.com",
        )
        u.rol = "CAJERO"
        u.save(update_fields=["rol"])
        g, _ = Group.objects.get_or_create(name="FARMACIA")
        u.groups.add(g)
        User.objects.filter(pk=u.pk).update(empresa_id=None)
        u = User.objects.get(pk=u.pk)
        self.client.force_login(u)
        response = self.client.get(reverse("farmacia:corte_caja"))
        self.assertEqual(response.status_code, 302)


class FarmaciaEntradaExpressTests(TestCase):
    """Tests para entrada express (fast restock)."""

    def setUp(self):
        self.empresa = Empresa.objects.create(
            nombre="Test Express", rfc="EXP123456ABC",
        )
        self.sucursal = Sucursal.objects.create(
            empresa=self.empresa, nombre="Matriz",
            codigo_sucursal=f"SUC-{uuid.uuid4().hex[:8]}", activa=True,
        )
        self.usuario = User.objects.create_user(
            username="cajero_expr", password="test123",
            email="expr@test.com", empresa=self.empresa,
        )
        self.usuario.rol = "CAJERO"
        self.usuario.sucursal = self.sucursal
        self.usuario.save(update_fields=["rol", "sucursal"])
        g, _ = Group.objects.get_or_create(name="FARMACIA")
        self.usuario.groups.add(g)
        self.producto = Producto.objects.create(
            empresa=self.empresa, nombre="Ibuprofeno 400mg",
            codigo_barras=_codigo_barras_unico(),
            forma_farmaceutica="Tabletas", concentracion="400mg",
            presentacion="10 tabletas", precio_publico=Decimal("75.00"),
            stock=0,
        )
        self.client = Client()
        self.client.force_login(self.usuario)

    def test_entrada_express_agrega_stock(self):
        """Entrada express válida crea lote y movimiento."""
        payload = {
            "codigo_barras": self.producto.codigo_barras,
            "cantidad": 50,
            "numero_lote": "LOTE-EXP-001",
            "fecha_caducidad": (_fecha_caducidad_valida()).strftime("%Y-%m-%d"),
            "precio_compra": "5.50",
        }
        response = self.client.post(
            reverse("farmacia:entrada_express"),
            data=json.dumps(payload),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["success"])
        self.assertEqual(MovimientoInventario.objects.filter(
            tipo_movimiento="ENTRADA_COMPRA", empresa=self.empresa
        ).count(), 1)

    def test_entrada_express_rechaza_datos_incompletos(self):
        """Falta código de barras devuelve 400."""
        response = self.client.post(
            reverse("farmacia:entrada_express"),
            data='{"codigo_barras": "", "cantidad": 10, "numero_lote": "L1", "fecha_caducidad": "2027-01-01"}',
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertFalse(response.json()["success"])

    def test_entrada_express_rechaza_producto_no_encontrado(self):
        """Código de barras inexistente devuelve 404."""
        response = self.client.post(
            reverse("farmacia:entrada_express"),
            data=json.dumps({
                "codigo_barras": "9999999999999",
                "cantidad": 10, "numero_lote": "L1",
                "fecha_caducidad": "2027-01-01",
            }),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 404)

    def test_entrada_express_sin_empresa_rechaza(self):
        """Usuario sin empresa recibe 403."""
        u = User.objects.create_user(
            username="sin_emp_expr", password="x", email="x@t.com",
        )
        u.rol = "CAJERO"
        u.save(update_fields=["rol"])
        g, _ = Group.objects.get_or_create(name="FARMACIA")
        u.groups.add(g)
        User.objects.filter(pk=u.pk).update(empresa_id=None)
        u = User.objects.get(pk=u.pk)
        self.client.force_login(u)
        response = self.client.post(
            reverse("farmacia:entrada_express"),
            data='{"codigo_barras": "123", "cantidad": 10, "numero_lote": "L1", "fecha_caducidad": "2027-01-01"}',
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 403)


class FarmaciaCOFEPRISTests(TestCase):
    """Tests para validación COFEPRIS de antibióticos."""

    def setUp(self):
        self.empresa = Empresa.objects.create(
            nombre="Test COFEPRIS", rfc="COF123456ABC",
        )
        self.sucursal = Sucursal.objects.create(
            empresa=self.empresa, nombre="Matriz",
            codigo_sucursal=f"SUC-{uuid.uuid4().hex[:8]}", activa=True,
        )
        self.usuario = User.objects.create_user(
            username="cajero_cof", password="test123",
            email="cof@test.com", empresa=self.empresa,
        )
        self.usuario.rol = "CAJERO"
        self.usuario.sucursal = self.sucursal
        self.usuario.save(update_fields=["rol", "sucursal"])
        g, _ = Group.objects.get_or_create(name="FARMACIA")
        self.usuario.groups.add(g)
        self.producto_normal = Producto.objects.create(
            empresa=self.empresa, nombre="Paracetamol",
            codigo_barras=_codigo_barras_unico(),
            forma_farmaceutica="Tabletas", concentracion="500mg",
            presentacion="20 tab", precio_publico=Decimal("50.00"),
            stock=0, es_antibiotico=False,
        )
        self.producto_antibiotico = Producto.objects.create(
            empresa=self.empresa, nombre="Amoxicilina",
            codigo_barras=_codigo_barras_unico(),
            forma_farmaceutica="Cápsulas", concentracion="500mg",
            presentacion="12 cap", precio_publico=Decimal("120.00"),
            stock=0, es_antibiotico=True,
        )
        self.client = Client()
        self.client.force_login(self.usuario)

    def test_validar_antibiotico_producto_normal_no_requiere(self):
        """Producto no antibiótico retorna requiere_validacion=False."""
        response = self.client.post(
            reverse("farmacia:validar_antibiotico"),
            data=json.dumps({"producto_id": self.producto_normal.id}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["success"])
        self.assertFalse(data["requiere_validacion"])

    def test_validar_antibiotico_sin_medico_rechaza(self):
        """Antibiótico sin receta ni datos de médico es rechazado."""
        response = self.client.post(
            reverse("farmacia:validar_antibiotico"),
            data=json.dumps({"producto_id": self.producto_antibiotico.id}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertFalse(data["success"])
        self.assertTrue(data["requiere_validacion"])

    def test_validar_antibiotico_con_medico_ok(self):
        """Antibiótico con datos de médico es validado."""
        response = self.client.post(
            reverse("farmacia:validar_antibiotico"),
            data=json.dumps({
                "producto_id": self.producto_antibiotico.id,
                "medico_cedula": "12345678",
                "medico_nombre": "Dr. García",
            }),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["success"])
        self.assertTrue(data["validado"])

    def test_reporte_cofepris_get(self):
        """GET al reporte COFEPRIS carga la vista."""
        response = self.client.get(reverse("farmacia:reporte_cofepris"))
        self.assertEqual(response.status_code, 200)


class FarmaciaCargaMasivaTests(TestCase):
    """Tests para carga masiva de productos."""

    def setUp(self):
        self.empresa = Empresa.objects.create(
            nombre="Test Carga", rfc="CAR123456ABC",
        )
        self.sucursal = Sucursal.objects.create(
            empresa=self.empresa, nombre="Matriz",
            codigo_sucursal=f"SUC-{uuid.uuid4().hex[:8]}", activa=True,
        )
        self.usuario = User.objects.create_user(
            username="admin_carga", password="test123",
            email="carga@test.com", empresa=self.empresa,
        )
        self.usuario.rol = "ADMIN"
        self.usuario.sucursal = self.sucursal
        self.usuario.save(update_fields=["rol", "sucursal"])
        g, _ = Group.objects.get_or_create(name="FARMACIA")
        self.usuario.groups.add(g)
        self.client = Client()
        self.client.force_login(self.usuario)

    def test_carga_masiva_get_rechaza(self):
        """GET no permitido en carga masiva."""
        response = self.client.get(reverse("farmacia:carga_masiva_productos"))
        self.assertEqual(response.status_code, 405)

    def test_carga_masiva_sin_archivo_rechaza(self):
        """POST sin archivo devuelve 400."""
        response = self.client.post(reverse("farmacia:carga_masiva_productos"))
        self.assertEqual(response.status_code, 400)

    def test_carga_masiva_csv_valido(self):
        """CSV con productos válidos los importa."""
        csv_content = (
            "nombre,codigo_barras,precio_publico,precio_compra,stock\r\n"
            f"Test Producto A,{_codigo_barras_unico()},100.00,50.00,20\r\n"
            f"Test Producto B,{_codigo_barras_unico()},200.00,100.00,10\r\n"
        )
        csv_file = io.BytesIO(csv_content.encode("utf-8-sig"))
        csv_file.name = "productos_test.csv"
        response = self.client.post(
            reverse("farmacia:carga_masiva_productos"),
            {"archivo": csv_file},
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("creados", data)

    def test_carga_masiva_sin_archivo_rechaza_sin_empresa_directa(self):
        """Usuario sin empresa FK: _empresa_desde_request usa fallback del middleware,
        así que pasa el guard pero falla por falta de archivo."""
        u = User.objects.create_user(
            username="sin_emp_carga", password="x", email="x@t.com",
        )
        u.rol = "ADMIN"
        u.save(update_fields=["rol"])
        g, _ = Group.objects.get_or_create(name="FARMACIA")
        u.groups.add(g)
        User.objects.filter(pk=u.pk).update(empresa_id=None)
        u = User.objects.get(pk=u.pk)
        self.client.force_login(u)
        response = self.client.post(reverse("farmacia:carga_masiva_productos"))
        self.assertEqual(response.status_code, 400)
