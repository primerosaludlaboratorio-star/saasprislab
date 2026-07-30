from datetime import date

from django.test import SimpleTestCase

from core.views.reportes_financieros import _fecha_segura


class FinancialReportDateTests(SimpleTestCase):
    def test_invalid_date_uses_safe_default(self):
        fallback = date(2026, 7, 29)
        self.assertEqual(_fecha_segura('no-es-fecha', fallback), fallback)

    def test_valid_date_is_parsed(self):
        self.assertEqual(_fecha_segura('2026-07-29', date.today()), date(2026, 7, 29))
