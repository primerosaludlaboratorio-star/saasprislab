"""
Regresión: el dashboard de Contabilidad NO debe contar ventas CANCELADAS como
ingreso del mes.

Bug original: `dashboard_contabilidad` sumaba `Venta.total` del mes sin filtrar
`estado`. Como `cancelar_venta` deja la venta con estado='CANCELADA' conservando
su `total`, los ingresos del mes quedaban inflados. Fix: filtrar estado='COMPLETADA'
(igual que el corte de caja y el dashboard de dirección).
"""
from decimal import Decimal

from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model

from core.models import Empresa, Sucursal, Venta

User = get_user_model()


class ContabilidadDashboardConteoTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.emp = Empresa.objects.create(nombre='Conta Co', rfc='CON010101AB1')
        cls.suc = Sucursal.objects.create(empresa=cls.emp, nombre='S', codigo_sucursal='S-CON')
        cls.user = User.objects.create_user(
            username='conta', password='test12345', email='c@c.com',
            empresa=cls.emp, sucursal=cls.suc, is_staff=True,
        )
        # Venta COMPLETADA (cuenta) + Venta CANCELADA (NO debe contar).
        Venta.objects.create(empresa=cls.emp, sucursal=cls.suc, usuario=cls.user,
                             total=Decimal('1000.00'), estado='COMPLETADA')
        Venta.objects.create(empresa=cls.emp, sucursal=cls.suc, usuario=cls.user,
                             total=Decimal('5000.00'), estado='CANCELADA')

    def test_ingresos_mes_excluye_ventas_canceladas(self):
        c = Client(); c.force_login(self.user)
        r = c.get(reverse('dashboard_contabilidad'))
        self.assertEqual(r.status_code, 200)
        ctx = r.context[-1]
        # Antes del fix daba 6000 (incluía la cancelada). Ahora solo la completada.
        self.assertEqual(ctx['ingresos_mes'], Decimal('1000.00'))
        self.assertEqual(ctx['ventas_count'], 1)
