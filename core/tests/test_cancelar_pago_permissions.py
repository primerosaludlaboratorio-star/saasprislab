from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from core.models import Empresa, OrdenDeServicio, Paciente, PagoOrden


Usuario = get_user_model()


class CancelarPagoPermissionsTest(TestCase):
    def setUp(self):
        self.empresa = Empresa.objects.create(
            nombre='Empresa Pago',
            rfc='PAG260711TST',
        )
        self.staff_sin_rol = Usuario.objects.create_user(
            username='staff_sin_rol_pago',
            password='test123456789',
            empresa=self.empresa,
            rol='CAJA',
            is_staff=True,
        )
        self.usuario_admin = Usuario.objects.create_user(
            username='admin_pago',
            password='test123456789',
            empresa=self.empresa,
            rol='ADMIN',
        )
        self.paciente = Paciente.objects.create(
            empresa=self.empresa,
            nombre_completo='Paciente Pago',
            sexo='F',
        )
        self.orden = OrdenDeServicio.objects.create(
            empresa=self.empresa,
            paciente=self.paciente,
            responsable_ingreso=self.usuario_admin,
            total=Decimal('100.00'),
            anticipo=Decimal('100.00'),
            estado='PAGADO',
            estado_pago='PAGADO',
        )
        self.pago = PagoOrden.objects.create(
            orden=self.orden,
            monto_efectivo=Decimal('100.00'),
            usuario_registro=self.usuario_admin,
        )

    def test_staff_sin_rol_autorizado_no_puede_cancelar_pago(self):
        self.client.force_login(self.staff_sin_rol)

        response = self.client.post(
            reverse('api_cancelar_pago', args=[self.pago.id]),
            data={'motivo': 'Intento no autorizado'},
        )

        self.assertEqual(response.status_code, 403)
        self.pago.refresh_from_db()
        self.assertFalse(self.pago.cancelado)
        self.assertIsNone(self.pago.cancelado_por)
