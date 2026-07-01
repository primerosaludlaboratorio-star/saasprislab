"""Enfoque 6 — Rol RECEPCION no puede guardar resultados de laboratorio (403)."""
import json
from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import Client, TestCase

from core.models import DetalleOrden, Empresa, OrdenDeServicio, Paciente
from lims.models import Analito

User = get_user_model()


class RolePermissionHygieneTests(TestCase):
    def setUp(self):
        self.empresa = Empresa.objects.create(nombre='Emp Roles', rfc='ROL123456AAA')
        self.quimico = User.objects.create_user(
            username='setup_quimico',
            password='x',
            empresa=self.empresa,
            rol='QUIMICO',
            is_staff=True,
        )
        self.recepcion = User.objects.create_user(
            username='solo_recepcion',
            password='rec-pass-55',
            empresa=self.empresa,
            rol='RECEPCION',
            is_staff=False,
        )
        self.paciente = Paciente.objects.create(
            empresa=self.empresa,
            nombre_completo='Pac Rol',
            nombres='P',
            apellido_paterno='R',
            fecha_nacimiento=date(1992, 1, 1),
            sexo='M',
        )
        self.analito = Analito.objects.create(
            empresa=self.empresa,
            codigo='ROL-GLU',
            abreviatura='RGLU',
            nombre='Glucosa Rol',
            departamento='Química',
            tipo_resultado='NUMERICO',
            es_calculado=False,
        )
        self.orden = OrdenDeServicio.objects.create(
            empresa=self.empresa,
            paciente=self.paciente,
            total=Decimal('60.00'),
            anticipo=Decimal('60.00'),
            estado='EN_PROCESO',
            estado_pago='PAGADO',
            responsable_ingreso=self.quimico,
        )
        self.detalle = DetalleOrden.objects.create(
            orden=self.orden,
            analito=self.analito,
            precio_momento=Decimal('60.00'),
        )

    def test_recepcion_recibe_403_en_api_guardar_resultados(self):
        self.client = Client()
        self.assertTrue(self.client.login(username='solo_recepcion', password='rec-pass-55'))
        url = f'/laboratorio/api/guardar-resultados/{self.orden.id}/'
        payload = {
            'accion': 'borrador',
            'resultados': {
                str(self.detalle.id): {
                    'resultado': '',
                    'observaciones': '',
                    'parametros': {str(self.analito.id): {'valor': '90'}},
                }
            },
        }
        r = self.client.post(
            url,
            data=json.dumps(payload),
            content_type='application/json',
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )
        self.assertEqual(r.status_code, 403)
