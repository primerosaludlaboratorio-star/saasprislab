"""
Regresión: el Dashboard de Director (/dashboard/) debe contar las ventas/órdenes
del día usando la fecha LOCAL, no la UTC.

Bug original: la vista usaba `timezone.now().date()` (fecha UTC) para construir la
ventana del día. Con TIME_ZONE=America/Mexico_City (UTC-6), entre 18:00 y 23:59
hora local la fecha UTC ya es "mañana", por lo que la ventana del día quedaba en el
futuro y el dashboard ejecutivo mostraba 0 ventas / 0 órdenes pese a la actividad
real de la tarde-noche. Fix: `timezone.localdate()`.
"""
from datetime import datetime, timezone as dt_timezone
from decimal import Decimal
from unittest import mock

from django.contrib.auth import get_user_model
from django.test import TestCase, Client

from core.models import Empresa, Sucursal, Venta

User = get_user_model()

# Instante en la ventana del bug: 03:30 UTC = 21:30 del día ANTERIOR en México (UTC-6).
EVENING_MX_UTC = datetime(2026, 6, 25, 3, 30, tzinfo=dt_timezone.utc)


class DirectorDashboardTZTest(TestCase):
    def test_dashboard_cuenta_ventas_del_dia_local_en_ventana_nocturna(self):
        with mock.patch('django.utils.timezone.now', return_value=EVENING_MX_UTC):
            emp = Empresa.objects.create(nombre='E DIR TZ', rfc='DTZ1234567')
            suc = Sucursal.objects.create(empresa=emp, nombre='S', codigo_sucursal='S-DTZ')
            director = User.objects.create_user(
                username='dirtz', password='p12345678', email='d@d.com',
                rol='DIRECTOR', empresa=emp, sucursal=suc,
                is_staff=True, is_superuser=True,
            )
            venta = Venta.objects.create(
                empresa=emp, sucursal=suc, usuario=director,
                total=Decimal('750.00'), estado='COMPLETADA',
            )
            # fecha es auto_now_add; la fijamos explícitamente al instante nocturno.
            Venta.objects.filter(pk=venta.pk).update(fecha=EVENING_MX_UTC)

            c = Client()
            c.force_login(director)
            r = c.get('/dashboard/')

        self.assertEqual(r.status_code, 200)
        ctx = r.context[-1]
        # Antes del fix esto daba 0 en la ventana nocturna; ahora cuenta la venta local.
        self.assertEqual(ctx['cantidad_ventas'], 1)
        self.assertEqual(ctx['total_ventas_hoy'], Decimal('750.00'))
