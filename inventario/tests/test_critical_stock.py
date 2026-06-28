"""Prueba agregación de stock crítico (cron / War Room) — campo cantidad_actual."""
from datetime import date
from decimal import Decimal

from django.db.models import Q
from django.test import TestCase

from core.models import Empresa
from inventario.models import CatalogoReactivoLab, LoteReactivoLab
from inventario.services.critical_stock import queryset_items_bajo_stock_minimo


class TestCriticalStockAggregation(TestCase):
    def setUp(self):
        self.empresa = Empresa.objects.create(nombre='Empresa Test Stock')
        self.reactivo = CatalogoReactivoLab.objects.create(
            empresa=self.empresa,
            codigo_interno='TST-R1',
            nombre='Reactivo prueba',
            stock_minimo=Decimal('10.0000'),
        )

    def test_lab_solo_suma_lotes_activos(self):
        LoteReactivoLab.objects.create(
            empresa=self.empresa,
            reactivo=self.reactivo,
            numero_lote='CUAR-1',
            fecha_caducidad=date(2030, 1, 1),
            cantidad_inicial=Decimal('100'),
            cantidad_actual=Decimal('100'),
            estado='CUARENTENA',
        )
        LoteReactivoLab.objects.create(
            empresa=self.empresa,
            reactivo=self.reactivo,
            numero_lote='ACT-1',
            fecha_caducidad=date(2030, 6, 1),
            cantidad_inicial=Decimal('5'),
            cantidad_actual=Decimal('5'),
            estado='ACTIVO',
        )
        qs = queryset_items_bajo_stock_minimo(
            self.empresa, CatalogoReactivoLab, Q(lotes__estado='ACTIVO')
        )
        self.assertTrue(qs.filter(pk=self.reactivo.pk).exists(), '5 activo < mínimo 10')
        agg = qs.get(pk=self.reactivo.pk)
        self.assertEqual(agg.stock_total, Decimal('5'))

    def test_solo_cuarentena_stock_operativo_cero_con_minimo_cero_no_alerta(self):
        CatalogoReactivoLab.objects.filter(pk=self.reactivo.pk).update(stock_minimo=Decimal('0'))
        LoteReactivoLab.objects.create(
            empresa=self.empresa,
            reactivo=self.reactivo,
            numero_lote='SOLO-CUAR',
            fecha_caducidad=date(2030, 1, 1),
            cantidad_inicial=Decimal('50'),
            cantidad_actual=Decimal('50'),
            estado='CUARENTENA',
        )
        qs = queryset_items_bajo_stock_minimo(
            self.empresa, CatalogoReactivoLab, Q(lotes__estado='ACTIVO')
        )
        self.assertFalse(
            qs.filter(pk=self.reactivo.pk).exists(),
            'Cuarentena no entra en suma ACTIVO; stock operativo 0 no debe disparar si mínimo es 0',
        )
