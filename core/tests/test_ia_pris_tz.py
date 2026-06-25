"""
Regresión: la herramienta de KPIs del agente PRIS (`tool_consultar_indicadores_kpi`)
debe usar la fecha LOCAL para el periodo "HOY", no la UTC.

Bug original: usaba `timezone.now().date()` (fecha UTC). Con
TIME_ZONE=America/Mexico_City (UTC-6), entre 18:00 y 23:59 hora local la fecha UTC
ya es "mañana", por lo que `desde`/`hasta` del KPI y el conteo de ventas del día
quedaban desfasados un día y el director veía 0 actividad en la tarde-noche.
Fix: `timezone.localdate()`.

La aserción principal es sobre `hasta` (== fecha local), que NO depende del
comportamiento de `__date` en SQLite y por tanto distingue de forma robusta el
código viejo (UTC) del nuevo (local).
"""
from datetime import datetime, timezone as dt_timezone
from decimal import Decimal
from unittest import mock

from django.contrib.auth import get_user_model
from django.test import TestCase

from core.models import Empresa, Sucursal, Venta
from core.agent.pris_tools_operativos import tool_consultar_indicadores_kpi

User = get_user_model()

# 03:30 UTC = 21:30 del día ANTERIOR en México (UTC-6).
EVENING_MX_UTC = datetime(2026, 6, 25, 3, 30, tzinfo=dt_timezone.utc)


class PrisKpiTZTest(TestCase):
    def test_kpi_periodo_hoy_usa_fecha_local_en_ventana_nocturna(self):
        with mock.patch('django.utils.timezone.now', return_value=EVENING_MX_UTC):
            emp = Empresa.objects.create(nombre='E KPI TZ', rfc='KTZ1234567')
            suc = Sucursal.objects.create(empresa=emp, nombre='S', codigo_sucursal='S-KTZ')
            cajero = User.objects.create_user(
                username='kpitz', password='p12345678', email='k@k.com',
                rol='DIRECTOR', empresa=emp, sucursal=suc, is_staff=True, is_superuser=True,
            )
            venta = Venta.objects.create(
                empresa=emp, sucursal=suc, usuario=cajero,
                total=Decimal('480.00'), estado='COMPLETADA',
            )
            Venta.objects.filter(pk=venta.pk).update(fecha=EVENING_MX_UTC)

            kpis = tool_consultar_indicadores_kpi(
                {'periodo': 'HOY', 'categoria': 'FARMACIA'}, emp, cajero
            )

        # Discriminador robusto: con el bug (UTC) 'hasta' sería 2026-06-25.
        self.assertEqual(kpis['hasta'], '2026-06-24')
        self.assertEqual(kpis['desde'], '2026-06-24')
        # Y la venta nocturna real entra en el conteo del día local.
        self.assertEqual(kpis['farmacia']['ventas_total'], 1)
        self.assertEqual(kpis['farmacia']['ingresos_farmacia'], 480.0)
