"""Regresiones del flujo visible de baja por caducidad en Farmacia."""
from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import Client, TestCase

from core.models import Empresa, Lote, Producto, Sucursal
from farmacia.models import MotivoAjuste, MovimientoInventario


User = get_user_model()


class BajaCaducidadFarmaciaTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.empresa = Empresa.objects.create(
            nombre='Empresa Caducidad',
            rfc='CAD123456789',
        )
        self.sucursal = Sucursal.objects.create(
            empresa=self.empresa,
            nombre='Sucursal Caducidad',
            codigo_sucursal='SUC-CAD-001',
        )
        self.user = User.objects.create_user(
            username='farmacia_caducidad',
            password='farmacia_caducidad_123',
            rol='ADMIN',
            empresa=self.empresa,
            sucursal=self.sucursal,
            is_staff=True,
        )
        self.producto = Producto.objects.create(
            nombre='Producto Caducado',
            codigo_barras='7500000000099',
            empresa=self.empresa,
            sucursal=self.sucursal,
            presentacion='10 piezas',
            precio_publico=Decimal('30.00'),
            precio_compra=Decimal('12.00'),
            stock=3,
        )
        self.lote = Lote.objects.create(
            producto=self.producto,
            numero_lote='CAD-001',
            cantidad=3,
            empresa=self.empresa,
            fecha_caducidad=date.today() - timedelta(days=1),
            costo_adquisicion=Decimal('12.00'),
        )
        self.motivo = MotivoAjuste.objects.create(
            empresa=self.empresa,
            codigo='MERMA_CADUCIDAD',
            descripcion='Merma por caducidad',
            activo=True,
        )
        self.client.login(username='farmacia_caducidad', password='farmacia_caducidad_123')

    def test_alerta_ofrece_flujo_real_y_baja_actualiza_lote(self):
        alerta = self.client.get('/farmacia/erp/alertas/')
        self.assertEqual(alerta.status_code, 200)
        self.assertContains(alerta, f'/farmacia/erp/kardex/crear-movimiento/?lote={self.lote.id}&tipo=MERMA')

        response = self.client.post('/farmacia/erp/kardex/crear-movimiento/', {
            'producto_id': self.producto.id,
            'lote_id': self.lote.id,
            'tipo_movimiento': 'SALIDA_MERMA',
            'cantidad': '3',
            'costo_unitario': '12.00',
            'motivo_ajuste_id': self.motivo.id,
            'observaciones': 'Baja por caducidad verificada en inventario físico.',
        })

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['status'], 'success')
        self.lote.refresh_from_db()
        self.producto.refresh_from_db()
        self.assertEqual(self.lote.cantidad, Decimal('0'))
        self.assertEqual(self.producto.stock, Decimal('0'))
        self.assertTrue(MovimientoInventario.objects.filter(
            lote=self.lote,
            tipo_movimiento='SALIDA_MERMA',
        ).exists())

    def test_baja_sin_lote_devuelve_error_operativo_no_500(self):
        response = self.client.post('/farmacia/erp/kardex/crear-movimiento/', {
            'producto_id': self.producto.id,
            'tipo_movimiento': 'SALIDA_MERMA',
            'cantidad': '1',
            'costo_unitario': '12.00',
            'observaciones': 'Intento sin lote.',
        })

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['status'], 'error')
