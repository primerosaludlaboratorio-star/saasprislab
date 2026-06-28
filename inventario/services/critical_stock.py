"""
Agregación de stock por catálogo para alertas de mínimo (cron / War Room).

Usa `cantidad_actual` en lotes (no existe `cantidad_disponible` en modelos).
Laboratorio: solo lotes ACTIVO (alineado con FEFO en `inventario.signals`).
Consultorio / Generales: lotes con cantidad_actual > 0.
"""
from django.db.models import DecimalField, F, Q, Sum, Value
from django.db.models.functions import Coalesce


def queryset_items_bajo_stock_minimo(empresa, modelo_catalogo, filtro_lotes: Q):
    """
    Catálogos de una empresa cuya suma de cantidad_actual en lotes (según filtro)
    es estrictamente menor que stock_minimo.
    """
    dec = DecimalField(max_digits=16, decimal_places=4)
    return (
        modelo_catalogo.objects.filter(empresa=empresa)
        .annotate(
            stock_total=Coalesce(
                Sum('lotes__cantidad_actual', filter=filtro_lotes),
                Value(0),
                output_field=dec,
            )
        )
        .filter(stock_total__lt=F('stock_minimo'))
    )
