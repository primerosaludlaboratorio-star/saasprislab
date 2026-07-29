"""Reglas únicas para excluir catálogo veterinario del sistema humano."""

import re
import unicodedata


VETERINARY_MARKERS = (
    'CANIN',
    ' CAN',
    'CAN ',
    'CAN-',
    'CAN_',
    'GLUCAN',
    'FELIN',
    'EQUIN',
    'VETERIN',
    'VET-',
)


def normalize_catalog_text(value) -> str:
    """Normaliza texto para comparar catálogos sin depender de acentos."""
    text = unicodedata.normalize('NFKD', str(value or ''))
    text = ''.join(char for char in text if not unicodedata.combining(char))
    return re.sub(r'\s+', ' ', text).strip().upper()


def is_veterinary_catalog_text(*values) -> bool:
    """Indica si alguno de los identificadores del registro es veterinario."""
    haystack = ' | '.join(normalize_catalog_text(value) for value in values if value)
    return any(marker in haystack for marker in VETERINARY_MARKERS)
