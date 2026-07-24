from datetime import date

from django.test import TestCase

from core.models import Empresa
from inventario.models import CatalogoReactivoLab, LoteReactivoLab


class TrazabilidadAdaptacionTests(TestCase):
    def setUp(self):
        self.empresa = Empresa.objects.create(nombre='Laboratorio de Adaptacion')
        self.reactivo = CatalogoReactivoLab.objects.create(
            empresa=self.empresa,
            codigo_interno='TST-001',
            nombre='Reactivo de prueba',
            tipo='REACTIVO',
            unidad_medida='UNIDAD',
        )

    def test_lote_operativo_puede_nacer_en_adaptacion(self):
        lote = LoteReactivoLab.objects.create(
            empresa=self.empresa,
            reactivo=self.reactivo,
            numero_lote='LOT-ADAPT-1',
            fecha_caducidad=date(2030, 1, 1),
            cantidad_inicial=10,
            cantidad_actual=10,
        )

        self.assertEqual(lote.trazabilidad_estado, 'ADAPTACION')
        self.assertIn('marca', lote.campos_pendientes)
        self.assertIn('factura', lote.campos_pendientes)
        self.assertIn('inserto', lote.campos_pendientes)
        self.assertEqual(lote.cantidad_actual, 10)

    def test_lote_pasa_a_completo_al_cerrar_datos_documentales(self):
        lote = LoteReactivoLab.objects.create(
            empresa=self.empresa,
            reactivo=self.reactivo,
            marca='Marca de prueba',
            numero_lote='LOT-COMP-1',
            fecha_caducidad=date(2030, 1, 1),
            fecha_compra=date(2026, 7, 23),
            factura_numero='FAC-001',
            inserto_estado='NO_APLICA',
            cantidad_inicial=10,
            cantidad_actual=10,
        )

        self.assertEqual(lote.trazabilidad_estado, 'COMPLETA')
        self.assertEqual(lote.campos_pendientes, [])
