"""Tests unitarios — validadores y saneamiento CFDI 4.0 (Hito 16 Fase 1)."""
from django.core.exceptions import ValidationError
from django.test import SimpleTestCase

from contabilidad.validators_cfdi40 import (
    clean_nombre_fiscal,
    validate_codigo_postal_sat40,
    validate_rfc_sat40,
)


class RfcSat40Tests(SimpleTestCase):
    def test_rfc_generico_publico_ok(self):
        validate_rfc_sat40('XAXX010101000')

    def test_rfc_moral_12_ok(self):
        validate_rfc_sat40('ABC010101XYZ')

    def test_rfc_rechaza_corto(self):
        with self.assertRaises(ValidationError):
            validate_rfc_sat40('XAX010101')

    def test_rfc_rechaza_minusculas_sin_normalizar_en_validator(self):
        # El validador espera mayúsculas; el modelo clean() las aplica antes.
        with self.assertRaises(ValidationError):
            validate_rfc_sat40('xaxx010101000')

    def test_rfc_rechaza_caracteres_invalidos_en_fecha(self):
        with self.assertRaises(ValidationError):
            validate_rfc_sat40('XAXX0101AB000')


class CodigoPostalSat40Tests(SimpleTestCase):
    def test_cp_ok(self):
        validate_codigo_postal_sat40('01000')

    def test_cp_rechaza_menos_digitos(self):
        with self.assertRaises(ValidationError):
            validate_codigo_postal_sat40('0100')

    def test_cp_rechaza_letras(self):
        with self.assertRaises(ValidationError):
            validate_codigo_postal_sat40('01A00')


class CleanNombreFiscalTests(SimpleTestCase):
    def test_mayusculas_y_espacios(self):
        self.assertEqual(
            clean_nombre_fiscal('  juan   pérez  '),
            'JUAN PÉREZ',
        )

    def test_quita_sa_de_cv(self):
        self.assertEqual(
            clean_nombre_fiscal('ACME LABORATORIOS SA DE CV'),
            'ACME LABORATORIOS',
        )

    def test_quita_sapi(self):
        self.assertEqual(
            clean_nombre_fiscal('PRISLAB SAPI DE CV'),
            'PRISLAB',
        )

    def test_quita_sc_final(self):
        self.assertEqual(
            clean_nombre_fiscal('CONSULTORIOS MÉDICOS SC'),
            'CONSULTORIOS MÉDICOS',
        )
