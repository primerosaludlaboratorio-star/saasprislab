# core/rbac/tests.py
# ==============================================================================
# PRISLAB SaaS — Tests de criterios de validación RBAC (Pasa/No Pasa)
# ==============================================================================
# Ejecutar: python manage.py test core.rbac
# ==============================================================================

from django.test import TestCase, RequestFactory
from django.core.exceptions import PermissionDenied
from unittest.mock import MagicMock

from core.rbac import (
    Rol, PERMISSION_MAP, check_permission, require_permission,
    require_roles, deny_roles, user_permissions,
)


def _make_user(rol: str, is_superuser: bool = False):
    user = MagicMock()
    user.rol = rol
    user.is_superuser = is_superuser
    user.is_authenticated = True
    user.username = f"test_{rol.lower()}"
    user.groups.filter.return_value.exists.return_value = False
    return user


class RolConstantsTest(TestCase):
    def test_caja_not_in_medical_roles(self):
        self.assertNotIn(Rol.CAJA, Rol.MEDICOS)

    def test_recepcion_not_in_medical_roles(self):
        self.assertNotIn(Rol.RECEPCION, Rol.MEDICOS)

    def test_admin_in_administrativos(self):
        self.assertIn(Rol.ADMIN, Rol.ADMINISTRATIVOS)


class PermissionMapTest(TestCase):
    """Criterio: query/endpoint sin rol correcto → denegado (no 0 resultados, 403)."""

    def test_quimico_puede_validar_resultados(self):
        user = _make_user(Rol.QUIMICO)
        # No debe lanzar excepción
        check_permission(user, "lab:validar_resultados")

    def test_caja_no_puede_validar_resultados(self):
        """CAJA_RECEPCION no puede acceder a endpoints de validación médica."""
        user = _make_user(Rol.CAJA)
        with self.assertRaises(PermissionDenied):
            check_permission(user, "lab:validar_resultados")

    def test_recepcion_no_puede_validar_resultados(self):
        user = _make_user(Rol.RECEPCION)
        with self.assertRaises(PermissionDenied):
            check_permission(user, "lab:validar_resultados")

    def test_caja_no_puede_modificar_dx(self):
        user = _make_user(Rol.CAJA)
        with self.assertRaises(PermissionDenied):
            check_permission(user, "consultorio:modificar_dx")

    def test_recepcion_no_puede_modificar_dx(self):
        user = _make_user(Rol.RECEPCION)
        with self.assertRaises(PermissionDenied):
            check_permission(user, "consultorio:modificar_dx")

    def test_caja_puede_registrar_venta(self):
        user = _make_user(Rol.CAJA)
        check_permission(user, "caja:registrar_venta")  # No debe lanzar

    def test_quimico_no_puede_cancelar_venta(self):
        user = _make_user(Rol.QUIMICO)
        with self.assertRaises(PermissionDenied):
            check_permission(user, "caja:cancelar_venta")

    def test_superadmin_tiene_todos_los_permisos(self):
        user = _make_user("", is_superuser=True)
        for perm in PERMISSION_MAP:
            check_permission(user, perm)  # Ninguno debe lanzar

    def test_permiso_desconocido_denegado(self):
        user = _make_user(Rol.ADMIN)
        with self.assertRaises(PermissionDenied):
            check_permission(user, "modulo_inexistente:accion_falsa")

    def test_director_puede_ver_costos(self):
        user = _make_user(Rol.DIRECTOR)
        check_permission(user, "finanzas:ver_costos")

    def test_medico_no_puede_ver_costos(self):
        user = _make_user(Rol.MEDICO)
        with self.assertRaises(PermissionDenied):
            check_permission(user, "finanzas:ver_costos")

    def test_caja_no_puede_gestionar_usuarios(self):
        user = _make_user(Rol.CAJA)
        with self.assertRaises(PermissionDenied):
            check_permission(user, "admin:gestionar_usuarios")


class DecoratorTest(TestCase):
    """Criterio: permisos inmutables — decoradores no bypasseables por rol."""

    def setUp(self):
        self.factory = RequestFactory()

    def _make_request(self, rol: str, is_superuser: bool = False):
        request = self.factory.get("/test/")
        request.user = _make_user(rol, is_superuser)
        return request

    def test_require_permission_bloquea_caja_en_endpoint_medico(self):
        @require_permission("lab:validar_resultados")
        def vista_validar(request):
            return MagicMock(status_code=200)

        request = self._make_request(Rol.CAJA)
        with self.assertRaises(PermissionDenied):
            vista_validar(request)

    def test_require_permission_permite_quimico(self):
        @require_permission("lab:validar_resultados")
        def vista_validar(request):
            return MagicMock(status_code=200)

        request = self._make_request(Rol.QUIMICO)
        resp = vista_validar(request)
        self.assertEqual(resp.status_code, 200)

    def test_require_roles_bloquea_rol_no_listado(self):
        @require_roles(Rol.ADMIN, Rol.DIRECTOR)
        def vista_admin(request):
            return MagicMock(status_code=200)

        request = self._make_request(Rol.CAJA)
        with self.assertRaises(PermissionDenied):
            vista_admin(request)

    def test_deny_roles_bloquea_caja(self):
        @deny_roles(Rol.CAJA, Rol.RECEPCION)
        def vista_clinica(request):
            return MagicMock(status_code=200)

        request = self._make_request(Rol.CAJA)
        with self.assertRaises(PermissionDenied):
            vista_clinica(request)

    def test_deny_roles_permite_quimico(self):
        @deny_roles(Rol.CAJA, Rol.RECEPCION)
        def vista_clinica(request):
            return MagicMock(status_code=200)

        request = self._make_request(Rol.QUIMICO)
        resp = vista_clinica(request)
        self.assertEqual(resp.status_code, 200)

    def test_superadmin_bypass_require_roles(self):
        @require_roles(Rol.ADMIN)
        def vista_admin(request):
            return MagicMock(status_code=200)

        request = self._make_request("", is_superuser=True)
        resp = vista_admin(request)
        self.assertEqual(resp.status_code, 200)


class UserPermissionsTest(TestCase):
    def test_caja_no_tiene_permiso_validar_resultados(self):
        user = _make_user(Rol.CAJA)
        perms = user_permissions(user)
        self.assertFalse(perms["lab_validar_resultados"])

    def test_quimico_tiene_permiso_validar_resultados(self):
        user = _make_user(Rol.QUIMICO)
        perms = user_permissions(user)
        self.assertTrue(perms["lab_validar_resultados"])

    def test_todos_los_roles_incluyen_key_completo(self):
        user = _make_user(Rol.ADMIN)
        perms = user_permissions(user)
        for key in PERMISSION_MAP:
            self.assertIn(key.replace(":", "_"), perms)
