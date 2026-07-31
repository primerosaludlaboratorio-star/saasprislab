from types import SimpleNamespace
from unittest.mock import patch

from django.test import RequestFactory, SimpleTestCase

from core.models import Empleado
from core.views.asistencia import _empleado_autorizado, autorizar_incidencia


class AsistenciaSecurityTests(SimpleTestCase):
    def test_employee_target_is_limited_to_own_employee_record(self):
        user = SimpleNamespace(
            is_superuser=False,
            rol='CAJERO',
            username='empleado',
        )
        request = SimpleNamespace(user=user)
        empresa = object()

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
