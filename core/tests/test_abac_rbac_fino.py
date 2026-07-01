"""
Tests PR1: ABAC / RBAC fino
Cubre:
  - RBAC whitelist: acceso denegado y permitido por rol
  - ABAC GRANT: override positivo temporal
  - ABAC REVOKE: override negativo temporal (prioridad sobre GRANT)
  - deny_roles: CAJA/RECEPCION bloqueados en endpoints médicos
  - check_sucursal_access: aislamiento por sucursal M2M
  - role_required: sin bypass de groups
"""
from django.test import TestCase, RequestFactory
from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied
from django.utils import timezone
from datetime import timedelta

from core.models import Empresa, Sucursal, Usuario_Sucursal, Usuario_Permiso_Extra
from core.rbac.permissions import (
    Rol,
    check_permission,
    check_sucursal_access,
    check_sucursal_assignment,
    require_permission,
    require_roles,
    deny_roles,
    _has_permission_with_abac,
    _has_permission,
)

User = get_user_model()


class RBACBaseTest(TestCase):
    """RBAC whitelist estricta por rol."""

    def setUp(self):
        self.empresa = Empresa.objects.create(nombre="Lab Test", rfc="LAB001", periodo_vigencia="2024-2030")
        self.quimico = User.objects.create_user(username="quimico1", password="x", rol=Rol.QUIMICO)
        self.quimico.empresa = self.empresa
        self.quimico.save()
        self.cajero = User.objects.create_user(username="cajero1", password="x", rol=Rol.CAJA)
        self.cajero.empresa = self.empresa
        self.cajero.save()

    def test_quimico_puede_capturar_resultados(self):
        self.assertTrue(_has_permission(self.quimico, "lab:captura_resultados"))

    def test_cajero_no_puede_capturar_resultados(self):
        self.assertFalse(_has_permission(self.cajero, "lab:captura_resultados"))

    def test_cajero_puede_registrar_venta(self):
        self.assertTrue(_has_permission(self.cajero, "caja:registrar_venta"))

    def test_quimico_no_puede_cancelar_venta(self):
        self.assertFalse(_has_permission(self.quimico, "caja:cancelar_venta"))

    def test_permiso_desconocido_denegado(self):
        self.assertFalse(_has_permission(self.quimico, "permiso:inexistente"))

    def test_check_permission_lanza_denied(self):
        with self.assertRaises(PermissionDenied):
            check_permission(self.cajero, "lab:captura_resultados")

    def test_check_permission_no_lanza_para_rol_correcto(self):
        try:
            check_permission(self.quimico, "lab:captura_resultados")
        except PermissionDenied:
            self.fail("check_permission lanzó PermissionDenied para un rol permitido")


class ABACGrantTest(TestCase):
    """ABAC: override GRANT otorga permisos fuera del rol base."""

    def setUp(self):
        self.empresa = Empresa.objects.create(nombre="Lab ABAC", rfc="ABAC001", periodo_vigencia="2024-2030")
        self.admin = User.objects.create_user(username="admin_abac", password="x", rol=Rol.ADMIN, is_superuser=False)
        self.admin.empresa = self.empresa
        self.admin.save()
        self.cajero = User.objects.create_user(username="cajero_abac", password="x", rol=Rol.CAJA)
        self.cajero.empresa = self.empresa
        self.cajero.save()

    def test_cajero_sin_override_no_puede_cancelar_venta(self):
        self.assertFalse(_has_permission_with_abac(self.cajero, "caja:cancelar_venta"))

    def test_cajero_con_grant_puede_cancelar_venta(self):
        Usuario_Permiso_Extra.objects.create(
            usuario=self.cajero,
            permiso_key="caja:cancelar_venta",
            tipo_override="GRANT",
            razon_negocio="Turno de cierre especial",
            otorgado_por=self.admin,
        )
        self.assertTrue(_has_permission_with_abac(self.cajero, "caja:cancelar_venta"))

    def test_grant_vencido_no_aplica(self):
        Usuario_Permiso_Extra.objects.create(
            usuario=self.cajero,
            permiso_key="caja:cancelar_venta",
            tipo_override="GRANT",
            fecha_vencimiento=timezone.now() - timedelta(hours=1),
            razon_negocio="Expirado",
            otorgado_por=self.admin,
        )
        self.assertFalse(_has_permission_with_abac(self.cajero, "caja:cancelar_venta"))


class ABACRevokeTest(TestCase):
    """ABAC: REVOKE quita permisos del rol base; REVOKE > GRANT."""

    def setUp(self):
        self.empresa = Empresa.objects.create(nombre="Lab Revoke", rfc="REV001", periodo_vigencia="2024-2030")
        self.admin = User.objects.create_user(username="admin_rev", password="x", rol=Rol.ADMIN, is_superuser=False)
        self.admin.empresa = self.empresa
        self.admin.save()
        self.quimico = User.objects.create_user(username="quimico_rev", password="x", rol=Rol.QUIMICO)
        self.quimico.empresa = self.empresa
        self.quimico.save()

    def test_quimico_con_revoke_no_puede_capturar(self):
        Usuario_Permiso_Extra.objects.create(
            usuario=self.quimico,
            permiso_key="lab:captura_resultados",
            tipo_override="REVOKE",
            razon_negocio="Licencia médica",
            otorgado_por=self.admin,
        )
        self.assertFalse(_has_permission_with_abac(self.quimico, "lab:captura_resultados"))

    def test_revoke_tiene_prioridad_sobre_grant(self):
        Usuario_Permiso_Extra.objects.create(
            usuario=self.quimico,
            permiso_key="lab:captura_resultados",
            tipo_override="GRANT",
            razon_negocio="Grant explícito",
            otorgado_por=self.admin,
        )
        # unique_together en (usuario, permiso_key, sucursal) — GRANT ya existe, creamos con sucursal distinta
        sucursal = Sucursal.objects.create(empresa=self.empresa, nombre="Suc A", codigo_sucursal="SA")
        Usuario_Permiso_Extra.objects.create(
            usuario=self.quimico,
            permiso_key="lab:captura_resultados",
            tipo_override="REVOKE",
            sucursal=sucursal,
            razon_negocio="REVOKE en sucursal A",
            otorgado_por=self.admin,
        )
        # REVOKE (con sucursal) coexiste con GRANT (global): REVOKE tiene prioridad
        self.assertFalse(_has_permission_with_abac(self.quimico, "lab:captura_resultados", sucursal_id=sucursal.pk))


class DenyRolesDecoratorTest(TestCase):
    """deny_roles bloquea CAJA/RECEPCION en endpoints médicos."""

    def setUp(self):
        self.factory = RequestFactory()
        self.empresa = Empresa.objects.create(nombre="Lab Deny", rfc="DEN001", periodo_vigencia="2024-2030")
        self.cajero = User.objects.create_user(username="cajero_deny", password="x", rol=Rol.CAJA)
        self.cajero.empresa = self.empresa
        self.cajero.save()
        self.quimico = User.objects.create_user(username="quimico_deny", password="x", rol=Rol.QUIMICO)
        self.quimico.empresa = self.empresa
        self.quimico.save()

    def _make_view(self):
        @deny_roles(Rol.CAJA, Rol.RECEPCION)
        def vista_medica(request):
            return "ok"
        return vista_medica

    def test_cajero_bloqueado_por_deny_roles(self):
        vista = self._make_view()
        request = self.factory.get("/lab/captura/")
        request.user = self.cajero
        with self.assertRaises(PermissionDenied):
            vista(request)

    def test_quimico_pasa_deny_roles(self):
        vista = self._make_view()
        request = self.factory.get("/lab/captura/")
        request.user = self.quimico
        result = vista(request)
        self.assertEqual(result, "ok")


class SucursalAislamientoTest(TestCase):
    """check_sucursal_access aísla datos por sucursal M2M."""

    def setUp(self):
        self.empresa = Empresa.objects.create(nombre="Lab Suc", rfc="SUC001", periodo_vigencia="2024-2030")
        self.suc_a = Sucursal.objects.create(empresa=self.empresa, nombre="Suc A", codigo_sucursal="SA")
        self.suc_b = Sucursal.objects.create(empresa=self.empresa, nombre="Suc B", codigo_sucursal="SB")
        self.quimico = User.objects.create_user(username="quimico_suc", password="x", rol=Rol.QUIMICO)
        self.quimico.empresa = self.empresa
        self.quimico.save()
        # Asignar solo suc_a
        Usuario_Sucursal.objects.create(usuario=self.quimico, sucursal=self.suc_a, activa=True)

    def test_quimico_accede_a_su_sucursal(self):
        try:
            check_sucursal_access(self.quimico, self.suc_a.pk, resource="resultados")
        except PermissionDenied:
            self.fail("check_sucursal_access denegó acceso a sucursal asignada")

    def test_quimico_no_accede_a_sucursal_ajena(self):
        with self.assertRaises(PermissionDenied):
            check_sucursal_access(self.quimico, self.suc_b.pk, resource="resultados")

    def test_admin_accede_a_cualquier_sucursal(self):
        admin = User.objects.create_user(username="admin_suc", password="x", rol=Rol.ADMIN)
        admin.empresa = self.empresa
        admin.save()
        try:
            check_sucursal_access(admin, self.suc_b.pk, resource="resultados")
        except PermissionDenied:
            self.fail("Admin no debería tener restricción por sucursal")

    def test_asignacion_inactiva_no_da_acceso(self):
        Usuario_Sucursal.objects.filter(usuario=self.quimico, sucursal=self.suc_a).update(activa=False)
        self.assertFalse(check_sucursal_assignment(self.quimico, self.suc_a.pk))


class RoleRequiredSinGroupsBypassTest(TestCase):
    """role_required ya no bypasea via user.groups."""

    def setUp(self):
        self.factory = RequestFactory()
        self.empresa = Empresa.objects.create(nombre="Lab Bypass", rfc="BYP001", periodo_vigencia="2024-2030")
        self.user = User.objects.create_user(username="user_bypass", password="x", rol="")
        self.user.empresa = self.empresa
        self.user.save()

    def test_user_sin_rol_y_con_grupo_es_denegado(self):
        from django.contrib.auth.models import Group
        from core.decorators import role_required

        grp, _ = Group.objects.get_or_create(name="ADMIN")
        self.user.groups.add(grp)

        @role_required("ADMIN")
        def vista(request):
            return "ok"

        request = self.factory.get("/admin/")
        request.user = self.user
        from django.http import HttpResponseForbidden
        response = vista(request)
        self.assertEqual(response.status_code, 403)
