"""
Servicios de catálogo PDV: búsqueda de productos y resolución de entidades operativas.
"""
import difflib
import logging
import unicodedata
from datetime import timedelta
from decimal import Decimal

from django.db.models import Q
from django.utils import timezone

from core.models import Lote, Producto, Sucursal
from core.utils.sucursal_helpers import get_user_primary_sucursal

logger = logging.getLogger("core.farmacia")


def _int_or_none(value):
    """Convierte un valor a int si es posible; de lo contrario None."""
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _normalizar_texto(valor):
    """Normaliza texto para búsquedas tolerantes a acentos y mayúsculas."""
    texto = unicodedata.normalize("NFKD", str(valor or ""))
    texto = "".join(ch for ch in texto if not unicodedata.combining(ch))
    return " ".join(texto.lower().split())


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
        sucursal = get_user_primary_sucursal(usuario)
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

        termino_norm = _normalizar_texto(termino)

        def _score_producto(p):
            nombre_norm = _normalizar_texto(p.nombre)
            sustancia_norm = _normalizar_texto(p.sustancia_activa)
            codigo_norm = _normalizar_texto(p.codigo_barras)
            marca_norm = _normalizar_texto(getattr(p, "marca_laboratorio", ""))
            equivalencias_norm = _normalizar_texto(getattr(p, "equivalencias_comerciales", ""))
            piezas = [nombre_norm, sustancia_norm, codigo_norm, marca_norm, equivalencias_norm]
            base_texto = " ".join(part for part in piezas if part)

            score = 0.0

            if nombre_norm == termino_norm:
                score = max(score, 1000.0)
            if sustancia_norm == termino_norm:
                score = max(score, 980.0)
            if codigo_norm == termino_norm:
                score = max(score, 970.0)
            if marca_norm == termino_norm:
                score = max(score, 960.0)
            if termino_norm and termino_norm in [x.strip() for x in equivalencias_norm.split(',')]:
                score = max(score, 950.0)

            if nombre_norm.startswith(termino_norm):
                score = max(score, 900.0 - min(len(nombre_norm) - len(termino_norm), 120))
            if sustancia_norm.startswith(termino_norm):
                score = max(score, 880.0 - min(len(sustancia_norm) - len(termino_norm), 120))
            if codigo_norm.startswith(termino_norm):
                score = max(score, 860.0 - min(len(codigo_norm) - len(termino_norm), 120))

            if termino_norm in nombre_norm:
                score = max(score, 800.0 - min(nombre_norm.index(termino_norm), 120))
            if termino_norm in sustancia_norm:
                score = max(score, 780.0 - min(sustancia_norm.index(termino_norm), 120))
            if termino_norm in codigo_norm:
                score = max(score, 760.0 - min(codigo_norm.index(termino_norm), 120))
            if termino_norm in marca_norm:
                score = max(score, 740.0 - min(marca_norm.index(termino_norm), 120))
            if termino_norm in equivalencias_norm:
                score = max(score, 735.0 - min(equivalencias_norm.index(termino_norm), 120))

            # Fuzzy suave para rescatar errores tipográficos leves.
            ratio = difflib.SequenceMatcher(None, termino_norm, base_texto).ratio()
            ratio_nombre = difflib.SequenceMatcher(None, termino_norm, nombre_norm).ratio()
            ratio_sust = difflib.SequenceMatcher(None, termino_norm, sustancia_norm).ratio()
            fuzzy = max(ratio, ratio_nombre, ratio_sust)
            if fuzzy >= 0.72:
                score = max(score, 500.0 + (fuzzy * 100.0))

            # Favorecer nombres simples y stock disponible cuando hay empate.
            score += min(len(nombre_norm), 80) * 0.01
            score += 1.0 if (p.stock or 0) > 0 else 0.0
            return score

        productos = (
            Producto.objects_all.filter(empresa=empresa)
            .filter(
                Q(codigo_barras__icontains=termino)
                | Q(nombre__icontains=termino)
                | Q(sustancia_activa__icontains=termino)
                | Q(marca_laboratorio__icontains=termino)
                | Q(equivalencias_comerciales__icontains=termino)
            )
            .only(
                "id",
                "nombre",
                "sustancia_activa",
                "codigo_barras",
                "precio_publico",
                "precio_compra",
                "stock",
                "marca_laboratorio",
                "equivalencias_comerciales",
                "iva_porcentaje",
                "es_antibiotico",
                "requiere_receta",
                "clasificacion_sanitaria",
                "categoria",
                "empresa_id",
            )
            .order_by("-id")[:40]
        )

        resultados = []
        vistos = set()
        productos_ordenados = sorted(
            list(productos),
            key=lambda p: (
                -_score_producto(p),
                _normalizar_texto(p.nombre).count(" "),
                -int(p.stock or 0),
                -int(p.id),
            ),
        )

        for p in productos_ordenados:
            precio_venta = float(p.precio_publico) if p.precio_publico else 0
            costo = float(p.precio_compra) if p.precio_compra else 0
            stock_total = int(p.stock) if p.stock else 0
            alerta_precio_bajo = precio_venta > 0 and costo > 0 and precio_venta < costo
            vistos.add(p.id)

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
                    "es_controlado": bool(p.clasificacion_sanitaria in {"I", "II", "III"} and p.categoria != "CURACION"),
                    "es_antibiotico": bool(p.es_antibiotico and p.categoria != "CURACION"),
                    "requiere_receta": bool(p.necesita_receta()),
                    "categoria": p.categoria or "",
                    "dias_restantes": 999,
                    "lote_id": None,
                    "sin_stock_vigente": False,
                    "alerta_precio_bajo": alerta_precio_bajo,
                }
            )

        if resultados:
            return resultados

        # Fallback tolerante a errores de escritura:
        # si el usuario escribe "paracetalmol", buscamos coincidencias cercanas
        # sobre nombre, sustancia activa, código y marca.
        candidatos = []
        for p in (
            Producto.objects_all.filter(empresa=empresa)
            .only(
                "id",
                "nombre",
                "sustancia_activa",
                "marca_laboratorio",
                "equivalencias_comerciales",
                "codigo_barras",
                "precio_publico",
                "precio_compra",
                "stock",
                "iva_porcentaje",
                "es_antibiotico",
                "requiere_receta",
                "clasificacion_sanitaria",
                "categoria",
                "empresa_id",
            )
            .iterator(chunk_size=500)
        ):
            nombre_norm = _normalizar_texto(p.nombre)
            sustancia_norm = _normalizar_texto(p.sustancia_activa)
            codigo_norm = _normalizar_texto(p.codigo_barras)
            marca_norm = _normalizar_texto(getattr(p, "marca_laboratorio", ""))
            equivalencias_norm = _normalizar_texto(getattr(p, "equivalencias_comerciales", ""))

            base_texto = " ".join(
                part for part in [nombre_norm, sustancia_norm, codigo_norm, marca_norm, equivalencias_norm] if part
            )
            ratio = difflib.SequenceMatcher(None, termino_norm, base_texto).ratio()
            ratio_nombre = difflib.SequenceMatcher(None, termino_norm, nombre_norm).ratio()
            ratio_sust = difflib.SequenceMatcher(None, termino_norm, sustancia_norm).ratio()
            ratio_equivalencias = difflib.SequenceMatcher(None, termino_norm, equivalencias_norm).ratio()
            score = max(ratio, ratio_nombre, ratio_sust, ratio_equivalencias)

            # Umbral conservador: evita ruido y solo rescata errores leves.
            if score >= 0.72:
                candidatos.append((score, p))

        candidatos.sort(key=lambda item: (-item[0], _normalizar_texto(item[1].nombre).count(" "), -int(item[1].stock or 0), -item[1].id))
        for _, p in candidatos[:40]:
            if p.id in vistos:
                continue
            precio_venta = float(p.precio_publico) if p.precio_publico else 0
            costo = float(p.precio_compra) if p.precio_compra else 0
            stock_total = int(p.stock) if p.stock else 0
            alerta_precio_bajo = precio_venta > 0 and costo > 0 and precio_venta < costo
            resultados.append(
                {
                    "id": p.id,
                    "nombre_comercial": p.nombre,
                    "sustancia_activa": p.sustancia_activa or "",
                    "marca_laboratorio": p.marca_laboratorio or "",
                    "equivalencias_comerciales": p.equivalencias_comerciales or "",
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
                    "es_controlado": bool(p.clasificacion_sanitaria in {"I", "II", "III"} and p.categoria != "CURACION"),
                    "es_antibiotico": bool(p.es_antibiotico and p.categoria != "CURACION"),
                    "requiere_receta": bool(p.necesita_receta()),
                    "categoria": p.categoria or "",
                    "dias_restantes": 999,
                    "lote_id": None,
                    "sin_stock_vigente": False,
                    "alerta_precio_bajo": alerta_precio_bajo,
                }
            )
        return resultados
