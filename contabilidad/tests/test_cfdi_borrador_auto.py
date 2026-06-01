"""Hito 16 Fase 2 — borradores CFDI automáticos desde cobro lab / venta PDV."""
import uuid
from decimal import Decimal

from django.test import TransactionTestCase

from contabilidad.models import FacturaCFDI
from contabilidad.services.cfdi_borrador_auto import (
    crear_borrador_cfdi_desde_pago_orden,
    crear_borrador_cfdi_desde_venta_farmacia,
)
from core.models import (
    DetalleOrden,
    DetalleVenta,
    Empresa,
    OrdenDeServicio,
    Paciente,
    PagoOrden,
    Producto,
    Venta,
)


class CfdiBorradorLabTests(TransactionTestCase):
    def setUp(self):
        self.empresa = Empresa.objects.create(nombre='Empresa CFDI Lab')
        self.user = self._create_user()
        self.paciente = Paciente.objects.create(
            empresa=self.empresa,
            nombre_completo='Paciente Prueba',
            nombres='P',
            apellido_paterno='T',
        )

    def _create_user(self):
        from core.models import Usuario

        return Usuario.objects.create_user(
            username='cajero_lab_cfdi',
            password='testpass123',
            empresa=self.empresa,
        )

    def test_pago_orden_crea_borrador_total_igual_monto(self):
        orden = OrdenDeServicio.objects.create(
            empresa=self.empresa,
            paciente=self.paciente,
            total=Decimal('116.00'),
            anticipo=Decimal('0.00'),
            estado='PAGADO',
            estado_pago='PAGADO',
            responsable_ingreso=self.user,
        )
        DetalleOrden.objects.create(
            orden=orden,
            descripcion_linea='Perfil básico',
            precio_momento=Decimal('116.00'),
        )
        monto = Decimal('116.00')
        pago = PagoOrden.objects.create(
            orden=orden,
            monto_efectivo=monto,
            monto_tarjeta=Decimal('0'),
            monto_transferencia=Decimal('0'),
            usuario_registro=self.user,
        )
        fac = crear_borrador_cfdi_desde_pago_orden(pago, self.user)
        self.assertIsNotNone(fac)
        self.assertEqual(fac.estado, 'BORRADOR')
        self.assertEqual(fac.pago_orden_id, pago.id)
        self.assertEqual(fac.orden_laboratorio_id, orden.id)
        self.assertEqual(fac.total, monto)
        self.assertEqual(fac.subtotal + fac.total_impuestos_trasladados, monto)

        dup = crear_borrador_cfdi_desde_pago_orden(pago, self.user)
        self.assertEqual(dup.id, fac.id)
        self.assertEqual(FacturaCFDI.objects.filter(pago_orden=pago).count(), 1)


class CfdiBorradorFarmaciaTests(TransactionTestCase):
    def setUp(self):
        self.empresa = Empresa.objects.create(nombre='Empresa CFDI PDV')
        from core.models import Usuario

        self.user = Usuario.objects.create_user(
            username='cajero_pdv_cfdi',
            password='testpass123',
            empresa=self.empresa,
        )
        self.producto = Producto.objects.create(
            empresa=self.empresa,
            nombre='Paracetamol',
            codigo_barras=f'CFDI-TEST-{uuid.uuid4().hex[:10]}',
            forma_farmaceutica='Tabletas',
            concentracion='500mg',
            presentacion='10',
            precio_publico=Decimal('50.00'),
            precio_compra=Decimal('20.00'),
        )

    def test_venta_crea_borrador_totales_alineados(self):
        sub = Decimal('100.00')
        iva = Decimal('16.00')
        total = Decimal('116.00')
        venta = Venta.objects.create(
            empresa=self.empresa,
            usuario=self.user,
            subtotal=sub,
            impuestos_iva=iva,
            redondeo=Decimal('0.00'),
            total=total,
            estado='COMPLETADA',
        )
        DetalleVenta.objects.create(
            venta=venta,
            producto=self.producto,
            cantidad=2,
            precio_unitario=Decimal('50.00'),
            subtotal=sub,
            iva_aplicado=iva,
            lote_vendido=None,
        )
        fac = crear_borrador_cfdi_desde_venta_farmacia(venta, self.user)
        self.assertIsNotNone(fac)
        self.assertEqual(fac.estado, 'BORRADOR')
        self.assertEqual(fac.venta_farmacia_id, venta.id)
        self.assertEqual(fac.total, total)
        self.assertEqual(fac.subtotal, sub)
        self.assertEqual(fac.total_impuestos_trasladados, iva)
