import os
import json
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

class PRISNLPEngine:
    """
    Motor de Procesamiento de Lenguaje Natural (NLP) para PRISLAB.
    Soporta múltiples backends. Principal: DeepSeek. Fallback: Local Regex.
    """
    
    def __init__(self):
        self.api_key = os.environ.get('DEEPSEEK_API_KEY', '')
        # DeepSeek usa formato compatible con OpenAI
        self.base_url = os.environ.get('DEEPSEEK_BASE_URL', 'https://api.deepseek.com/v1')
        self.model_name = os.environ.get('DEEPSEEK_MODEL', 'deepseek-chat')
        
        self.client = None
        if self.api_key:
            try:
                from openai import OpenAI
                self.client = OpenAI(
                    api_key=self.api_key,
                    base_url=self.base_url
                )
                logger.info(f"PRIS NLP: Motor LLM inicializado ({self.model_name})")
            except ImportError:
                logger.warning("PRIS NLP: Librería 'openai' no instalada. Usando fallback.")

    def analyze_command(self, text: str) -> Dict[str, Any]:
        """
        Analiza un comando de voz médico y extrae la intención y entidades.
        Retorna un diccionario con action, url y metadata.
        """
        if not text:
            return {"action": "error", "message": "Texto vacío"}
            
        logger.info(f"PRIS NLP Analizando: '{text}'")

        if self.client:
            return self._analyze_with_llm(text)
        else:
            return self._analyze_with_fallback(text)

    def _analyze_with_llm(self, text: str) -> Dict[str, Any]:
        """Usa el LLM (DeepSeek) para estructurar el comando."""
        prompt = f"""
Eres el asistente médico de IA del sistema PRISLAB. El usuario dijo: "{text}"
Analiza la intención del usuario y responde estrictamente con un objeto JSON (sin markdown) con esta estructura:
{{
    "intent": "search_patient" | "authorize_result" | "open_pharmacy" | "unknown",
    "entities": {{"nombre": "...", "id": "..."}},
    "suggested_action": {{
        "type": "redirect" | "api_call" | "message",
        "url_path": "/ruta/sugerida/",
        "message": "Mensaje de respuesta"
    }}
}}
Ejemplos de intenciones:
- "busca a juan perez" -> intent: search_patient, entities: {{"nombre": "juan perez"}}, url_path: "/pacientes/buscar/?q=juan+perez"
- "abre la farmacia" -> intent: open_pharmacy, url_path: "/farmacia/"
"""
        try:
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                max_tokens=150
            )
            
            result_text = response.choices[0].message.content.strip()
            # Limpiar posible formato markdown de json
            if result_text.startswith('```json'):
                result_text = result_text.replace('```json', '').replace('```', '').strip()
                
            data = json.loads(result_text)
            return {
                "success": True,
                "engine": "deepseek",
                "data": data
            }
        except Exception as e:
            logger.error(f"Error en LLM PRIS NLP: {str(e)}")
            return self._analyze_with_fallback(text)

    def _analyze_with_fallback(self, text: str) -> Dict[str, Any]:
        """Fallback local con regex o palabras clave en caso de no tener API Key o fallar LLM."""
        logger.info("PRIS NLP: Usando Regex Fallback.")
        t = text.lower()
        
        data = {
            "intent": "unknown",
            "entities": {},
            "suggested_action": {
                "type": "message",
                "url_path": "",
                "message": "Comando no reconocido por el sistema local."
            }
        }

        if "busca" in t or "paciente" in t:
            # Extracción muy básica
            nombre = t.replace("busca a", "").replace("busca al paciente", "").strip()
            data["intent"] = "search_patient"
            data["entities"] = {"nombre": nombre}
            data["suggested_action"] = {
                "type": "redirect",
                "url_path": f"/pacientes/?q={nombre}",
                "message": f"Buscando al paciente {nombre}"
            }
        elif "farmacia" in t:
            data["intent"] = "open_pharmacy"
            data["suggested_action"] = {
                "type": "redirect",
                "url_path": "/farmacia/",
                "message": "Abriendo módulo de farmacia"
            }
            
        return {
            "success": True,
            "engine": "local_fallback",
            "data": data
        }

nlp_engine = PRISNLPEngine()
