"""Punto 18 — PRIS no libera resultados clínicos ni orden validada sin captura humana."""
from pathlib import Path
from unittest.mock import MagicMock

from django.conf import settings
from django.test import SimpleTestCase

from core.agent.pris_tools_operativos import tool_cambiar_estado_orden
from core.services.ia_clinical_governance import METODO_IA_BORRADOR, defaults_resultado_ia_borrador


class IAEthicsToolTests(SimpleTestCase):
    def setUp(self):
        self.empresa = MagicMock()
        self.user = MagicMock()
        self.user.username = 'test_quimico'
        self.user.pk = 1

    def test_cambiar_estado_bloquea_resultados_listos(self):
        r = tool_cambiar_estado_orden(
            {
                'folio_orden': 'LAB-001',
                'nuevo_estado': 'RESULTADOS_LISTOS',
                'confirmado': True,
            },
            self.empresa,
            self.user,
        )
        self.assertIn('error', r)
        self.assertEqual(r.get('codigo'), 'IA_ETHICS_NO_RELEASE')

    def test_cambiar_estado_bloquea_entregado(self):
        r = tool_cambiar_estado_orden(
            {
                'folio_orden': 'LAB-001',
                'nuevo_estado': 'ENTREGADO',
                'confirmado': True,
            },
            self.empresa,
            self.user,
        )
        self.assertIn('error', r)
        self.assertEqual(r.get('codigo'), 'IA_ETHICS_NO_RELEASE')

    def test_defaults_ia_borrador_sin_aprobacion(self):
        d = defaults_resultado_ia_borrador()
        self.assertEqual(d['metodo_captura'], METODO_IA_BORRADOR)
        self.assertFalse(d['validado'])
        self.assertFalse(d['aprobado_por_humano'])


class CapturaIndustrialP18LeyendaTests(SimpleTestCase):
    def test_leyenda_p18_siempre_presente_en_plantilla(self):
        path = Path(settings.BASE_DIR) / "core/templates/core/captura_resultados_industrial.html"
        html = path.read_text(encoding="utf-8")
        self.assertIn('data-testid="p18-leyenda-global"', html)
        self.assertIn("Ética IA (P18)", html)
