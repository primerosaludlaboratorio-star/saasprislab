"""Sanitization for tenant-controlled CSS rendered in the application shell."""

from __future__ import annotations

import re


_STYLE_TAG_RE = re.compile(r"</?style\b[^>]*>", re.IGNORECASE)
_HTML_TAG_RE = re.compile(r"<[^>]*>")
_IMPORT_RE = re.compile(r"@import\b[^;{}]*(?:;|$)", re.IGNORECASE)
_EXPRESSION_RE = re.compile(r"expression\s*\([^)]*\)", re.IGNORECASE)
_DANGEROUS_URL_RE = re.compile(
    r"url\(\s*(['\"]?)\s*(?:javascript|vbscript|data):.*?\1\s*\)",
    re.IGNORECASE,
)


def sanitize_tenant_css(value: object, *, max_length: int = 20_000) -> str:
    """Return CSS safe to place inside an existing ``<style>`` element.

    Tenant CSS is intentionally supported, but it must not be able to escape
    the style element or load executable/resource schemes from user input.
    """
    css = str(value or "")[:max_length]
    css = _STYLE_TAG_RE.sub("", css)
    css = _HTML_TAG_RE.sub("", css)
    css = _IMPORT_RE.sub("", css)
    css = _EXPRESSION_RE.sub("", css)
    return _DANGEROUS_URL_RE.sub("url()", css)
