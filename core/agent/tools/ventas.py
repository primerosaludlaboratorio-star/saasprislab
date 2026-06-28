"""
Herramientas PRIS para ventas de farmacia y cotizaciones.
"""
import logging
from django.utils import timezone
from django.utils.timezone import localdate
from django.db import transaction

logger = logging.getLogger('core')


def tool_registrar_venta_farmacia(args: dict, empresa, user) -> dict:
    """
    Registra una venta en farmacia PDV.
    Args: productos ([{"nombre": str, "cantidad": int}] o [{"id": int, "cantidad": int}]),
          metodo_pago, paciente_nombre, confirmado
    """
    confirmado = args.get("confirmado", False)
    productos_req = args.get("productos") or []
    metodo_pago = (args.get("metodo_pago") or "EFECTIVO").upper()
    paciente_nombre = args.get("paciente_nombre", "")

    if not productos_req:
        return {"error": "Necesito la lista de productos para registrar la venta."}

    from core.models import Producto, Venta, DetalleVenta, Lote

    # Resolver productos
    items_resueltos = []
    for item in productos_req:
        pid = item.get("id")
        nombre = item.get("nombre", "")
        cantidad_raw = item.get("cantidad")
        if cantidad_raw in (None, ""):
            cantidad = 1
        else:
            try:
                cantidad = int(cantidad_raw)
            except (TypeError, ValueError):
                return {"error": f"La cantidad para '{nombre or pid}' debe ser un entero válido."}

        if cantidad <= 0:
            return {"error": f"La cantidad para '{nombre or pid}' debe ser mayor a cero."}

        if pid:
            try:
                prod = Producto.objects.get(id=pid, empresa=empresa)
            except Producto.DoesNotExist:
                return {"error": f"Producto ID {pid} no encontrado."}
        elif nombre:
            prod = Producto.objects.filter(
                empresa=empresa,
                nombre__icontains=nombre,
            ).first()
            if not prod:
                return {"error": f"No encontré el producto '{nombre}'."}
        else:
            return {"error": "Cada producto necesita 'id' o 'nombre'."}

        # Verificar stock en lotes
        lote = Lote.objects.filter(producto=prod, cantidad__gte=cantidad).order_by('fecha_caducidad').first()
        if not lote:
            return {"error": f"Sin stock suficiente para '{prod.nombre}'. Necesitas {cantidad} unidades."}

        precio = float(prod.precio_publico or 0)
        items_resueltos.append({
            "producto": prod,
            "lote": lote,
            "cantidad": cantidad,
            "precio_unitario": precio,
            "subtotal": precio * cantidad,
        })

    total = sum(i["subtotal"] for i in items_resueltos)

    if not confirmado:
        lista = "\n".join(
            f"  • {i['producto'].nombre} x{i['cantidad']} — ${i['subtotal']:,.2f}"
            for i in items_resueltos
        )
        return {
            "necesita_confirmacion": True,
            "resumen": (
                f"Voy a registrar la siguiente venta:\n"
                f"• Paciente/cliente: {paciente_nombre or 'Público general'}\n"
                f"• Productos:\n{lista}\n"
                f"• Total: ${total:,.2f}\n"
                f"• Método de pago: {metodo_pago}\n\n"
                "¿Confirmas la venta? Responde 'sí'."
            ),
            "plan": {"accion": "registrar_venta_farmacia", "datos": args},
        }

    try:
        with transaction.atomic():
            venta = Venta.objects.create(
                empresa=empresa,
                usuario=user,
                paciente_nombre=paciente_nombre or "Público general",
                subtotal=total,
                total=total,
                impuestos_iva=0,
                redondeo=0,
                descuento_aplicado=0,
            )
            for item in items_resueltos:
                DetalleVenta.objects.create(
                    venta=venta,
                    producto=item["producto"],
                    lote_vendido=item["lote"],
                    cantidad=item["cantidad"],
                    precio_unitario=item["precio_unitario"],
                    subtotal=item["subtotal"],
                    costo_unitario_momento=float(item["lote"].costo_adquisicion or 0),
                )
                # Descontar stock del lote
                item["lote"].cantidad -= item["cantidad"]
                item["lote"].save(update_fields=["cantidad"])

        logger.info(f"PRIS registró venta farmacia ${total} por {user.username}")
        return {
            "exito": True,
            "folio": venta.folio_operacion or str(venta.id),
            "total": total,
            "metodo_pago": metodo_pago,
            "productos": [i["producto"].nombre for i in items_resueltos],
            "mensaje": f"Venta registrada. Total: ${total:,.2f}. Folio: {venta.folio_operacion or venta.id}.",
        }
    except Exception as e:
        logger.exception("PRIS tool_registrar_venta_farmacia error")
        return {"error": str(e)}



def tool_crear_cotizacion(args: dict, empresa, user) -> dict:
    """
    Genera una cotización de estudios para un paciente o cliente anónimo.
    Args: paciente_nombre, estudios_nombres ([str,...]), estudios_ids ([int,...]),
          descuento_porcentaje (float)
    No requiere confirmación — es solo un cálculo de precios.
    """
    paciente_nombre = (args.get("paciente_nombre") or "Público general").strip()
    estudios_nombres = args.get("estudios_nombres") or []
    estudios_ids = args.get("estudios_ids") or []
    descuento_pct = float(args.get("descuento_porcentaje") or 0)

    from django.db.models import Q

    from laboratorio.models import Estudio as LabEstudio

    estudios = []
    if estudios_ids:
        estudios = list(LabEstudio.objects.filter(id__in=estudios_ids, activo=True))
    elif estudios_nombres:
        for nombre_est in estudios_nombres:
            est = (
                LabEstudio.objects.filter(
                    Q(nombre__icontains=nombre_est) | Q(abreviatura__icontains=nombre_est)
                )
                .filter(activo=True)
                .first()
            )
            if est:
                estudios.append(est)
            else:
                return {"error": f"No encontré el estudio '{nombre_est}'. Usa 'buscar_estudio' primero."}
    else:
        return {"error": "Necesito la lista de estudios para la cotización."}

    subtotal = sum(float(e.precio_base or 0) for e in estudios)
    descuento_monto = subtotal * (descuento_pct / 100)
    total = subtotal - descuento_monto

    # La cotización no requiere confirmación — es solo una presentación de precios
    lista = "\n".join(f"  • {e.nombre} — ${float(e.precio_base or 0):,.2f}" for e in estudios)
    logger.info(f"PRIS generó cotización para {paciente_nombre} por {user.username}")
    return {
        "exito": True,
        "paciente": paciente_nombre,
        "estudios": [{"nombre": e.nombre, "precio": float(e.precio_base or 0)} for e in estudios],
        "subtotal": subtotal,
        "descuento_porcentaje": descuento_pct,
        "descuento_monto": descuento_monto,
        "total": total,
        "mensaje": (
            f"Cotización para {paciente_nombre}:\n{lista}\n"
            f"Subtotal: ${subtotal:,.2f}\n"
            + (f"Descuento ({descuento_pct}%): -${descuento_monto:,.2f}\n" if descuento_pct else "")
            + f"**Total: ${total:,.2f}**"
        ),
    }


