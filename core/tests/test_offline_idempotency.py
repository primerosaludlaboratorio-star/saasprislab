"""Punto 11: restricciones DB client_mutation_id (orden + pago laboratorio)."""
import uuid
from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.db import IntegrityError
from django.test import TestCase

from core.models import Empresa, OrdenDeServicio, Paciente, PagoOrden

User = get_user_model()


class ClientMutationConstraintTests(TestCase):
    def setUp(self):
        self.empresa = Empresa.objects.create(nombre='Emp Offline Idem', rfc='OFI123456AAA')
        self.user = User.objects.create_user(
            username='off_idem', password='secret123', empresa=self.empresa, rol='ADMIN',
        )
        self.paciente = Paciente.objects.create(
            empresa=self.empresa,
            nombre_completo='Ana Test',
            nombres='Ana',
            apellido_paterno='Test',
            fecha_nacimiento=date(2000, 1, 1),
            sexo='F',
        )

    def test_unique_orden_client_mutation_per_empresa(self):
        mid = uuid.uuid4()
        OrdenDeServicio.objects.create(
            empresa=self.empresa,
            paciente=self.paciente,
            total=Decimal('10.00'),
            anticipo=Decimal('0'),
            estado='PAGADO',
            estado_pago='PAGADO',
            responsable_ingreso=self.user,
            client_mutation_id=mid,
        )
        with self.assertRaises(IntegrityError):
            OrdenDeServicio.objects.create(
                empresa=self.empresa,
                paciente=self.paciente,
                total=Decimal('11.00'),
                anticipo=Decimal('0'),
                estado='PAGADO',
                estado_pago='PAGADO',
                responsable_ingreso=self.user,
                client_mutation_id=mid,
            )

    def test_unique_pago_orden_client_mutation(self):
        orden = OrdenDeServicio.objects.create(
            empresa=self.empresa,
            paciente=self.paciente,
            total=Decimal('100.00'),
            anticipo=Decimal('0'),
            estado='PENDIENTE_PAGO',
            estado_pago='PENDIENTE',
            responsable_ingreso=self.user,
        )
        mid = uuid.uuid4()
        PagoOrden.objects.create(
            orden=orden,
            monto_efectivo=Decimal('10.00'),
            client_mutation_id=mid,
        )
        with self.assertRaises(IntegrityError):
            PagoOrden.objects.create(
                orden=orden,
                monto_efectivo=Decimal('5.00'),
                client_mutation_id=mid,
            )
