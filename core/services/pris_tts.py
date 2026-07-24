"""Síntesis de voz neural opcional para PRIS.

La credencial se obtiene desde el entorno del servidor. Nunca se envía al
navegador ni se guarda el audio generado.
"""

import logging
import os

import requests
from google.auth import default
from google.auth.transport.requests import Request

logger = logging.getLogger("pris.tts")

TTS_ENDPOINT = "https://texttospeech.googleapis.com/v1/text:synthesize"
MAX_TEXT_LENGTH = 4000


def synthesize_pris_voice(text):
    """Devuelve MP3 para PRIS o ``None`` si debe usarse el fallback local."""
    if not text or os.environ.get("PRIS_TTS_ENABLED", "true").lower() in {"0", "false", "no"}:
        return None

    credentials_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS", "").strip()
    if not credentials_path:
        logger.info("PRIS TTS omitido: falta GOOGLE_APPLICATION_CREDENTIALS")
        return None

    try:
        credentials, project_id = default(
            scopes=["https://www.googleapis.com/auth/cloud-platform"]
        )
        credentials.refresh(Request())
        payload = {
            "input": {"text": text[:MAX_TEXT_LENGTH]},
            "voice": {
                # Google ofrece la voz neural latinoamericana bajo es-US.
                "languageCode": os.environ.get("PRIS_TTS_LANGUAGE", "es-US"),
                "name": os.environ.get("PRIS_TTS_VOICE", "es-US-Neural2-A"),
                "ssmlGender": "FEMALE",
            },
            "audioConfig": {
                "audioEncoding": "MP3",
                "speakingRate": 0.93,
                "pitch": 1.0,
                "volumeGainDb": 0.0,
            },
        }
        response = requests.post(
            TTS_ENDPOINT,
            headers={"Authorization": f"Bearer {credentials.token}"},
            json=payload,
            timeout=20,
        )
        response.raise_for_status()
        audio_content = response.json().get("audioContent")
        if not audio_content:
            logger.warning("PRIS TTS no devolvio audio; proyecto=%s", project_id or "unknown")
            return None

        import base64

        return base64.b64decode(audio_content)
    except Exception:
        logger.warning("PRIS TTS no disponible; se usara voz local", exc_info=True)
        return None
