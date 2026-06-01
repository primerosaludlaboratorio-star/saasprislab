"""
Salida centralizada a Telegram (Punto 23 — Sandbox).
En `IS_SANDBOX` no se realiza HTTP; solo log [SANDBOX SUPPRESSED].
"""
from __future__ import annotations

import logging

import requests
from django.conf import settings

logger = logging.getLogger(__name__)


def send_telegram_message(
    token: str | None,
    chat_id: str | int | None,
    text: str,
    *,
    parse_mode: str | None = None,
    timeout: float = 5.0,
) -> bool:
    """
    Envía un mensaje a Telegram. En modo training_sandbox simula éxito y registra log.

    Returns:
        True si se envió correctamente o se suprimió en sandbox.
        False si faltan credenciales o falló la petición real.
    """
    if not token or chat_id is None or chat_id == '':
        return False

    chat_display = str(chat_id)
    if getattr(settings, 'IS_SANDBOX', False):
        logger.warning(
            '[SANDBOX SUPPRESSED] Telegram a Chat ID %s: %s',
            chat_display,
            text,
        )
        return True

    payload: dict = {'chat_id': chat_id, 'text': text}
    if parse_mode:
        payload['parse_mode'] = parse_mode

    try:
        r = requests.post(
            f'https://api.telegram.org/bot{token}/sendMessage',
            json=payload,
            timeout=timeout,
        )
        return bool(r.ok)
    except Exception as exc:
        logger.debug('Telegram sendMessage falló: %s', exc)
        return False
