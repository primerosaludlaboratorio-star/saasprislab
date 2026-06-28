"""Punto 13 — handshake HL7 (unidades + Decimal)."""
from decimal import Decimal

from django.test import SimpleTestCase

from laboratorio.services.hl7_handshake import (
    decimal_desde_valor_hl7,
    formatear_decimal_para_rp,
    normalizar_unidad,
    unidad_equipo_vs_catalogo,
)


class HL7HandshakeTests(SimpleTestCase):
    def test_normalizar_unidad(self):
        self.assertEqual(normalizar_unidad('  mg/dl  '), 'MG/DL')
        self.assertEqual(normalizar_unidad('mmol / l'), 'MMOL/L')

    def test_unidad_catalogo_vacio_acepta(self):
        ok, _ = unidad_equipo_vs_catalogo('', 'mmol/L')
        self.assertTrue(ok)

    def test_unidad_estricta(self):
        ok, _ = unidad_equipo_vs_catalogo('mg/dL', 'mmol/L')
        self.assertFalse(ok)
        ok2, _ = unidad_equipo_vs_catalogo('mg/dL', 'mg/dl')
        self.assertTrue(ok2)

    def test_decimal_sin_float(self):
        d, err = decimal_desde_valor_hl7('5,1234')
        self.assertIsNone(err)
        self.assertEqual(d, Decimal('5.1234'))

    def test_decimal_rechaza_texto(self):
        d, err = decimal_desde_valor_hl7('Positivo')
        self.assertIsNone(d)
        self.assertEqual(err, 'no_decimal')

    def test_formatear_decimal(self):
        s = formatear_decimal_para_rp(Decimal('1.234'), 2)
        self.assertEqual(s, '1.23')
