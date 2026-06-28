"""
Tokens firmados para enlaces de tracking (paciente / prospecto + empresa).
Django signing — sin almacenar secretos en el cliente más allá del token opaco.
"""
from __future__ import annotations

from django.core import signing

TRACKING_SALT = "pris.marketing.tracking.v1"
_DEFAULT_MAX_AGE = 60 * 60 * 24 * 90  # 90 días


def sign_paciente_track(*, empresa_id: int, paciente_id: int) -> str:
    signer = signing.TimestampSigner(salt=TRACKING_SALT)
    return signer.sign_object(
        {"e": int(empresa_id), "p": int(paciente_id)},
        compress=True,
    )


def sign_prospecto_track(*, empresa_id: int, prospecto_id: int) -> str:
    signer = signing.TimestampSigner(salt=TRACKING_SALT)
    return signer.sign_object(
        {"e": int(empresa_id), "pr": int(prospecto_id)},
        compress=True,
    )


def sign_track_token(payload: dict) -> str:
    """
    Firma un dict con claves ``e`` (empresa), ``p`` (paciente) y/o ``pr`` (prospecto),
    mismo formato que espera ``unsign_track_token`` / ``track_pixel_204``.
    """
    if not payload:
        return ""
    obj: dict = {}
    for key in ("e", "p", "pr"):
        if key not in payload or payload[key] is None:
            continue
        try:
            obj[key] = int(payload[key])
        except (TypeError, ValueError):
            continue
    if not obj:
        return ""
    signer = signing.TimestampSigner(salt=TRACKING_SALT)
    return signer.sign_object(obj, compress=True)


def unsign_track_token(token: str, *, max_age: int = _DEFAULT_MAX_AGE) -> dict | None:
    if not token or not str(token).strip():
        return None
    signer = signing.TimestampSigner(salt=TRACKING_SALT)
    try:
        return signer.unsign_object(str(token).strip(), max_age=max_age)
    except (signing.BadSignature, signing.SignatureExpired):
        return None
