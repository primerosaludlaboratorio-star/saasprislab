"""Tests motor clínico de fórmulas LIMS (Punto 10) — sin eval inseguro."""
from decimal import Decimal

from django.test import SimpleTestCase

from core.services.clinical_math import (
    FormulaUnsafeError,
    evaluate_formula,
    formula_dependency_names,
    format_result_value,
    parse_numeric_text,
    _reject_unsafe_nodes,
)
import ast


class ClinicalMathTests(SimpleTestCase):
    def test_parse_numeric_text(self):
        self.assertEqual(parse_numeric_text('12,5')[0], 12.5)
        self.assertEqual(parse_numeric_text('  -3.2 ')[0], -3.2)
        self.assertIsNone(parse_numeric_text('Positivo')[0])
        self.assertIsNone(parse_numeric_text('')[0])

    def test_evaluate_simple(self):
        v, err = evaluate_formula('A + B', {'A': 2.0, 'B': 3.0})
        self.assertIsNone(err)
        self.assertEqual(v, Decimal('5'))

    def test_evaluate_case_insensitive_name(self):
        v, err = evaluate_formula('col + hdl', {'COL': 200.0, 'HDL': 50.0})
        self.assertIsNone(err)
        self.assertEqual(v, Decimal('250'))

    def test_division_by_zero(self):
        v, err = evaluate_formula('1 / (A - A)', {'A': 1.0})
        self.assertIsNone(v)
        self.assertEqual(err, 'division_cero')

    def test_missing_variable(self):
        v, err = evaluate_formula('X + 1', {'Y': 1.0})
        self.assertIsNone(v)
        self.assertTrue((err or '').startswith('variable_faltante'))

    def test_sqrt_allowed(self):
        v, err = evaluate_formula('sqrt(16)', {})
        self.assertIsNone(err)
        self.assertEqual(v, Decimal('4'))

    def test_reject_import_injection(self):
        with self.assertRaises(FormulaUnsafeError):
            tree = ast.parse("__import__('os').system('x')", mode='eval')
            _reject_unsafe_nodes(tree)

    def test_reject_attribute_access(self):
        with self.assertRaises(FormulaUnsafeError):
            tree = ast.parse("(1).__class__", mode='eval')
            _reject_unsafe_nodes(tree)

    def test_negative_numeric_result_policy(self):
        """El motor permite negativos; la política clínica (no persistir) está en sync_."""
        v, err = evaluate_formula('1 - 5', {})
        self.assertIsNone(err)
        self.assertEqual(v, Decimal('-4'))

    def test_formula_dependencies(self):
        deps = formula_dependency_names('sqrt(COL) / HDL')
        self.assertEqual(deps, {'COL', 'HDL'})

    def test_format_decimals(self):
        self.assertEqual(format_result_value(Decimal('1.2345'), 2), '1.23')
