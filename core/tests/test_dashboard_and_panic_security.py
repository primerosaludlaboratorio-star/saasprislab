import json
from types import SimpleNamespace
from unittest.mock import Mock, patch

from django.test import RequestFactory, SimpleTestCase

from core.views.dashboard_unificado import api_kpis_tiempo_real, dashboard_unificado
from core.views.laboratorio_captura import registrar_notificacion_panico


class DashboardAndPanicSecurityTests(SimpleTestCase):
    def test_employee_cannot_access_financial_dashboard(self):
        request = RequestFactory().get('/dashboard-unificado/')
        request.user = SimpleNamespace(
            is_authenticated=True,
            is_superuser=False,
            rol='CAJERO',
            username='empleado',
        )

        response = dashboard_unificado.__wrapped__(request)

        self.assertEqual(response.status_code, 403)

    def test_employee_cannot_access_realtime_financial_kpis(self):
        request = RequestFactory().get('/api/kpis-tiempo-real/')
        request.user = SimpleNamespace(
            is_authenticated=True,
            is_superuser=False,
            rol='RECEPCION',
            username='recepcion',
        )

        response = api_kpis_tiempo_real.__wrapped__(request)

        self.assertEqual(response.status_code, 403)

    def test_panic_notification_rejects_analito_outside_order(self):
        request = RequestFactory().post(
            '/laboratorio/captura/1/panico/',
            data={
                'analito_id': '77',
                'valor_critico': '1',
                'medico_notificado': 'Dr. Prueba',
                'medio_notificacion': 'TEL',
            },
        )
        request.user = SimpleNamespace(
            is_authenticated=True,
            empresa=object(),
            username='quimico',
        )
        orden = Mock()
        orden.detalles.filter.return_value.exists.return_value = False

        with patch(
            'core.views.laboratorio_captura.get_object_or_404',
            return_value=orden,
        ):
            response = registrar_notificacion_panico.__wrapped__(request, 1)

        self.assertEqual(response.status_code, 400)
        self.assertEqual(json.loads(response.content)['success'], False)
