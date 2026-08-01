from django.test import SimpleTestCase

from laboratorio.utils.label_printer import firmar_token_kiosko, verificar_token_kiosko


class KioskoQrSecurityTests(SimpleTestCase):
    def test_signed_token_round_trip(self):
        token = firmar_token_kiosko('LAB-00123')
        self.assertNotEqual(token, 'LAB-00123')
        self.assertEqual(verificar_token_kiosko(token), 'LAB-00123')

    def test_plain_folio_is_rejected(self):
        with self.assertRaises(ValueError):
            verificar_token_kiosko('LAB-00123')
