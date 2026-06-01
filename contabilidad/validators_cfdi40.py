"""
Validaciones y saneamiento alineados con receptor CFDI 4.0 (SAT México).
Fase Hito 16 — no sustituyen validación del PAC; reducen rechazos por formato.
"""
from __future__ import annotations

import re

from django.core.exceptions import ValidationError

# Persona moral 12: 3 letras + 6 dígitos fecha + homoclave 3
# Persona física 13: 4 letras + 6 dígitos + homoclave 3
# & y Ñ permitidos en prefijo según nomenclatura SAT.
RFC_SAT40_RE = re.compile(r'^[A-ZÑ&]{3,4}\d{6}[A-Z0-9]{3}$')

# Sufijos societarios prohibidos en Nombre del receptor (CFDI 4.0) — se eliminan al final.
_NOMBRE_FISCAL_SUFFIX_PATTERNS = (
    r'\s+S\.?\s*A\.?\s*P\.?\s*I\.?\s+DE\s+C\.?\s*V\.?\s*$',
    r'\s+S\.?\s*A\.?\s+DE\s+C\.?\s*V\.?\s*$',
    r'\s+S\.?\s*D\.?\s*E\s+R\.?\s*L\.?\s+DE\s+C\.?\s*V\.?\s*$',
    r'\s+S\.?\s*D\.?\s*E\s+R\.?\s*L\.?\s*$',
    r'\s+S\.?\s*C\.?\s*$',
    r'\s+A\.?\s*C\.?\s*$',
    r'\s+I\.?\s*A\.?\s*P\.?\s*$',
)


def validate_rfc_sat40(value: str) -> None:
    """RFC 12 o 13 caracteres con estructura SAT (no valida dígito verificador). Debe ir en MAYÚSCULAS."""
    if value is None or not str(value).strip():
        raise ValidationError('RFC obligatorio.', code='rfc_vacio')
    v = str(value).strip()
    if not RFC_SAT40_RE.fullmatch(v):
        raise ValidationError(
            'RFC inválido: use formato SAT (moral 12 o física 13 caracteres: letras/Ñ/&, '
            'fecha yymmdd, homoclave).',
            code='rfc_invalido',
        )


def validate_codigo_postal_sat40(value: str) -> None:
    """Código postal mexicano: exactamente 5 dígitos."""
    if value is None:
        raise ValidationError('Código postal obligatorio.', code='cp_vacio')
    v = str(value).strip()
    if not re.fullmatch(r'\d{5}', v):
        raise ValidationError(
            'Código postal debe ser exactamente 5 dígitos numéricos.',
            code='cp_invalido',
        )


def clean_nombre_fiscal(raw: str) -> str:
    """
    MAYÚSCULAS, espacios simples, sin sufijos societarios al final (requisito nombre receptor 4.0).
    """
    if raw is None:
        return ''
    s = ' '.join(str(raw).split()).strip()
    if not s:
        return ''
    s = s.upper()
    prev = None
    while prev != s:
        prev = s
        for pat in _NOMBRE_FISCAL_SUFFIX_PATTERNS:
            s = re.sub(pat, '', s, flags=re.IGNORECASE)
        s = ' '.join(s.split()).strip()
    return s
