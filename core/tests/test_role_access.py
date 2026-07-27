"""Regresiones de provision automatica de acceso por rol."""

from django.test import TestCase

from core.models import Empresa, Usuario
from core.utils.role_access import sincronizar_acceso_por_rol


class RoleAccessProvisioningTests(TestCase):
    def test_farmacia_inherits_group_and_app_permissions(self):
        empresa = Empresa.objects.create(nombre='Empresa Role Access', rfc='RAC010101AAA')
        usuario = Usuario.objects.create_user(
            username='farmacia_role_access',
            password='Prueba-2468',
            empresa=empresa,
            rol='FARMACIA',
        )

        grupo = sincronizar_acceso_por_rol(usuario)

        self.assertEqual(grupo.name, 'FARMACIA')
        self.assertTrue(usuario.groups.filter(name='FARMACIA').exists())
        self.assertTrue(usuario.has_perm('farmacia.add_movimientoinventario'))

    def test_cajero_does_not_retain_farmacia_group(self):
        empresa = Empresa.objects.create(nombre='Empresa Role Access 2', rfc='RAC010101AAB')
        usuario = Usuario.objects.create_user(
            username='cajero_role_access',
            password='Prueba-2468',
            empresa=empresa,
            rol='FARMACIA',
        )
        sincronizar_acceso_por_rol(usuario)
        usuario.rol = 'CAJERO'
        usuario.save(update_fields=['rol'])
        sincronizar_acceso_por_rol(usuario)

        self.assertFalse(usuario.groups.filter(name='FARMACIA').exists())
        self.assertTrue(usuario.groups.filter(name='CAJERO').exists())
