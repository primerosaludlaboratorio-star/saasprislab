from unittest.mock import patch

from cryptography.fernet import Fernet
from django.core.exceptions import ImproperlyConfigured
from django.test import SimpleTestCase, TestCase, override_settings

from core.fields import EncryptedTextField
from core.models import (
    ConfiguracionModulos,
    Empresa,
    verificar_pin_farmacia,
)


class FarmaciaPinSecurityTests(TestCase):
    def test_pins_are_hashed_and_verifiable(self):
        config = ConfiguracionModulos.objects.create(
            empresa=Empresa.objects.create(nombre='PIN seguro'),
            pin_precio_neto='5938',
            pin_cancelacion_venta='2468',
        )
        config.refresh_from_db()

        self.assertNotEqual(config.pin_precio_neto, '5938')
        self.assertNotEqual(config.pin_cancelacion_venta, '2468')
        self.assertTrue(verificar_pin_farmacia(config.pin_precio_neto, '5938'))
        self.assertTrue(verificar_pin_farmacia(config.pin_cancelacion_venta, '2468'))
        self.assertFalse(verificar_pin_farmacia(config.pin_precio_neto, '0000'))


class EncryptedTextFieldSecurityTests(SimpleTestCase):
    @override_settings(FERNET_KEY=Fernet.generate_key().decode())
    def test_encrypt_returns_ciphertext(self):
        ciphertext = EncryptedTextField.encrypt('dato confidencial')
        self.assertNotEqual(ciphertext, 'dato confidencial')

    @patch('core.fields._get_fernet', return_value=None)
    def test_encrypt_fails_closed_when_fernet_unavailable(self, _mock_fernet):
        with self.assertRaises(ImproperlyConfigured):
            EncryptedTextField.encrypt('dato confidencial')

    @patch('core.fields._get_fernet', side_effect=ValueError('clave inválida'))
    def test_encrypt_fails_closed_when_fernet_errors(self, _mock_fernet):
        with self.assertRaises(ImproperlyConfigured):
            EncryptedTextField.encrypt('dato confidencial')
