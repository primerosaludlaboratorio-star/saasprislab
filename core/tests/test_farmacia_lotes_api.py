"""Regresiones de contrato para endpoints de lotes Farmacia core/ERP."""
from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import Client, TestCase

from core.models import Empresa, Lote, Producto, Sucursal


User = get_user_model()


class FarmaciaLotesAPITest(TestCase):
    def setUp(self):
        self.client = Client()
        self.empresa = Empresa.objects.create(
            nombre='Empresa Lotes',
            rfc='LOT123456789',
        )
        self.sucursal = Sucursal.objects.create(
            empresa=self.empresa,
            nombre='Sucursal Lotes',
            codigo_sucursal='SUC-LOT-001',
        )
        self.user = User.objects.create_user(
            username='farmacia_lotes',
            password='farmacia_lotes_123',
            email='farmacia-lotes@example.com',
            rol='ADMIN',
            empresa=self.empresa,
            sucursal=self.sucursal,
            is_staff=True,
        )
        self.producto = Producto.objects.create(
            nombre='Paracetamol 500mg',
            codigo_barras='7500000000011',
            empresa=self.empresa,
            sucursal=self.sucursal,
            forma_farmaceutica='Tabletas',
            concentracion='500mg',
            presentacion='20 tabletas',
            precio_publico=Decimal('45.00'),
            precio_compra=Decimal('20.00'),
            stock=5,
        )
        Lote.objects.create(
            producto=self.producto,
            numero_lote='LOT-VIGENTE',
            cantidad=3,
            empresa=self.empresa,
            fecha_caducidad=date.today() + timedelta(days=365),
            costo_adquisicion=Decimal('19.50'),
        )
        Lote.objects.create(
            producto=self.producto,
            numero_lote='LOT-POSTERIOR',
            cantidad=2,
            empresa=self.empresa,
            fecha_caducidad=date.today() + timedelta(days=730),
            costo_adquisicion=Decimal('18.00'),
        )
        self.client.login(username='farmacia_lotes', password='farmacia_lotes_123')

    def _assert_lotes_contract(self, data):
        self.assertIn('producto', data)
        self.assertIn('lotes', data)
        self.assertIsInstance(data['lotes'], list)
        self.assertGreaterEqual(len(data['lotes']), 2)

        producto = data['producto']
        self.assertEqual(producto['id'], self.producto.id)
        self.assertIn('stock_total', producto)
        self.assertIn('lote_id', producto)
        self.assertIn('numero_lote_proximo', producto)
        self.assertIn('sin_stock_vigente', producto)

        lote = data['lotes'][0]
        self.assertIn('id', lote)
        self.assertIn('numero_lote', lote)
        self.assertIn('fecha_caducidad', lote)
        self.assertIn('cantidad', lote)
        self.assertIn('costo_adquisicion', lote)
        self.assertIn('dias_restantes', lote)
        self.assertIn('es_vencido', lote)

    def test_core_lotes_producto_expone_contrato_completo(self):
        response = self.client.get(f'/farmacia/api/lotes-producto/{self.producto.id}/')

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self._assert_lotes_contract(data)
        self.assertEqual(data['producto']['stock_total'], 5)
        self.assertEqual(data['producto']['numero_lote_proximo'], 'LOT-VIGENTE')

    def test_erp_lotes_producto_mantiene_contrato_completo(self):
        response = self.client.get(f'/farmacia/erp/api/lotes-producto/{self.producto.id}/')

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self._assert_lotes_contract(data)
        self.assertEqual(data['producto']['stock_total'], 5.0)
        self.assertEqual(data['producto']['stock_total_fisico'], 5.0)
