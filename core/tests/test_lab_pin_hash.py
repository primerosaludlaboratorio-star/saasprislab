import hashlib

from django.contrib.auth.hashers import make_password
from django.test import SimpleTestCase

from core.models.expediente_blindaje import _validar_pin_hash


class LabPinHashTest(SimpleTestCase):
    def test_valida_hash_django(self):
        almacenado = make_password('2468')
        self.assertTrue(_validar_pin_hash('2468', almacenado))
        self.assertFalse(_validar_pin_hash('9999', almacenado))

    def test_migra_hash_sha256_legacy_al_validar(self):
        almacenado = hashlib.sha256(b'2468').hexdigest()
        self.assertTrue(_validar_pin_hash('2468', almacenado))
        self.assertFalse(_validar_pin_hash('9999', almacenado))
