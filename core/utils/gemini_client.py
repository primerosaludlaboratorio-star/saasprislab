"""
Cliente centralizado de Google Gemini API.
ACTUALIZADO Feb-2026: Migrado a google.genai (SDK unificado v1.60+).
El paquete `google.generativeai` fue deprecado; este módulo usa google.genai.

API principal:
    client = get_gemini_client()          → google.genai.Client
    response = client.models.generate_content(model='gemini-2.0-flash', contents='...')
    response.text  → texto de respuesta

Modo supervivencia: test_gemini_connection() usa timeout 15s. Los llamadores
DEBEN envolver en try/except y mostrar mensajes amigables.
"""
import logging
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
from django.conf import settings

logger = logging.getLogger('core')
GEMINI_TEST_TIMEOUT_SEC = 15
_MODELOS_FALLBACK = ['gemini-2.0-flash', 'gemini-2.0-flash-lite', 'gemini-1.5-flash']
_MIGRATION_MAP = {
    'gemini-1.5-flash': 'gemini-2.0-flash',
    'gemini-1.5-flash-latest': 'gemini-2.0-flash',
    'gemini-1.5-pro': 'gemini-2.0-flash',
    'gemini-1.5-pro-latest': 'gemini-2.0-flash',
}


def _get_api_key() -> str:
    """Obtiene y limpia la GOOGLE_API_KEY del entorno."""
    key = (
        getattr(settings, 'GOOGLE_API_KEY', '') or
        getattr(settings, 'GOOGLE_GEMINI_API_KEY', '') or
        getattr(settings, 'GEMINI_API_KEY', '')
    )
    return key.strip().replace('\r', '').replace('\n', '') if key else ''


def get_gemini_client():
    """
    Retorna un cliente `google.genai.Client` configurado.

    Uso:
        client = get_gemini_client()
        resp = client.models.generate_content(model='gemini-2.0-flash', contents='Hola')
        print(resp.text)
    """
    api_key = _get_api_key()
    if not api_key:
        raise ValueError(
            "GOOGLE_API_KEY no está configurada. "
            "Defínala en .env o como variable de entorno en Cloud Run."
        )
    try:
        from google import genai
        client = genai.Client(api_key=api_key)
        return client
    except ImportError:
        raise ImportError(
            "google-genai no está instalado. Ejecute: pip install google-genai"
        )


def get_gemini_model(model_name: str = 'gemini-2.0-flash') -> str:
    """
    Normaliza el nombre del modelo (migra nombres deprecados).
    Retorna el nombre del modelo normalizado (str) para usar en
    client.models.generate_content(model=..., ...).
    No requiere API key; la validación ocurre en get_gemini_client().
    """
    model_name = _MIGRATION_MAP.get(model_name, model_name)
    if model_name in _MIGRATION_MAP.values() or model_name in _MODELOS_FALLBACK:
        return model_name
    logger.warning("Modelo Gemini desconocido '%s', usando fallback 'gemini-2.0-flash'", model_name)
    return 'gemini-2.0-flash'


def generate_content(prompt: str, model_name: str = 'gemini-2.0-flash',
                     temperature: float = 0.2, max_tokens: int = 2048) -> str:
    """
    Atajo de alto nivel: genera contenido con Gemini y retorna el texto.

    Params:
        prompt      — Texto del prompt
        model_name  — Nombre del modelo (se normaliza automáticamente)
        temperature — Control de creatividad (0.0 - 1.0)
        max_tokens  — Máximo de tokens en la respuesta

    Returns:
        str — Texto de la respuesta

    Raises:
        Exception si la API falla o no está configurada
    """
    client = get_gemini_client()
    model = get_gemini_model(model_name)

    from google.genai import types
    config = types.GenerateContentConfig(
        temperature=temperature,
        max_output_tokens=max_tokens,
    )

    for intento_model in [model, *[m for m in _MODELOS_FALLBACK if m != model]]:
        try:
            response = client.models.generate_content(
                model=intento_model,
                contents=prompt,
                config=config,
            )
            logger.info("Gemini respuesta OK — modelo: %s", intento_model)
            return response.text or ""
        except Exception as e:
            logger.warning("Gemini fallo con %s: %s — reintentando con siguiente", intento_model, e)

    raise Exception(f"Gemini no respondió con ningún modelo. Último intento: {intento_model}")


def _test_gemini_connection_impl() -> dict:
    """Implementación interna de test de conexión (sin timeout propio)."""
    try:
        texto = generate_content("Responde solo con: OK", max_tokens=10)
        return {
            'success': bool(texto),
            'message': 'Conexión exitosa con Gemini API',
            'model': 'gemini-2.0-flash',
            'response': texto.strip(),
        }
    except Exception as e:
        return {
            'success': False,
            'message': str(e),
            'model': 'gemini-2.0-flash',
        }


def test_gemini_connection() -> dict:
    """
    Test de vida: verifica que la conexión con Gemini funcione.
    Usa timeout de 15s para no colgar si la API está caída.

    Returns:
        dict: {'success': bool, 'message': str, 'model': str}
    """
    try:
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(_test_gemini_connection_impl)
            try:
                return future.result(timeout=GEMINI_TEST_TIMEOUT_SEC)
            except FuturesTimeoutError:
                logger.warning("Gemini: test agotó tiempo (%ss)", GEMINI_TEST_TIMEOUT_SEC)
                return {
                    'success': False,
                    'message': f'Gemini no respondió en {GEMINI_TEST_TIMEOUT_SEC}s.',
                    'model': 'gemini-2.0-flash',
                }
    except Exception as e:
        logger.exception("Gemini: error en test de conexión")
        return {'success': False, 'message': str(e), 'model': 'gemini-2.0-flash'}
