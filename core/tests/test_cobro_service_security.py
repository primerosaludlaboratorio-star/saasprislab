from decimal import Decimal

from django.test import SimpleTestCase

from core.services.ventas.cobro_service import (
    porcentaje_descuento_autorizado,
    redondeo_efectivo_valido,
)


class CobroServiceSecurityTests(SimpleTestCase):
    def test_redondeo_efectivo_se_limita_a_cincuenta_centavos(self):
        self.assertTrue(redondeo_efectivo_valido(Decimal('0.50')))
        self.assertTrue(redondeo_efectivo_valido(Decimal('-0.50')))
        self.assertFalse(redondeo_efectivo_valido(Decimal('0.51')))
        self.assertFalse(redondeo_efectivo_valido(Decimal('-1.00')))

    def test_porcentaje_descuento_se_calcula_en_servidor(self):
        self.assertEqual(
            porcentaje_descuento_autorizado(Decimal('25.00'), Decimal('100.00')),
            Decimal('25.00'),
        )
        self.assertEqual(
            porcentaje_descuento_autorizado(Decimal('99.00'), Decimal('0.00')),
            Decimal('0.00'),
        )
