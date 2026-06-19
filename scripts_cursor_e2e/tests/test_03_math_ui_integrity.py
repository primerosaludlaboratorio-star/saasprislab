"""Enfoque 3 — Integridad fórmulas: preview API devuelve analito calculado coherente."""
import json
from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import Client, TestCase

from core.models import DetalleOrden, Empresa, OrdenDeServicio, Paciente
from lims.models import Analito

User = get_user_model()


class MathUiIntegrityTests(TestCase):
    def setUp(self):
        self.empresa = Empresa.objects.create(nombre='Emp Math UI', rfc='MAT123456AAA')
        self.user = User.objects.create_user(
            username='math_ui_user',
            password='math-pass-77',
            empresa=self.empresa,
            rol='QUIMICO',
            is_staff=True,
        )
        self.paciente = Paciente.objects.create(
            empresa=self.empresa,
            nombre_completo='Pac Math',
            nombres='P',
            apellido_paterno='M',
            fecha_nacimiento=date(1988, 1, 1),
            sexo='M',
        )
        self.base = Analito.objects.create(
            empresa=self.empresa,
            codigo='MATH_COL',
            abreviatura='COL',
            nombre='Colesterol base',
            departamento='Química',
            tipo_resultado='NUMERICO',
            unidades='mg/dL',
            es_calculado=False,
        )
        self.calc = Analito.objects.create(
            empresa=self.empresa,
            codigo='MATH_LDL',
            abreviatura='LDL',
            nombre='LDL calculado',
            departamento='Química',
            tipo_resultado='NUMERICO',
            unidades='mg/dL',
            es_calculado=True,
            formula='COL / 2',
        )
        self.orden = OrdenDeServicio.objects.create(
            empresa=self.empresa,
            paciente=self.paciente,
            total=Decimal('50.00'),
            anticipo=Decimal('50.00'),
            estado='EN_PROCESO',
            estado_pago='PAGADO',
            responsable_ingreso=self.user,
        )
        DetalleOrden.objects.create(orden=self.orden, analito=self.base, precio_momento=Decimal('25'))
        DetalleOrden.objects.create(orden=self.orden, analito=self.calc, precio_momento=Decimal('25'))
        self.client = Client()
        self.assertTrue(self.client.login(username='math_ui_user', password='math-pass-77'))

    def test_preview_formulas_propaga_valor_calculado(self):
        url = f'/laboratorio/api/preview-formulas/{self.orden.id}/'
        body = {'overrides': {str(self.base.id): '200'}}
        r = self.client.post(
            url,
            data=json.dumps(body),
            content_type='application/json',
        )
        self.assertEqual(r.status_code, 200, r.content[:600])
        data = r.json()
        self.assertEqual(data.get('status'), 'success')
        comp = data.get('computados') or {}
        self.assertIn(str(self.calc.id), comp)
        self.assertIn('100', str(comp[str(self.calc.id)]))
