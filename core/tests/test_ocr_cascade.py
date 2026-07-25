from unittest.mock import patch

from django.test import SimpleTestCase, override_settings

from core.services.ocr_documental import _leer_receta_en_cascada


class OCRRecetaCascadaTests(SimpleTestCase):
    @override_settings(
        OCR_VISION_PRIMARY='gemini',
        OCR_VISION_FALLBACK='deepseek',
        OCR_VISION_CONFIDENCE_THRESHOLD=0.72,
        GOOGLE_API_KEY='test-gemini',
        DEEPSEEK_API_KEY='test-deepseek',
        DEEPSEEK_VISION_MODEL='test-vision',
    )
    @patch('core.services.ocr_documental._deepseek_vision_call')
    @patch('core.services.ocr_documental._gemini_vision_call')
    def test_fallbacka_si_gemini_tiene_baja_confianza(self, gemini, deepseek):
        gemini.return_value = '{"confianza": 0.30, "medicamentos": []}'
        deepseek.return_value = '{"confianza": 0.91, "medicamentos": [{"texto": "paracetamol"}]}'

        datos, proveedor, meta = _leer_receta_en_cascada('data:image/png;base64,AAAA')

        self.assertEqual(proveedor, 'deepseek')
        self.assertEqual(datos['medicamentos'][0]['texto'], 'paracetamol')
        self.assertTrue(meta['fallback_utilizado'])
        self.assertFalse(meta['requiere_revision_humana'])

    @override_settings(
        OCR_VISION_PRIMARY='gemini',
        OCR_VISION_FALLBACK='',
        GOOGLE_API_KEY='test-gemini',
        OCR_VISION_CONFIDENCE_THRESHOLD=0.72,
    )
    @patch('core.services.ocr_documental._gemini_vision_call')
    def test_mantiene_revision_humana_bajo_umbral(self, gemini):
        gemini.return_value = '{"confianza": 0.40, "medicamentos": []}'

        datos, proveedor, meta = _leer_receta_en_cascada('data:image/png;base64,AAAA')

        self.assertEqual(proveedor, 'gemini')
        self.assertEqual(datos['confianza'], 0.40)
        self.assertTrue(meta['requiere_revision_humana'])
