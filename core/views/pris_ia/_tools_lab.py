"""
core/views/pris_ia/_tools_lab.py

Herramientas de laboratorio de Prisci: reactivos, silos, validación,
notificaciones WhatsApp y consulta de manuales RAG.
"""

import logging

from django.db import OperationalError
from django.db.models import Q

from core.models import AccionPRIS

logger = logging.getLogger('core')


def _tool_buscar_reactivo_lab(args, empresa):
    """Busca reactivos y consumibles analíticos en el Silo de Laboratorio (solo lotes ACTIVOS)."""
    nombre = args.get("nombre", "")
    limite = min(int(args.get("limite", 8)), 20)
    try:
        from inventario.models import LoteReactivoLab
        qs = LoteReactivoLab.objects.filter(
            empresa=empresa,
            cantidad_actual__gt=0,
            estado='ACTIVO',
        ).select_related('reactivo')
        if nombre:
            qs = qs.filter(Q(reactivo__nombre__icontains=nombre) | Q(reactivo__codigo_interno__icontains=nombre))
        qs = qs.order_by('fecha_caducidad')[:limite]
        lotes = [
            {
                'lote': l.numero_lote or '—',
                'reactivo': l.reactivo.nombre if l.reactivo else '—',
                'stock': float(l.cantidad_actual),
                'unidad': l.reactivo.unidad_medida if l.reactivo else '',
                'caducidad': l.fecha_caducidad.strftime('%d/%m/%Y') if l.fecha_caducidad else '—',
                'estado': l.estado,
            }
            for l in qs
        ]
        return {"total": len(lotes), "lotes": lotes}
    except (ImportError, LookupError, OperationalError) as e:
        logger.warning(f"PRIS buscar_reactivo_lab: {e}")
        return {"error": str(e), "lotes": []}


def _tool_consultar_stock_silos(args, empresa):
    """Consulta stock en cualquier silo de inventario (LAB/CONSULTORIO/GENERAL)."""
    silo = args.get("silo", "LAB").upper()
    nombre = args.get("nombre", "")
    try:
        if silo == "LAB":
            from inventario.models import LoteReactivoLab
            qs = LoteReactivoLab.objects.filter(
                empresa=empresa, estado='ACTIVO', cantidad_actual__gt=0,
            ).select_related('reactivo')
            if nombre:
                qs = qs.filter(Q(reactivo__nombre__icontains=nombre))
            items = [
                {
                    "nombre": l.reactivo.nombre if l.reactivo else "—",
                    "stock": float(l.cantidad_actual),
                    "lote": l.numero_lote or "—",
                    "caducidad": l.fecha_caducidad.strftime('%d/%m/%Y') if l.fecha_caducidad else "—",
                }
                for l in qs[:10]
            ]
        elif silo == "CONSULTORIO":
            from inventario.models import LoteInsumoConsultorio
            qs = LoteInsumoConsultorio.objects.filter(empresa=empresa, cantidad_disponible__gt=0).select_related('insumo')
            if nombre:
                qs = qs.filter(Q(insumo__nombre__icontains=nombre))
            items = [{"nombre": l.insumo.nombre if l.insumo else "—", "stock": float(l.cantidad_disponible), "lote": l.numero_lote or "—"} for l in qs[:10]]
        elif silo == "GENERAL":
            from inventario.models import LoteInsumoGeneral
            qs = LoteInsumoGeneral.objects.filter(empresa=empresa, cantidad_disponible__gt=0).select_related('insumo')
            if nombre:
                qs = qs.filter(Q(insumo__nombre__icontains=nombre))
            items = [{"nombre": l.insumo.nombre if l.insumo else "—", "stock": float(l.cantidad_disponible), "lote": l.numero_lote or "—"} for l in qs[:10]]
        else:
            return {"error": f"Silo '{silo}' no reconocido. Usa LAB, CONSULTORIO o GENERAL."}
        return {"silo": silo, "total": len(items), "items": items}
    except (ImportError, LookupError, OperationalError) as e:
        logger.warning(f"PRIS consultar_stock_silos: {e}")
        return {"error": str(e), "items": []}


def _tool_validar_orden_laboratorio(args, empresa, user):
    """
    Crea una AccionPRIS para validar y liberar resultados de una orden.
    El QFB debe confirmar en el panel de Pendientes.
    """
    from core.models import OrdenDeServicio
    folio = args.get("folio_orden", "")
    confirmado = args.get("confirmado", False)

    orden = OrdenDeServicio.objects.filter(empresa=empresa).filter(
        Q(folio_orden=folio) | Q(id__icontains=folio)
    ).first() if folio else None

    if not orden:
        return {"error": f"No se encontró la orden con folio '{folio}'."}

    if orden.estado == "RESULTADOS_LISTOS":
        return {"info": f"La orden {folio} ya está validada (RESULTADOS_LISTOS)."}

    if not confirmado:
        return {
            "requiere_confirmacion": True,
            "resumen": f"PRIS validará la orden {orden.folio_orden or orden.id} del paciente {orden.paciente.nombre_completo if orden.paciente else '—'}. ¿Confirmar?",
        }

    # Crear AccionPRIS para auditoría y ejecución confirmada
    accion = AccionPRIS.objects.create(
        empresa=empresa,
        usuario_solicitante=user,
        tipo=AccionPRIS.TIPO_VALIDAR_RESULTADO,
        modulo_destino="laboratorio.validar_resultado",
        instruccion_original=f"Jarvis: validar orden {folio}",
        payload={"orden_id": orden.id, "folio": orden.folio_orden or str(orden.id)},
    )
    return {
        "accion_id": accion.id,
        "mensaje": f"Acción de validación creada (#{accion.id}). Confirma en el panel de Pendientes para liberar los resultados.",
    }


def _tool_notificar_resultados_whatsapp(args, empresa, user):
    """Genera el enlace WhatsApp para notificar al paciente sobre sus resultados listos."""
    from core.models import OrdenDeServicio
    from core.utils.whatsapp_sender import generar_enlace_whatsapp
    folio = args.get("folio_orden", "")
    confirmado = args.get("confirmado", False)

    orden = OrdenDeServicio.objects.filter(empresa=empresa).filter(
        Q(folio_orden=folio) | Q(id__icontains=folio)
    ).select_related("paciente", "empresa").first() if folio else None

    if not orden:
        return {"error": f"Orden '{folio}' no encontrada."}

    telefono = ""
    nombre_paciente = "Paciente"
    if orden.paciente:
        telefono = orden.paciente.telefono or ""
        nombre_paciente = orden.paciente.nombre_completo or "Paciente"

    if not telefono:
        return {"error": f"El paciente {nombre_paciente} no tiene teléfono registrado. Agrégalo en su expediente."}

    if not orden.paciente:
        return {"error": "La orden no tiene paciente asociado."}

    from core.utils.lfpdppp_resultados import paciente_autorizado_canal_digital_resultados

    if not paciente_autorizado_canal_digital_resultados(orden.paciente):
        return {
            "error": (
                "LFPDPPP: sin consentimiento informado (privacidad y tratamiento) para comunicación digital. "
                "Regularizar en recepción antes de notificar resultados por WhatsApp."
            )
        }

    if not confirmado:
        return {
            "requiere_confirmacion": True,
            "resumen": f"Enviar WhatsApp a {nombre_paciente} ({telefono}) notificando que sus resultados del folio {folio} están listos.",
        }

    empresa_nombre = getattr(empresa, 'nombre', 'PRISLAB')
    mensaje = (
        f"Hola {nombre_paciente.split()[0]}, tus resultados de laboratorio ({folio}) "
        f"de {empresa_nombre} están listos. "
        f"Puedes recogerlos en sucursal o solicitarlos por este medio. "
        f"¡Que te encuentres muy bien! 🧬"
    )
    enlace = generar_enlace_whatsapp(telefono, mensaje)
    return {
        "enlace_whatsapp": enlace,
        "mensaje_preview": mensaje,
        "instruccion": "Haz clic en el enlace para abrir WhatsApp y enviar el mensaje al paciente.",
    }


def _tool_consultar_manual_lab(args, empresa):
    """
    Micro-Learning RAG — consulta la biblioteca de manuales/protocolos de laboratorio.
    Responde preguntas clínicas basadas en documentos cargados por el Director.
    Fallback inteligente: si no hay docs en el RAG, responde con conocimiento base.
    """
    pregunta = str(args.get('pregunta', '')).strip()
    if not pregunta:
        return {'error': 'Proporciona una pregunta para consultar los manuales.'}

    categoria = args.get('categoria', 'LABORATORIO')
    empresa_id = getattr(empresa, 'id', 0)

    try:
        from core.utils.rag_engine import consultar_cerebro
        resultado = consultar_cerebro(
            pregunta=pregunta,
            empresa_id=empresa_id,
            categoria=categoria,
        )
        respuesta = resultado.get('respuesta', '')
        fuentes = resultado.get('fuentes', [])

        # Si el RAG no encontró contexto relevante, dar respuesta base
        if 'No encontré contexto' in respuesta or not respuesta:
            return {
                'respuesta': (
                    f'No tengo documentos cargados en la biblioteca RAG para responder "{pregunta}". '
                    f'El Director puede cargar manuales en /capacitacion/manuales/ para activar '
                    f'el Micro-Learning. Como referencia general: consulta el Manual de Toma de Muestra '
                    f'o los Procedimientos Normalizados de Trabajo (PNT) de tu laboratorio.'
                ),
                'fuentes': [],
                'tipo': 'sin_contexto',
            }
        return {
            'respuesta': respuesta,
            'fuentes': fuentes,
            'tipo': 'rag',
        }
    except Exception as e:
        # Broad catch intencional: RAG externo puede fallar de múltiples formas.
        logger.warning('_tool_consultar_manual_lab: RAG no disponible: %s', e)
        return {
            'respuesta': (
                f'El motor RAG no está disponible en este momento ({e}). '
                f'Para tu pregunta "{pregunta}", te sugiero consultar los manuales físicos '
                f'o comunicarte con el QFB responsable.'
            ),
            'fuentes': [],
            'tipo': 'fallback_error',
        }
