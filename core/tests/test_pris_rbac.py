from unittest.mock import Mock

from django.test import SimpleTestCase

from core.views.pris_ia._rbac import _verificar_rbac
from core.utils.pris_identity import nombre_asistente_ia


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

    def test_assistant_name_is_tenant_customizable(self):
        empresa = Mock(nombre='Primero Salud Laboratorio', nombre_asistente_ia='')
        self.assertEqual(nombre_asistente_ia(empresa), 'PRIS')
        empresa.nombre_asistente_ia = 'LIA'
        self.assertEqual(nombre_asistente_ia(empresa), 'LIA')

    def test_valle_gets_legacy_brand_default(self):
        empresa = Mock(nombre='Clinica del Valle', nombre_asistente_ia='')
        self.assertEqual(nombre_asistente_ia(empresa), 'LIA')
