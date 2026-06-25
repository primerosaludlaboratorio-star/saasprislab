"""
PRIS Tools Operativos — Acciones reales en el sistema
======================================================
Herramientas de ESCRITURA que PRIS puede ejecutar en nombre del usuario.
Cada herramienta está protegida por RBAC: si el usuario no tiene el grupo/permiso
requerido, PRIS devuelve un mensaje de denegación sin ejecutar nada.

CONVENCIÓN DE CONFIRMACIÓN:
  - Todas las herramientas que modifican datos aceptan el argumento
    "confirmado": true/false.
  - Si confirmado es False/ausente, la herramienta devuelve un resumen
    del plan y pide al usuario que confirme antes de ejecutar.
  - El chat de PRIS maneja el flujo de confirmación de forma conversacional.
"""
import logging
from django.utils import timezone
from django.db import transaction

logger = logging.getLogger('core')


# ─── RECEPCIÓN / LABORATORIO ──────────────────────────────────────────────────

def tool_crear_paciente(args: dict, empresa, user) -> dict:
    """
    Crea un paciente nuevo.
    Args: nombres, apellido_paterno, apellido_materno, telefono,
          fecha_nacimiento (YYYY-MM-DD), sexo (M/F/O), email, confirmado
    """
    confirmado = args.get("confirmado", False)

    nombres = (args.get("nombres") or args.get("nombre") or "").strip()
    apellido_p = (args.get("apellido_paterno") or args.get("apellido") or "").strip()
    apellido_m = (args.get("apellido_materno") or "").strip()
    telefono = (args.get("telefono") or "").strip()
    fecha_nac = (args.get("fecha_nacimiento") or "").strip()
    sexo = (args.get("sexo") or "O").upper()
    email = (args.get("email") or "").strip()

    if not nombres or not apellido_p:
        return {"error": "Se requieren al menos 'nombres' y 'apellido_paterno' para crear el paciente."}

    # Construir nombre completo para el resumen
    nombre_completo = f"{nombres} {apellido_p} {apellido_m}".strip()

    if not confirmado:
        return {
            "necesita_confirmacion": True,
            "resumen": (
                f"Voy a crear el siguiente paciente:\n"
                f"• Nombre: {nombre_completo}\n"
                f"• Teléfono: {telefono or 'no proporcionado'}\n"
                f"• Fecha de nacimiento: {fecha_nac or 'no proporcionada'}\n"
                f"• Sexo: {sexo}\n"
                f"• Email: {email or 'no proporcionado'}\n\n"
                "¿Confirmas que quieres crear este paciente? Responde 'sí' para proceder."
            ),
            "plan": {"accion": "crear_paciente", "datos": args},
        }

    from core.models import Paciente
    from datetime import datetime

    try:
        # Verificar duplicado por nombre+teléfono
        duplicado = Paciente.objects.filter(
            empresa=empresa,
            nombres__iexact=nombres,
            apellido_paterno__iexact=apellido_p,
        ).first()
        if duplicado:
            return {
                "aviso": "duplicado",
                "mensaje": f"Ya existe un paciente con ese nombre: {duplicado.nombre_completo} (ID: {duplicado.id}). ¿Quieres usar este paciente o crear uno nuevo de todas formas?",
                "paciente_existente": {
                    "id": duplicado.id,
                    "nombre": duplicado.nombre_completo,
                    "telefono": duplicado.telefono or "",
                },
            }

        fecha_obj = None
        if fecha_nac:
            try:
                fecha_obj = datetime.strptime(fecha_nac, "%Y-%m-%d").date()
            except ValueError:
                pass

        with transaction.atomic():
            paciente = Paciente.objects.create(
                empresa=empresa,
                nombres=nombres,
                apellido_paterno=apellido_p,
                apellido_materno=apellido_m,
                telefono=telefono,
                fecha_nacimiento=fecha_obj,
                sexo=sexo if sexo in ("M", "F", "O") else "O",
                email=email,
            )

        logger.info(f"PRIS creó paciente ID={paciente.id} por {user.username}")
        return {
            "exito": True,
            "paciente_id": paciente.id,
            "nombre_completo": paciente.nombre_completo,
            "mensaje": f"Paciente '{paciente.nombre_completo}' creado correctamente (ID: {paciente.id}).",
        }
    except Exception as e:
        logger.exception("PRIS tool_crear_paciente error")
        return {"error": str(e)}


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
                sucursal=getattr(user, "sucursal", None),
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
    except Exception as e:
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
    except Exception as e:
        logger.exception("PRIS tool_cobrar_orden error")
        return {"error": str(e)}


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

    from core.models import Producto, Venta, DetalleVenta
    from farmacia.models import Lote

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


def tool_buscar_o_crear_paciente(args: dict, empresa, user) -> dict:
    """
    Busca un paciente; si no existe, lo crea automáticamente.
    Útil para flujos rápidos de registro de orden.
    Args: nombres, apellido_paterno, apellido_materno, telefono,
          fecha_nacimiento, sexo, confirmado
    """
    from core.models import Paciente
    from django.db.models import Q

    confirmado = args.get("confirmado", False)
    nombres = (args.get("nombres") or args.get("nombre") or "").strip()
    apellido_p = (args.get("apellido_paterno") or "").strip()
    telefono = (args.get("telefono") or "").strip()

    if not nombres:
        return {"error": "Se requiere al menos el nombre del paciente."}

    # Buscar por nombre + apellido
    qs = Paciente.objects.filter(empresa=empresa)
    if apellido_p:
        qs = qs.filter(nombres__icontains=nombres, apellido_paterno__icontains=apellido_p)
    elif telefono:
        qs = qs.filter(telefono=telefono)
    else:
        qs = qs.filter(Q(nombres__icontains=nombres))

    if qs.exists():
        p = qs.first()
        return {
            "encontrado": True,
            "paciente_id": p.id,
            "nombre_completo": p.nombre_completo,
            "telefono": p.telefono or "",
            "mensaje": f"Paciente encontrado: {p.nombre_completo} (ID: {p.id}).",
        }

    if not confirmado:
        nombre_completo = f"{nombres} {apellido_p}".strip()
        return {
            "necesita_confirmacion": True,
            "resumen": (
                f"No encontré un paciente existente con esos datos.\n"
                f"Voy a crear un nuevo paciente:\n"
                f"• Nombre: {nombre_completo}\n"
                f"• Teléfono: {telefono or 'no proporcionado'}\n\n"
                "¿Confirmas que quieres crearlo? Responde 'sí' para proceder."
            ),
            "plan": {"accion": "buscar_o_crear_paciente", "datos": args},
        }

    return tool_crear_paciente({**args, "confirmado": True}, empresa, user)


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
    except Exception as e:
        logger.exception("PRIS tool_actualizar_resultado_laboratorio error")
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

def tool_consultar_expediente_paciente(args: dict, empresa, user) -> dict:
    """
    Consulta el expediente completo de un paciente: historial de órdenes, resultados,
    citas, signos vitales y notas clínicas.
    Args: paciente_id (int) O nombre (str), limite_ordenes (int, default 10)
    """
    from core.models import Paciente, OrdenDeServicio
    from django.db.models import Q

    pid = args.get("paciente_id")
    nombre = args.get("nombre") or args.get("paciente_nombre", "")
    limite = min(int(args.get("limite_ordenes", 10)), 50)

    try:
        if pid:
            paciente = Paciente.objects.get(id=pid, empresa=empresa)
        elif nombre:
            qs = Paciente.objects.filter(empresa=empresa).filter(
                Q(nombre_completo__icontains=nombre) |
                Q(nombres__icontains=nombre) |
                Q(apellido_paterno__icontains=nombre)
            )
            if qs.count() == 0:
                return {"error": f"No encontré paciente con nombre '{nombre}'."}
            if qs.count() > 1:
                return {
                    "necesita_aclaracion": True,
                    "mensaje": f"Hay {qs.count()} pacientes con ese nombre. ¿Cuál quieres consultar?",
                    "pacientes": [{"id": p.id, "nombre": p.nombre_completo, "telefono": p.telefono or ""} for p in qs[:5]],
                }
            paciente = qs.first()
        else:
            return {"error": "Proporciona paciente_id o nombre del paciente."}

        # Órdenes recientes
        ordenes = OrdenDeServicio.objects.filter(
            empresa=empresa, paciente=paciente
        ).order_by('-fecha_creacion')[:limite]

        ordenes_data = []
        for o in ordenes:
            estudios = list(o.detalles.values_list('estudio__nombre', flat=True))
            ordenes_data.append({
                "folio": o.folio_orden,
                "fecha": timezone.localtime(o.fecha_creacion).strftime("%d/%m/%Y"),
                "estado": o.estado,
                "estudios": estudios,
                "total": float(o.total or 0),
            })

        # Signos vitales recientes
        sv_data = []
        try:
            from core.models import SignosVitales
            svs = SignosVitales.objects.filter(
                empresa=empresa, paciente=paciente
            ).order_by('-fecha_toma')[:5]
            for sv in svs:
                sv_data.append({
                    "fecha": timezone.localtime(sv.fecha_toma).strftime("%d/%m/%Y"),
                    "peso": float(sv.peso or 0),
                    "talla": float(sv.talla or 0),
                    "ta": f"{sv.presion_sistolica or ''}/{sv.presion_diastolica or ''}",
                    "temperatura": float(sv.temperatura or 0),
                })
        except Exception:
            pass

        return {
            "paciente_id": paciente.id,
            "nombre": paciente.nombre_completo,
            "telefono": paciente.telefono or "",
            "fecha_nacimiento": paciente.fecha_nacimiento.isoformat() if paciente.fecha_nacimiento else "",
            "sexo": paciente.sexo,
            "email": paciente.email or "",
            "total_ordenes": OrdenDeServicio.objects.filter(empresa=empresa, paciente=paciente).count(),
            "ordenes_recientes": ordenes_data,
            "signos_vitales_recientes": sv_data,
            "mensaje": f"Expediente de {paciente.nombre_completo}: {len(ordenes_data)} órdenes recientes.",
        }
    except Paciente.DoesNotExist:
        return {"error": f"Paciente ID {pid} no encontrado."}
    except Exception as e:
        logger.exception("PRIS tool_consultar_expediente_paciente")
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


def tool_programar_cita(args: dict, empresa, user) -> dict:
    """
    Programa una cita médica o de laboratorio para un paciente.
    Args: paciente_id (int) O paciente_nombre (str), fecha (YYYY-MM-DD), hora (HH:MM),
          tipo_cita (LABORATORIO/CONSULTORIO/ULTRASONIDO), motivo, confirmado
    """
    confirmado = args.get("confirmado", False)
    paciente_id = args.get("paciente_id")
    paciente_nombre = args.get("paciente_nombre", "")
    fecha = args.get("fecha", "")
    hora = args.get("hora", "09:00")
    tipo_cita = (args.get("tipo_cita") or "LABORATORIO").upper()
    motivo = (args.get("motivo") or "Cita programada por PRIS").strip()

    if not fecha:
        return {"error": "Necesito la fecha de la cita (formato YYYY-MM-DD)."}

    from core.models import Paciente, CitaMedica
    from django.db.models import Q
    from datetime import datetime

    # Resolver paciente
    paciente = None
    if paciente_id:
        try:
            paciente = Paciente.objects.get(id=paciente_id, empresa=empresa)
        except Paciente.DoesNotExist:
            return {"error": f"Paciente ID {paciente_id} no encontrado."}
    elif paciente_nombre:
        qs = Paciente.objects.filter(empresa=empresa).filter(
            Q(nombre_completo__icontains=paciente_nombre) | Q(nombres__icontains=paciente_nombre)
        )
        if qs.count() == 0:
            return {"error": f"Paciente '{paciente_nombre}' no encontrado. Crea el paciente primero."}
        if qs.count() > 1:
            return {
                "necesita_aclaracion": True,
                "mensaje": f"Hay {qs.count()} pacientes con ese nombre. ¿Cuál es el correcto?",
                "pacientes": [{"id": p.id, "nombre": p.nombre_completo, "telefono": p.telefono or ""} for p in qs[:5]],
            }
        paciente = qs.first()
    else:
        return {"error": "Necesito el paciente (paciente_id o paciente_nombre)."}

    try:
        fecha_dt = datetime.strptime(f"{fecha} {hora}", "%Y-%m-%d %H:%M")
    except ValueError:
        return {"error": f"Fecha u hora inválida. Usa formato YYYY-MM-DD y HH:MM."}

    if not confirmado:
        return {
            "necesita_confirmacion": True,
            "resumen": (
                f"Voy a programar una cita:\n"
                f"• Paciente: {paciente.nombre_completo}\n"
                f"• Fecha: {fecha} a las {hora}\n"
                f"• Tipo: {tipo_cita}\n"
                f"• Motivo: {motivo}\n\n"
                "¿Confirmas agendar esta cita? Responde 'sí'."
            ),
            "plan": {"accion": "programar_cita", "datos": args},
        }

    try:
        cita = CitaMedica.objects.create(
            empresa=empresa,
            paciente=paciente,
            fecha_hora=timezone.make_aware(fecha_dt) if timezone.is_naive(fecha_dt) else fecha_dt,
            tipo=tipo_cita,
            motivo_consulta=motivo,
            estado="PROGRAMADA",
            creado_por=user,
        )
        return {
            "exito": True,
            "cita_id": cita.id,
            "paciente": paciente.nombre_completo,
            "fecha": fecha,
            "hora": hora,
            "tipo": tipo_cita,
            "mensaje": f"Cita programada para {paciente.nombre_completo} el {fecha} a las {hora}.",
        }
    except Exception as e:
        logger.exception("PRIS tool_programar_cita error")
        return {"error": f"No se pudo crear la cita: {e}"}


def tool_enviar_notificacion_paciente(args: dict, empresa, user) -> dict:
    """
    Registra una notificación para enviar a un paciente (SMS/Email/WhatsApp).
    Args: paciente_id (int) O paciente_nombre (str), canal (SMS/EMAIL/WHATSAPP),
          mensaje, confirmado
    """
    confirmado = args.get("confirmado", False)
    paciente_id = args.get("paciente_id")
    paciente_nombre = args.get("paciente_nombre", "")
    canal = (args.get("canal") or "WHATSAPP").upper()
    mensaje = (args.get("mensaje") or "").strip()

    if not mensaje:
        return {"error": "Necesito el mensaje a enviar."}

    from core.models import Paciente, NotificacionSistema
    from django.db.models import Q

    paciente = None
    if paciente_id:
        try:
            paciente = Paciente.objects.get(id=paciente_id, empresa=empresa)
        except Paciente.DoesNotExist:
            return {"error": f"Paciente ID {paciente_id} no encontrado."}
    elif paciente_nombre:
        qs = Paciente.objects.filter(empresa=empresa).filter(
            Q(nombre_completo__icontains=paciente_nombre) | Q(nombres__icontains=paciente_nombre)
        )
        if qs.count() == 0:
            return {"error": f"Paciente '{paciente_nombre}' no encontrado."}
        paciente = qs.first()
    else:
        return {"error": "Necesito el paciente."}

    contacto = ""
    if canal == "WHATSAPP" or canal == "SMS":
        contacto = paciente.telefono or ""
        if not contacto:
            return {"error": f"El paciente {paciente.nombre_completo} no tiene teléfono registrado."}
    elif canal == "EMAIL":
        contacto = paciente.email or ""
        if not contacto:
            return {"error": f"El paciente {paciente.nombre_completo} no tiene email registrado."}

    if not confirmado:
        return {
            "necesita_confirmacion": True,
            "resumen": (
                f"Voy a enviar una notificación:\n"
                f"• Paciente: {paciente.nombre_completo}\n"
                f"• Canal: {canal}\n"
                f"• Contacto: {contacto}\n"
                f"• Mensaje: {mensaje[:100]}{'...' if len(mensaje) > 100 else ''}\n\n"
                "¿Confirmas el envío? Responde 'sí'."
            ),
            "plan": {"accion": "enviar_notificacion_paciente", "datos": args},
        }

    try:
        notif = NotificacionSistema.objects.create(
            empresa=empresa,
            titulo=f"Notificación {canal} para {paciente.nombre_completo}",
            mensaje=mensaje,
            tipo="INFO",
            destinatario_paciente_id=paciente_id,
        )
        logger.info(f"PRIS registró notificación {canal} para paciente {paciente.id} por {user.username}")
        return {
            "exito": True,
            "notificacion_id": notif.id,
            "paciente": paciente.nombre_completo,
            "canal": canal,
            "contacto": contacto,
            "mensaje": f"Notificación {canal} registrada para {paciente.nombre_completo}. Contacto: {contacto}.",
        }
    except Exception as e:
        logger.exception("PRIS tool_enviar_notificacion_paciente")
        return {"error": str(e)}


def tool_consultar_indicadores_kpi(args: dict, empresa, user) -> dict:
    """
    Consulta los KPIs del día/semana/mes para el director.
    Args: periodo (HOY/SEMANA/MES), categoria (LABORATORIO/FARMACIA/GENERAL)
    """
    from core.models import OrdenDeServicio, Venta, Producto
    from django.db.models import Sum, Count
    from datetime import timedelta

    periodo = (args.get("periodo") or "HOY").upper()
    categoria = (args.get("categoria") or "GENERAL").upper()
    hoy = timezone.localdate()

    if periodo == "HOY":
        fecha_desde = hoy
    elif periodo == "SEMANA":
        fecha_desde = hoy - timedelta(days=7)
    elif periodo == "MES":
        fecha_desde = hoy.replace(day=1)
    else:
        fecha_desde = hoy

    kpis = {"periodo": periodo, "desde": fecha_desde.isoformat(), "hasta": hoy.isoformat()}

    # Lab KPIs
    if categoria in ("LABORATORIO", "GENERAL"):
        ordenes = OrdenDeServicio.objects.filter(
            empresa=empresa, fecha_creacion__date__gte=fecha_desde
        )
        kpis["laboratorio"] = {
            "ordenes_total": ordenes.count(),
            "ordenes_completadas": ordenes.filter(estado__in=["RESULTADOS_LISTOS", "ENTREGADO"]).count(),
            "ordenes_pendientes": ordenes.filter(estado__in=["PENDIENTE_PAGO", "PAGADO", "EN_PROCESO"]).count(),
            "ingresos_lab": float(ordenes.filter(estado="PAGADO").aggregate(t=Sum("total"))["t"] or 0),
        }

    # Farmacia KPIs
    if categoria in ("FARMACIA", "GENERAL"):
        ventas = Venta.objects.filter(
            empresa=empresa, fecha__date__gte=fecha_desde, estado="COMPLETADA"
        )
        kpis["farmacia"] = {
            "ventas_total": ventas.count(),
            "ingresos_farmacia": float(ventas.aggregate(t=Sum("total"))["t"] or 0),
            "ticket_promedio": float((ventas.aggregate(t=Sum("total"))["t"] or 0) / max(ventas.count(), 1)),
        }

        # Stock bajo
        productos_bajo = Producto.objects.filter(
            empresa=empresa, stock__lte=10
        ).count()
        kpis["farmacia"]["productos_stock_bajo"] = productos_bajo

    # General
    if categoria == "GENERAL":
        from core.models import Paciente
        kpis["pacientes_nuevos"] = Paciente.objects.filter(
            empresa=empresa, fecha_registro__date__gte=fecha_desde
        ).count()

    return kpis


def tool_modificar_paciente(args: dict, empresa, user) -> dict:
    """
    Modifica datos de un paciente existente.
    Args: paciente_id (int), [campos a actualizar: telefono, email, direccion, fecha_nacimiento, sexo], confirmado
    """
    confirmado = args.get("confirmado", False)
    paciente_id = args.get("paciente_id")
    if not paciente_id:
        return {"error": "Necesito el paciente_id para modificar."}

    from core.models import Paciente

    try:
        paciente = Paciente.objects.get(id=paciente_id, empresa=empresa)
    except Paciente.DoesNotExist:
        return {"error": f"Paciente ID {paciente_id} no encontrado."}

    campos_permitidos = {
        "telefono": args.get("telefono"),
        "email": args.get("email"),
        "sexo": args.get("sexo"),
    }
    cambios = {k: v for k, v in campos_permitidos.items() if v is not None}

    if not cambios:
        return {"error": "No especificaste qué campos modificar (telefono, email, sexo)."}

    if not confirmado:
        cambios_str = "\n".join(f"  • {k}: {v}" for k, v in cambios.items())
        return {
            "necesita_confirmacion": True,
            "resumen": (
                f"Voy a modificar los datos del paciente {paciente.nombre_completo} (ID: {paciente_id}):\n"
                f"{cambios_str}\n\n"
                "¿Confirmas los cambios? Responde 'sí'."
            ),
            "plan": {"accion": "modificar_paciente", "datos": args},
        }

    for campo, valor in cambios.items():
        setattr(paciente, campo, valor)
    paciente.save(update_fields=list(cambios.keys()))
    logger.info(f"PRIS modificó paciente {paciente_id}: {cambios} por {user.username}")
    return {
        "exito": True,
        "paciente_id": paciente_id,
        "nombre": paciente.nombre_completo,
        "cambios": cambios,
        "mensaje": f"Datos de {paciente.nombre_completo} actualizados: {', '.join(f'{k}={v}' for k, v in cambios.items())}.",
    }


def tool_gestionar_usuario(args: dict, empresa, user) -> dict:
    """
    Crea o modifica un usuario del sistema. ACCIÓN ADMINISTRATIVA — requiere doble confirmación.
    Args: accion (CREAR/MODIFICAR/DESACTIVAR), username, nombres, apellido_paterno,
          email, rol (RECEPCION/LABORATORIO/FARMACIA/ADMIN/DIRECTOR), password (solo CREAR), confirmado
    """
    if not (user.is_superuser or getattr(user, 'rol', '') in ('ADMIN', 'DIRECTOR')):
        return {"error": "Solo el Director o Administrador puede gestionar usuarios."}

    confirmado = args.get("confirmado", False)
    accion = (args.get("accion") or "CREAR").upper()
    username = (args.get("username") or "").strip()
    nombres = (args.get("nombres") or "").strip()
    apellido = (args.get("apellido_paterno") or "").strip()
    email = (args.get("email") or "").strip()
    rol = (args.get("rol") or "RECEPCION").upper()
    password = (args.get("password") or "").strip()

    from core.models import Usuario

    if accion == "CREAR":
        if not username or not password:
            return {"error": "Para crear usuario necesito username y password."}

        if not confirmado:
            return {
                "necesita_confirmacion": True,
                "resumen": (
                    f"ACCION ADMINISTRATIVA — Crear usuario:\n"
                    f"• Username: {username}\n"
                    f"• Nombre: {nombres} {apellido}\n"
                    f"• Email: {email}\n"
                    f"• Rol: {rol}\n"
                    f"• Empresa: {empresa.nombre}\n\n"
                    "ADVERTENCIA: Esta accion crea un usuario con acceso al sistema. ¿Confirmas? Responde 'sí'."
                ),
                "plan": {"accion": "gestionar_usuario", "datos": args},
            }

        try:
            if Usuario.objects.filter(username=username).exists():
                return {"error": f"Ya existe un usuario con username '{username}'."}
            u = Usuario.objects.create_user(
                username=username,
                password=password,
                email=email,
                first_name=nombres,
                last_name=apellido,
                empresa=empresa,
                rol=rol,
            )
            return {
                "exito": True,
                "usuario_id": u.id,
                "username": u.username,
                "mensaje": f"Usuario '{username}' con rol {rol} creado exitosamente.",
            }
        except Exception as e:
            return {"error": str(e)}

    elif accion == "DESACTIVAR":
        if not username:
            return {"error": "Necesito el username del usuario a desactivar."}
        if not confirmado:
            return {
                "necesita_confirmacion": True,
                "resumen": f"Voy a DESACTIVAR al usuario '{username}'. ¿Confirmas? Esta acción bloquea su acceso al sistema.",
                "plan": {"accion": "gestionar_usuario", "datos": args},
            }
        try:
            u = Usuario.objects.get(username=username, empresa=empresa)
            u.is_active = False
            u.save(update_fields=["is_active"])
            return {"exito": True, "mensaje": f"Usuario '{username}' desactivado."}
        except Usuario.DoesNotExist:
            return {"error": f"Usuario '{username}' no encontrado."}
        except Exception as e:
            return {"error": str(e)}

    return {"error": f"Acción '{accion}' no válida. Usa CREAR, MODIFICAR o DESACTIVAR."}


# ─── MAPA DE HERRAMIENTAS OPERATIVAS ──────────────────────────────────────────
# PRIS/Prisci aplica RBAC en core.views.pris_ia antes de llegar aqui.
# grupos=[] mantiene compatibilidad con el mapa central _TOOL_RBAC.
# La confirmacion humana es una defensa adicional para escrituras.

TOOLS_OPERATIVOS = {
    # ── Recepción / Laboratorio ──────────────────────────────────────────────
    "crear_paciente": {
        "ejecutor": tool_crear_paciente,
        "grupos": [],
        "descripcion": "Crea un paciente nuevo en el sistema.",
    },
    "crear_orden_laboratorio": {
        "ejecutor": tool_crear_orden_laboratorio,
        "grupos": [],
        "descripcion": "Crea una orden de laboratorio con estudios para un paciente.",
    },
    "cobrar_orden": {
        "ejecutor": tool_cobrar_orden,
        "grupos": [],
        "descripcion": "Cobra/paga una orden de laboratorio.",
    },
    "registrar_venta_farmacia": {
        "ejecutor": tool_registrar_venta_farmacia,
        "grupos": [],
        "descripcion": "Registra una venta de productos en farmacia.",
    },
    "crear_cotizacion": {
        "ejecutor": tool_crear_cotizacion,
        "grupos": [],
        "descripcion": "Crea una cotización de estudios.",
    },
    "buscar_o_crear_paciente": {
        "ejecutor": tool_buscar_o_crear_paciente,
        "grupos": [],
        "descripcion": "Busca un paciente y lo crea si no existe.",
    },
    "actualizar_resultado_laboratorio": {
        "ejecutor": tool_actualizar_resultado_laboratorio,
        "grupos": [],
        "descripcion": "Guarda o actualiza el resultado de un parámetro de laboratorio.",
    },
    "cancelar_orden": {
        "ejecutor": tool_cancelar_orden,
        "grupos": [],
        "descripcion": "Cancela una orden de laboratorio.",
    },
    # ── Nuevas herramientas Jarvis ────────────────────────────────────────────
    "consultar_expediente_paciente": {
        "ejecutor": tool_consultar_expediente_paciente,
        "grupos": [],
        "descripcion": "Consulta el expediente completo de un paciente.",
    },
    "aplicar_descuento_orden": {
        "ejecutor": tool_aplicar_descuento_orden,
        "grupos": [],
        "descripcion": "Aplica un descuento a una orden de laboratorio.",
    },
    "cambiar_estado_orden": {
        "ejecutor": tool_cambiar_estado_orden,
        "grupos": [],
        "descripcion": "Cambia el estado de una orden de laboratorio.",
    },
    "programar_cita": {
        "ejecutor": tool_programar_cita,
        "grupos": [],
        "descripcion": "Programa una cita médica o de laboratorio.",
    },
    "enviar_notificacion_paciente": {
        "ejecutor": tool_enviar_notificacion_paciente,
        "grupos": [],
        "descripcion": "Envía una notificación a un paciente por SMS/Email/WhatsApp.",
    },
    "consultar_indicadores_kpi": {
        "ejecutor": tool_consultar_indicadores_kpi,
        "grupos": [],
        "descripcion": "KPIs del día/semana/mes para el director.",
    },
    "modificar_paciente": {
        "ejecutor": tool_modificar_paciente,
        "grupos": [],
        "descripcion": "Modifica datos de un paciente existente.",
    },
    "gestionar_usuario": {
        "ejecutor": tool_gestionar_usuario,
        "grupos": [],
        "descripcion": "Crea, modifica o desactiva usuarios del sistema (solo Director/Admin).",
    },
}
