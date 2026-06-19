from __future__ import annotations

import hashlib
import json
import os
import time
from pathlib import Path
from urllib import error, request


def _env(name: str, default: str = "") -> str:
    return os.environ.get(name, default).strip()


LIBRARY_ID = _env("BUNNY_LIBRARY_ID")
STREAM_API_KEY = _env("BUNNY_STREAM_API_KEY")
EMBED_SECURITY_KEY = _env("BUNNY_EMBED_SECURITY_KEY")

PLAYER_BASE_URL_NUEVO = _env("BUNNY_PLAYER_BASE_URL", "https://player.mediadelivery.net/embed")
PLAYER_BASE_URL_LEGACY = "https://iframe.mediadelivery.net/embed"
PLAYER_BASE_URL = PLAYER_BASE_URL_NUEVO or PLAYER_BASE_URL_LEGACY

STREAM_API_BASE = f"https://video.bunnycdn.com/library/{LIBRARY_ID}/videos" if LIBRARY_ID else ""


def _ensure_config() -> None:
    missing = [
        name for name, value in [
            ("BUNNY_LIBRARY_ID", LIBRARY_ID),
            ("BUNNY_STREAM_API_KEY", STREAM_API_KEY),
            ("BUNNY_EMBED_SECURITY_KEY", EMBED_SECURITY_KEY),
        ]
        if not value
    ]
    if missing:
        raise RuntimeError(f"Faltan variables de entorno para Bunny Stream: {', '.join(missing)}")


def generar_token_embed(bunny_video_id: str, ttl_segundos: int = 4 * 3600) -> tuple[str, int, str]:
    _ensure_config()
    expires = int(time.time()) + ttl_segundos
    hashable = f"{EMBED_SECURITY_KEY}{bunny_video_id}{expires}"
    token = hashlib.sha256(hashable.encode("utf-8")).hexdigest()
    embed_url = f"{PLAYER_BASE_URL}/{LIBRARY_ID}/{bunny_video_id}?token={token}&expires={expires}"
    return token, expires, embed_url


def _json_request(url: str, method: str, payload: dict | None = None) -> dict:
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    req = request.Request(url, data=data, method=method)
    req.add_header("AccessKey", STREAM_API_KEY)
    req.add_header("accept", "application/json")
    if payload is not None:
        req.add_header("Content-Type", "application/json")
    try:
        with request.urlopen(req, timeout=60) as resp:
            body = resp.read().decode("utf-8") or "{}"
            return json.loads(body)
    except error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="ignore")
        raise RuntimeError(f"Bunny Stream HTTP {exc.code}: {body}") from exc


def crear_video(titulo: str) -> str:
    _ensure_config()
    data = _json_request(STREAM_API_BASE, "POST", {"title": titulo})
    guid = data.get("guid") or data.get("videoGuid") or data.get("id")
    if not guid:
        raise RuntimeError(f"Bunny no devolvio GUID al crear video: {data}")
    return str(guid)


def subir_archivo_video(bunny_video_id: str, ruta_archivo: str | Path) -> None:
    _ensure_config()
    ruta = Path(ruta_archivo)
    req = request.Request(f"{STREAM_API_BASE}/{bunny_video_id}", method="PUT")
    req.add_header("AccessKey", STREAM_API_KEY)
    req.add_header("Content-Type", "application/octet-stream")
    with ruta.open("rb") as fh:
        data = fh.read()
    try:
        with request.urlopen(req, data=data, timeout=600) as resp:
            resp.read()
    except error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="ignore")
        raise RuntimeError(f"Bunny Stream HTTP {exc.code}: {body}") from exc
