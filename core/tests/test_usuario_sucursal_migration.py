"""
Tests para validar la migración de FK usuario.sucursal → M2M Usuario_Sucursal.
Verifica que:
1. El puente de compatibilidad funciona correctamente
2. Los datos se migran correctamente
3. El código legacy no se rompe
"""
from django.test import TestCase
from django.utils import timezone
from django.contrib.auth import get_user_model
from datetime import timedelta

from core.models import Empresa, Sucursal, Usuario_Sucursal
from core.utils.sucursal_helpers import (
    get_user_primary_sucursal,
    get_user_sucursales,
    assign_sucursal_to_user,
    user_has_sucursal,
)

User = get_user_model()


class UsuarioSucursalMigrationTest(TestCase):
    """Tests para migración M2M de sucursales."""

    def setUp(self):
        """Crear datos de prueba."""
        self.empresa = Empresa.objects.create(
            nombre="Test Empresa",
            rfc="TEST001",
            periodo_vigencia="2024-2030"
        )
        self.suc1 = Sucursal.objects.create(
            empresa=self.empresa,
            nombre="Sucursal 1",
            codigo_sucursal="SUC-001"
        )
        self.suc2 = Sucursal.objects.create(
            empresa=self.empresa,
            nombre="Sucursal 2",
            codigo_sucursal="SUC-002"
        )
        self.user = User.objects.create_user(
            username="testuser",
            email="test@test.com",
            password="test123"
        )
        self.user.empresa = self.empresa
        self.user.save()

    def test_bridge_setter_getter(self):
        """Prueba que el puente de compatibilidad (property) funciona."""
        # Legacy: asignar via setter
        self.user.sucursal = self.suc1
        self.user.save()

        # Validar que se creó en M2M
        self.assertTrue(Usuario_Sucursal.objects.filter(
            usuario=self.user,
            sucursal=self.suc1
        ).exists())

        # Legacy: acceder via getter
        retrieved = self.user.sucursal
        self.assertEqual(retrieved.pk, self.suc1.pk)

    def test_bridge_sucursal_id_getter_setter(self):
        """Prueba que sucursal_id (property) funciona."""
        self.user.sucursal_id = self.suc1.pk
        self.user.save()

        self.assertEqual(self.user.sucursal_id, self.suc1.pk)
        self.assertIsNotNone(self.user.sucursal)

    def test_add_sucursal_method(self):
        """Prueba el nuevo método add_sucursal()."""
        assign_sucursal_to_user(self.user, self.suc1)

        self.assertTrue(Usuario_Sucursal.objects.filter(
            usuario=self.user,
            sucursal=self.suc1
        ).exists())

    def test_multiple_sucursales_m2m(self):
        """Prueba que un usuario puede tener múltiples sucursales asignadas."""
        assign_sucursal_to_user(self.user, self.suc1)
        assign_sucursal_to_user(self.user, self.suc2)

        # get_primary_sucursal debe retornar la primera
        primary = get_user_primary_sucursal(self.user)
        self.assertEqual(primary.pk, self.suc1.pk)

        # get_user_sucursales debe retornar ambas
        sucursales = get_user_sucursales(self.user)
        ids = list(sucursales.values_list('pk', flat=True))
        self.assertIn(self.suc1.pk, ids)
        self.assertIn(self.suc2.pk, ids)

    def test_has_sucursal_check(self):
        """Prueba user_has_sucursal()."""
        assign_sucursal_to_user(self.user, self.suc1)

        self.assertTrue(user_has_sucursal(self.user, self.suc1.pk))
        self.assertFalse(user_has_sucursal(self.user, self.suc2.pk))

    def test_sucursal_expiration(self):
        """Prueba que las asignaciones con vencimiento se respetan."""
        past_date = timezone.now() - timedelta(days=1)
        assign_sucursal_to_user(self.user, self.suc1, vencimiento=past_date)

        # has_sucursal debe retornar False si está vencido
        self.assertFalse(user_has_sucursal(self.user, self.suc1.pk))

        # Pero la asignación debe existir
        self.assertTrue(Usuario_Sucursal.objects.filter(
            usuario=self.user,
            sucursal=self.suc1
        ).exists())

    def test_deactivate_assignment(self):
        """Prueba que desactivar una asignación funciona."""
        assign_sucursal_to_user(self.user, self.suc1)

        # Desactivar
        Usuario_Sucursal.objects.filter(
            usuario=self.user,
            sucursal=self.suc1
        ).update(activa=False)

        # has_sucursal debe retornar False
        self.assertFalse(user_has_sucursal(self.user, self.suc1.pk))

    def test_legacy_and_new_api_coexist(self):
        """Prueba que ambas APIs (legacy + nueva) funcionan juntas."""
        # Legacy: asignar via setter
        self.user.sucursal = self.suc1
        self.user.save()

        # Nueva API: leer via helper
        primary = get_user_primary_sucursal(self.user)
        self.assertEqual(primary.pk, self.suc1.pk)

        # Nueva API: agregar otra sucursal
        assign_sucursal_to_user(self.user, self.suc2)

        # Legacy: leer la principal (debe ser la primera)
        self.assertEqual(self.user.sucursal.pk, self.suc1.pk)

        # Nueva API: ambas deben estar
        sucursales = list(get_user_sucursales(self.user).values_list('pk', flat=True))
        self.assertEqual(len(sucursales), 2)

    def test_clear_sucursales_via_setter(self):
        """Prueba que asignar None limpia todas las sucursales."""
        assign_sucursal_to_user(self.user, self.suc1)
        assign_sucursal_to_user(self.user, self.suc2)

        # Clear via setter
        self.user.sucursal = None
        self.user.save()

        # Debe estar vacío
        sucursales = get_user_sucursales(self.user)
        self.assertEqual(sucursales.count(), 0)

    def test_migration_data_backfill(self):
        """
        Simula la migración de datos desde FK vieja a M2M.
        (Esto se hace en la migración 0083, este test valida la lógica)
        """
        # Crear una asignación directa via M2M (como lo haría la migración)
        asignacion, created = Usuario_Sucursal.objects.get_or_create(
            usuario=self.user,
            sucursal=self.suc1,
            defaults={'activa': True}
        )
        self.assertTrue(created)

        # Validar que funciona con el puente
        self.assertEqual(self.user.sucursal.pk, self.suc1.pk)

    def test_empty_user_sucursal(self):
        """Prueba que un usuario sin sucursal retorna None en lugar de error."""
        # Usuario sin sucursal asignada
        primary = get_user_primary_sucursal(self.user)
        self.assertIsNone(primary)

        # sucursal property también debe retornar None
        self.assertIsNone(self.user.sucursal)
