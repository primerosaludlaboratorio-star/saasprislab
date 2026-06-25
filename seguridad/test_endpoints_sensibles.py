"""
Matriz de autorización de los endpoints sensibles de Seguridad.

Cubre los escenarios que faltaban:
- usuario SIN empresa en endpoints sensibles
- usuario con rol/permiso insuficiente
- staff/superuser SIN empresa
- distinción JSON (403) vs redirect (302) según el endpoint
- auditoría y estadísticas de seguridad

Endpoints bajo prueba:
- dashboard_auditoria  -> guard staff+empresa, responde con REDIRECT
- logs_auditoria       -> guard staff+empresa, REDIRECT
- api_estadisticas     -> guard staff+empresa, responde con JSON 403
- panic_button         -> requiere empresa (cualquier rol), JSON; POST-only
- rastro_paciente      -> role_required(DIRECTOR/ADMIN/GERENTE)+empresa
"""
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model

from core.models import Empresa

User = get_user_model()


def _mk(username, empresa=None, *, is_staff=False, is_superuser=False, rol=''):
    u = User.objects.create_user(username=username, password='test12345', email=f'{username}@t.com')
    u.is_staff = is_staff
    u.is_superuser = is_superuser
    if rol:
        u.rol = rol
    u.empresa = empresa
    u.save()
    # El signal auto_assign_empresa_nuevo_usuario vincula al usuario nuevo a la
    # empresa del hilo. Para EJERCITAR el guard "sin empresa" forzamos NULL real
    # vía .update() (bypassa save()/signals), que es el estado que el guard cubre.
    if empresa is None:
        User.objects.filter(pk=u.pk).update(empresa=None)
        u.refresh_from_db()
    return u


class SeguridadEndpointsSensiblesTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.empresa = Empresa.objects.create(nombre='Sec Co', rfc='SEC010101AB1')

    def _login(self, user):
        c = Client()
        c.force_login(user)
        return c

    # ---------- dashboard_auditoria (REDIRECT) ----------
    def test_dashboard_no_staff_redirige(self):
        c = self._login(_mk('u_nostaff', self.empresa, is_staff=False, rol='CAJERO'))
        r = c.get(reverse('seguridad:dashboard_auditoria'))
        self.assertEqual(r.status_code, 302)  # guard staff -> redirect

    def test_dashboard_staff_sin_empresa_redirige(self):
        c = self._login(_mk('u_staff_noemp', None, is_staff=True))
        r = c.get(reverse('seguridad:dashboard_auditoria'))
        self.assertEqual(r.status_code, 302)  # corta en empresa=None

    def test_dashboard_staff_con_empresa_ok(self):
        c = self._login(_mk('u_staff_ok', self.empresa, is_staff=True))
        r = c.get(reverse('seguridad:dashboard_auditoria'))
        self.assertEqual(r.status_code, 200)

    # ---------- logs_auditoria (REDIRECT) ----------
    def test_logs_no_staff_redirige(self):
        c = self._login(_mk('u_logs_nostaff', self.empresa, is_staff=False, rol='RECEPCION'))
        r = c.get(reverse('seguridad:logs_auditoria'))
        self.assertEqual(r.status_code, 302)

    # ---------- api_estadisticas (JSON 403) ----------
    def test_api_estadisticas_no_staff_json_403(self):
        c = self._login(_mk('u_api_nostaff', self.empresa, is_staff=False, rol='CAJERO'))
        r = c.get(reverse('seguridad:api_estadisticas'))
        self.assertEqual(r.status_code, 403)
        self.assertEqual(r['Content-Type'], 'application/json')
        self.assertIn('error', r.json())

    def test_api_estadisticas_staff_sin_empresa_json_403(self):
        c = self._login(_mk('u_api_noemp', None, is_staff=True))
        r = c.get(reverse('seguridad:api_estadisticas'))
        self.assertEqual(r.status_code, 403)
        self.assertEqual(r['Content-Type'], 'application/json')

    def test_api_estadisticas_staff_con_empresa_ok(self):
        c = self._login(_mk('u_api_ok', self.empresa, is_staff=True))
        r = c.get(reverse('seguridad:api_estadisticas'))
        self.assertEqual(r.status_code, 200)
        self.assertIn('sesiones_activas', r.json())

    # ---------- panic_button (JSON, POST-only, requiere empresa) ----------
    def test_panic_sin_empresa_json_403(self):
        c = self._login(_mk('u_panic_noemp', None, is_staff=False, rol='CAJERO'))
        r = c.post(reverse('seguridad:panic_button'), {})
        self.assertEqual(r.status_code, 403)
        self.assertFalse(r.json()['ok'])

    def test_panic_get_405(self):
        c = self._login(_mk('u_panic_get', self.empresa, rol='CAJERO'))
        r = c.get(reverse('seguridad:panic_button'))
        self.assertEqual(r.status_code, 405)

    def test_panic_con_empresa_ok(self):
        c = self._login(_mk('u_panic_ok', self.empresa, rol='CAJERO'))
        r = c.post(reverse('seguridad:panic_button'), {'ubicacion': 'Recepción'})
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.json()['ok'])

    # ---------- rastro_paciente (role_required + empresa) ----------
    def test_rastro_rol_insuficiente_403(self):
        c = self._login(_mk('u_rastro_caj', self.empresa, is_staff=False, rol='CAJERO'))
        r = c.get(reverse('seguridad:rastro_paciente'))
        self.assertEqual(r.status_code, 403)

    def test_rastro_director_ok(self):
        c = self._login(_mk('u_rastro_dir', self.empresa, is_staff=False, rol='DIRECTOR'))
        r = c.get(reverse('seguridad:rastro_paciente'))
        self.assertEqual(r.status_code, 200)
