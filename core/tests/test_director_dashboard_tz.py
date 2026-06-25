from datetime import date, datetime, timezone as dt_timezone
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from core.models import Empresa, Venta


User = get_user_model()


class DirectorDashboardTimezoneRegressionTest(TestCase):
    def setUp(self):
        self.empresa = Empresa.objects.create(nombre="Empresa Director TZ", rfc="DTZ260625AAA")
        self.usuario = User.objects.create_user(
            username="director_tz_fix",
            password="Test2026!PRIS",
            empresa=self.empresa,
            rol="DIRECTOR",
        )
        self.client.login(username="director_tz_fix", password="Test2026!PRIS")

    def test_dashboard_director_usa_fecha_local_para_metricas_del_dia(self):
        venta = Venta.objects.create(
            empresa=self.empresa,
            usuario=self.usuario,
            subtotal=Decimal("500.00"),
            total=Decimal("500.00"),
            estado="COMPLETADA",
        )
        fecha_local_venta = timezone.make_aware(datetime(2026, 6, 24, 21, 30, 0))
        Venta.objects.filter(pk=venta.pk).update(fecha=fecha_local_venta)

        fake_utc_now = datetime(2026, 6, 25, 3, 32, 0, tzinfo=dt_timezone.utc)
        with patch("core.views.director.timezone.now", return_value=fake_utc_now), patch(
            "core.views.director.localdate", return_value=date(2026, 6, 24)
        ):
            response = self.client.get(reverse("dashboard_director"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(int(response.context["total_ventas_hoy"]), 500)
