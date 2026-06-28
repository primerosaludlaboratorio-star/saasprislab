"""
Módulo de vistas para Farmacia (wrapper legacy).

Conserva compatibilidad con imports, nombres de rutas y templates históricos
después de la extracción de lógica hacia ``farmacia/views/``.
"""

import warnings
from datetime import timedelta
from decimal import Decimal

from django.contrib.auth.decorators import login_required
from django.db.models import DecimalField, ExpressionWrapper, F, Sum, Value
from django.db.models.functions import Coalesce
from django.http import HttpResponseForbidden, HttpResponseRedirect, JsonResponse
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.utils import timezone

from core.models import DetalleVenta, Venta
from core.services.ventas.venta_farmacia_service import VentaFarmaciaService

warnings.warn(
    "core.views.farmacia está deprecado. Use farmacia.views.pdv, farmacia.views.inventario, "
    "farmacia.views.devoluciones o farmacia.views.reportes en su lugar.",
    DeprecationWarning,
    stacklevel=2,
)

from farmacia.views.pdv import (  # noqa: E402
    api_buscar_producto_pdv,
    api_lotes_producto,
    pdv_buscar_fragmento,
    pdv_farmacia,
    procesar_venta,
    _empresa_desde_request,
    _verificar_acceso,
)
from farmacia.views.inventario import (  # noqa: E402
    api_buscar_productos_compra,
    api_listas_precio_pdv,
    api_saldo_caja,
    api_validar_cupon,
    carga_masiva_productos,
    dashboard_farmacia,
    entrada_mercancia,
    gestionar_politicas_descuento,
    imprimir_etiquetas,
    libro_control_antibioticos,
    registrar_compra,
    registro_gasto,
    validar_pin_precio_neto,
)
from farmacia.views.devoluciones import (  # noqa: E402
    _es_gerente_o_admin,
    buscar_venta_devolucion,
    detalle_devolucion,
    historial_devoluciones,
    procesar_devolucion,
    procesar_devolucion_venta,
)

# Alias legacy exportado por tests y vistas antiguas de core.views.farmacia
es_gerente_o_admin = _es_gerente_o_admin
from farmacia.views.reportes import (  # noqa: E402
    facturacion_40,
    lista_ventas_farmacia,
    reporte_productos_mas_vendidos,
    reporte_ventas_fecha,
    reporte_ventas_metodo_pago,
)


@login_required
def carga_masiva_excel(request):
    """Alias legacy al endpoint canónico de carga de catálogo."""
    return carga_masiva_productos(request)


@login_required
def ajustes_inventario(request):
    """Alias legacy al flujo canónico de movimientos manuales."""
    destino = reverse("farmacia:crear_movimiento")
    query = request.META.get("QUERY_STRING", "")
    if query:
        destino = f"{destino}?{query}"
    return HttpResponseRedirect(destino)


@login_required
def farmacia_inventario_general(request):
    """Alias legacy al tablero principal mientras se define la vista canónica de stock por lote."""
    return dashboard_farmacia(request)


@login_required
def inventario_general(request):
    """Alias histórico consumido por config/urls.py."""
    return farmacia_inventario_general(request)


@login_required
def estadisticas_ventas(request):
    """Alias legacy al reporte principal de ventas."""
    return reporte_ventas_fecha(request)


@login_required
def imprimir_ticket(request, venta_id):
    """Reimpresión legacy de ticket para ventas de farmacia."""
    empresa = _empresa_desde_request(request)
    if not empresa:
        return HttpResponseForbidden("Usuario sin empresa asignada.")

    venta = get_object_or_404(
        Venta.objects.select_related("empresa", "usuario", "paciente"),
        pk=venta_id,
        empresa=empresa,
    )
    detalles = venta.detalles.select_related("producto").all()
    pagos = venta.pagos.all().order_by("fecha_pago", "id")
    facturas_rel = getattr(venta, "facturas_cfdi", None)
    facturas_cfdi = facturas_rel.all() if facturas_rel is not None else []

    return render(
        request,
        "core/ticket_venta.html",
        {
            "venta": venta,
            "detalles": detalles,
            "pagos": pagos,
            "facturas_cfdi": facturas_cfdi,
        },
    )


@login_required
def imprimir_ticket_raw(request, venta_id):
    """Compatibilidad legacy: reutiliza ticket HTML si no existe formatter raw de farmacia."""
    return imprimir_ticket(request, venta_id)


@login_required
def cancelar_venta(request, venta_id):
    """Wrapper legacy para cancelación de venta con reversión de stock."""
    empresa = _empresa_desde_request(request)
    resultado = VentaFarmaciaService.cancelar_venta_resultado(request, empresa, venta_id)
    return JsonResponse(resultado["body"], status=resultado["http_status"])


@login_required
def api_carga_masiva_productos(request):
    """Alias legacy al endpoint canónico de carga masiva."""
    return carga_masiva_productos(request)


@login_required
def api_buscar_productos_lectura(request):
    """Alias legacy para lectura de catálogo desde módulos médicos."""
    return api_buscar_productos_compra(request)


@login_required
def registrar_gasto(request):
    """Alias legacy al flujo canónico de registro de gasto."""
    return registro_gasto(request)


@login_required
def corte_caja_dia(request):
    """Alias legacy al flujo actual de corte de caja."""
    return HttpResponseRedirect(reverse("corte_caja_legacy"))


def _resolver_periodo_kpis(periodo):
    dias = {
        "7d": 7,
        "30d": 30,
        "90d": 90,
    }.get((periodo or "7d").lower(), 7)
    hoy = timezone.localdate()
    return hoy - timedelta(days=dias - 1), hoy


@login_required
def api_farmacia_kpis(request):
    """Contrato JSON legado usado por dashboard_farmacia.html."""
    empresa = _empresa_desde_request(request)
    if not empresa:
        return JsonResponse({"status": "error", "message": "Usuario sin empresa asignada."}, status=403)

    inicio, fin = _resolver_periodo_kpis(request.GET.get("periodo", "7d"))

    ventas_qs = Venta.objects.filter(
        empresa=empresa,
        estado="COMPLETADA",
        fecha__date__gte=inicio,
        fecha__date__lte=fin,
    )
    detalles_qs = DetalleVenta.objects.filter(
        venta__empresa=empresa,
        venta__estado="COMPLETADA",
        venta__fecha__date__gte=inicio,
        venta__fecha__date__lte=fin,
    )

    costo_expr = Coalesce(F("costo_unitario_momento"), Value(Decimal("0.00")))
    margen_expr = ExpressionWrapper(
        (F("precio_unitario") - costo_expr) * F("cantidad"),
        output_field=DecimalField(max_digits=14, decimal_places=2),
    )

    labels = []
    data = []
    margenes = []
    cursor = inicio
    while cursor <= fin:
        total_dia = ventas_qs.filter(fecha__date=cursor).aggregate(
            total=Coalesce(
                Sum("total"),
                Decimal("0.00"),
                output_field=DecimalField(max_digits=14, decimal_places=2),
            )
        )["total"] or Decimal("0.00")
        margen_dia = detalles_qs.filter(venta__fecha__date=cursor).aggregate(
            total=Coalesce(
                Sum(margen_expr),
                Decimal("0.00"),
                output_field=DecimalField(max_digits=14, decimal_places=2),
            )
        )["total"] or Decimal("0.00")
        labels.append(cursor.strftime("%d/%m"))
        data.append(float(total_dia))
        margenes.append(float(margen_dia))
        cursor += timedelta(days=1)

    total_periodo = ventas_qs.aggregate(
        total=Coalesce(
            Sum("total"),
            Decimal("0.00"),
            output_field=DecimalField(max_digits=14, decimal_places=2),
        )
    )["total"] or Decimal("0.00")
    margen_periodo = detalles_qs.aggregate(
        total=Coalesce(
            Sum(margen_expr),
            Decimal("0.00"),
            output_field=DecimalField(max_digits=14, decimal_places=2),
        )
    )["total"] or Decimal("0.00")
    pct_margen = round((margen_periodo / total_periodo) * 100, 2) if total_periodo else 0.0

    top_productos = list(
        detalles_qs.values("producto__nombre")
        .annotate(
            cantidad=Coalesce(Sum("cantidad"), 0),
            total=Coalesce(
                Sum("subtotal"),
                Decimal("0.00"),
                output_field=DecimalField(max_digits=14, decimal_places=2),
            ),
        )
        .order_by("-total", "-cantidad")[:5]
    )

    return JsonResponse(
        {
            "status": "success",
            "labels": labels,
            "data": data,
            "margenes": margenes,
            "top_productos": [
                {
                    "nombre": row["producto__nombre"] or "Sin nombre",
                    "cantidad": int(row["cantidad"] or 0),
                    "total": float(row["total"] or 0),
                }
                for row in top_productos
            ],
            "total_periodo": float(total_periodo),
            "margen_periodo": float(margen_periodo),
            "pct_margen": float(pct_margen),
        }
    )


__all__ = [
    "api_lotes_producto",
    "api_buscar_producto_pdv",
    "pdv_buscar_fragmento",
    "pdv_farmacia",
    "procesar_venta",
    "_empresa_desde_request",
    "_verificar_acceso",
    "entrada_mercancia",
    "registrar_compra",
    "api_carga_masiva_productos",
    "api_buscar_productos_compra",
    "api_buscar_productos_lectura",
    "carga_masiva_productos",
    "carga_masiva_excel",
    "registrar_gasto",
    "corte_caja_dia",
    "farmacia_inventario_general",
    "inventario_general",
    "libro_control_antibioticos",
    "dashboard_farmacia",
    "gestionar_politicas_descuento",
    "api_listas_precio_pdv",
    "registro_gasto",
    "api_saldo_caja",
    "validar_pin_precio_neto",
    "imprimir_etiquetas",
    "api_validar_cupon",
    "ajustes_inventario",
    "estadisticas_ventas",
    "imprimir_ticket",
    "imprimir_ticket_raw",
    "cancelar_venta",
    "api_farmacia_kpis",
    "historial_devoluciones",
    "buscar_venta_devolucion",
    "procesar_devolucion",
    "procesar_devolucion_venta",
    "detalle_devolucion",
    "lista_ventas_farmacia",
    "facturacion_40",
    "reporte_ventas_fecha",
    "reporte_productos_mas_vendidos",
    "reporte_ventas_metodo_pago",
]

# Alias legacy todavía consumido por config/urls.py en producción: procesar_devolucion
# se importa directamente desde farmacia.views.devoluciones.

