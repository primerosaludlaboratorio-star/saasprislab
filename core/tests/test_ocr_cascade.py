from unittest.mock import patch

from django.test import SimpleTestCase, override_settings

from core.services.ocr_documental import analizar_documento, _leer_receta_en_cascada, _vision_call_cascade


class OCRRecetaCascadaTests(SimpleTestCase):
    @override_settings(
        OCR_VISION_PRIMARY='deepseek',
        OCR_VISION_FALLBACK='gemini',
        DEEPSEEK_API_KEY='test-deepseek',
        DEEPSEEK_VISION_MODEL='test-vision',
        GOOGLE_API_KEY='test-gemini',
    )
    @patch('core.services.ocr_documental._deepseek_vision_call')
    @patch('core.services.ocr_documental._gemini_vision_call')
    def test_vision_usa_deepseek_como_primario(self, gemini, deepseek):
        deepseek.return_value = '{"tipo_documento":"RECETA_MEDICA"}'

        raw, proveedor, intentados = _vision_call_cascade('data:image/png;base64,AAAA', 'prompt')

        self.assertEqual(proveedor, 'deepseek')
        self.assertEqual(raw, '{"tipo_documento":"RECETA_MEDICA"}')
        self.assertEqual(intentados, ['deepseek'])
        gemini.assert_not_called()

    @override_settings(
        OCR_VISION_PRIMARY='deepseek',
        OCR_VISION_FALLBACK='gemini',
        DEEPSEEK_API_KEY='test-deepseek',
        DEEPSEEK_VISION_MODEL='test-vision',
        GOOGLE_API_KEY='test-gemini',
    )
    @patch('core.services.ocr_documental._deepseek_vision_call', return_value='')
    @patch('core.services.ocr_documental._gemini_vision_call', return_value='{"ok":true}')
    def test_vision_fallbacka_a_gemini_si_deepseek_no_responde(self, gemini, deepseek):
        raw, proveedor, intentados = _vision_call_cascade('data:image/png;base64,AAAA', 'prompt')

        self.assertEqual(proveedor, 'gemini')
        self.assertEqual(raw, '{"ok":true}')
        self.assertEqual(intentados, ['deepseek', 'gemini'])

    @override_settings(
        OCR_VISION_PRIMARY='deepseek',
        OCR_VISION_FALLBACK='gemini',
        DEEPSEEK_API_KEY='test-deepseek',
        DEEPSEEK_VISION_MODEL='test-vision',
        GOOGLE_API_KEY='',
    )
    @patch('core.services.feature_flags.flag_activo', return_value=True)
    @patch('core.services.ocr_documental._deepseek_vision_call', side_effect=[
        '{"tipo_documento":"OTRO","confianza":0.95}',
        '{"observaciones":"documento"}',
    ])
    def test_documento_no_exige_gemini_si_deepseek_esta_configurado(self, deepseek, _flag_activo):
        resultado = analizar_documento('data:image/png;base64,AAAA')

        self.assertEqual(resultado['proveedor_vision'], 'deepseek')
        self.assertEqual(resultado['datos_extraidos']['observaciones'], 'documento')
        self.assertTrue(resultado['requiere_revision_humana'])
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
