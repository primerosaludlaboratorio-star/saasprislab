"""
Tests de regresión para el flujo de devoluciones de farmacia (core).
Verifica que el contrato UI/backend esté sincronizado y que la API
busque ventas por el parámetro que envía el frontend.
"""
import json
from decimal import Decimal
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from core.models import Empresa, Sucursal, Paciente, Producto, Lote, Venta, DetalleVenta

User = get_user_model()


class DevolucionesFarmaciaAPITest(TestCase):
    """Regresión para devoluciones de farmacia."""

    def setUp(self):
        self.client = Client()

        self.empresa = Empresa.objects.create(
            nombre='Empresa Devoluciones',
            rfc='DEV123456789'
        )
        self.sucursal = Sucursal.objects.create(
            empresa=self.empresa,
            nombre='Sucursal Devoluciones',
            codigo_sucursal='SUC-DEV-001'
        )

        self.admin_user = User.objects.create_user(
            username='admin_dev',
            password='admin_dev_123',
            email='admin@dev.com',
            rol='ADMIN',
            empresa=self.empresa,
            sucursal=self.sucursal,
            is_staff=True
        )
        Group.objects.get_or_create(name='Administrador')
        self.admin_user.groups.add(Group.objects.get(name='Administrador'))

        self.paciente = Paciente.objects.create(
            nombres='María',
            apellido_paterno='López',
            nombre_completo='María López',
            empresa=self.empresa,
            sucursal=self.sucursal,
            telefono='5555555555'
        )

        self.producto = Producto.objects.create(
            nombre='Ibuprofeno 400mg',
            codigo_barras='7501234567890',
            empresa=self.empresa,
            sucursal=self.sucursal,
            forma_farmaceutica='Tabletas',
            concentracion='400mg',
            presentacion='10 tabletas',
            precio_publico=Decimal('80.00'),
            stock=50
        )
        self.lote = Lote.objects.create(
            producto=self.producto,
            numero_lote='LOT-DEV-001',
            cantidad=50,
            empresa=self.empresa,
            fecha_caducidad='2030-12-31',
            costo_adquisicion=Decimal('40.00')
        )

        self.venta = Venta.objects.create(
            empresa=self.empresa,
            sucursal=self.sucursal,
            usuario=self.admin_user,
            paciente=self.paciente,
            total=Decimal('80.00'),
            subtotal=Decimal('80.00')
        )
        DetalleVenta.objects.create(
            venta=self.venta,
            producto=self.producto,
            cantidad=1,
            precio_unitario=Decimal('80.00'),
            subtotal=Decimal('80.00')
        )

        self.client.login(username='admin_dev', password='admin_dev_123')

    def test_buscar_venta_devolucion_por_busqueda(self):
        """El frontend envía ?busqueda=; la API debe responder con el contrato esperado."""
        response = self.client.get(
            f'/farmacia/devoluciones/buscar/?busqueda={self.venta.folio_operacion}'
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['status'], 'success')
        venta = data['venta']
        self.assertEqual(venta['id'], self.venta.id)
        self.assertEqual(venta['folio'], self.venta.folio_operacion)
        self.assertIn('cliente', venta)
        self.assertIn('cajero_original', venta)
        self.assertIn('detalles', venta)
        self.assertEqual(venta['cliente'], 'María López')
        self.assertEqual(len(venta['detalles']), 1)
        self.assertEqual(venta['detalles'][0]['producto_nombre'], 'Ibuprofeno 400mg')

    def test_procesar_devolucion_con_campos_frontend(self):
        """La API debe aceptar los nombres de campo que envía el frontend."""
        payload = {
            'venta_id': self.venta.id,
            'tipo_devolucion': 'TOTAL',
            'monto_reembolsado': '80.00',
            'motivo_error': 'Producto caducado',
            'accion_stock': 'REINGRESAR',
        }
        response = self.client.post(
            '/farmacia/devoluciones/procesar/',
            data=json.dumps(payload),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['status'], 'success')

    def test_procesar_devolucion_con_productos_auditoria(self):
        """El backend debe persistir el detalle de productos devueltos para auditoría."""
        from core.models import SalesReturn
        detalle = self.venta.detalles.first()
        payload = {
            'venta_id': self.venta.id,
            'tipo_devolucion': 'PARCIAL',
            'monto_reembolsado': '80.00',
            'motivo_error': 'Error de cobro',
            'accion_stock': 'REINGRESAR',
            'productos': [
                {'detalle_id': detalle.id, 'cantidad': 1, 'motivo': 'Producto equivocado'}
            ],
        }
        response = self.client.post(
            '/farmacia/devoluciones/procesar/',
            data=json.dumps(payload),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        devolucion = SalesReturn.objects.filter(venta_original=self.venta).first()
        self.assertIsNotNone(devolucion)
        self.assertIn('productos_devueltos', devolucion.observaciones or '')
