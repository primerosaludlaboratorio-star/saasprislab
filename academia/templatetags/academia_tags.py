from __future__ import annotations

from django import template

from academia.services.access import academia_habilitada_para_empresa

register = template.Library()


@register.filter
def academia_activa_para_empresa(empresa) -> bool:
    return academia_habilitada_para_empresa(empresa)

