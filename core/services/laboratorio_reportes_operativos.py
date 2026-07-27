"""Helpers for progressive laboratory sales reporting.

Sales must remain reportable while the laboratory gradually completes its
reactive, cost and presentation catalog.  These helpers deliberately use
optional enrichment and never replace a missing cost with zero.
"""

from collections import OrderedDict
from decimal import Decimal


PENDIENTE = "Pendiente de capturar"


def construir_resumen_ventas_laboratorio(detalles, empresa):
    """Return report rows from order lines plus any enrichment already known.

    The order line and ``precio_momento`` are the minimum commercial source of
    truth.  Reactive formulas and analytical cost snapshots are optional and
    are joined only when their tables/data are available.
    """
    detalles = list(detalles)
    formulas_por_analito = {}
    costeos_por_clave = {}

    try:
        from inventario.models import ConsumoEstudioReactivo, CosteoEjecucionAnaliticaLab

        analito_ids = {d.analito_id for d in detalles if getattr(d, "analito_id", None)}
        if analito_ids:
            formulas = ConsumoEstudioReactivo.objects.filter(
                empresa=empresa,
                analito_id__in=analito_ids,
                activo=True,
            ).select_related("reactivo")
            for formula in formulas:
                formulas_por_analito.setdefault(formula.analito_id, []).append(formula)

        orden_ids = {d.orden_id for d in detalles if getattr(d, "orden_id", None)}
        if orden_ids and analito_ids:
            costeos = CosteoEjecucionAnaliticaLab.objects.filter(
                empresa=empresa,
                orden_id__in=orden_ids,
                analito_id__in=analito_ids,
            )
            for costeo in costeos:
                key = (costeo.orden_id, costeo.analito_id)
                current = costeos_por_clave.setdefault(
                    key, {"costo": Decimal("0"), "ingreso": Decimal("0"), "ejecuciones": 0}
                )
                current["costo"] += costeo.costo_materiales or Decimal("0")
                current["ingreso"] += costeo.ingreso_asignado or Decimal("0")
                current["ejecuciones"] += costeo.cantidad_ejecuciones or 0
    except Exception:
        # A report must remain usable during staged migrations or before the
        # inventory app has been populated. Missing enrichment is not an error.
        formulas_por_analito = {}
        costeos_por_clave = {}

    rows = OrderedDict()
    for detalle in detalles:
        label = _label(detalle)
        row = rows.setdefault(
            label,
            {
                "estudio": label,
                "cantidad": 0,
                "ingresos": Decimal("0"),
                "reactivos": set(),
                "costos": Decimal("0"),
                "ejecuciones_costeadas": 0,
                "tiene_costo": False,
                "tiene_formula": False,
            },
        )
        row["cantidad"] += 1
        row["ingresos"] += _decimal(getattr(detalle, "precio_momento", None))

        formulas = formulas_por_analito.get(getattr(detalle, "analito_id", None), [])
        if formulas:
            row["tiene_formula"] = True
            row["reactivos"].update(
                formula.reactivo.nombre
                for formula in formulas
                if getattr(formula, "reactivo", None)
            )

        costeo = costeos_por_clave.get((detalle.orden_id, getattr(detalle, "analito_id", None)))
        if costeo and costeo["ejecuciones"]:
            row["tiene_costo"] = True
            row["costos"] += costeo["costo"]
            row["ejecuciones_costeadas"] += costeo["ejecuciones"]

    result = []
    for row in rows.values():
        row["reactivos"] = ", ".join(sorted(row["reactivos"])) or PENDIENTE
        row["costo_estado"] = "Capturado" if row["tiene_costo"] else PENDIENTE
        row["reactivo_estado"] = "Capturado" if row["tiene_formula"] else PENDIENTE
        # Presentation is not required by the sales line; expose the gap
        # explicitly until a presentation is captured in the inventory catalog.
        row["presentacion_estado"] = PENDIENTE
        row["enriquecimiento_pendiente"] = not (
            row["tiene_formula"] and row["tiene_costo"]
        )
        result.append(row)
    return result


def _label(detalle):
    from core.lims_cart import detalle_orden_etiqueta

    label = (detalle_orden_etiqueta(detalle) or "").strip()
    return label if label and label != "?" else f"Línea de laboratorio #{detalle.pk}"


def _decimal(value):
    return Decimal(str(value or "0"))
