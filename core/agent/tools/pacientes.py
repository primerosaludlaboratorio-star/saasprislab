"""
Herramientas PRIS para creacion, consulta y modificacion de pacientes.
"""
import logging
from django.utils import timezone
from django.utils.timezone import localdate
from django.db import transaction, IntegrityError

logger = logging.getLogger('core')


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
    except (IntegrityError, ValueError, AttributeError) as e:
        logger.exception("PRIS tool_crear_paciente error")
        return {"error": str(e)}



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
            logging.getLogger(__name__).exception("Error inesperado en tool_consultar_expediente_paciente (pacientes.py)")
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
    except (OSError, RuntimeError, ValueError) as e:
        logger.exception("PRIS tool_consultar_expediente_paciente")
        return {"error": str(e)}

