"""Enfoque 4 — Caja: saldo pendiente bloquea imprimir en UI (título del botón deshabilitado)."""
from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import Client, TestCase

from core.models import Empresa, OrdenDeServicio, Paciente

User = get_user_model()


class FinanceCajaSyncTests(TestCase):
    def setUp(self):
        self.empresa = Empresa.objects.create(nombre='Emp Finance UI', rfc='FIN123456AAA')
        self.user = User.objects.create_user(
            username='fin_ui_user',
            password='fin-pass-66',
            empresa=self.empresa,
            rol='QUIMICO',
            is_staff=True,
        )
        self.paciente = Paciente.objects.create(
            empresa=self.empresa,
            nombre_completo='Pac Fin',
            nombres='P',
            apellido_paterno='F',
            fecha_nacimiento=date(1990, 1, 1),
            sexo='M',
        )
        self.orden = OrdenDeServicio.objects.create(
            empresa=self.empresa,
            paciente=self.paciente,
            total=Decimal('500.00'),
            anticipo=Decimal('100.00'),
            estado='RESULTADOS_LISTOS',
            estado_pago='PAGADO',
            responsable_ingreso=self.user,
        )
        self.client = Client()
        self.client.force_login(self.user)

    def test_captura_muestra_bloqueo_financiero_en_ui(self):
        r = self.client.get(f'/laboratorio/captura/{self.orden.id}/', follow=True)
        self.assertIn(r.status_code, [200, 301, 302])
        html = r.content.decode('utf-8', errors='replace')
        self.assertIn('La orden no está completamente pagada', html)
