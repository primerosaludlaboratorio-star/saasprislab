"""Regresiones para corte de caja unificado de Farmacia."""
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase

from core.models import Empresa, Paciente, Sucursal, Venta
from farmacia.models import AperturaCaja, CierreTurnoFarmacia
from farmacia.services.corte_caja_unificado import cerrar_turno_unificado


User = get_user_model()


class CorteCajaUnificadoTest(TestCase):
    def setUp(self):
        self.empresa = Empresa.objects.create(
            nombre='Empresa Corte',
            rfc='COR123456789',
        )
        self.sucursal = Sucursal.objects.create(
            empresa=self.empresa,
            nombre='Sucursal Corte',
            codigo_sucursal='SUC-COR-001',
        )
        self.user = User.objects.create_user(
            username='cajero_corte',
            password='cajero_corte_123',
            email='cajero-corte@example.com',
            rol='ADMIN',
            empresa=self.empresa,
            sucursal=self.sucursal,
            is_staff=True,
        )
        self.paciente = Paciente.objects.create(
            nombres='Cliente',
            apellido_paterno='Corte',
            nombre_completo='Cliente Corte',
            empresa=self.empresa,
            sucursal=self.sucursal,
        )
        self.apertura = AperturaCaja.objects.create(
            empresa=self.empresa,
            sucursal=self.sucursal,
            usuario_responsable=self.user,
            fondo_efectivo=Decimal('100.00'),
            fondo_vales=Decimal('0.00'),
        )
        self.venta = Venta.objects.create(
            empresa=self.empresa,
            sucursal=self.sucursal,
            usuario=self.user,
            paciente=self.paciente,
            total=Decimal('80.00'),
            subtotal=Decimal('80.00'),
            estado='COMPLETADA',
        )

    def test_corte_unificado_crea_cierre_formal_y_cierra_apertura(self):
        corte = cerrar_turno_unificado(
            cajero=self.user,
            empresa=self.empresa,
            sucursal=self.sucursal,
            efectivo_declarado=Decimal('180.00'),
            imprimir_ticket=False,
        )

        self.apertura.refresh_from_db()
        cierre = CierreTurnoFarmacia.objects.get(apertura_caja=self.apertura)

        self.assertFalse(self.apertura.activa)
        self.assertEqual(self.apertura.cerrada_con, cierre)
        self.assertEqual(cierre.efectivo_teorico, Decimal('80.00'))
        self.assertEqual(cierre.efectivo_declarado, Decimal('180.00'))
        self.assertEqual(cierre.diferencia_efectivo, Decimal('0.00'))
        self.assertEqual(corte['farmacia']['cierre_id'], cierre.id)
        self.assertEqual(corte['fondo_inicial'], '100.00')
        self.assertEqual(corte['efectivo_esperado'], '180.00')
        self.assertEqual(corte['diferencia'], '0.00')

    def test_corte_unificado_no_duplica_cierre_si_no_hay_apertura_activa(self):
        cerrar_turno_unificado(
            cajero=self.user,
            empresa=self.empresa,
            sucursal=self.sucursal,
            efectivo_declarado=Decimal('180.00'),
            imprimir_ticket=False,
        )
        segundo = cerrar_turno_unificado(
            cajero=self.user,
            empresa=self.empresa,
            sucursal=self.sucursal,
            efectivo_declarado=Decimal('180.00'),
            imprimir_ticket=False,
        )

        self.assertEqual(CierreTurnoFarmacia.objects.filter(apertura_caja=self.apertura).count(), 1)
        self.assertEqual(segundo['farmacia']['estado'], 'sin_apertura')
