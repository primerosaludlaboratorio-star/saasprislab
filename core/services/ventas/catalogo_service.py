"""
Servicios de catálogo PDV: búsqueda de productos y resolución de entidades operativas.
"""
import logging
from datetime import timedelta
from decimal import Decimal

from django.db.models import Q
from django.utils import timezone

from core.models import Lote, Producto, Sucursal

logger = logging.getLogger("core.farmacia")


def _int_or_none(value):
    """Convierte un valor a int si es posible; de lo contrario None."""
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


class CatalogoService:
    """Métodos auxiliares de catálogo y resolución de entidades operativas."""

    @staticmethod
    def materializar_lote_operativo_si_falta(producto, empresa):
        """
        Convierte stock heredado (Producto.stock sin lotes) en un lote operativo.

        Esto evita que el PDV muestre un producto como vendible y luego falle al cobrar
        por no tener trazabilidad PEPS cargada todavía.
        """
        if not producto or not empresa:
            return None

        if producto.lotes.exists():
            return None

        stock_actual = int(producto.stock or 0)
        if stock_actual <= 0 or getattr(producto, 'es_servicio', False):
            return None

        hoy = timezone.now().date()
        return Lote.objects.create(
            empresa=empresa,
            producto=producto,
            numero_lote=f"AUTO-{producto.id}-{hoy.strftime('%Y%m%d')}",
            fecha_caducidad=hoy + timedelta(days=3650),
            cantidad=stock_actual,
            costo_adquisicion=producto.precio_compra or Decimal('0.00'),
            ubicacion_fisica='AUTO-MIGRADO-PDV',
        )

    @staticmethod
    def resolver_sucursal_operativa(usuario, empresa):
        """Obtiene una sucursal operativa o crea una matriz mínima para empresa única."""
        sucursal = getattr(usuario, 'sucursal', None)
        if sucursal:
            return sucursal

        sucursal = empresa.sucursales.filter(activa=True).order_by('pk').first()
        if sucursal:
            return sucursal

        sucursal = empresa.sucursales.order_by('pk').first()
        if sucursal:
            return sucursal

        base_codigo = f"AUTO-SUC-{empresa.pk}"
        codigo = base_codigo
        i = 1
        while Sucursal.objects.filter(codigo_sucursal=codigo).exists():
            i += 1
            codigo = f"{base_codigo}-{i}"

        return Sucursal.objects.create(
            empresa=empresa,
            nombre='Matriz Principal',
            codigo_sucursal=codigo,
            direccion='Configuracion automatica inicial',
            activa=True,
        )

    @staticmethod
    def buscar_productos_pdv(empresa, termino):
        """
        Catálogo ultraligero para tipeo en vivo (<200 ms objetivo sin middleware).
        Sin lotes ni FEFO: el stock mostrado es el campo `Producto.stock`.
        La validación real (lotes, caducidad, PEPS) ocurre en /farmacia/api/lotes-producto/<id>/
        al agregar al carrito (intentarAgregar).
        """
        termino = (termino or "").strip()
        if len(termino) < 2:
            return []

        productos = (
            Producto.objects_all.filter(empresa=empresa)
            .filter(
                Q(codigo_barras__icontains=termino)
                | Q(nombre__icontains=termino)
                | Q(sustancia_activa__icontains=termino)
                | Q(marca_laboratorio__icontains=termino)
            )
            .only(
                "id",
                "nombre",
                "sustancia_activa",
                "codigo_barras",
                "precio_publico",
                "precio_compra",
                "stock",
                "iva_porcentaje",
                "es_antibiotico",
                "requiere_receta",
                "categoria",
                "empresa_id",
            )
            .order_by("-id")[:40]
        )

        resultados = []
        for p in productos:
            precio_venta = float(p.precio_publico) if p.precio_publico else 0
            costo = float(p.precio_compra) if p.precio_compra else 0
            stock_total = int(p.stock) if p.stock else 0
            alerta_precio_bajo = precio_venta > 0 and costo > 0 and precio_venta < costo

            resultados.append(
                {
                    "id": p.id,
                    "nombre_comercial": p.nombre,
                    "sustancia_activa": p.sustancia_activa or "",
                    "codigo_barras": p.codigo_barras or "",
                    "precio_base": precio_venta,
                    "precio_venta": precio_venta,
                    "precio_compra": costo,
                    "costo_lote": costo,
                    "stock": stock_total,
                    "stock_total": stock_total,
                    "proxima_caducidad": None,
                    "dias_restantes_fefo": None,
                    "numero_lote_proximo": None,
                    "iva_pct": float(p.iva_porcentaje) if p.iva_porcentaje else 0,
                    "es_controlado": bool(p.es_antibiotico),
                    "es_antibiotico": bool(p.es_antibiotico),
                    "requiere_receta": bool(
                        getattr(p, "requiere_receta", False) or p.es_antibiotico
                    ),
                    "categoria": p.categoria or "",
                    "dias_restantes": 999,
                    "lote_id": None,
                    "sin_stock_vigente": False,
                    "alerta_precio_bajo": alerta_precio_bajo,
                }
            )
        return resultados
