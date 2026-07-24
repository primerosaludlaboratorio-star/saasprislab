from unittest.mock import patch

from django.test import SimpleTestCase

from .services.ocr_service import PRISOcrService


class LegacyOcrAdapterTests(SimpleTestCase):
    def test_empty_image_returns_controlled_error(self):
        result = PRISOcrService.procesar_receta('')

        self.assertFalse(result['success'])
        self.assertEqual(result['error'], 'Imagen vacía.')

    @patch('pris_ai_core.services.ocr_service.analizar_receta_farmacia')
    def test_adapter_exposes_central_ocr_result(self, analyze):
        analyze.return_value = {
            'datos_extraidos': {'medicamentos': [{'texto': 'Paracetamol'}]},
            'confianza': 0.91,
        }

        result = PRISOcrService.procesar_receta('data:image/png;base64,abc')

        self.assertTrue(result['success'])
        self.assertEqual(result['engine'], 'ocr_documental')
        self.assertEqual(result['confidence'], 0.91)
        analyze.assert_called_once()

    def test_adapter_propagates_provider_error_without_fake_data(self):
        with patch(
            'pris_ai_core.services.ocr_service.analizar_receta_farmacia',
            return_value={'error': 'Proveedor visual no disponible.'},
        ):
            result = PRISOcrService.procesar_receta('data:image/png;base64,abc')

        self.assertFalse(result['success'])
        self.assertEqual(result['error'], 'Proveedor visual no disponible.')
        self.assertNotIn('Paracetamol', result)
