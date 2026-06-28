"""Caracterizacion no destructiva de la arquitectura doble de Farmacia."""
from django.apps import apps
from django.test import SimpleTestCase
from django.urls import resolve


class FarmaciaArchitectureCharacterizationTest(SimpleTestCase):
    def test_rutas_devolucion_core_y_erp_resuelven_a_vistas_distintas(self):
        core_match = resolve('/farmacia/devoluciones/procesar/')
        erp_match = resolve('/farmacia/erp/devoluciones/procesar/')

        self.assertEqual(core_match.func.__module__, 'farmacia.views.devoluciones')
        self.assertEqual(core_match.func.__name__, 'procesar_devolucion')
        self.assertEqual(erp_match.func.__module__, 'farmacia.views.devoluciones')
        self.assertEqual(erp_match.func.__name__, 'procesar_devolucion')

    def test_no_existe_modelo_producto_en_app_farmacia(self):
        with self.assertRaises(LookupError):
            apps.get_model('farmacia', 'Producto')

    def test_devoluciones_referencian_venta_core(self):
        from core.models import SalesReturn
        from core.models.ventas import DevolucionVenta as CoreDevolucionVenta, Venta
        from farmacia.models import DevolucionVenta as FarmaciaDevolucionVenta

        self.assertIs(
            FarmaciaDevolucionVenta._meta.get_field('venta_original').remote_field.model,
            Venta,
        )
        self.assertIs(SalesReturn._meta.get_field('venta_original').remote_field.model, Venta)
        self.assertIs(
            CoreDevolucionVenta._meta.get_field('venta_original').remote_field.model,
            Venta,
        )

    def test_cierre_farmacia_tiene_constraint_por_apertura(self):
        from farmacia.models import AperturaCaja, CierreTurnoFarmacia

        self.assertIs(
            CierreTurnoFarmacia._meta.get_field('apertura_caja').remote_field.model,
            AperturaCaja,
        )
        self.assertIn(
            'unique_cierre_por_apertura',
            {constraint.name for constraint in CierreTurnoFarmacia._meta.constraints},
        )

