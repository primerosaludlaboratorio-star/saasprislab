"""
PRISLAB V5 — Filtros matemáticos para templates.
Proporciona operaciones aritméticas básicas que Django no incluye de forma nativa.

Uso en templates:
    {% load math_filters %}
    {{ valor|sub:descuento }}          → valor - descuento
    {{ precio|mul:cantidad }}          → precio * cantidad
    {{ total|div:30 }}                 → total / 30
    {{ diferencia|abs }}               → valor absoluto
    {{ valor|multiply:factor }}        → alias de mul (compatibilidad)
    {{ pct|pct_of:total }}             → (pct / total) * 100
"""
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from django import template

register = template.Library()


def _to_decimal(value) -> Decimal:
    """Convierte un valor a Decimal de forma segura."""
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return Decimal('0')


@register.filter(name='sub')
def sub(value, arg):
    """Resta: {{ value|sub:arg }} → value - arg"""
    return _to_decimal(value) - _to_decimal(arg)


@register.filter(name='mul')
def mul(value, arg):
    """Multiplica: {{ value|mul:arg }} → value * arg"""
    return _to_decimal(value) * _to_decimal(arg)


@register.filter(name='multiply')
def multiply(value, arg):
    """Alias de mul para compatibilidad: {{ value|multiply:arg }}"""
    return _to_decimal(value) * _to_decimal(arg)


@register.filter(name='div')
def div(value, arg):
    """Divide: {{ value|div:arg }} → value / arg (retorna 0 si arg == 0)"""
    divisor = _to_decimal(arg)
    if divisor == 0:
        return Decimal('0')
    return (_to_decimal(value) / divisor).quantize(Decimal('0.0001'), rounding=ROUND_HALF_UP)


@register.filter(name='abs')
def absolute(value):
    """Valor absoluto: {{ value|abs }}"""
    try:
        return abs(_to_decimal(value))
    except Exception:
        return value


@register.filter(name='pct_of')
def pct_of(value, total):
    """Porcentaje: {{ value|pct_of:total }} → (value / total) * 100"""
    t = _to_decimal(total)
    if t == 0:
        return Decimal('0')
    return (_to_decimal(value) / t * 100).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)


@register.filter(name='floatformat_es')
def floatformat_es(value, decimals=2):
    """Formatea número con separador de miles en español: 1,234.56"""
    try:
        d = _to_decimal(value)
        fmt = f'{{:,.{int(decimals)}f}}'
        return fmt.format(float(d))
    except Exception:
        return value
