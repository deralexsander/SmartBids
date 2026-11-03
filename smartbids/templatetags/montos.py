from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

from django import template

register = template.Library()


@register.filter
def miles_chilenos(value):
    if value in (None, ''):
        return ''
    try:
        monto = Decimal(str(value)).quantize(Decimal('1'), rounding=ROUND_HALF_UP)
    except (InvalidOperation, TypeError, ValueError):
        return value
    return f'{monto:,.0f}'.replace(',', '.')


@register.filter
def nombre_comuna(value):
    if not value:
        return ''
    from smartbids.utils.licitacion_utils import obtener_nombre_comuna
    return obtener_nombre_comuna(value)

