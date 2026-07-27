from decimal import Decimal

from django.test import SimpleTestCase

from core.services.laboratorio_reportes_operativos import (
    construir_resumen_ventas_laboratorio,
)


class LaboratorioReportesProgresivosTest(SimpleTestCase):
    def test_linea_minima_se_reporta_sin_datos_de_inventario(self):
        detalle = type(
            "Detalle",
            (),
            {
                "pk": 17,
                "orden_id": 9,
                "analito_id": None,
                "perfil_lims_id": None,
                "paquete_lims_id": None,
                "descripcion_linea": "Glucosa",
                "precio_momento": Decimal("85.00"),
            },
        )()

        rows = construir_resumen_ventas_laboratorio([detalle], empresa=object())

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["estudio"], "Glucosa")
        self.assertEqual(rows[0]["ingresos"], Decimal("85.00"))
        self.assertEqual(rows[0]["reactivo_estado"], "Pendiente de capturar")
        self.assertEqual(rows[0]["costo_estado"], "Pendiente de capturar")
        self.assertTrue(rows[0]["enriquecimiento_pendiente"])

    def test_linea_sin_etiqueta_tiene_fallback_determinista(self):
        detalle = type(
            "Detalle",
            (),
            {
                "pk": 23,
                "orden_id": 9,
                "analito_id": None,
                "perfil_lims_id": None,
                "paquete_lims_id": None,
                "descripcion_linea": "",
                "precio_momento": Decimal("0.00"),
            },
        )()

        rows = construir_resumen_ventas_laboratorio([detalle], empresa=object())

        self.assertEqual(rows[0]["estudio"], "Línea de laboratorio #23")
