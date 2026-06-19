"""
GUARDIÁN 360 v5.3 — evidencias mínimas sin crear BD de prueba completa.

- Ángulo 9 (CISO): War Room solo Director/Admin/Gerente; recepción → HTTP 403.
"""

from django.contrib.auth.models import Group
from django.test import RequestFactory, SimpleTestCase

from core.views.war_room import api_war_room_anomalias, war_room


class _UserRecepcion:
    is_authenticated = True
    is_superuser = False
    is_staff = False
    username = 'meli_recepcion_test'
    rol = 'RECEPCION'
    empresa = None


class TestWarRoomCisoRecepcion(SimpleTestCase):
    """Recepcionista no debe acceder a /director/war-room/ ni a su API (decorador)."""

    def test_war_room_ui_403_recepcion(self):
        request = RequestFactory().get('/director/war-room/')
        request.user = _UserRecepcion()
        response = war_room(request)
        self.assertEqual(response.status_code, 403)

    def test_war_room_api_403_recepcion(self):
        request = RequestFactory().get('/director/war-room/api/anomalias/')
        request.user = _UserRecepcion()
        response = api_war_room_anomalias(request)
        self.assertEqual(response.status_code, 403)
