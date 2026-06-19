import json
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from core.models import AuditLog, DetalleVenta, Empresa, Producto, Venta


Usuario = get_user_model()


class DashboardUnificadoTest(TestCase):
    def setUp(self):
        self.empresa = Empresa.objects.create(
            nombre='Empresa Dashboard',
            rfc='DAS260507TST',
        )
        self.usuario = Usuario.objects.create_user(
            username='dashboard_user',
            password='test123456789',
            empresa=self.empresa,
        )
        self.client.login(username='dashboard_user', password='test123456789')

    def test_dashboard_consolida_ventas_costos_y_auditoria(self):
        producto = Producto.objects.create(
            empresa=self.empresa,
            nombre='Reactivo smoke',
            codigo_barras='DASH-001',
            forma_farmaceutica='Caja',
            concentracion='1 unidad',
            presentacion='Caja',
            precio_compra=Decimal('30.00'),
            precio_publico=Decimal('50.00'),
            stock=4,
            stock_minimo=5,
        )
        venta = Venta.objects.create(
            empresa=self.empresa,
            usuario=self.usuario,
            subtotal=Decimal('100.00'),
            total=Decimal('100.00'),
            estado='COMPLETADA',
        )
        DetalleVenta.objects.create(
            venta=venta,
            producto=producto,
            cantidad=2,
            precio_unitario=Decimal('50.00'),
            subtotal=Decimal('100.00'),
            costo_unitario_momento=Decimal('30.00'),
        )
        AuditLog.objects.create(
            empresa=self.empresa,
            usuario=self.usuario,
            accion=AuditLog.ACCION_CREATE,
            modelo_afectado='Venta',
            objeto_id=str(venta.id),
        )

        response = self.client.get(reverse('dashboard_unificado'))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['total_ventas'], Decimal('100.00'))
        self.assertEqual(response.context['total_compras'], Decimal('60.00'))
        self.assertEqual(response.context['utilidad_bruta'], Decimal('40.00'))
        self.assertEqual(response.context['total_operaciones'], 1)

        operaciones = json.loads(response.context['datos_operaciones_modulo'])
        self.assertIn('Venta', operaciones['labels'])

        api_response = self.client.get(reverse('api_kpis_tiempo_real'), follow=True)
        self.assertIn(api_response.status_code, [200, 301, 302])
        data = api_response.json()
        self.assertEqual(data['ventas_hoy'], 100.0)
        self.assertEqual(data['cantidad_ventas_hoy'], 1)
        self.assertEqual(data['operaciones_hoy'], 1)
