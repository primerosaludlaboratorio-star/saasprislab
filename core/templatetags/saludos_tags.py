"""
Template tags para saludos personalizados del Equipo de Élite.
"""
from django import template
from core.utils.saludos import obtener_saludo_personalizado

register = template.Library()


@register.simple_tag(takes_context=False)
def get_saludo_personalizado(usuario):
    """
    Template tag que retorna el saludo personalizado para un usuario.
    Uso: {% get_saludo_personalizado user as saludo_info %}
    """
    return obtener_saludo_personalizado(usuario)
