"""
Pruebas canónicas del módulo Recepción (equivalentes al resto de módulos auditados):
- aislamiento multi-tenant (IDOR) en check-in y cobro de citas
- corte por empresa=None en endpoints sensibles
- regresión de zona horaria: el dashboard cuenta las citas del día LOCAL

Bug TZ original: dashboard_recepcion/lista_espera usaban timezone.now().date()
(fecha UTC). Con TIME_ZONE=America/Mexico_City (UTC-6), entre 18:00 y 23:59 hora
local la fecha UTC ya es "mañana", por lo que `fecha_cita=hoy` no encontraba las
citas reales del día y el tablero mostraba 0. Fix: timezone.localdate().
"""
from datetime import datetime, timezone as dt_timezone, date, time
from unittest import mock

from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model

from core.models import Empresa, Sucursal, Paciente, CitaMedica

User = get_user_model()

# 03:30 UTC = 21:30 del día ANTERIOR en México (UTC-6).
EVENING_MX_UTC = datetime(2026, 6, 25, 3, 30, tzinfo=dt_timezone.utc)
LOCAL_TODAY = date(2026, 6, 24)  # fecha local en ese instante


def _user(username, empresa, *, sucursal=None, rol='RECEPCION'):
    u = User.objects.create_user(username=username, password='test12345', email=f'{username}@t.com')
    u.empresa = empresa
    u.sucursal = sucursal
    u.rol = rol
    u.save()
    return u


def _cita(empresa, paciente, fecha_cita, estado='PENDIENTE'):
    return CitaMedica.objects.create(
        empresa=empresa, paciente=paciente, fecha_cita=fecha_cita,
        hora_cita=time(10, 0), motivo='Consulta', estado=estado,
    )


class RecepcionTenantTest(TestCase):
    """check-in y cobro NO deben tocar citas de otra empresa (IDOR)."""

    @classmethod
    def setUpTestData(cls):
        cls.empA = Empresa.objects.create(nombre='Rec A', rfc='RCA010101AA1')
        cls.empB = Empresa.objects.create(nombre='Rec B', rfc='RCB010101BB2')
        cls.userA = _user('recA', cls.empA)
        cls.pacB = Paciente.objects.create(empresa=cls.empB, nombres='P', apellido_paterno='B', nombre_completo='P B')
        cls.citaB = _cita(cls.empB, cls.pacB, LOCAL_TODAY)

    def _c(self):
        c = Client(); c.force_login(self.userA); return c

    def test_check_in_cita_de_otra_empresa_404(self):
        r = self._c().get(reverse('recepcion:check_in_paciente', args=[self.citaB.id]))
        self.assertEqual(r.status_code, 404)

    def test_cobrar_cita_de_otra_empresa_404(self):
        r = self._c().get(reverse('recepcion:cobrar_consulta', args=[self.citaB.id]))
        self.assertEqual(r.status_code, 404)


class RecepcionEmpresaNoneTest(TestCase):
    """Sin empresa => corta a 'home' (redirect)."""

    def test_dashboard_sin_empresa_redirige(self):
        u = _user('rec_noemp', None)
        # El signal auto_assign_empresa_nuevo_usuario vincula al crear; forzamos NULL real.
        User.objects.filter(pk=u.pk).update(empresa=None)
        c = Client(); c.force_login(u)
        r = c.get(reverse('recepcion:dashboard_recepcion'))
        self.assertEqual(r.status_code, 302)


class RecepcionDashboardTZTest(TestCase):
    """El dashboard cuenta las citas del día LOCAL en la ventana nocturna."""

    def test_dashboard_cuenta_citas_del_dia_local(self):
        with mock.patch('django.utils.timezone.now', return_value=EVENING_MX_UTC):
            emp = Empresa.objects.create(nombre='Rec TZ', rfc='RTZ010101TZ1')
            user = _user('rec_tz', emp)
            pac = Paciente.objects.create(empresa=emp, nombres='P', apellido_paterno='T', nombre_completo='P T')
            _cita(emp, pac, LOCAL_TODAY)  # cita de "hoy" local
            c = Client(); c.force_login(user)
            r = c.get(reverse('recepcion:dashboard_recepcion'))

        self.assertEqual(r.status_code, 200)
        # Con el bug (UTC) esto daba 0 en la ventana nocturna; con el fix cuenta la cita local.
        self.assertEqual(r.context[-1]['total_citas_hoy'], 1)
        self.assertEqual(r.context[-1]['citas_pendientes'], 1)
