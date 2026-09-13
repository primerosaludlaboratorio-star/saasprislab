from decimal import Decimal

from django.test import SimpleTestCase

from core.services.ventas.cobro_service import redondeo_efectivo_valido


class CobroServiceSecurityTests(SimpleTestCase):
    def test_redondeo_efectivo_se_limita_a_cincuenta_centavos(self):
        self.assertTrue(redondeo_efectivo_valido(Decimal('0.50')))
        self.assertTrue(redondeo_efectivo_valido(Decimal('-0.50')))
        self.assertFalse(redondeo_efectivo_valido(Decimal('0.51')))
        self.assertFalse(redondeo_efectivo_valido(Decimal('-1.00')))
