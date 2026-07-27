import json
from unittest.mock import patch

from django.test import SimpleTestCase

from core.services.ocr_documental import (
    _leer_receta_por_ocr_documental,
    _parsear_lineas_receta,
)


class OCRRecetaFarmaciaFallbackTests(SimpleTestCase):
    def test_parser_conserva_medicamento_dosis_y_duracion(self):
        datos = _parsear_lineas_receta(
            "1. Paracetamol 500 mg - tomar 1 tableta cada 8 horas por 5 dias\n"
            "2. Ibuprofeno 400 mg - tomar 1 tableta cada 12 horas por 3 dias"
        )

        self.assertEqual(len(datos["medicamentos"]), 2)
        self.assertIn("500 mg", datos["medicamentos"][0]["concentracion"])
        self.assertIn("5 dias", datos["medicamentos"][0]["indicaciones"])
        self.assertIn("12 horas", datos["medicamentos"][1]["indicaciones"])

    @patch("core.services.ocr_documental._deepseek_text_call")
    @patch("core.services.ocr_documental._google_cloud_vision_text")
    def test_cascada_vision_y_deepseek_devuelve_estructura(
        self, vision_mock, deepseek_mock
    ):
        vision_mock.return_value = "Paracetamol 500 mg cada 8 horas por 5 dias"
        deepseek_mock.return_value = json.dumps({
            "tipo_documento": "RECETA_MEDICA",
            "confianza": 0.91,
            "medicamentos": [{
                "texto": "Paracetamol 500 mg cada 8 horas por 5 dias",
                "nombre_comercial": "Paracetamol",
                "concentracion": "500 mg",
                "cantidad": 1,
                "indicaciones": "cada 8 horas por 5 dias",
                "confianza": 0.9,
            }],
        })

        datos, proveedor, meta = _leer_receta_por_ocr_documental("data:image/png;base64,AA==")

        self.assertEqual(proveedor, "google_cloud_vision+deepseek")
        self.assertEqual(datos["medicamentos"][0]["nombre_comercial"], "Paracetamol")
        self.assertTrue(meta["requiere_revision_humana"])

    @patch("core.services.ocr_documental._deepseek_text_call", return_value="")
    @patch("core.services.ocr_documental._google_cloud_vision_text")
    def test_parser_determinista_no_deja_vacia_la_lectura(self, vision_mock, _deepseek_mock):
        vision_mock.return_value = "1. Paracetamol 500 mg - 1 tableta cada 8 horas por 5 dias"

        datos, proveedor, meta = _leer_receta_por_ocr_documental("data:image/png;base64,AA==")

        self.assertEqual(proveedor, "google_cloud_vision+parser")
        self.assertEqual(len(datos["medicamentos"]), 1)
        self.assertTrue(meta["requiere_revision_humana"])
