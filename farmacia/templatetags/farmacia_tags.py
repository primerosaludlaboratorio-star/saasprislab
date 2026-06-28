"""
Filtros y tags personalizados para el módulo de Farmacia.
"""
from django import template
from decimal import Decimal, InvalidOperation

register = template.Library()


@register.filter(name='mul')
def multiply(value, arg):
    """Multiplica value por arg. Usado para calcular valor de inventario en templates."""
    try:
        return Decimal(str(value)) * Decimal(str(arg))
    except (InvalidOperation, TypeError, ValueError):
        return 0


@register.filter(name='div')
def divide(value, arg):
    """Divide value entre arg."""
    try:
        divisor = Decimal(str(arg))
        if divisor == 0:
            return 0
        return Decimal(str(value)) / divisor
    except (InvalidOperation, TypeError, ValueError):
        return 0


@register.filter(name='subtract')
def subtract(value, arg):
    """Resta arg de value."""
    try:
        return Decimal(str(value)) - Decimal(str(arg))
    except (InvalidOperation, TypeError, ValueError):
        return 0


@register.filter(name='currency')
def currency(value):
    """Formatea un número como moneda MXN."""
    try:
        return f'${Decimal(str(value)):,.2f}'
    except (InvalidOperation, TypeError, ValueError):
        return '$0.00'


@register.simple_tag
def calcular_valor_lote(cantidad, costo):
    """Calcula el valor de un lote: cantidad × costo."""
    try:
        return Decimal(str(cantidad)) * Decimal(str(costo))
    except (InvalidOperation, TypeError, ValueError):
        return Decimal('0')
