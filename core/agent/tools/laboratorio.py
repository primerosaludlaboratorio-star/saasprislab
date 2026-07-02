"""
Herramientas PRIS para ordenes de laboratorio, cobro, resultados y estados.
"""
import logging
from django.utils import timezone
from django.utils.timezone import localdate
from django.db import transaction, IntegrityError, OperationalError
from core.utils.sucursal_helpers import get_user_primary_sucursal

logger = logging.getLogger('core')


def tool_crear_orden_laboratorio(args: dict, empresa, user) -> dict:
    """
    Crea una orden de laboratorio LIMS v7.5 (DetalleOrden con analito/perfil/paquete).
    Args: paciente_id (int) O paciente_nombre (str),
          estudios_ids — tokens del carrito LIMS: enteros (se resuelven como analito/perfil/paquete)
          o cadenas ``analito:ID`` / ``perfil:ID`` / ``paquete:ID``,
          estudios_nombres ([str,...]) — búsqueda por nombre/código/abreviatura en ``lims.Analito``,
          metodo_pago (informativo en resumen), descuento_monto, confirmado
    """
    from decimal import Decimal, ROUND_HALF_UP

    confirmado = args.get("confirmado", False)

    paciente_id = args.get("paciente_id")
    paciente_nombre = args.get("paciente_nombre", "")
    estudios_ids = args.get("estudios_ids") or []
    estudios_nombres = args.get("estudios_nombres") or []
    metodo_pago = (args.get("metodo_pago") or "EFECTIVO").upper()
    descuento_monto = Decimal(str(args.get("descuento_monto") or 0)).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )

    from django.db.models import Q
    from django.utils import timezone
    import uuid as _uuid

    from lims.models import Analito

    from core.lims_cart import aplicar_precio_convenio, resolve_lims_cart_ids
    from core.models import DetalleOrden, OrdenDeServicio, Paciente

    # Resolver paciente
    paciente = None
    if paciente_id:
        try:
            paciente = Paciente.objects.get(id=paciente_id, empresa=empresa)
        except Paciente.DoesNotExist:
            return {"error": f"No se encontró el paciente con ID {paciente_id}."}
    elif paciente_nombre:
        qs = Paciente.objects.filter(empresa=empresa).filter(
            Q(nombres__icontains=paciente_nombre)
            | Q(apellido_paterno__icontains=paciente_nombre)
            | Q(nombre_completo__icontains=paciente_nombre)
        )
        if qs.count() == 1:
            paciente = qs.first()
        elif qs.count() > 1:
            return {
                "necesita_aclaracion": True,
                "mensaje": f"Encontré {qs.count()} pacientes con ese nombre. ¿Puedes darme más información?",
                "pacientes": [
                    {"id": p.id, "nombre": p.nombre_completo, "telefono": p.telefono or ""}
                    for p in qs[:5]
                ],
            }
        else:
            return {
                "error": f"No encontré paciente con nombre '{paciente_nombre}'. Primero crea el paciente."
            }
    else:
        return {"error": "Necesito el paciente: proporciona 'paciente_id' o 'paciente_nombre'."}

    raw_tokens: list = []
    if estudios_ids:
        raw_tokens = list(estudios_ids)
    elif estudios_nombres:
        for nombre_est in estudios_nombres:
            an = (
                Analito.objects.filter(activo=True)
                .filter(
                    Q(nombre__icontains=nombre_est)
                    | Q(abreviatura__icontains=nombre_est)
                    | Q(codigo__icontains=nombre_est)
                )
                .first()
            )
            if not an:
                return {
                    "error": (
                        f"No encontré analito LIMS '{nombre_est}'. "
                        "Use identificadores del buscador (analito:ID) o nombres del catálogo."
                    )
                }
            raw_tokens.append(f"analito:{an.id}")
    else:
        return {"error": "Necesito la lista de ítems LIMS: 'estudios_ids' o 'estudios_nombres'."}

    lineas = resolve_lims_cart_ids(raw_tokens)
    if len(lineas) != len(raw_tokens):
        return {
            "error": (
                "No se pudieron resolver todos los ítems del catálogo LIMS "
                "(analito/perfil/paquete). Verifique IDs o use formato analito:ID."
            )
        }

    precios_especiales: dict = {}
    descuento_pct = Decimal("0")
    subtotal = Decimal("0.00")
    for row in lineas:
        subtotal += aplicar_precio_convenio(
            row["precio_base"], row["precio_key"], precios_especiales, descuento_pct
        )
    subtotal = subtotal.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    total = subtotal - descuento_monto
    if total < 0:
        total = Decimal("0.00")

    nombres_linea = [
        (row.get("descripcion_linea") or row.get("precio_key") or "?") for row in lineas
    ]

    if not confirmado:
        lista_est = "\n".join(
            f"  • {nombre} — ${float(aplicar_precio_convenio(row['precio_base'], row['precio_key'], precios_especiales, descuento_pct)):,.2f}"
            for nombre, row in zip(nombres_linea, lineas)
        )
        return {
            "necesita_confirmacion": True,
            "resumen": (
                f"Voy a crear la siguiente orden (LIMS v7.5):\n"
                f"• Paciente: {paciente.nombre_completo}\n"
                f"• Líneas:\n{lista_est}\n"
                f"• Descuento: ${float(descuento_monto):,.2f}\n"
                f"• Total: ${float(total):,.2f}\n"
                f"• Método de pago (referencia): {metodo_pago}\n\n"
                "¿Confirmas? Responde 'sí' para proceder."
            ),
            "plan": {"accion": "crear_orden_laboratorio", "datos": args},
        }

    hoy = timezone.localtime(timezone.now())
    folio_orden = f"LAB-PRIS-{hoy.strftime('%Y%m%d%H%M%S')}-{_uuid.uuid4().hex[:4].upper()}"

    try:
        with transaction.atomic():
            orden = OrdenDeServicio.objects.create(
                empresa=empresa,
                sucursal=get_user_primary_sucursal(user),
                paciente=paciente,
                paciente_nombre_snapshot=paciente.nombre_completo,
                paciente_edad_snapshot=paciente.edad if hasattr(paciente, "edad") else None,
                paciente_sexo_snapshot=getattr(paciente, "sexo", None),
                responsable_ingreso=user,
                estado="PENDIENTE_PAGO",
                estado_pago="PENDIENTE",
                total=total,
                anticipo=Decimal("0.00"),
                descuento_monto=descuento_monto,
                tipo_servicio="RUTINA",
                folio_orden=folio_orden,
            )
            for row in lineas:
                precio_momento = aplicar_precio_convenio(
                    row["precio_base"],
                    row["precio_key"],
                    precios_especiales,
                    descuento_pct,
                )
                desc = (row.get("descripcion_linea") or "")[:300]
                DetalleOrden.objects.create(
                    orden=orden,
                    analito=row["analito"],
                    perfil_lims=row["perfil_lims"],
                    paquete_lims=row["paquete_lims"],
                    descripcion_linea=desc,
                    precio_momento=precio_momento,
                )

        logger.info("PRIS creó orden %s por %s", orden.folio_orden, user.username)
        return {
            "exito": True,
            "folio_orden": orden.folio_orden,
            "paciente": paciente.nombre_completo,
            "estudios": nombres_linea,
            "total": float(total),
            "estado": "PENDIENTE_PAGO",
            "mensaje": (
                f"Orden '{orden.folio_orden}' creada para {paciente.nombre_completo}. "
                f"Total: ${float(total):,.2f}. Estado: pendiente de pago."
            ),
        }
    except (IntegrityError, OperationalError, ValueError, AttributeError) as e:
        logger.exception("PRIS tool_crear_orden_laboratorio error")
        return {"error": str(e)}



def tool_cobrar_orden(args: dict, empresa, user) -> dict:
    """
    Marca una orden de laboratorio como pagada.
    Args: folio_orden (str), metodo_pago (EFECTIVO/TARJETA/TRANSFERENCIA),
          monto_pagado (float, opcional), confirmado
    """
    confirmado = args.get("confirmado", False)
    folio = (args.get("folio_orden") or args.get("folio") or "").strip().upper()
    metodo_pago = (args.get("metodo_pago") or "EFECTIVO").upper()
    monto_pagado = args.get("monto_pagado")

    if not folio:
        return {"error": "Necesito el folio de la orden para processar el cobro."}

    from core.models import OrdenDeServicio

    try:
        orden = OrdenDeServicio.objects.get(folio_orden=folio, empresa=empresa)
    except OrdenDeServicio.DoesNotExist:
        return {"error": f"No encontré la orden con folio '{folio}'."}

    if orden.estado == "PAGADO":
        return {"aviso": "ya_pagada", "mensaje": f"La orden {folio} ya está marcada como PAGADA."}

    total_orden = float(orden.total or 0)
    monto = float(monto_pagado or total_orden)

    if not confirmado:
        return {
            "necesita_confirmacion": True,
            "resumen": (
                f"Voy a cobrar la orden:\n"
                f"• Folio: {folio}\n"
                f"• Paciente: {orden.paciente.nombre_completo if orden.paciente else orden.paciente_nombre_snapshot}\n"
                f"• Total: ${total_orden:,.2f}\n"
                f"• Monto recibido: ${monto:,.2f}\n"
                f"• Método de pago: {metodo_pago}\n"
                f"• Cambio: ${max(0, monto - total_orden):,.2f}\n\n"
                "¿Confirmas el cobro? Responde 'sí'."
            ),
            "plan": {"accion": "cobrar_orden", "datos": args},
        }

    try:
        with transaction.atomic():
            orden.estado = "PAGADO"
            orden.anticipo = total_orden
            orden.save(update_fields=["estado", "anticipo"])

        logger.info(f"PRIS cobró orden {folio} (${total_orden}) por {user.username}")
        cambio = max(0, monto - total_orden)
        return {
            "exito": True,
            "folio_orden": folio,
            "total": total_orden,
            "monto_pagado": monto,
            "cambio": cambio,
            "metodo_pago": metodo_pago,
            "mensaje": f"Orden {folio} cobrada. Total: ${total_orden:,.2f}. Cambio: ${cambio:,.2f}.",
        }
    except (IntegrityError, OperationalError, ValueError) as e:
        logger.exception("PRIS tool_cobrar_orden error")
        return {"error": str(e)}



def tool_cancelar_orden(args: dict, empresa, user) -> dict:
    """
    Cancela una orden de laboratorio.
    Args: folio_orden, motivo, confirmado
    """
    confirmado = args.get("confirmado", False)
    folio = (args.get("folio_orden") or args.get("folio") or "").strip().upper()
    motivo = (args.get("motivo") or "Cancelado por PRIS").strip()

    if not folio:
        return {"error": "Necesito el folio de la orden a cancelar."}

    from core.models import OrdenDeServicio

    try:
        orden = OrdenDeServicio.objects.get(folio_orden=folio, empresa=empresa)
    except OrdenDeServicio.DoesNotExist:
        return {"error": f"No encontré la orden '{folio}'."}

    if orden.estado == "CANCELADA":
        return {"aviso": "ya_cancelada", "mensaje": f"La orden {folio} ya está cancelada."}

    if not confirmado:
        return {
            "necesita_confirmacion": True,
            "resumen": (
                f"Voy a CANCELAR la orden:\n"
                f"• Folio: {folio}\n"
                f"• Paciente: {orden.paciente.nombre_completo if orden.paciente else orden.paciente_nombre_snapshot}\n"
                f"• Estado actual: {orden.estado}\n"
                f"• Motivo: {motivo}\n\n"
                "Esta acción es importante. ¿Confirmas la cancelación? Responde 'sí'."
            ),
            "plan": {"accion": "cancelar_orden", "datos": args},
        }

    orden.estado = "CANCELADA"
    orden.diagnostico = f"[CANCELADA] {motivo}"
    orden.save(update_fields=["estado", "diagnostico"])
    logger.info(f"PRIS canceló orden {folio} por {user.username}: {motivo}")
    return {
        "exito": True,
        "folio_orden": folio,
        "mensaje": f"Orden {folio} cancelada. Motivo: {motivo}.",
    }


# ─── NUEVAS HERRAMIENTAS JARVIS ────────────────────────────────────────────────


def tool_actualizar_resultado_laboratorio(args: dict, empresa, user) -> dict:
    """
    Sugiere un valor de resultado (borrador IA). No valida ni libera la orden.
    Args: folio_orden, nombre_parametro, valor, confirmado
    """
    confirmado = args.get("confirmado", False)
    folio = (args.get("folio_orden") or args.get("folio") or "").strip().upper()
    nombre_param = (args.get("nombre_parametro") or args.get("parametro") or "").strip()
    valor = str(args.get("valor") or "").strip()

    if not folio or not nombre_param or not valor:
        return {"error": "Se requieren folio_orden, nombre_parametro y valor."}

    if not confirmado:
        return {
            "necesita_confirmacion": True,
            "resumen": (
                f"Voy a registrar como BORRADOR IA (no validado) el resultado:\n"
                f"• Orden: {folio}\n"
                f"• Parámetro: {nombre_param}\n"
                f"• Valor: {valor}\n\n"
                "Un QFB debe validar en captura. ¿Confirmas el borrador? Responde 'sí'."
            ),
            "plan": {"accion": "actualizar_resultado_laboratorio", "datos": args},
        }

    try:
        from django.db.models import Q
        from lims.models import Analito
        from core.models import OrdenDeServicio, ResultadoParametro, DetalleOrden
        from core.services.ia_clinical_governance import METODO_IA_BORRADOR, defaults_resultado_ia_borrador

        orden = OrdenDeServicio.objects.get(folio_orden=folio, empresa=empresa)
        analitos_ids = list(
            DetalleOrden.objects.filter(orden=orden, analito__isnull=False).values_list(
                'analito_id', flat=True,
            )
        )
        analito = Analito.objects.filter(id__in=analitos_ids).filter(
            Q(nombre__icontains=nombre_param)
            | Q(codigo__icontains=nombre_param)
            | Q(abreviatura__icontains=nombre_param)
        ).first()
        if not analito:
            return {"error": f"Analito '{nombre_param}' no encontrado en la orden."}
        if getattr(analito, "es_calculado", False):
            return {
                "error": (
                    f"El analito '{analito.abreviatura}' es calculado; "
                    "use captura clínica / motor de fórmulas, no PRIS."
                )
            }

        _ia_def = defaults_resultado_ia_borrador()
        rp, created = ResultadoParametro.objects.update_or_create(
            orden=orden,
            analito=analito,
            defaults={
                "valor": valor,
                "capturado_por": user,
                **_ia_def,
                "validado_por": None,
                "fecha_validacion": None,
            },
        )
        return {
            "exito": True,
            "accion": "creado" if created else "actualizado",
            "parametro": analito.nombre,
            "valor": valor,
            "aprobado_por_humano": False,
            "metodo_captura": METODO_IA_BORRADOR,
            "aviso_etico": (
                "Borrador IA: validación formal solo en pantalla de captura por personal autorizado."
            ),
            "mensaje": f"Resultado '{analito.nombre}' guardado como borrador IA: {valor}",
        }
    except OrdenDeServicio.DoesNotExist:
        return {"error": f"Orden '{folio}' no encontrada."}
    except (IntegrityError, OperationalError, ValueError, AttributeError) as e:
        logger.exception("PRIS tool_actualizar_resultado_laboratorio error")
        return {"error": str(e)}



def tool_aplicar_descuento_orden(args: dict, empresa, user) -> dict:
    """
    Aplica o modifica el descuento de una orden de laboratorio.
    Args: folio_orden, descuento_monto (float) O descuento_porcentaje (float), motivo, confirmado
    """
    confirmado = args.get("confirmado", False)
    folio = (args.get("folio_orden") or args.get("folio") or "").strip().upper()
    descuento_monto = float(args.get("descuento_monto") or 0)
    descuento_pct = float(args.get("descuento_porcentaje") or 0)
    motivo = (args.get("motivo") or "Descuento aplicado por PRIS").strip()

    if not folio:
        return {"error": "Necesito el folio de la orden."}

    from core.models import OrdenDeServicio

    try:
        orden = OrdenDeServicio.objects.get(folio_orden=folio, empresa=empresa)
    except OrdenDeServicio.DoesNotExist:
        return {"error": f"Orden '{folio}' no encontrada."}

    subtotal = float(orden.total or 0) + float(orden.descuento_monto or 0)

    if descuento_pct > 0:
        descuento_monto = subtotal * (descuento_pct / 100)
    if descuento_monto > subtotal:
        return {"error": f"El descuento (${descuento_monto:.2f}) no puede ser mayor al total (${subtotal:.2f})."}

    nuevo_total = subtotal - descuento_monto

    if not confirmado:
        return {
            "necesita_confirmacion": True,
            "resumen": (
                f"Voy a aplicar descuento a la orden {folio}:\n"
                f"• Paciente: {orden.paciente.nombre_completo if orden.paciente else orden.paciente_nombre_snapshot}\n"
                f"• Subtotal: ${subtotal:,.2f}\n"
                f"• Descuento: ${descuento_monto:,.2f} ({descuento_pct:.0f}%)\n"
                f"• Nuevo total: ${nuevo_total:,.2f}\n"
                f"• Motivo: {motivo}\n\n"
                "¿Confirmas aplicar este descuento? Responde 'sí'."
            ),
            "plan": {"accion": "aplicar_descuento_orden", "datos": args},
        }

    orden.descuento_monto = descuento_monto
    orden.total = nuevo_total
    orden.save(update_fields=["descuento_monto", "total"])
    logger.info(f"PRIS aplicó descuento ${descuento_monto} a orden {folio} por {user.username}")
    return {
        "exito": True,
        "folio_orden": folio,
        "descuento_monto": descuento_monto,
        "nuevo_total": nuevo_total,
        "mensaje": f"Descuento de ${descuento_monto:,.2f} aplicado a orden {folio}. Nuevo total: ${nuevo_total:,.2f}.",
    }



def tool_cambiar_estado_orden(args: dict, empresa, user) -> dict:
    """
    Cambia el estado operativo de una orden (sin liberar resultados clínicos).
    Args: folio_orden, nuevo_estado (PENDIENTE_PAGO/PAGADO/EN_PROCESO/CANCELADA), confirmado
    """
    confirmado = args.get("confirmado", False)
    folio = (args.get("folio_orden") or args.get("folio") or "").strip().upper()
    nuevo_estado = (args.get("nuevo_estado") or "").strip().upper()

    # Punto 18: la IA no puede poner RESULTADOS_LISTOS ni ENTREGADO (carga legal = humano en captura)
    _bloqueados_ia = ("RESULTADOS_LISTOS", "ENTREGADO")
    if nuevo_estado in _bloqueados_ia:
        return {
            "error": (
                f"PRIS no puede cambiar la orden a {nuevo_estado}. "
                "Solo un químico autorizado valida en la pantalla de captura de laboratorio."
            ),
            "codigo": "IA_ETHICS_NO_RELEASE",
        }

    estados_validos = ["PENDIENTE_PAGO", "PAGADO", "EN_PROCESO", "CANCELADA"]
    if nuevo_estado not in estados_validos:
        return {"error": f"Estado inválido vía PRIS. Opciones: {', '.join(estados_validos)}"}

    from core.models import OrdenDeServicio

    try:
        orden = OrdenDeServicio.objects.get(folio_orden=folio, empresa=empresa)
    except OrdenDeServicio.DoesNotExist:
        return {"error": f"Orden '{folio}' no encontrada."}

    if not confirmado:
        return {
            "necesita_confirmacion": True,
            "resumen": (
                f"Voy a cambiar el estado de la orden {folio}:\n"
                f"• Estado actual: {orden.estado}\n"
                f"• Nuevo estado: {nuevo_estado}\n\n"
                "¿Confirmas el cambio de estado? Responde 'sí'."
            ),
            "plan": {"accion": "cambiar_estado_orden", "datos": args},
        }

    estado_anterior = orden.estado
    orden.estado = nuevo_estado
    orden.save(update_fields=["estado"])
    logger.info(f"PRIS cambió estado orden {folio}: {estado_anterior} → {nuevo_estado} por {user.username}")
    return {
        "exito": True,
        "folio_orden": folio,
        "estado_anterior": estado_anterior,
        "nuevo_estado": nuevo_estado,
        "mensaje": f"Orden {folio} cambiada de '{estado_anterior}' a '{nuevo_estado}'.",
    }


