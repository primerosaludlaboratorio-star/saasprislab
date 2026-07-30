from types import SimpleNamespace

from django.test import SimpleTestCase

from core.views.pris_jarvis import _puede_confirmar_accion


class PrisJarvisActionRbacTests(SimpleTestCase):
    def _user(self, rol='', superuser=False):
        return SimpleNamespace(rol=rol, is_superuser=superuser)

    def _action(self, modulo):
        return SimpleNamespace(modulo_destino=modulo)

    def test_quimico_can_confirm_laboratory_action(self):
        self.assertTrue(_puede_confirmar_accion(
            self._action('laboratorio.validar_resultado'),
            self._user('QUIMICO'),
        ))

    def test_reception_cannot_confirm_laboratory_action(self):
        self.assertFalse(_puede_confirmar_accion(
            self._action('laboratorio.validar_resultado'),
            self._user('RECEPCION'),
        ))

    def test_unknown_module_is_denied_by_default(self):
        self.assertFalse(_puede_confirmar_accion(
            self._action('modulo_no_registrado.accion'),
            self._user('GERENTE'),
        ))
