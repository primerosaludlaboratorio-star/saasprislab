from types import SimpleNamespace
from unittest.mock import Mock, patch

from django.contrib.auth import get_user_model
from django.contrib.messages.storage.fallback import FallbackStorage
from django.contrib.messages import get_messages
from django.http import HttpResponse
from django.contrib.sessions.middleware import SessionMiddleware
from django.test import RequestFactory, TestCase
from django.urls import reverse

from core.models import Empresa
from core.views import operaciones

User = get_user_model()


class OperacionesViewsTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.empresa_a = Empresa.objects.create(nombre='Empresa A', rfc='AAA010101AAA')
        self.empresa_b = Empresa.objects.create(nombre='Empresa B', rfc='BBB010101BBB')
        self.user_a = User.objects.create_user(
            username='operaciones_a',
            password='testpass123',
            empresa=self.empresa_a,
            rol='ADMIN',
        )
        self.user_sin_empresa = User.objects.create_user(
            username='operaciones_sin_empresa',
            password='testpass123',
            empresa=None,
            rol='ADMIN',
        )

    def _prepare_request(self, request):
        middleware = SessionMiddleware(lambda req: None)
        middleware.process_request(request)
        request.session.save()
        setattr(request, '_messages', FallbackStorage(request))
        return request

    @patch('core.views.operaciones.render')
    @patch('core.views.operaciones.OrdenDeServicio.objects.filter')
    def test_rutas_recoleccion_usa_empresa_efectiva_request(self, mock_filter, mock_render):
        request = self._prepare_request(self.factory.get('/logistica/rutas-recoleccion/'))
        request.user = self.user_a
        fake_ordenes = [
            SimpleNamespace(id=1, latitud=18.1, longitud=-95.2),
            SimpleNamespace(id=2, latitud=None, longitud=None),
        ]
        mock_qs = Mock()
        mock_qs.order_by.return_value = fake_ordenes
        mock_filter.return_value = mock_qs
        mock_render.return_value = HttpResponse('ok')

        response = operaciones.rutas_recoleccion.__wrapped__(request)

        self.assertEqual(response.status_code, 200)
        mock_filter.assert_called_once_with(empresa=self.empresa_a)
        _, _, context = mock_render.call_args[0]
        self.assertEqual(context['empresa'], self.empresa_a)
        self.assertEqual(context['total_ordenes'], 2)
        self.assertEqual(context['total_con_geo'], 1)

    @patch('core.views.operaciones.render')
    @patch('core.views.operaciones.OrdenDeServicio.objects.filter')
    def test_rutas_recoleccion_prioriza_empresa_actual_del_request(self, mock_filter, mock_render):
        request = self._prepare_request(self.factory.get('/logistica/rutas-recoleccion/'))
        request.user = self.user_a
        request.empresa_actual = self.empresa_b
        fake_ordenes = [SimpleNamespace(id=1, latitud=None, longitud=None)]
        mock_qs = Mock()
        mock_qs.order_by.return_value = fake_ordenes
        mock_filter.return_value = mock_qs
        mock_render.return_value = HttpResponse('ok')

        response = operaciones.rutas_recoleccion.__wrapped__(request)

        self.assertEqual(response.status_code, 200)
        mock_filter.assert_called_once_with(empresa=self.empresa_b)

    def test_rutas_recoleccion_redirige_si_no_hay_empresa(self):
        request = self._prepare_request(self.factory.get('/logistica/rutas-recoleccion/'))
        request.user = self.user_sin_empresa
        request.empresa_actual = None

        response = operaciones.rutas_recoleccion.__wrapped__(request)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('home'))
        mensajes = [m.message for m in get_messages(request)]
        self.assertIn('Usuario no tiene empresa asignada.', mensajes)

    @patch('core.views.operaciones.rutas_recoleccion')
    def test_monitor_rutas_delega_en_rutas_recoleccion(self, mock_rutas):
        request = self.factory.get('/logistica/rutas-recoleccion/')
        request.user = self.user_a
        mock_rutas.return_value = SimpleNamespace(status_code=200)

        response = operaciones.monitor_rutas.__wrapped__(request)

        self.assertEqual(response.status_code, 200)
        mock_rutas.assert_called_once_with(request)
