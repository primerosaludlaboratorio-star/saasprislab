import logging
from core.services.ocr_documental import analizar_receta_farmacia

logger = logging.getLogger(__name__)

class PRISOcrService:
    """
    Servicio de Inteligencia Artificial Embebido para extraer
    texto clínico (CIE-10, Medicamentos, Dosis) a partir de imágenes de recetas.
    Adaptador legacy al motor documental central.

    No devuelve datos simulados. Si el proveedor visual no está disponible,
    devuelve un error controlado para que el usuario pueda corregirlo.
    """
    @classmethod
    def procesar_receta(cls, image_data_b64: str) -> dict:
        """
        Procesa una receta mediante el flujo OCR centralizado.
        """
        try:
            if not image_data_b64:
                return {'success': False, 'error': 'Imagen vacía.'}
            logger.info("PRIS AI: Procesando imagen de receta médica (OCR Inferencia)")

            result = analizar_receta_farmacia(image_data_b64)
            if result.get('error'):
                return {
                    'success': False,
                    'error': result['error'],
                }
            return {
                'success': True,
                'engine': 'ocr_documental',
                'data': result.get('datos_extraidos', {}),
                'confidence': result.get('confianza', 0),
            }
        except Exception as e:
            logger.error(f"Error en PRIS AI OCR: {str(e)}")
            return {
                "success": False,
                "error": "El modelo no pudo extraer la información con confianza suficiente."
            }
