"""
Regresión: Caja de Laboratorio (finanzas/lab/caja/) debe contar las órdenes del
día usando la fecha LOCAL, no la UTC.

Bug original: la vista usaba `timezone.now().date()` (fecha UTC). Con
TIME_ZONE=America/Mexico_City (UTC-6), entre 18:00 y 23:59 hora local la fecha
UTC ya es "mañana", por lo que la ventana del día quedaba en el futuro y la caja
mostraba 0 ingresos/órdenes pese a haber actividad real. Fix: `timezone.localdate()`.
"""
from datetime import datetime, timezone as dt_timezone
from decimal import Decimal
from unittest import mock

from django.contrib.auth import get_user_model
from django.test import TestCase, Client

from core.models import Empresa, Sucursal, Paciente, OrdenDeServicio, DetalleOrden, PagoOrden

User = get_user_model()

# Instante en la ventana del bug: 03:30 UTC = 21:30 del día ANTERIOR en México (UTC-6).
EVENING_MX_UTC = datetime(2026, 6, 25, 3, 30, tzinfo=dt_timezone.utc)


class CajaLaboratorioTZTest(TestCase):
    def test_caja_cuenta_ordenes_del_dia_local_en_ventana_nocturna(self):
        with mock.patch('django.utils.timezone.now', return_value=EVENING_MX_UTC):
            emp = Empresa.objects.create(nombre='E TZ', rfc='TZ91234567')
            suc = Sucursal.objects.create(empresa=emp, nombre='S', codigo_sucursal='S-TZ9')
            u = User.objects.create_user(username='tzcaja', password='p12345678', email='t@t.com',
                                         rol='ADMIN', empresa=emp, sucursal=suc, is_staff=True, is_superuser=True)
            pac = Paciente.objects.create(nombres='P', apellido_paterno='T', nombre_completo='P T',
                                          empresa=emp, sucursal=suc)
            orden = OrdenDeServicio.objects.create(empresa=emp, sucursal=suc, paciente=pac, folio_orden='ORD-TZ',
                                                   total=Decimal('500'), anticipo=Decimal('500'), estado='PAGADO')
            DetalleOrden.objects.create(orden=orden, precio_momento=Decimal('500'))
            OrdenDeServicio.objects.filter(pk=orden.pk).update(estado='ENTREGADO')
            kw = {'orden': orden}
            flds = {f.name for f in PagoOrden._meta.fields}
            for k, v in [('monto_efectivo', Decimal('300')), ('monto_tarjeta', Decimal('200'))]:
                if k in flds:
                    kw[k] = v
            PagoOrden.objects.create(**kw)

            c = Client()
            c.force_login(u)
            r = c.get('/finanzas/lab/caja/')

        self.assertEqual(r.status_code, 200)
        ctx = r.context[-1]
        # Antes del fix esto daba 0 en la ventana nocturna; ahora cuenta la orden local.
        self.assertEqual(ctx['ingresos_dia'], Decimal('500'))
        self.assertEqual(ctx['ordenes_completadas'], 1)
        self.assertEqual(ctx['pacientes_atendidos'], 1)
