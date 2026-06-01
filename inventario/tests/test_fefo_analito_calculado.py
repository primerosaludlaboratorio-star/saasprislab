"""Punto 4 post-v1.40: FEFO no descuenta inventario para analitos calculados (es_calculado)."""
from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase

from core.models import Empresa, OrdenDeServicio, Paciente, ResultadoParametro
from lims.models import Analito
from inventario.models import (
    CatalogoReactivoLab,
    ConsumoEstudioReactivo,
    LoteReactivoLab,
    SalidaAnaliticaLab,
)

User = get_user_model()


class TestFefoIgnoraAnalitoCalculado(TestCase):
    def setUp(self):
        self.empresa = Empresa.objects.create(nombre='Emp FEFO Calc', rfc='FEC123456AAA')
        self.user = User.objects.create_user(
            username='fefo_calc_user',
            password='secret123',
            empresa=self.empresa,
            rol='ADMIN',
        )
        self.paciente = Paciente.objects.create(
            empresa=self.empresa,
            nombre_completo='Pac Calc',
            nombres='Pac',
            apellido_paterno='Calc',
            fecha_nacimiento=date(1990, 1, 1),
            sexo='M',
        )
        self.orden = OrdenDeServicio.objects.create(
            empresa=self.empresa,
            paciente=self.paciente,
            total=Decimal('50.00'),
            anticipo=Decimal('0'),
            estado='EN_PROCESO',
            estado_pago='PAGADO',
            responsable_ingreso=self.user,
        )
        self.analito = Analito.objects.create(
            empresa=self.empresa,
            codigo='TST-CALC-FEFO',
            abreviatura='TCF',
            nombre='Analito calculado prueba FEFO',
            departamento='Química',
            es_calculado=True,
            formula='1',
        )
        self.reactivo = CatalogoReactivoLab.objects.create(
            empresa=self.empresa,
            codigo_interno='R-CALC-GUARD',
            nombre='Reactivo no debe consumirse',
        )
        ConsumoEstudioReactivo.objects.create(
            empresa=self.empresa,
            analito=self.analito,
            reactivo=self.reactivo,
            cantidad_por_prueba=Decimal('5.0000'),
            unidad='UL',
            activo=True,
        )
        self.lote = LoteReactivoLab.objects.create(
            empresa=self.empresa,
            reactivo=self.reactivo,
            numero_lote='L-CALC-GUARD',
            fecha_caducidad=date(2030, 6, 1),
            cantidad_inicial=Decimal('100'),
            cantidad_actual=Decimal('100'),
            estado='ACTIVO',
        )

    def test_validar_resultado_calculado_no_crea_salida_ni_baja_stock(self):
        rp = ResultadoParametro.objects.create(
            orden=self.orden,
            analito=self.analito,
            valor='1.0',
            capturado_por=self.user,
            validado=True,
            validado_por=self.user,
            aprobado_por_humano=True,
        )
        self.assertTrue(rp.validado and rp.validado_por_id)

        self.lote.refresh_from_db()
        self.assertEqual(self.lote.cantidad_actual, Decimal('100'))
        self.assertFalse(
            SalidaAnaliticaLab.objects.filter(orden=self.orden, analito=self.analito).exists()
        )
