from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from django.test import RequestFactory, SimpleTestCase

from core.models import Empleado, IncidenciaAsistencia
from core.views.asistencia import _empleado_autorizado, autorizar_incidencia, crear_incidencia


class AsistenciaSecurityTests(SimpleTestCase):
    def test_employee_target_is_limited_to_own_employee_record(self):
        user = SimpleNamespace(
            is_superuser=False,
            rol='CAJERO',
            username='empleado',
        )
        request = SimpleNamespace(user=user)
        empresa = 7

        with patch('core.views.asistencia.get_object_or_404', return_value='empleado') as finder:
            self.assertEqual(_empleado_autorizado(request, empresa, 17), 'empleado')

        finder.assert_called_once_with(
            Empleado,
            id=17,
            empresa=empresa,
            usuario=user,
        )

    def test_employee_cannot_authorize_an_incidence(self):
        request = RequestFactory().post('/asistencia/incidencia/1/autorizar/')
        request.user = SimpleNamespace(
            is_authenticated=True,
            is_superuser=False,
            rol='CAJERO',
            username='empleado',
        )

        response = autorizar_incidencia.__wrapped__(request, 1)

        self.assertEqual(response.status_code, 403)

    def test_employee_get_cannot_load_another_employee_incidence(self):
        empresa = 7
        user = SimpleNamespace(
            is_authenticated=True,
            is_superuser=False,
            rol='CAJERO',
            username='empleado',
            empresa=empresa,
        )
        request = RequestFactory().get('/asistencia/incidencia/editar/?id=42')
        request.user = user

        with patch('core.views.asistencia.get_object_or_404', return_value='incidencia') as finder:
            empleados_qs = MagicMock()
            empleados_qs.filter.return_value.order_by.return_value = []
            with patch('core.views.asistencia.Empleado.objects.filter', return_value=empleados_qs):
                with patch('core.views.asistencia.render', return_value='response'):
                    crear_incidencia.__wrapped__(request)

        finder.assert_called_once_with(
            IncidenciaAsistencia,
            id='42',
            empresa=empresa,
            empleado__usuario=user,
        )
