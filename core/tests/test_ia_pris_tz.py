from datetime import date, datetime, timezone as dt_timezone
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase

from core.agent.pris_tools_operativos import tool_consultar_indicadores_kpi
from core.models import Empresa


User = get_user_model()


class IaPrisTimezoneRegressionTest(TestCase):
    def setUp(self):
        self.empresa = Empresa.objects.create(nombre="Empresa IA TZ", rfc="IAT260625AAA")
        self.usuario = User.objects.create_user(
            username="ia_tz_fix",
            password="Test2026!PRIS",
            empresa=self.empresa,
            rol="DIRECTOR",
        )

    def test_tool_consultar_indicadores_kpi_usa_fecha_local_en_hoy(self):
        fake_utc_now = datetime(2026, 6, 25, 3, 32, 0, tzinfo=dt_timezone.utc)
        with patch("core.agent.pris_tools_operativos.timezone.now", return_value=fake_utc_now), patch(
            "core.agent.pris_tools_operativos.localdate", return_value=date(2026, 6, 24)
        ):
            resultado = tool_consultar_indicadores_kpi(
                {"periodo": "HOY", "categoria": "GENERAL"},
                self.empresa,
                self.usuario,
            )

        self.assertEqual(resultado["periodo"], "HOY")
        self.assertEqual(resultado["desde"], "2026-06-24")
        self.assertEqual(resultado["hasta"], "2026-06-24")
