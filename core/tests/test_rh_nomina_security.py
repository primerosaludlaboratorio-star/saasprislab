"""
Tests de seguridad para RH/Nómina — PRISLAB v5.1
Cubre: acceso por rol, tenant isolation, mis_resultados, nómina sin empresa, PDFs.
"""
from datetime import date
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse

from core.models import (
    Empresa, Empleado, Competencia, EvaluacionDesempeno,
    PeriodoNomina, ReciboNomina, Bitacora39A,
)

User = get_user_model()


class RHAccessControlTests(TestCase):
    """Acceso por rol a vistas RH sensibles."""

    def setUp(self):
        self.empresa = Empresa.objects.create(nombre='RH Test', rfc='RHTEST123')
        self.director = User.objects.create_user(
            username='rh_director', password='test', empresa=self.empresa, rol='DIRECTOR')
        self.gerente = User.objects.create_user(
            username='rh_gerente', password='test', empresa=self.empresa, rol='GERENTE')
        self.cajero = User.objects.create_user(
            username='rh_cajero', password='test', empresa=self.empresa, rol='CAJERO')
        self.recepcion = User.objects.create_user(
            username='rh_recepcion', password='test', empresa=self.empresa, rol='RECEPCION')

        self.empleado = Empleado.objects.create(
            usuario=self.cajero, empresa=self.empresa,
            puesto='Cajero', fecha_ingreso=date.today())

        self.evaluacion = EvaluacionDesempeno.objects.create(
            empleado=self.empleado, evaluador=self.director,
            periodo='Q1 2026', estado='COMPLETADA')

        self.bitacora = Bitacora39A.objects.create(
            empleado=self.empleado, periodo_semanal='2026-S01',
            fecha_inicio=date.today(), fecha_fin=date.today(),
            evaluador=self.director)

        self.competencia = Competencia.objects.create(
            nombre='Liderazgo', tipo='BLANDA')

    def _login(self, user):
        self.client = Client()
        self.client.login(username=user.username, password='test')

    # ── Evaluaciones 39-A ──────────────────────────────────────────────
    def test_cajero_403_lista_evaluaciones_39a(self):
        self._login(self.cajero)
        r = self.client.get(reverse('lista_evaluaciones_39a'))
        self.assertEqual(r.status_code, 403)

    def test_director_200_lista_evaluaciones_39a(self):
        self._login(self.director)
        r = self.client.get(reverse('lista_evaluaciones_39a'))
        self.assertEqual(r.status_code, 200)

    def test_cajero_403_crear_evaluacion_39a(self):
        self._login(self.cajero)
        r = self.client.get(reverse('crear_evaluacion_39a'))
        self.assertEqual(r.status_code, 403)

    def test_cajero_403_ver_evaluacion_39a(self):
        self._login(self.cajero)
        r = self.client.get(reverse('ver_evaluacion_39a', args=[self.bitacora.id]))
        self.assertEqual(r.status_code, 403)

    def test_cajero_403_descargar_pdf_39a(self):
        self._login(self.cajero)
        r = self.client.get(reverse('descargar_pdf_evaluacion_39a', args=[self.bitacora.id]))
        self.assertEqual(r.status_code, 403)

    # ── Evaluación de Desempeño ────────────────────────────────────────
    def test_cajero_403_nueva_evaluacion_desempeno(self):
        self._login(self.cajero)
        r = self.client.get(reverse('nueva_evaluacion_desempeno'))
        self.assertEqual(r.status_code, 403)

    def test_cajero_403_ver_evaluacion_desempeno(self):
        self._login(self.cajero)
        r = self.client.get(reverse('ver_evaluacion_desempeno', args=[self.evaluacion.id]))
        self.assertEqual(r.status_code, 403)

    def test_director_200_ver_evaluacion_desempeno(self):
        self._login(self.director)
        r = self.client.get(reverse('ver_evaluacion_desempeno', args=[self.evaluacion.id]))
        self.assertEqual(r.status_code, 200)

    # ── Matriz de Talento ──────────────────────────────────────────────
    def test_cajero_403_matriz_talento(self):
        self._login(self.cajero)
        r = self.client.get(reverse('matriz_talento'))
        self.assertEqual(r.status_code, 403)

    def test_director_200_matriz_talento(self):
        self._login(self.director)
        r = self.client.get(reverse('matriz_talento'))
        self.assertEqual(r.status_code, 200)


class TenantIsolationRHTests(TestCase):
    """Tenant isolation en evaluaciones RH."""

    def setUp(self):
        self.empresa_a = Empresa.objects.create(nombre='Emp A', rfc='AAAA123456')
        self.empresa_b = Empresa.objects.create(nombre='Emp B', rfc='BBBB123456')

        self.user_a = User.objects.create_user(
            username='user_a', password='test', empresa=self.empresa_a, rol='DIRECTOR')
        self.user_b = User.objects.create_user(
            username='user_b', password='test', empresa=self.empresa_b, rol='DIRECTOR')

        self.empleado_a = Empleado.objects.create(
            usuario=self.user_a, empresa=self.empresa_a,
            puesto='Dir', fecha_ingreso=date.today())

        self.eval_a = EvaluacionDesempeno.objects.create(
            empleado=self.empleado_a, evaluador=self.user_a,
            periodo='Q1', estado='COMPLETADA')

        self.bitacora_a = Bitacora39A.objects.create(
            empleado=self.empleado_a, periodo_semanal='2026-S01',
            fecha_inicio=date.today(), fecha_fin=date.today(),
            evaluador=self.user_a)

    def test_user_b_cannot_see_evaluacion_39a_of_empresa_a(self):
        self.client = Client()
        self.client.login(username='user_b', password='test')
        r = self.client.get(reverse('ver_evaluacion_39a', args=[self.bitacora_a.id]))
        self.assertEqual(r.status_code, 404)

    def test_user_b_cannot_see_evaluacion_desempeno_of_empresa_a(self):
        self.client = Client()
        self.client.login(username='user_b', password='test')
        r = self.client.get(reverse('ver_evaluacion_desempeno', args=[self.eval_a.id]))
        self.assertEqual(r.status_code, 404)


class MisResultadosTenantTests(TestCase):
    """Tenant isolation en mis_resultados."""

    def setUp(self):
        self.empresa_a = Empresa.objects.create(nombre='Emp A', rfc='CCCC123456')
        self.empresa_b = Empresa.objects.create(nombre='Emp B', rfc='DDDD123456')

        self.user_a = User.objects.create_user(
            username='emp_a_user', password='test', empresa=self.empresa_a, rol='CAJERO')
        self.user_b = User.objects.create_user(
            username='emp_b_user', password='test', empresa=self.empresa_b, rol='CAJERO')
        # Usuario separado para el cross-tenant (OneToOneField en Empleado)
        self.user_cross = User.objects.create_user(
            username='emp_cross_user', password='test', empresa=self.empresa_a, rol='CAJERO')

        # Empleado en empresa A con usuario de empresa A
        self.empleado_a = Empleado.objects.create(
            usuario=self.user_a, empresa=self.empresa_a,
            puesto='Cajero', fecha_ingreso=date.today())

        # Empleado en empresa B pero con usuario cuya empresa es A (cross-tenant)
        self.empleado_cross = Empleado.objects.create(
            usuario=self.user_cross, empresa=self.empresa_b,
            puesto='Cajero', fecha_ingreso=date.today())

    def test_mis_resultados_blocks_cross_tenant_empleado(self):
        """Si empleado.empresa != user.empresa, debe redirigir a home."""
        self.client = Client()
        self.client.login(username='emp_cross_user', password='test')
        r = self.client.get(reverse('mis_resultados'))
        self.assertEqual(r.status_code, 302)

    def test_mis_resultados_allows_same_tenant(self):
        """Si empleado.empresa == user.empresa, debe permitir acceso."""
        self.empleado_cross.delete()  # Eliminar el cross-tenant
        self.client = Client()
        self.client.login(username='emp_a_user', password='test')
        r = self.client.get(reverse('mis_resultados'))
        self.assertEqual(r.status_code, 200)


class NominaSinEmpresaTests(TestCase):
    """Nómina debe fallar con 403 si usuario no tiene empresa."""

    def setUp(self):
        self.empresa = Empresa.objects.create(nombre='Nom Emp', rfc='NOM123456')
        self.user_sin_empresa = User.objects.create_user(
            username='sin_emp', password='test', empresa=None, rol='DIRECTOR')

    def test_nomina_dashboard_sin_empresa_bloqueado(self):
        """Sin empresa, _empresa() lanza PermissionDenied → Sentinel devuelve 503."""
        self.client = Client()
        self.client.login(username='sin_emp', password='test')
        r = self.client.get(reverse('nomina_dashboard'))
        self.assertIn(r.status_code, [403, 503])

    def test_nomina_lista_periodos_sin_empresa_bloqueado(self):
        """Sin empresa, _empresa() lanza PermissionDenied → Sentinel devuelve 503."""
        self.client = Client()
        self.client.login(username='sin_emp', password='test')
        r = self.client.get(reverse('nomina_lista_periodos'))
        self.assertIn(r.status_code, [403, 503])


class NominaRoleAccessTests(TestCase):
    """Acceso por rol a vistas de nómina."""

    def setUp(self):
        self.empresa = Empresa.objects.create(nombre='Nom Role', rfc='NRL123456')
        self.director = User.objects.create_user(
            username='nom_dir', password='test', empresa=self.empresa, rol='DIRECTOR')
        self.cajero = User.objects.create_user(
            username='nom_caj', password='test', empresa=self.empresa, rol='CAJERO')

        self.periodo = PeriodoNomina.objects.create(
            empresa=self.empresa, nombre='Q1-2026',
            frecuencia='QUINCENAL', fecha_inicio=date.today(),
            fecha_fin=date.today())

    def test_cajero_403_nomina_dashboard(self):
        self.client = Client()
        self.client.login(username='nom_caj', password='test')
        r = self.client.get(reverse('nomina_dashboard'))
        self.assertEqual(r.status_code, 403)

    def test_director_200_nomina_dashboard(self):
        self.client = Client()
        self.client.login(username='nom_dir', password='test')
        r = self.client.get(reverse('nomina_dashboard'))
        self.assertEqual(r.status_code, 200)

    def test_cajero_403_nomina_detalle_periodo(self):
        self.client = Client()
        self.client.login(username='nom_caj', password='test')
        r = self.client.get(reverse('nomina_detalle_periodo', args=[self.periodo.id]))
        self.assertEqual(r.status_code, 403)


class CompetenciaCatalogTests(TestCase):
    """Pruebas de catálogo Competencia (global)."""

    def setUp(self):
        self.empresa = Empresa.objects.create(nombre='Comp Emp', rfc='CMP123456')
        self.admin = User.objects.create_user(
            username='comp_admin', password='test', empresa=self.empresa,
            rol='ADMIN', is_staff=True)
        self.normal = User.objects.create_user(
            username='comp_user', password='test', empresa=self.empresa, rol='CAJERO')

    def test_competencia_no_tiene_fk_empresa(self):
        """Competencia es catálogo global — no debe tener FK a empresa."""
        from django.db.models import ForeignKey
        fks = [f for f in Competencia._meta.get_fields() if isinstance(f, ForeignKey)]
        fk_names = [f.name for f in fks]
        self.assertNotIn('empresa', fk_names)

    def test_competencia_admin_solo_superuser_puede_crear(self):
        from core.admin import CompetenciaAdmin
        admin = CompetenciaAdmin(Competencia, None)
        request = type('req', (), {'user': self.admin})()
        self.assertFalse(admin.has_add_permission(request))

    def test_competencia_admin_superuser_puede_crear(self):
        from core.admin import CompetenciaAdmin
        admin = CompetenciaAdmin(Competencia, None)
        su = User.objects.create_superuser(username='su', password='test')
        request = type('req', (), {'user': su})()
        self.assertTrue(admin.has_add_permission(request))

    def test_competencia_admin_non_superuser_cannot_change_or_delete(self):
        from core.admin import CompetenciaAdmin
        admin = CompetenciaAdmin(Competencia, None)
        request = type('req', (), {'user': self.admin})()
        competencia = Competencia.objects.create(nombre='Comunicación', tipo='BLANDA')
        self.assertFalse(admin.has_change_permission(request, competencia))
        self.assertFalse(admin.has_delete_permission(request, competencia))


class PDFDownloadPermissionsTests(TestCase):
    """Descarga de PDF con permisos correctos."""

    def setUp(self):
        self.empresa = Empresa.objects.create(nombre='PDF Emp', rfc='PDF123456')
        self.director = User.objects.create_user(
            username='pdf_dir', password='test', empresa=self.empresa, rol='DIRECTOR')
        self.cajero = User.objects.create_user(
            username='pdf_caj', password='test', empresa=self.empresa, rol='CAJERO')
        self.empleado = Empleado.objects.create(
            usuario=self.cajero, empresa=self.empresa,
            puesto='Cajero', fecha_ingreso=date.today())
        self.bitacora = Bitacora39A.objects.create(
            empleado=self.empleado, periodo_semanal='2026-S01',
            fecha_inicio=date.today(), fecha_fin=date.today(),
            evaluador=self.director)

    def test_cajero_403_descargar_pdf(self):
        self.client = Client()
        self.client.login(username='pdf_caj', password='test')
        r = self.client.get(reverse('descargar_pdf_evaluacion_39a', args=[self.bitacora.id]))
        self.assertEqual(r.status_code, 403)

    def test_director_puede_descargar_pdf(self):
        """Director puede acceder a la descarga de PDF (puede fallar si no hay archivo)."""
        self.client = Client()
        self.client.login(username='pdf_dir', password='test')
        r = self.client.get(reverse('descargar_pdf_evaluacion_39a', args=[self.bitacora.id]))
        self.assertNotEqual(r.status_code, 403)
