"""
Tests PR2: KPIs / Dashboard
Cubre:
  - Tenant-safety: empresa A no ve datos de empresa B
  - Permisos: GERENTE puede ver reportes, no puede generar snapshots
  - KPIService: cálculos básicos aislados por empresa
  - dashboard_hoy / generar_snapshot: 403 para rol sin permiso
"""
from decimal import Decimal
from django.test import TestCase, RequestFactory
from django.contrib.auth import get_user_model
from django.utils import timezone

from core.models import Empresa, Sucursal, KPI_Snapshot
from core.services.kpi_service import KPIService
from core.rbac.permissions import Rol, _has_permission
from core.tenant import set_current_empresa, clear_current_empresa, set_current_sucursal, clear_current_sucursal

User = get_user_model()


class KPIServiceTenantSafetyTest(TestCase):
    """KPIService filtra estrictamente por empresa."""

    def setUp(self):
        self.emp_a = Empresa.objects.create(nombre="Lab A", rfc="LABA001", periodo_vigencia="2024-2030")
        self.emp_b = Empresa.objects.create(nombre="Lab B", rfc="LABB001", periodo_vigencia="2024-2030")
        self.svc_a = KPIService(self.emp_a)
        self.svc_b = KPIService(self.emp_b)

    def test_snapshot_empresa_a_no_visible_desde_empresa_b(self):
        KPI_Snapshot.objects.create(
            empresa=self.emp_a,
            fecha=timezone.now().date(),
            ingresos_total=Decimal("5000.00"),
        )
        # KPIService de empresa B no debe ver el snapshot de A
        snapshots_b = KPI_Snapshot.objects.filter(empresa=self.emp_b)
        self.assertEqual(snapshots_b.count(), 0)

    def test_generar_snapshot_hoy_crea_para_empresa_correcta(self):
        snap = self.svc_a.generar_snapshot_hoy()
        self.assertEqual(snap.empresa_id, self.emp_a.pk)
        # No debe haber nada en empresa B
        self.assertEqual(KPI_Snapshot.objects.filter(empresa=self.emp_b).count(), 0)

    def test_snapshots_son_idempotentes_por_dia(self):
        snap1 = self.svc_a.generar_snapshot_hoy()
        snap2 = self.svc_a.generar_snapshot_hoy()
        self.assertEqual(snap1.pk, snap2.pk)
        self.assertEqual(KPI_Snapshot.objects.filter(empresa=self.emp_a).count(), 1)


class KPIServiceSucursalScopeTest(TestCase):
    """KPIService con sucursal filtra dentro de la empresa."""

    def setUp(self):
        self.empresa = Empresa.objects.create(nombre="Lab Suc", rfc="LS001", periodo_vigencia="2024-2030")
        self.suc_a = Sucursal.objects.create(empresa=self.empresa, nombre="Suc A", codigo_sucursal="SA")
        self.suc_b = Sucursal.objects.create(empresa=self.empresa, nombre="Suc B", codigo_sucursal="SB")

    def test_snapshot_con_sucursal_queda_aislado(self):
        snap_a = KPI_Snapshot.objects.create(
            empresa=self.empresa,
            sucursal=self.suc_a,
            fecha=timezone.now().date(),
            ingresos_total=Decimal("1000.00"),
        )
        self.assertIsNone(
            KPI_Snapshot.objects.filter(empresa=self.empresa, sucursal=self.suc_b).first()
        )
        self.assertEqual(
            KPI_Snapshot.objects.filter(empresa=self.empresa, sucursal=self.suc_a).count(), 1
        )


class DashboardPermisosTest(TestCase):
    """Endpoints respetan permisos por rol."""

    def setUp(self):
        self.factory = RequestFactory()
        self.empresa = Empresa.objects.create(nombre="Lab Perm", rfc="LP001", periodo_vigencia="2024-2030")

        self.gerente = User.objects.create_user(username="gerente_kpi", password="x", rol=Rol.GERENTE)
        self.gerente.empresa = self.empresa
        self.gerente.save()

        self.cajero = User.objects.create_user(username="cajero_kpi", password="x", rol=Rol.CAJA)
        self.cajero.empresa = self.empresa
        self.cajero.save()

        self.admin = User.objects.create_user(username="admin_kpi", password="x", rol=Rol.ADMIN)
        self.admin.empresa = self.empresa
        self.admin.save()

    def test_gerente_puede_ver_reportes(self):
        self.assertTrue(_has_permission(self.gerente, "finanzas:ver_reportes"))

    def test_cajero_no_puede_ver_reportes(self):
        self.assertFalse(_has_permission(self.cajero, "finanzas:ver_reportes"))

    def test_gerente_no_puede_exportar(self):
        """generar_snapshot requiere finanzas:exportar — GERENTE no lo tiene."""
        self.assertFalse(_has_permission(self.gerente, "finanzas:exportar"))

    def test_admin_puede_exportar(self):
        self.assertTrue(_has_permission(self.admin, "finanzas:exportar"))

    def test_director_puede_exportar(self):
        director = User.objects.create_user(username="dir_kpi", password="x", rol=Rol.DIRECTOR)
        director.empresa = self.empresa
        director.save()
        self.assertTrue(_has_permission(director, "finanzas:exportar"))

    def test_dashboard_hoy_403_para_cajero(self):
        from core.views.dashboard import dashboard_hoy
        request = self.factory.get("/api/dashboard/hoy")
        request.user = self.cajero
        # Simular tenant en thread-local
        set_current_empresa(self.empresa)
        try:
            response = dashboard_hoy(request)
            self.assertEqual(response.status_code, 403)
        finally:
            clear_current_empresa()

    def test_generar_snapshot_403_para_gerente(self):
        from core.views.dashboard import generar_snapshot
        request = self.factory.post("/api/dashboard/snapshot/generar")
        request.user = self.gerente
        set_current_empresa(self.empresa)
        try:
            response = generar_snapshot(request)
            self.assertEqual(response.status_code, 403)
        finally:
            clear_current_empresa()

    def test_generar_snapshot_201_para_admin(self):
        from core.views.dashboard import generar_snapshot
        request = self.factory.post("/api/dashboard/snapshot/generar")
        request.user = self.admin
        set_current_empresa(self.empresa)
        try:
            response = generar_snapshot(request)
            self.assertEqual(response.status_code, 201)
        finally:
            clear_current_empresa()
