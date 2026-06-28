"""Candado financiero intrínseco en generar_reporte_pdf (Punto 15)."""
from decimal import Decimal
from unittest.mock import MagicMock

from django.test import SimpleTestCase

from core.utils.candado_financiero import ReportePdfSaldoPendienteError


class MotorReportePdfCandadoTests(SimpleTestCase):
    def test_generar_reporte_pdf_aborta_con_saldo(self):
        from core.services.motor_reportes_lab import generar_reporte_pdf

        orden = MagicMock()
        orden.total = Decimal("100.00")
        orden.anticipo = Decimal("50.00")

        with self.assertRaises(ReportePdfSaldoPendienteError) as ctx:
            generar_reporte_pdf(orden, request=None)
        self.assertEqual(ctx.exception.saldo_pendiente, Decimal("50.00"))

    def test_generar_reporte_pdf_simple_aborta_con_saldo(self):
        from core.services.motor_reportes_lab import generar_reporte_pdf_simple

        orden = MagicMock()
        orden.total = Decimal("200.00")
        orden.anticipo = Decimal("0.00")

        with self.assertRaises(ReportePdfSaldoPendienteError):
            generar_reporte_pdf_simple(orden, request=None)
