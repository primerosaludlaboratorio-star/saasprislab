from datetime import date, datetime, timezone as dt_timezone
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from core.models import Empresa, OrdenDeServicio, Paciente, PagoOrden, Sucursal


User = get_user_model()


class LabCajaTimezoneRegressionTest(TestCase):
    def setUp(self):
        self.empresa = Empresa.objects.create(nombre="Empresa Finanzas TZ", rfc="FTZ260624AAA")
        self.sucursal = Sucursal.objects.create(
            empresa=self.empresa,
            nombre="Matriz TZ",
            codigo_sucursal="TZ-MTZ",
            activa=True,
        )
        self.usuario = User.objects.create_user(
            username="finanzas_tz_admin",
            password="Test2026!PRIS",
            empresa=self.empresa,
            sucursal=self.sucursal,
            rol="ADMIN",
        )
        self.paciente = Paciente.objects.create(
            empresa=self.empresa,
            sucursal=self.sucursal,
            nombre_completo="Paciente Finanzas TZ",
            nombres="Paciente",
            apellido_paterno="Finanzas",
            apellido_materno="TZ",
            sexo="F",
            fecha_nacimiento=date(1990, 1, 1),
        )
        self.client.login(username="finanzas_tz_admin", password="Test2026!PRIS")

    def test_caja_laboratorio_usa_fecha_local_para_kpis_del_dia(self):
        orden = OrdenDeServicio.objects.create(
            empresa=self.empresa,
            sucursal=self.sucursal,
            paciente=self.paciente,
            total=Decimal("500.00"),
            anticipo=Decimal("0.00"),
            estado="PAGADO",
            estado_pago="PAGADO",
            responsable_ingreso=self.usuario,
        )
        fecha_local_orden = timezone.make_aware(datetime(2026, 6, 24, 21, 30, 0))
        OrdenDeServicio.objects.filter(pk=orden.pk).update(
            fecha_creacion=fecha_local_orden,
            estado="ENTREGADO",
        )
        orden.refresh_from_db()

        pago = PagoOrden.objects.create(
            orden=orden,
            monto_efectivo=Decimal("500.00"),
            usuario_registro=self.usuario,
        )
        PagoOrden.objects.filter(pk=pago.pk).update(fecha_pago=fecha_local_orden)

        fake_utc_now = datetime(2026, 6, 25, 3, 32, 0, tzinfo=dt_timezone.utc)
        with patch("core.views.finanzas.timezone.now", return_value=fake_utc_now), patch(
            "core.views.finanzas.timezone.localdate", return_value=date(2026, 6, 24)
        ):
            response = self.client.get(reverse("caja_laboratorio"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["pacientes_atendidos"], 1)
        self.assertEqual(response.context["ordenes_completadas"], 1)
        self.assertEqual(response.context["ingresos_dia"], Decimal("500.00"))
