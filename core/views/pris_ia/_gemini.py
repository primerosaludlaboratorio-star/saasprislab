"""Compatibilidad para el transporte centralizado de Gemini."""


def _gemini_rest_call(api_key: str, prompt_text: str, imagen_b64: str = '',
                      temperatura: float = 0.4, max_tokens: int = 1200) -> str:
    from core.utils.gemini_transport import generate_gemini_content

    return generate_gemini_content(
        prompt_text,
        api_key=api_key,
        image_b64=imagen_b64,
        temperature=temperatura,
        max_tokens=max_tokens,
    )
