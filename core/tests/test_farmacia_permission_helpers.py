"""Regresiones de permisos tenant-sensitive para helpers de Farmacia."""
from types import SimpleNamespace

from django.test import SimpleTestCase

from core.views.farmacia import _verificar_acceso
from farmacia.views.semaforo import es_farmacia_o_director


class _FakeGroups:
    def __init__(self, names=None):
        self.names = set(names or [])

    def filter(self, name__in=None):
        names = set(name__in or [])
        return SimpleNamespace(exists=lambda: bool(self.names.intersection(names)))


def _user(*, empresa=None, superuser=False, staff=False, rol='', groups=None):
    return SimpleNamespace(
        empresa=empresa,
        is_superuser=superuser,
        is_staff=staff,
        rol=rol,
        groups=_FakeGroups(groups),
    )


class FarmaciaPermissionHelpersTest(SimpleTestCase):
    def test_verificar_acceso_requiere_empresa_para_superuser(self):
        self.assertFalse(
            _verificar_acceso(
                _user(superuser=True, staff=True),
                ['ADMIN'],
                ['FARMACIA'],
            )
        )
        self.assertTrue(
            _verificar_acceso(
                _user(empresa=object(), superuser=True, staff=True),
                ['ADMIN'],
                ['FARMACIA'],
            )
        )

    def test_verificar_acceso_requiere_empresa_para_grupo_o_rol(self):
        self.assertFalse(_verificar_acceso(_user(rol='FARMACIA'), ['FARMACIA']))
        self.assertFalse(
            _verificar_acceso(
                _user(groups=['FARMACIA']),
                ['CAJERO'],
                ['FARMACIA'],
            )
        )
        self.assertTrue(_verificar_acceso(_user(empresa=object(), rol='FARMACIA'), ['FARMACIA']))
        self.assertTrue(
            _verificar_acceso(
                _user(empresa=object(), groups=['FARMACIA']),
                ['CAJERO'],
                ['FARMACIA'],
            )
        )

    def test_semaforo_requiere_empresa_para_superuser_y_grupo(self):
        self.assertFalse(es_farmacia_o_director(_user(superuser=True)))
        self.assertFalse(es_farmacia_o_director(_user(groups=['FARMACIA'])))
        self.assertTrue(es_farmacia_o_director(_user(empresa=object(), superuser=True)))
        self.assertTrue(es_farmacia_o_director(_user(empresa=object(), groups=['FARMACIA'])))

