"""Transporte REST unico para Gemini usado por PRIS y compatibilidad legacy."""

import json
import logging
import time
import urllib.error
import urllib.request

from django.conf import settings

logger = logging.getLogger('core')

_URL = 'https://generativelanguage.googleapis.com/v1/models/{model}:generateContent?key={key}'
_MODELS = ('gemini-2.0-flash', 'gemini-2.0-flash-lite', 'gemini-2.5-flash-lite')


def generate_gemini_content(prompt, api_key=None, image_b64='', temperature=0.4, max_tokens=1200):
    key = (api_key or getattr(settings, 'GOOGLE_API_KEY', '') or '').strip()
    if not key:
        raise ValueError('GOOGLE_API_KEY no configurada.')
    if len(image_b64 or '') > 12 * 1024 * 1024:
        raise ValueError('Imagen demasiado grande.')

    parts = [{'text': str(prompt or '')}]
    if image_b64:
        raw = image_b64.split(',', 1)[1] if ',' in image_b64 else image_b64
        mime_type = 'image/jpeg'
        if image_b64.startswith('data:'):
            mime_type = image_b64.split(';', 1)[0].split(':', 1)[1]
        parts.append({'inline_data': {'mime_type': mime_type, 'data': raw}})

    body = json.dumps({
        'contents': [{'role': 'user', 'parts': parts}],
        'generationConfig': {
            'temperature': max(0.0, min(float(temperature), 1.0)),
            'maxOutputTokens': max(1, min(int(max_tokens), 4096)),
        },
    }).encode('utf-8')

    last_error = None
    for model in _MODELS:
        for attempt in range(3):
            request = urllib.request.Request(
                _URL.format(model=model, key=key),
                data=body,
                headers={'Content-Type': 'application/json'},
                method='POST',
            )
            try:
                with urllib.request.urlopen(request, timeout=45) as response:
                    data = json.loads(response.read().decode('utf-8'))
                candidates = data.get('candidates') or []
                text = ''.join(
                    part.get('text', '')
                    for part in candidates[0].get('content', {}).get('parts', [])
                ) if candidates else ''
                if text.strip():
                    logger.info('Gemini REST OK - modelo: %s', model)
                    return text.strip()
                last_error = f'Gemini {model} no devolvio candidatos.'
                break
            except urllib.error.HTTPError as exc:
                details = exc.read().decode('utf-8', errors='ignore')[:200]
                if exc.code == 403:
                    raise PermissionError(
                        'Gemini devolvio 403/Forbidden; revise API, clave y modelo.'
                    ) from exc
                last_error = f'HTTP {exc.code}: {details}'
                if exc.code not in (429, 503) or attempt == 2:
                    break
                time.sleep(2 + attempt * 3)
            except (OSError, ValueError, TypeError) as exc:
                last_error = str(exc)
                break

    raise RuntimeError(last_error or 'Gemini no respondio con ningun modelo.')
