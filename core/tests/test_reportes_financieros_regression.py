import json
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from core.models import Empresa, GastoCaja, GastoOperativo, Pago, Venta


Usuario = get_user_model()


class ReportesFinancierosRegressionTests(TestCase):
    def setUp(self):
        self.empresa = Empresa.objects.create(
            nombre='Empresa Reportes',
            rfc='REP260620TST',
        )
        self.usuario = Usuario.objects.create_user(
            username='reportes_user',
            password='test123456789',
            empresa=self.empresa,
            rol='ADMIN',
        )
        self.client.login(username='reportes_user', password='test123456789')

    def test_reporte_ingresos_egresos_incluye_gastos_operativos_en_detalle_diario(self):
        venta = Venta.objects.create(
            empresa=self.empresa,
            usuario=self.usuario,
            total=Decimal('100.00'),
            estado='COMPLETADA',
        )
        GastoCaja.objects.create(
            empresa=self.empresa,
            usuario=self.usuario,
            concepto='Caja',
            monto=Decimal('10.00'),
        )
        GastoOperativo.objects.create(
            empresa=self.empresa,
            usuario=self.usuario,
            categoria='SERVICIOS',
            descripcion='Internet',
            monto=Decimal('15.00'),
        )

        response = self.client.get(reverse('reporte_ingresos_egresos'))

        self.assertEqual(response.status_code, 200)
        datos_diarios = json.loads(response.context['datos_diarios'])
        self.assertTrue(datos_diarios)
        self.assertEqual(datos_diarios[-1]['ingresos'], 100.0)
        self.assertEqual(datos_diarios[-1]['egresos'], 25.0)
        self.assertEqual(datos_diarios[-1]['utilidad'], 75.0)

    def test_reporte_caja_excluye_ventas_canceladas_y_pagos_asociados(self):
        venta_ok = Venta.objects.create(
            empresa=self.empresa,
            usuario=self.usuario,
            total=Decimal('100.00'),
            estado='COMPLETADA',
        )
        venta_cancelada = Venta.objects.create(
            empresa=self.empresa,
            usuario=self.usuario,
            total=Decimal('999.00'),
            estado='CANCELADA',
        )
        Pago.objects.create(
            venta=venta_ok,
            metodo='EFECTIVO',
            monto=Decimal('100.00'),
        )
        Pago.objects.create(
            venta=venta_cancelada,
            metodo='EFECTIVO',
            monto=Decimal('999.00'),
        )

        response = self.client.get(reverse('genera_reporte_caja'))

        self.assertEqual(response.status_code, 200)
        datos = response.context['datos']
        self.assertEqual(datos['total_ventas'], Decimal('100.00'))
        self.assertEqual(datos['pagos_efectivo'], Decimal('100.00'))
