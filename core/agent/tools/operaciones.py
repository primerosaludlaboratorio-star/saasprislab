"""
Herramientas PRIS para citas, notificaciones, KPI y gestion de usuarios.
"""
import logging
from django.utils import timezone
from django.utils.timezone import localdate
from django.db import transaction

logger = logging.getLogger('core')


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
    hoy = localdate()

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
            logging.getLogger(__name__).exception("Error inesperado en tool_gestionar_usuario (operaciones.py)")
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
            logging.getLogger(__name__).exception("Error inesperado en tool_gestionar_usuario (operaciones.py)")
            return {"error": str(e)}

    return {"error": f"Acción '{accion}' no válida. Usa CREAR, MODIFICAR o DESACTIVAR."}

