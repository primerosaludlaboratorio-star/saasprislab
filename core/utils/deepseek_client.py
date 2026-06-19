"""Cliente DeepSeek compatible con los flujos de texto de PRISLAB."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

import requests
from django.conf import settings

logger = logging.getLogger("core")


@dataclass
class DeepSeekResponse:
    text: str


def _get_api_key() -> str:
    key = getattr(settings, "DEEPSEEK_API_KEY", "") or ""
    return key.strip().replace("\r", "").replace("\n", "")


def _get_api_url() -> str:
    return (
        getattr(settings, "DEEPSEEK_API_URL", "")
        or "https://api.deepseek.com/v1/chat/completions"
    ).strip()


def _normalizar_prompt(contents: Any) -> str:
    if isinstance(contents, str):
        return contents
    if isinstance(contents, (list, tuple)):
        partes: list[str] = []
        for item in contents:
            if isinstance(item, str):
                partes.append(item)
            elif isinstance(item, dict):
                partes.append(str(item.get("text") or item.get("content") or ""))
        return "\n".join(p for p in partes if p).strip()
    return str(contents or "")


def generate_content(
    prompt: str,
    model_name: str | None = None,
    temperature: float = 0.2,
    max_tokens: int = 2048,
    timeout: int = 30,
) -> str:
    """Genera texto con DeepSeek y retorna solo el contenido."""
    api_key = _get_api_key()
    if not api_key:
        raise ValueError("DEEPSEEK_API_KEY no configurada.")

    model = model_name or getattr(settings, "DEEPSEEK_MODEL", "deepseek-chat")
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    response = requests.post(
        _get_api_url(),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json=payload,
        timeout=timeout,
    )
    response.raise_for_status()
    data = response.json()
    try:
        return (data["choices"][0]["message"]["content"] or "").strip()
    except (KeyError, IndexError, TypeError) as exc:
        logger.warning("DeepSeek: respuesta inesperada: %s", data)
        raise ValueError("Respuesta inesperada de DeepSeek.") from exc


class _DeepSeekModels:
    def generate_content(
        self,
        model: str | None = None,
        contents: Any = "",
        config: dict[str, Any] | None = None,
        generation_config: Any | None = None,
        request_options: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> DeepSeekResponse:
        cfg = config if isinstance(config, dict) else {}
        if generation_config is not None:
            cfg = {
                **cfg,
                "temperature": getattr(generation_config, "temperature", None),
                "max_output_tokens": getattr(generation_config, "max_output_tokens", None),
            }
        timeout = int((request_options or {}).get("timeout") or kwargs.get("timeout") or 30)
        text = generate_content(
            _normalizar_prompt(contents),
            model_name=model,
            temperature=cfg.get("temperature") if cfg.get("temperature") is not None else 0.2,
            max_tokens=cfg.get("max_output_tokens") or cfg.get("max_tokens") or 2048,
            timeout=timeout,
        )
        return DeepSeekResponse(text=text)


class DeepSeekClient:
    """Adaptador minimo para codigo que usa client.models.generate_content(...)."""

    def __init__(self) -> None:
        self.models = _DeepSeekModels()


def get_deepseek_client() -> DeepSeekClient:
    return DeepSeekClient()


def test_deepseek_connection() -> dict:
    try:
        text = generate_content("Responde solo con: OK", max_tokens=10, timeout=15)
        return {
            "success": bool(text),
            "message": "Conexion exitosa con DeepSeek",
            "model": getattr(settings, "DEEPSEEK_MODEL", "deepseek-chat"),
            "response": text,
        }
    except Exception as exc:
        return {
            "success": False,
            "message": str(exc),
            "model": getattr(settings, "DEEPSEEK_MODEL", "deepseek-chat"),
        }
