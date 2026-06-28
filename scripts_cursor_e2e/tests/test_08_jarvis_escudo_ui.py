"""Enfoque 8 — Badge escudo IA (PRIS-Jarvis): tooltip y copy legibles en partial."""
from django.template.loader import render_to_string
from django.test import SimpleTestCase

from core.services.ia_clinical_governance import METODO_IA_BORRADOR


class JarvisEscudoUiTests(SimpleTestCase):
    def test_badge_muestra_title_etica_ia_y_testid(self):
        html = render_to_string(
            'core/partials/escudo_ia_captura_badge.html',
            {'mostrar': True},
        )
        self.assertIn('data-testid="robot-chemist-escudo-ia"', html)
        self.assertIn('Ética IA', html)
        self.assertIn('P18', html)
        self.assertIn('aprobación humana', html.lower())

    def test_badge_oculto_cuando_mostrar_falso(self):
        html = render_to_string(
            'core/partials/escudo_ia_captura_badge.html',
            {'mostrar': False},
        )
        self.assertNotIn('robot-chemist-escudo-ia', html)

    def test_regla_contexto_escudo_ia_documentada(self):
        class _Rp:
            valor = '10'
            aprobado_por_humano = False
            metodo_captura = METODO_IA_BORRADOR

        rp = _Rp()
        tiene_valor = bool((rp.valor or '').strip())
        adv = tiene_valor and (
            not getattr(rp, 'aprobado_por_humano', True)
            or getattr(rp, 'metodo_captura', '') == METODO_IA_BORRADOR
        )
        self.assertTrue(adv)
