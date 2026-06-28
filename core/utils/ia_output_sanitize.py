"""
Filtro de salida IA / voz: reduce fuga de PII y menciones de otros tenants.
No sustituye controles de acceso en herramientas; es capa adicional en la respuesta al usuario.
"""
from __future__ import annotations

import re
from typing import Optional, Tuple

# CURP (patrón típico 18 caracteres)
_CURP_RE = re.compile(
    r'\b[A-Z]{4}\d{6}[HM][A-Z]{5}[A-Z0-9]\d\b',
    re.IGNORECASE,
)
# RFC persona moral 12 / física 13
_RFC_RE = re.compile(
    r'\b([A-ZÑ&]{3,4}\d{6}[A-Z0-9]{3})\b',
    re.IGNORECASE,
)
_EMAIL_RE = re.compile(r'\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b', re.IGNORECASE)
# Teléfonos MX 10 dígitos (con o sin +52 / espacios)
_PHONE_RE = re.compile(
    r'(?:\+?\s*52\s*)?(\d{3}[\s.-]?\d{3}[\s.-]?\d{4})\b',
)
_EMPRESA_ID_RE = re.compile(
    r'empresa[_\s]*id\s*[:=]\s*(\d+)',
    re.IGNORECASE,
)


def sanitizar_salida_ia(
    texto: str,
    empresa_id: Optional[int] = None,
    mensaje_sustituto: str = (
        'Por políticas de privacidad y multi-tenant no puedo incluir esos datos en la respuesta. '
        'Reformula la consulta sin datos personales identificables.'
    ),
) -> Tuple[str, bool]:
    """
    Retorna (texto, ok). Si ok es False, la respuesta fue sustituida por bloqueo.
    """
    if not texto or not str(texto).strip():
        return texto, True

    t = str(texto)
    if _CURP_RE.search(t) or _EMAIL_RE.search(t):
        return mensaje_sustituto, False
    if _RFC_RE.search(t) and len(_RFC_RE.findall(t)) > 0:
        # Evitar falsos positivos muy cortos: longitud RFC ya acotada en regex
        return mensaje_sustituto, False
    for m in _PHONE_RE.finditer(t):
        digits = re.sub(r'\D', '', m.group(1) or '')
        if len(digits) >= 10:
            return mensaje_sustituto, False

    if empresa_id is not None:
        for m in _EMPRESA_ID_RE.finditer(t):
            try:
                if int(m.group(1)) != int(empresa_id):
                    return mensaje_sustituto, False
            except (TypeError, ValueError):
                continue

    return t, True
