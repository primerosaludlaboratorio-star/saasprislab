from types import SimpleNamespace
from unittest.mock import patch

from django.test import TestCase

from core.models import Empresa
from core.services.auto_repair import reparar_permisos_sesion


class AutoRepairTenantGuardTest(TestCase):
    def _request(self, user):
        return SimpleNamespace(user=user, session={})

    def test_auto_repair_rechaza_superuser_sin_empresa(self):
        user = SimpleNamespace(
            username="super_sin_empresa",
            is_authenticated=True,
            is_superuser=True,
            rol="DIRECTOR",
            empresa=None,
            groups=SimpleNamespace(values_list=lambda *args, **kwargs: []),
        )

        with patch("core.services.auto_repair._regenerar_sesion_permisos") as regen:
            result = reparar_permisos_sesion(self._request(user), "/director/")

        self.assertFalse(result)
        regen.assert_not_called()

    def test_auto_repair_permite_superuser_con_empresa(self):
        empresa = Empresa.objects.create(nombre="Empresa Repair", rfc="ERP260623TST")
        user = SimpleNamespace(
            username="super_con_empresa",
            is_authenticated=True,
            is_superuser=True,
            rol="DIRECTOR",
            empresa=empresa,
            groups=SimpleNamespace(values_list=lambda *args, **kwargs: []),
        )

        with patch("core.services.auto_repair._regenerar_sesion_permisos") as regen:
            result = reparar_permisos_sesion(self._request(user), "/director/")

        self.assertTrue(result)
        regen.assert_called_once()
