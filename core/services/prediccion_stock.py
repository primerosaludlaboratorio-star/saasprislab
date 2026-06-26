"""
IA de Reabastecimiento Predictivo — Servicio de Fondo
══════════════════════════════════════════════════════
Analiza consumo histórico de los últimos 30 días y predice
cuándo se agotará cada producto.

"Director, hemos usado 50 kits de Glucosa esta semana.
Al ritmo actual, el stock se agota el jueves."
"""
import logging
from datetime import timedelta
from typing import Any

from django.utils import timezone

logger = logging.getLogger('core.prediccion_stock')


def calcular_consumo_diario(empresa, producto, dias_historico: int = 30) -> float:
    """
    Calcula el consumo diario promedio de un producto en los últimos N días.
    Usa DetalleVenta (farmacia) y AjusteInventario (laboratorio).
    """
    desde = timezone.now() - timedelta(days=dias_historico)
    consumo_total = 0.0

    try:
        from core.models import DetalleVenta
        ventas = DetalleVenta.objects.filter(
            producto=producto,
            venta__empresa=empresa,
            venta__fecha__gte=desde,
            venta__estado='COMPLETADA',
        )
        consumo_ventas = sum(float(d.cantidad or 0) for d in ventas)
        consumo_total += consumo_ventas
    except Exception as exc:
        logging.getLogger(__name__).exception("Error inesperado en calcular_consumo_diario (prediccion_stock.py)")
        logger.debug(f'prediccion_stock - DetalleVenta: {exc}')

    try:
        from core.models import AjusteInventario
        ajustes = AjusteInventario.objects.filter(
            producto=producto,
            empresa=empresa,
            fecha__gte=desde,
            tipo_ajuste__in=['SALIDA', 'CONSUMO', 'MERMA'],
        )
        consumo_ajustes = sum(abs(float(a.cantidad or 0)) for a in ajustes)
        consumo_total += consumo_ajustes
    except Exception as exc:
        logging.getLogger(__name__).exception("Error inesperado en calcular_consumo_diario (prediccion_stock.py)")
        logger.debug(f'prediccion_stock - AjusteInventario: {exc}')

    return consumo_total / max(dias_historico, 1)


def obtener_stock_actual(empresa, producto) -> float:
    """Obtiene el stock real desde los lotes activos."""
    try:
        from core.models import Lote
        from django.db.models import Sum
        stock = Lote.objects.filter(
            producto=producto,
            empresa=empresa,
            cantidad__gt=0,
        ).aggregate(total=Sum('cantidad'))['total']
        return float(stock or 0)
    except Exception:
        logging.getLogger(__name__).exception("Error inesperado en obtener_stock_actual (prediccion_stock.py)")
        return float(producto.stock or 0)


def predecir_dias_hasta_agotamiento(
    empresa,
    producto,
    dias_historico: int = 30
) -> dict[str, Any]:
    """
    Predice cuántos días quedan hasta que se agote un producto.
    Retorna diccionario con predicción completa.
    """
    consumo_diario = calcular_consumo_diario(empresa, producto, dias_historico)
    stock_actual = obtener_stock_actual(empresa, producto)

    if consumo_diario <= 0:
        dias_restantes = 999
        fecha_agotamiento = None
    else:
        dias_restantes = int(stock_actual / consumo_diario)
        fecha_agotamiento = (timezone.now() + timedelta(days=dias_restantes)).date()

    return {
        'producto_id': producto.id,
        'producto_nombre': producto.nombre,
        'sustancia': getattr(producto, 'sustancia_activa', '') or '',
        'stock_actual': stock_actual,
        'consumo_diario': round(consumo_diario, 2),
        'consumo_semanal': round(consumo_diario * 7, 1),
        'dias_restantes': dias_restantes,
        'fecha_agotamiento': fecha_agotamiento.isoformat() if fecha_agotamiento else None,
        'nivel_alerta': _calcular_nivel_alerta(dias_restantes),
        'recomendacion': _generar_recomendacion(producto.nombre, dias_restantes, consumo_diario),
    }


def _calcular_nivel_alerta(dias_restantes: int) -> str:
    if dias_restantes <= 0:
        return 'AGOTADO'
    if dias_restantes <= 1:
        return 'CRITICO'
    if dias_restantes <= 3:
        return 'URGENTE'
    if dias_restantes <= 7:
        return 'BAJO'
    return 'OK'


def _generar_recomendacion(nombre: str, dias: int, consumo_diario: float) -> str:
    cantidad_sugerida = round(consumo_diario * 14)  # 2 semanas de stock
    if dias <= 0:
        return f'AGOTADO: Solicitar {cantidad_sugerida} unidades de {nombre} de inmediato.'
    if dias <= 1:
        return f'CRITICO: {nombre} se agota HOY. Solicitar {cantidad_sugerida} unidades urgente.'
    if dias <= 3:
        return f'URGENTE: {nombre} se agota en {dias} dias. Solicitar {cantidad_sugerida} unidades.'
    if dias <= 7:
        return f'{nombre} tiene {dias} dias de stock. Programar pedido de {cantidad_sugerida} unidades.'
    return f'{nombre} tiene suficiente stock ({dias} dias).'


def predecir_agotamiento_critico(
    empresa,
    dias_umbral: int = 3,
    limite: int = 20
) -> list[dict[str, Any]]:
    """
    Retorna lista de productos con riesgo de agotamiento en menos de `dias_umbral` días.
    Ordenados por urgencia (menos días primero).
    """
    from core.models import Producto

    productos = Producto.objects.filter(
        empresa=empresa,
        stock__gt=0,
    ).order_by('nombre')[:200]

    criticos = []
    for prod in productos:
        try:
            pred = predecir_dias_hasta_agotamiento(empresa, prod)
            if pred['consumo_diario'] > 0 and pred['dias_restantes'] <= dias_umbral:
                criticos.append(pred)
        except Exception as exc:
            logging.getLogger(__name__).exception("Error inesperado en predecir_agotamiento_critico (prediccion_stock.py)")
            logger.debug(f'prediccion_stock - producto {prod.id}: {exc}')

    criticos.sort(key=lambda x: x['dias_restantes'])
    return criticos[:limite]


def reporte_inventario_predictivo(empresa, dias_umbral: int = 7) -> dict[str, Any]:
    """
    Genera un reporte completo para el War Room y el módulo de Inventario.
    """
    agotados = predecir_agotamiento_critico(empresa, dias_umbral=0)
    criticos = predecir_agotamiento_critico(empresa, dias_umbral=1)
    urgentes = predecir_agotamiento_critico(empresa, dias_umbral=3)
    bajos = predecir_agotamiento_critico(empresa, dias_umbral=7)

    return {
        'generado_en': timezone.localtime(timezone.now()).strftime('%d/%m/%Y %H:%M'),
        'resumen': {
            'agotados': len(agotados),
            'criticos_hoy': len(criticos),
            'urgentes_3_dias': len(urgentes),
            'bajos_7_dias': len(bajos),
        },
        'agotados': agotados,
        'criticos': criticos,
        'urgentes': urgentes,
        'bajos': bajos,
    }