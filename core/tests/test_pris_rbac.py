from unittest.mock import Mock

from django.test import SimpleTestCase

from core.views.pris_ia._rbac import _verificar_rbac


class PrisRbacTests(SimpleTestCase):
    def _user(self, rol='', grupos=()):
        user = Mock()
        user.is_authenticated = True
        user.is_superuser = False
        user.rol = rol
        user.groups.values_list.return_value = list(grupos)
        return user

    def test_manual_operativo_is_available_to_authenticated_staff(self):
        permitido, _ = _verificar_rbac('consultar_manual_lab', self._user(rol='EMPLEADO'))
        self.assertTrue(permitido)

    def test_patient_records_require_an_authorized_role(self):
        permitido, _ = _verificar_rbac('consultar_expediente_paciente', self._user(rol='EMPLEADO'))
        self.assertFalse(permitido)
        permitido, _ = _verificar_rbac('consultar_expediente_paciente', self._user(rol='RECEPCION'))
        self.assertFalse(permitido)
        permitido, _ = _verificar_rbac('consultar_expediente_paciente', self._user(rol='MEDICO'))
        self.assertTrue(permitido)

    def test_unknown_tool_is_denied_by_default(self):
        permitido, mensaje = _verificar_rbac('herramienta_no_registrada', self._user(rol='ADMIN'))
        self.assertFalse(permitido)
        self.assertIn('no está registrada', mensaje)
