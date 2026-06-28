"""
core/views/pris_ia/_gemini.py

Cliente REST directo para la API de Gemini v1.
Sin dependencia del SDK de Google para máximo control del endpoint.
"""

import json
import logging
import time
import urllib.request
import urllib.error

logger = logging.getLogger('core')


_GEMINI_REST_URL = "https://generativelanguage.googleapis.com/v1/models/{model}:generateContent?key={key}"
_DEFAULT_GEMINI_MODEL = "gemini-2.0-flash"
_FALLBACK_MODELS = ["gemini-2.0-flash", "gemini-2.0-flash-lite", "gemini-2.5-flash-lite"]


def _gemini_rest_call(api_key: str, prompt_text: str, imagen_b64: str = "",
                      temperatura: float = 0.4, max_tokens: int = 1200) -> str:
    """
    Llama al REST API de Gemini v1 directamente.
    Soporta texto y una imagen opcional en base64.
    Retorna el texto de la respuesta.
    """
    if not imagen_b64:
        try:
            from core.utils.gemini_client import generate_content
            return generate_content(
                prompt_text,
                model_name=_DEFAULT_GEMINI_MODEL,
                temperature=temperatura,
                max_tokens=max_tokens,
            ).strip()
        except (ImportError, OSError, ConnectionError, RuntimeError) as provider_error:
            logger.warning("PRIS proveedor IA texto no disponible, intentando REST Gemini: %s", provider_error)

    parts = [{"text": prompt_text}]

    if imagen_b64:
        try:
            raw = imagen_b64.split(',', 1)[1] if ',' in imagen_b64 else imagen_b64
            # Detectar mime_type del header de data URI
            mime_type = "image/jpeg"
            if imagen_b64.startswith("data:"):
                mime_type = imagen_b64.split(';')[0].split(':')[1]
            parts.append({
                "inline_data": {
                    "mime_type": mime_type,
                    "data": raw,
                }
            })
        except (ValueError, AttributeError) as img_err:
            logger.warning(f"PRIS: imagen inválida, se omite: {img_err}")

    payload = {
        "contents": [{"role": "user", "parts": parts}],
        "generationConfig": {
            "temperature": temperatura,
            "maxOutputTokens": max_tokens,
        },
    }
    body = json.dumps(payload).encode("utf-8")

    last_error = None
    for model in _FALLBACK_MODELS:
        url = _GEMINI_REST_URL.format(model=model, key=api_key)
        req = urllib.request.Request(
            url, data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        # Reintentos con backoff para 429/503 (rate limit / sobrecarga)
        for intento in range(3):
            try:
                with urllib.request.urlopen(req, timeout=45) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                candidates = data.get("candidates", [])
                if candidates:
                    parts_resp = candidates[0].get("content", {}).get("parts", [])
                    text = "".join(p.get("text", "") for p in parts_resp)
                    logger.info(f"PRIS Gemini REST OK — modelo: {model}")
                    return text.strip()
                logger.warning(f"PRIS Gemini '{model}': sin candidatos")
                break
            except urllib.error.HTTPError as e:
                err_body = e.read().decode("utf-8", errors="ignore")
                logger.warning(f"PRIS Gemini '{model}' HTTP {e.code} intento {intento+1}: {err_body[:200]}")
                if e.code == 403:
                    raise PermissionError(
                        "Gemini REST devolvió 403/Forbidden. "
                        "Verifica que la API key esté autorizada para generativelanguage.googleapis.com "
                        "y que el modelo solicitado esté habilitado."
                    ) from e
                if e.code in (429, 503) and intento < 2:
                    # Espera escalonada: 2s, 5s
                    time.sleep(2 + intento * 3)
                    continue
                last_error = f"HTTP {e.code}: {err_body[:150]}"
                break
            except (OSError, ConnectionError, ValueError) as e:
                logger.warning(f"PRIS Gemini '{model}' error: {e}")
                last_error = str(e)
                break

    raise Exception(last_error or "Gemini no respondió con ningún modelo.")
