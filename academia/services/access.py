from __future__ import annotations

from django.conf import settings
from django.utils.text import slugify


def _normalizar(valor) -> str:
    return slugify(str(valor or "").strip()).lower()


def academia_habilitada_para_empresa(empresa) -> bool:
    """
    Determina si la academia está habilitada para la empresa actual.

    Reglas:
    - Superusuario: siempre permitido.
    - Por defecto: solo PRISLAB.
    - Se puede ampliar con ACADEMIA_EMPRESAS_PERMITIDAS en el entorno.
      Acepta nombre, slug o ID de empresa.
    """
    if not empresa:
        return False

    if getattr(empresa, "id", None) and str(empresa.id) in {str(x).strip() for x in getattr(settings, "ACADEMIA_EMPRESAS_PERMITIDAS", [])}:
        return True

    permitido = {_normalizar(x) for x in getattr(settings, "ACADEMIA_EMPRESAS_PERMITIDAS", ["prislab"])}
    empresa_norm = _normalizar(getattr(empresa, "nombre", ""))
    return empresa_norm in permitido

