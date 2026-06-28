"""Regression de roles para vistas financieras no cubiertas por test_finanzas_seguridad."""
import json
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.http import Http404
from django.test import RequestFactory, TestCase
from django.urls import reverse

from core.models import Empresa, OrdenDeServicio, Paciente, Sucursal


Usuario = get_user_model()


class _RoleTestMixin:
    """Helper para crear usuarios con distintos roles."""

    def _user(self, rol, empresa, username=None):
        username = username or f'{rol.lower()}_role_test'
        return Usuario.objects.create_user(
            username=username,
            password='testpass123',
            empresa=empresa,
            rol=rol,
        )

    def _login(self, user):
        self.client.force_login(user)


class MotorFinancieroRoleTests(TestCase, _RoleTestMixin):
    """Vistas de motor_financiero deben requerir rol financiero."""

    def setUp(self):
        self.empresa = Empresa.objects.create(nombre='Empresa Motor', rfc='MOT260626AAA')
        self.finanzas = self._user('FINANZAS', self.empresa)
        self.cajero = self._user('CAJERO', self.empresa, username='cajero_role_test')

    def test_genera_reporte_caja_permite_finanzas(self):
        self._login(self.finanzas)
        resp = self.client.get(reverse('genera_reporte_caja'))
        self.assertEqual(resp.status_code, 200)

    def test_genera_reporte_caja_rechaza_cajero(self):
        self._login(self.cajero)
        resp = self.client.get(reverse('genera_reporte_caja'))
        self.assertEqual(resp.status_code, 403)

    def test_api_resumen_ejecutivo_permite_finanzas(self):
        self._login(self.finanzas)
        resp = self.client.get(reverse('api_resumen_ejecutivo_pris'))
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.content)
        self.assertEqual(data['status'], 'success')

    def test_api_resumen_ejecutivo_rechaza_cajero(self):
        self._login(self.cajero)
        resp = self.client.get(reverse('api_resumen_ejecutivo_pris'))
        self.assertEqual(resp.status_code, 403)


class CuentasPorCobrarRoleTests(TestCase, _RoleTestMixin):
    """APIs de CxC y convenios deben requerir rol financiero (vistas directas, no en URLconf)."""

    def setUp(self):
        self.empresa = Empresa.objects.create(nombre='Empresa CxC', rfc='CXC260626AAA')
        self.sucursal = Sucursal.objects.create(
            empresa=self.empresa,
            nombre='Matriz',
            codigo_sucursal='CXC-MTZ',
            activa=True,
        )
        self.finanzas = self._user('FINANZAS', self.empresa)
        self.cajero = self._user('CAJERO', self.empresa, username='cajero_cxc_test')
        self.paciente = Paciente.objects.create(
            empresa=self.empresa,
            sucursal=self.sucursal,
            nombre_completo='Paciente CxC',
            nombres='Paciente',
            apellido_paterno='CxC',
        )
        self.orden = OrdenDeServicio.objects.create(
            empresa=self.empresa,
            sucursal=self.sucursal,
            paciente=self.paciente,
            total=Decimal('100.00'),
            anticipo=Decimal('0.00'),
            estado='PAGADO',
            estado_pago='PAGADO',
            responsable_ingreso=self.finanzas,
        )

    def _request(self, user, method='GET', body=None):
        rf = RequestFactory()
        if method == 'GET':
            req = rf.get('/fake/')
        else:
            req = rf.post('/fake/', data=json.dumps(body or {}), content_type='application/json')
        req.user = user
        return req

    def test_reporte_fiscal_mensual_permite_finanzas(self):
        from core.views.cuentas_por_cobrar import reporte_fiscal_mensual

        req = self._request(self.finanzas)
        resp = reporte_fiscal_mensual(req)
        self.assertEqual(resp.status_code, 200)

    def test_reporte_fiscal_mensual_rechaza_cajero(self):
        from core.views.cuentas_por_cobrar import reporte_fiscal_mensual

        req = self._request(self.cajero)
        resp = reporte_fiscal_mensual(req)
        self.assertEqual(resp.status_code, 403)

    def test_api_registrar_pago_cxc_rechaza_cajero(self):
        from core.views.cuentas_por_cobrar import api_registrar_pago_cxc

        req = self._request(self.cajero, 'POST', {'cuenta_id': 1, 'monto': '10.00'})
        resp = api_registrar_pago_cxc(req)
        self.assertEqual(resp.status_code, 403)

    def test_api_crear_cxc_rechaza_cajero(self):
        from core.views.cuentas_por_cobrar import api_crear_cxc

        req = self._request(self.cajero, 'POST', {'orden_id': self.orden.id, 'convenio_id': 1})
        resp = api_crear_cxc(req)
        # No importa 403 o 404 por convenio inexistente; el rol debe bloquear primero.
        self.assertEqual(resp.status_code, 403)

    def test_convenios_lista_rechaza_cajero(self):
        from core.views.cuentas_por_cobrar import convenios_lista

        req = self._request(self.cajero)
        resp = convenios_lista(req)
        self.assertEqual(resp.status_code, 403)

    def test_api_crear_convenio_rechaza_cajero(self):
        from core.views.cuentas_por_cobrar import api_crear_convenio

        req = self._request(self.cajero, 'POST', {'nombre': 'Convenio'})
        resp = api_crear_convenio(req)
        self.assertEqual(resp.status_code, 403)
