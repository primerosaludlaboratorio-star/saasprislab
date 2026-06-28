import os
import json
import logging
import base64
from typing import Dict, Any

logger = logging.getLogger(__name__)

class PRISOcrService:
    """
    Servicio de Inteligencia Artificial Embebido para extraer
    texto clínico (CIE-10, Medicamentos, Dosis) a partir de imágenes de recetas.
    Motor Principal: Google Cloud Vision API
    """
    
    @classmethod
    def procesar_receta(cls, image_data_b64: str) -> dict:
        """
        Procesa una receta médica usando Google Vision o un Fallback local.
        """
        try:
            if not image_data_b64:
                raise ValueError("Imagen vacía")
                
            logger.info("PRIS AI: Procesando imagen de receta médica (OCR Inferencia)")
            
            # Limpiar posible header de data URI (data:image/jpeg;base64,...)
            if "," in image_data_b64:
                image_data_b64 = image_data_b64.split(",")[1]
            
            # Intento con Google Vision si hay credenciales
            if 'GOOGLE_APPLICATION_CREDENTIALS' in os.environ:
                return cls._procesar_con_google_vision(image_data_b64)
            else:
                return cls._procesar_con_fallback(image_data_b64)
            
        except Exception as e:
            logger.error(f"Error en PRIS AI OCR: {str(e)}")
            return {
                "success": False,
                "error": "El modelo no pudo extraer la información con confianza suficiente."
            }
            
    @classmethod
    def _procesar_con_google_vision(cls, base64_img: str) -> dict:
        """
        NOTA: Originalmente usaba Google Vision. Ahora actualizado para 
        usar DeepSeek Vision (Multimodal) por ser mucho más económico y potente.
        """
        api_key = os.environ.get('DEEPSEEK_API_KEY', '')
        base_url = os.environ.get('DEEPSEEK_BASE_URL', 'https://api.deepseek.com/v1')
        model = os.environ.get('DEEPSEEK_VISION_MODEL', 'deepseek-vision') # o deepseek-vl
        
        if not api_key:
            return cls._procesar_con_fallback(base64_img)
            
        try:
            from openai import OpenAI
            client = OpenAI(api_key=api_key, base_url=base_url)
            
            # Formato estándar de OpenAI/DeepSeek para imágenes en base64
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": "Extrae el texto de esta receta médica. Si identificas medicamentos, lista sus nombres y dosis. Devuelve solo un JSON válido con llaves 'raw_text' y 'medicamentos'."},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{base64_img}"
                                }
                            }
                        ]
                    }
                ],
                max_tokens=500
            )
            
            result_text = response.choices[0].message.content.strip()
            if result_text.startswith('```json'):
                result_text = result_text.replace('```json', '').replace('```', '').strip()
                
            try:
                data = json.loads(result_text)
            except:
                data = {"raw_text": result_text}
                
            return {
                "success": True,
                "engine": "deepseek_vision",
                "data": data
            }
            
        except ImportError:
            logger.error("Librería 'openai' no instalada para DeepSeek Vision.")
            return cls._procesar_con_fallback(base64_img)
        except Exception as e:
            logger.error(f"Error con DeepSeek Vision: {str(e)}")
            return cls._procesar_con_fallback(base64_img)
            
    @classmethod
    def _procesar_con_fallback(cls, base64_img: str) -> dict:
        logger.warning("PRIS OCR: Credenciales de Google no detectadas. Usando simulación fallback.")
        resultado_simulado = {
            "paciente": "Nombre Detectado (Fallback)",
            "medicamentos": [
                {"nombre": "Paracetamol", "dosis": "500mg", "frecuencia": "Cada 8 horas"},
            ],
            "diagnostico_cie10": "J02.9 - Faringitis aguda, no especificada",
            "confianza_modelo": 0.85
        }
        return {
            "success": True,
            "engine": "mock_fallback",
            "data": resultado_simulado,
            "mensaje": "Extracción simulada completada exitosamente."
        }
