from types import SimpleNamespace
from unittest.mock import patch

from django.core.exceptions import PermissionDenied
from django.http import HttpResponse
from django.test import RequestFactory, TestCase
from django.test import TestCase

from core.models import Empresa
from core.services.auto_repair import reparar_permisos_sesion
from core.middleware.sentinel import SentinelTelemetryMiddleware, _error_cache


class AutoRepairTenantGuardTest(TestCase):
    def setUp(self):
        _error_cache.clear()
        self.factory = RequestFactory()

    def _request(self, user):
        return SimpleNamespace(user=user, session={})

    def test_auto_repair_rechaza_superuser_sin_empresa(self):
        user = SimpleNamespace(
            username="super_sin_empresa",
            is_authenticated=True,
            is_superuser=True,
            rol="DIRECTOR",
            empresa=None,
            groups=SimpleNamespace(values_list=lambda *args, **kwargs: []),
        )

        with patch("core.services.auto_repair._regenerar_sesion_permisos") as regen:
            result = reparar_permisos_sesion(self._request(user), "/director/")

        self.assertFalse(result)
        regen.assert_not_called()

    def test_auto_repair_permite_superuser_con_empresa(self):
        empresa = Empresa.objects.create(nombre="Empresa Repair", rfc="ERP260623TST")
        user = SimpleNamespace(
            username="super_con_empresa",
            is_authenticated=True,
            is_superuser=True,
            rol="DIRECTOR",
            empresa=empresa,
            groups=SimpleNamespace(values_list=lambda *args, **kwargs: []),
        )

        with patch("core.services.auto_repair._regenerar_sesion_permisos") as regen:
            result = reparar_permisos_sesion(self._request(user), "/director/")

        self.assertTrue(result)
        regen.assert_called_once()

    def test_sentinel_permission_denied_no_auto_repair(self):
        empresa = Empresa.objects.create(nombre="Empresa Sentinel", rfc="SEN260623TST")
        user = SimpleNamespace(
            username="sentinel_user",
            is_authenticated=True,
            is_superuser=True,
            rol="DIRECTOR",
            empresa=empresa,
            id=77,
            groups=SimpleNamespace(values_list=lambda *args, **kwargs: []),
        )
        request = self.factory.get("/director/analizadores/")
        request.user = user

        middleware = SentinelTelemetryMiddleware(lambda req: None)

        with patch("core.services.auto_repair.reparar_permisos_sesion", return_value=True) as repair, \
             patch.object(SentinelTelemetryMiddleware, "_resolver_namespace", return_value="director"), \
             patch.object(SentinelTelemetryMiddleware, "_registrar_incidencia_async"), \
             patch.object(
                 SentinelTelemetryMiddleware,
                 "_render_error_page",
                 return_value=HttpResponse(status=403),
             ) as render_error:
            first = middleware.process_exception(request, PermissionDenied("denied"))

        repair.assert_not_called()
        render_error.assert_called_once()
        self.assertEqual(first.status_code, 403)

    def test_sentinel_error_page_responde_503_y_headers_degradados(self):
        request = self.factory.get("/director/analizadores/")
        request.user = SimpleNamespace(
            is_authenticated=True,
            is_superuser=True,
            username="sentinel_user",
            empresa=SimpleNamespace(pk=1),
        )
        middleware = SentinelTelemetryMiddleware(lambda req: None)

        response = middleware._render_error_page(
            request,
            "PermissionDenied",
            "MEDIA",
            "director",
            "/director/analizadores/",
            PermissionDenied("denied"),
        )

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response["X-Sentinel-Degraded"], "1")
        self.assertEqual(response["X-Sentinel-Error-Type"], "PermissionDenied")
        self.assertIn("Retry-After", response)
