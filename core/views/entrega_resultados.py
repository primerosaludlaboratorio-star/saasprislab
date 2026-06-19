"""
Vista para Entrega de Resultados de Laboratorio.
"""
import json
import logging
from decimal import Decimal
from types import SimpleNamespace
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from django.utils import timezone
from datetime import timedelta
from django.views.decorators.http import require_http_methods
from django.http import JsonResponse, HttpResponse
from django.core import signing
from django.urls import reverse
from django.conf import settings
from urllib.parse import quote

from core.models import OrdenDeServicio, BitacoraEntregaResultados, ForenseAcceso
from core.services.forense_service import metadata_consentimiento_snapshot, registrar_acceso_forense
from core.utils.lfpdppp_resultados import paciente_autorizado_canal_digital_resultados

logger = logging.getLogger(__name__)


def _paciente_nombre_para_bitacora(orden):
    return (
        getattr(orden, "paciente_nombre_snapshot", None)
        or getattr(getattr(orden, "paciente", None), "nombre_completo", "")
        or "Paciente sin nombre"
    )[:200]


def _estado_bitacora_vacio():
    return SimpleNamespace(
        ultima=None,
        fecha_enviado_mail=None,
        fecha_whatsapp_enviado=None,
        fecha_leido_paciente=None,
    )


def _crear_bitacora_entrega(
    orden,
    *,
    canal,
    request=None,
    usuario=None,
    destino="",
    estado="ENTREGADO",
    observaciones="",
    confirmado_lectura=False,
):
    """Registra una entrega de resultados usando el modelo core vigente."""
    try:
        return BitacoraEntregaResultados.objects.create(
            empresa=orden.empresa,
            sucursal=getattr(orden, "sucursal", None),
            usuario_entrega=usuario if getattr(usuario, "is_authenticated", False) else None,
            orden_id=orden.id,
            folio_orden=orden.folio_orden or f"ORD-{orden.id}",
            paciente_nombre=_paciente_nombre_para_bitacora(orden),
            paciente_id=orden.paciente_id,
            canal=canal,
            estado=estado,
            destino_envio=(destino or "")[:200],
            confirmado_lectura=confirmado_lectura,
            observaciones=observaciones or "",
        )
    except Exception as exc:
        logger.exception("No se pudo registrar bitacora de entrega orden=%s canal=%s: %s", orden.id, canal, exc)
        return None


def _bitacoras_por_orden(empresa, orden_ids):
    estado_por_orden = {orden_id: _estado_bitacora_vacio() for orden_id in orden_ids}
    if not orden_ids:
        return estado_por_orden

    for bit in (
        BitacoraEntregaResultados.objects.filter(empresa=empresa, orden_id__in=orden_ids)
        .order_by("orden_id", "fecha_entrega")
    ):
        estado = estado_por_orden.setdefault(bit.orden_id, _estado_bitacora_vacio())
        estado.ultima = bit
        if bit.canal == "EMAIL":
            estado.fecha_enviado_mail = bit.fecha_entrega
        elif bit.canal == "WHATSAPP":
            estado.fecha_whatsapp_enviado = bit.fecha_entrega
        elif bit.canal == "PORTAL":
            estado.fecha_leido_paciente = bit.fecha_entrega
    return estado_por_orden


def _contexto_meta_portal_paciente(request):
    """Open Graph neutro (sin folio ni nombre) para previsualización en WhatsApp."""
    from django.templatetags.static import static

    return {
        "og_title": "PRISLAB - Tus resultados están listos",
        "og_description": "Consulta tu reporte validado de forma segura.",
        "og_image_absolute": request.build_absolute_uri(static("logos/600.png")),
        "og_site_name": "PRISLAB",
    }


def _resumen_semaforo_portal(detalles_procesados):
    n_criticos = n_fuera = n_resto = 0
    for item in detalles_procesados:
        rps = item.get("resultado_parseado")
        if rps:
            for p in rps:
                if p.get("es_critico"):
                    n_criticos += 1
                elif p.get("es_anormal"):
                    n_fuera += 1
                else:
                    n_resto += 1
        else:
            n_resto += 1
    return n_criticos, n_fuera, n_resto


@login_required
def entrega_resultados(request):
    """
    SEMÁFORO DE LOGÍSTICA DE ENTREGA
    Tabla de estatus con iconos: Correo Enviado, WhatsApp Enviado, PDF Generado.
    """
    empresa = getattr(request.user, 'empresa', None)
    if not empresa:
        from django.contrib import messages
        from django.shortcuts import redirect
        messages.error(request, 'Usuario no tiene empresa asignada.')
        return redirect('home')
    
    # Filtrar órdenes con resultados listos (validados)
    ordenes_listas = OrdenDeServicio.objects.filter(
        empresa=empresa,
        estado='RESULTADOS_LISTOS'
    ).select_related('paciente', 'sucursal').order_by('-fecha_creacion')
    
    # Búsqueda por folio o nombre de paciente
    busqueda = request.GET.get('busqueda', '').strip()
    if busqueda:
        ordenes_listas = ordenes_listas.filter(
            Q(folio_orden__icontains=busqueda) |
            Q(paciente__nombre_completo__icontains=busqueda)
        )
    
    # Filtrar por fecha (últimos 30 días por defecto)
    dias = int(request.GET.get('dias', 30))
    fecha_limite = timezone.now().date() - timedelta(days=dias)
    ordenes_listas = ordenes_listas.filter(fecha_creacion__date__gte=fecha_limite)
    
    from core.utils.candado_financiero import tiene_saldo_pendiente, calcular_saldo

    ordenes_visibles = list(ordenes_listas[:500])
    bitacoras = _bitacoras_por_orden(empresa, [o.id for o in ordenes_visibles])

    items = []
    for o in ordenes_visibles:
        bitacora = bitacoras.get(o.id) or _estado_bitacora_vacio()
        token = signing.dumps({"oid": o.id, "eid": empresa.id}, salt="resultados-publicos")
        link_publico = request.build_absolute_uri(reverse("resultados_publicos", args=[token]))
        tel = (getattr(o.paciente, "telefono", "") or "").strip().replace(" ", "")

        # Calcular saldo para el semáforo financiero
        saldo_ord = calcular_saldo(o)
        bloqueado_por_saldo = saldo_ord > Decimal("0.01")

        whatsapp_link = None
        if tel and not bloqueado_por_saldo and o.paciente and paciente_autorizado_canal_digital_resultados(o.paciente):
            # LFPDPPP: solo enlace WA si hay consentimiento informado (privacidad + tratamiento)
            mensaje = f"Hola, tus resultados están listos (Folio {o.folio_orden or o.id}). Puedes verlos aquí: {link_publico}"
            whatsapp_link = f"https://wa.me/52{tel}?text={quote(mensaje)}"

        # Estado del semáforo
        email_enviado = bitacora.fecha_enviado_mail is not None
        whatsapp_enviado = bitacora.fecha_whatsapp_enviado is not None
        pdf_generado = True  # Si está en RESULTADOS_LISTOS, el PDF ya se puede generar
        leido_paciente = bitacora.fecha_leido_paciente is not None

        items.append(
            {
                "orden": o,
                "bitacora": bitacora,
                "link_publico": link_publico if not bloqueado_por_saldo else None,
                "whatsapp_link": whatsapp_link,
                "email_enviado": email_enviado,
                "whatsapp_enviado": whatsapp_enviado,
                "pdf_generado": pdf_generado,
                "leido_paciente": leido_paciente,
                # Candado financiero — usado en el template para badge/alerta
                "saldo_pendiente": saldo_ord,
                "bloqueado_por_saldo": bloqueado_por_saldo,
            }
        )

    return render(request, 'core/laboratorio/entrega_resultados.html', {
        'items': items,
        'busqueda': busqueda,
        'dias': dias,
    })


@login_required
def marcar_entregado(request, orden_id):
    """Marca una orden como entregada."""
    empresa = getattr(request.user, 'empresa', None)
    if not empresa:
        messages.error(request, 'Usuario no tiene empresa asignada.')
        return redirect('home')
    orden = get_object_or_404(OrdenDeServicio, id=orden_id, empresa=empresa)
    
    if orden.estado != 'RESULTADOS_LISTOS':
        messages.error(request, 'Solo se pueden entregar resultados listos/validados.')
        return redirect('entrega_resultados')
    
    orden.estado = 'ENTREGADO'
    orden.save()
    _crear_bitacora_entrega(
        orden,
        canal="PRESENCIAL",
        request=request,
        usuario=request.user,
        observaciones="Resultado marcado como entregado desde logistica de entrega.",
    )
    
    messages.success(request, f'Resultado entregado: {orden.folio_orden}')
    return redirect('entrega_resultados')


@login_required
@require_http_methods(["POST"])
def api_enviar_email_masivo_resultados(request):
    """
    BITÁCORA LOGÍSTICA: Envío masivo de resultados por Email (1 clic).
    - Marca timestamp: Enviado Mail
    - Genera link con token para medir: Leído por Paciente
    """
    empresa = getattr(request.user, 'empresa', None)
    if not empresa:
        return JsonResponse({"ok": False, "error": "Usuario sin empresa asignada"}, status=403)
    try:
        data = json.loads(request.body or "{}")
    except Exception:
        data = {}

    orden_ids = data.get("ordenes", []) or []
    if not isinstance(orden_ids, list) or not orden_ids:
        return JsonResponse({"ok": False, "error": "Debe enviar una lista de órdenes"}, status=400)

    # Permisos mínimos: recepción/químico/admin
    if not (request.user.is_staff or request.user.is_superuser or getattr(request.user, "rol", "") in ["RECEPCION", "QUIMICO", "ADMIN"]):
        return JsonResponse({"ok": False, "error": "Acceso denegado"}, status=403)

    from django.core.mail import EmailMultiAlternatives

    enviados = []
    omitidos = []
    errores = []

    for oid in orden_ids:
        try:
            oid_int = int(oid)
        except Exception:
            continue

        orden = OrdenDeServicio.objects.filter(id=oid_int, empresa=empresa).select_related("paciente").first()
        if not orden:
            omitidos.append({"orden_id": oid_int, "motivo": "No encontrada"})
            continue

        if orden.estado != "RESULTADOS_LISTOS":
            omitidos.append({"orden_id": oid_int, "motivo": f"Estado {orden.estado}"})
            continue

        # ── CANDADO FINANCIERO ───────────────────────────────────────────────
        from core.utils.candado_financiero import tiene_saldo_pendiente, calcular_saldo
        if tiene_saldo_pendiente(orden):
            saldo = calcular_saldo(orden)
            omitidos.append({
                "orden_id": oid_int,
                "motivo": f"Saldo pendiente ${saldo:.2f} — no se envía correo hasta liquidar",
            })
            continue
        # ────────────────────────────────────────────────────────────────────

        email_destino = (orden.paciente.email or "").strip() if orden.paciente else ""
        if not email_destino:
            omitidos.append({"orden_id": oid_int, "motivo": "Paciente sin email"})
            continue

        if not paciente_autorizado_canal_digital_resultados(orden.paciente):
            omitidos.append({
                "orden_id": oid_int,
                "motivo": "LFPDPPP: sin consentimiento informado para comunicación digital de resultados",
            })
            continue

        # Token de lectura (30 días)
        token = signing.dumps({"oid": orden.id, "eid": empresa.id}, salt="resultados-publicos")
        link_publico = request.build_absolute_uri(reverse("resultados_publicos", args=[token]))

        asunto = f"PRISLAB | Resultados listos - Folio {orden.folio_orden or orden.id}"
        cuerpo = (
            f"Hola.\n\n"
            f"Tus resultados ya están listos.\n"
            f"Folio: {orden.folio_orden or orden.id}\n\n"
            f"Abre tus resultados aquí:\n{link_publico}\n\n"
            f"— PRISLAB v5\n"
        )

        try:
            msg = EmailMultiAlternatives(
                subject=asunto,
                body=cuerpo,
                from_email=getattr(settings, "DEFAULT_FROM_EMAIL", None) or None,
                to=[email_destino],
            )
            sent_count = msg.send(fail_silently=False)
            if sent_count:
                _crear_bitacora_entrega(
                    orden,
                    canal="EMAIL",
                    request=request,
                    usuario=request.user,
                    destino=email_destino,
                    observaciones=f"Resultados enviados por correo. Link publico: {link_publico}",
                )

                enviados.append({"orden_id": orden.id, "email": email_destino, "link": link_publico})
            else:
                errores.append({"orden_id": orden.id, "error": "Email no enviado (sent_count=0)"})
        except Exception as e:
            errores.append({"orden_id": orden.id, "error": str(e)})

    return JsonResponse(
        {
            "ok": True,
            "enviados": enviados,
            "omitidos": omitidos,
            "errores": errores,
            "resumen": {
                "total": len(orden_ids),
                "enviados": len(enviados),
                "omitidos": len(omitidos),
                "errores": len(errores),
            },
        }
    )


@require_http_methods(["GET"])
def resultados_publicos(request, token: str):
    """
    Portal móvil del paciente (token firmado).
    PDF idéntico al interno: solo vía `resultados_publicos_pdf` → `generar_reporte_pdf`.
    """
    try:
        payload = signing.loads(token, salt="resultados-publicos", max_age=60 * 60 * 24 * 30)
        oid = int(payload.get("oid"))
        eid = int(payload.get("eid"))
    except Exception:
        return HttpResponse("Enlace inválido o expirado.", status=400)

    orden = OrdenDeServicio.objects.select_related("paciente", "empresa", "responsable_ingreso").filter(
        id=oid, empresa_id=eid
    ).first()
    if not orden:
        return HttpResponse("Orden no encontrada.", status=404)

    from core.services.resultados_impresion_presentacion import construir_detalles_procesados_orden
    from core.utils.candado_financiero import tiene_saldo_pendiente

    if tiene_saldo_pendiente(orden):
        logger.warning(
            "CANDADO: resultados_publicos — saldo pendiente, portal sin datos — orden %s token=%s",
            orden.id,
            token[:16],
        )
        ctx = {
            "solo_deuda": True,
            "empresa": orden.empresa,
            "orden": orden,
            "token": token,
            "mensaje_deuda": (
                "Tu reporte está listo, pero detectamos un saldo pendiente. "
                "Por favor, acude a recepción para liquidar y liberar tus resultados."
            ),
            **_contexto_meta_portal_paciente(request),
        }
        return render(request, "core/resultados_portal_paciente.html", ctx)

    esta_validado = orden.estado in ("RESULTADOS_LISTOS", "ENTREGADO")
    firma_privacidad = paciente_autorizado_canal_digital_resultados(orden.paciente)

    if not esta_validado:
        return HttpResponse(
            "Resultados no disponibles — el laboratorio aún no ha validado esta orden.",
            status=403,
        )
    if not firma_privacidad:
        return HttpResponse(
            "Resultados no disponibles — se requiere la firma de aviso de privacidad.",
            status=403,
        )

    _crear_bitacora_entrega(
        orden,
        canal="PORTAL",
        request=request,
        destino="portal paciente",
        confirmado_lectura=True,
        observaciones="Paciente abrió el portal público de resultados.",
    )

    meta = metadata_consentimiento_snapshot(orden.paciente) if orden.paciente_id else {}
    meta["vista"] = "resultados_publicos"
    registrar_acceso_forense(
        request,
        ForenseAcceso.ACCION_PDF_PUBLICO,
        paciente_id=orden.paciente_id,
        orden_id=orden.id,
        metadata=meta,
        es_publico=True,
        empresa=orden.empresa,
        token_str=token,
    )

    from core.views.laboratorio import generar_qr_orden

    detalles_procesados, ultimo_validador = construir_detalles_procesados_orden(orden)
    fecha_entrega = timezone.localtime(orden.fecha_creacion)
    qr_image_base64 = generar_qr_orden(orden.id, orden.folio_orden)

    paciente_nombre_documento = (getattr(orden, "paciente_nombre_snapshot", None) or "").strip()
    if not paciente_nombre_documento and orden.paciente_id:
        paciente_nombre_documento = (
            getattr(orden.paciente, "nombre_completo", None) or str(orden.paciente)
        )

    n_criticos, n_fuera, n_resto = _resumen_semaforo_portal(detalles_procesados)
    pdf_url = reverse("resultados_publicos_pdf", args=[token])

    ctx = {
        "solo_deuda": False,
        "orden": orden,
        "empresa": orden.empresa,
        "paciente": orden.paciente,
        "paciente_nombre_documento": paciente_nombre_documento,
        "detalles": detalles_procesados,
        "fecha_entrega": fecha_entrega,
        "ultimo_validador": ultimo_validador,
        "fecha_impresion": timezone.localtime(timezone.now()),
        "qr_image": qr_image_base64,
        "pdf_url": pdf_url,
        "token": token,
        "n_criticos": n_criticos,
        "n_fuera": n_fuera,
        "n_resto": n_resto,
        **_contexto_meta_portal_paciente(request),
    }
    return render(request, "core/resultados_portal_paciente.html", ctx)


@require_http_methods(["GET"])
def resultados_publicos_pdf(request, token: str):
    """
    Descarga del PDF institucional con el mismo token que el portal.
    Usa exclusivamente `generar_reporte_pdf` (mismo motor que staff).
    """
    try:
        payload = signing.loads(token, salt="resultados-publicos", max_age=60 * 60 * 24 * 30)
        oid = int(payload.get("oid"))
        eid = int(payload.get("eid"))
    except Exception:
        return HttpResponse("Enlace inválido o expirado.", status=400)

    orden = OrdenDeServicio.objects.select_related("paciente", "empresa").filter(
        id=oid, empresa_id=eid
    ).first()
    if not orden:
        return HttpResponse("Orden no encontrada.", status=404)

    from core.services.motor_reportes_lab import generar_reporte_pdf
    from core.utils.candado_financiero import (
        ReportePdfSaldoPendienteError,
        calcular_saldo,
        tiene_saldo_pendiente,
    )

    if tiene_saldo_pendiente(orden):
        logger.warning(
            "CANDADO: resultados_publicos_pdf — saldo pendiente — orden %s",
            orden.id,
        )
        return HttpResponse(
            "Resultados retenidos por saldo pendiente. Acude a recepción.",
            status=403,
            content_type="text/plain; charset=utf-8",
        )

    if orden.estado not in ("RESULTADOS_LISTOS", "ENTREGADO"):
        return HttpResponse("Resultados no disponibles.", status=403)
    if not paciente_autorizado_canal_digital_resultados(orden.paciente):
        return HttpResponse("Se requiere aviso de privacidad firmado.", status=403)

    meta = metadata_consentimiento_snapshot(orden.paciente) if orden.paciente_id else {}
    meta["vista"] = "resultados_publicos_pdf"
    registrar_acceso_forense(
        request,
        ForenseAcceso.ACCION_PDF_PUBLICO,
        paciente_id=orden.paciente_id,
        orden_id=orden.id,
        metadata=meta,
        es_publico=True,
        empresa=orden.empresa,
        token_str=token,
    )

    try:
        pdf_bytes = generar_reporte_pdf(orden, request=request)
    except ReportePdfSaldoPendienteError:
        saldo = calcular_saldo(orden)
        logger.warning("PDF público bloqueado por saldo (doble chequeo) orden=%s saldo=%s", orden.id, saldo)
        return HttpResponse(
            "Resultados retenidos por saldo pendiente.",
            status=403,
            content_type="text/plain; charset=utf-8",
        )
    except Exception as exc:
        logger.exception("Error generando PDF público orden=%s: %s", orden.id, exc)
        return HttpResponse("No se pudo generar el PDF.", status=500)

    folio = orden.folio_orden or f"ORD-{orden.id}"
    response = HttpResponse(pdf_bytes, content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="Resultados_{folio}.pdf"'
    return response


@login_required
@require_http_methods(["POST"])
def api_marcar_whatsapp_enviado(request, orden_id: int):
    """Marca timestamp de WhatsApp enviado (manual / click operacional)."""
    empresa = getattr(request.user, 'empresa', None)
    if not empresa:
        messages.error(request, 'Usuario no tiene empresa asignada.')
        return redirect('home')
    orden = get_object_or_404(OrdenDeServicio, id=orden_id, empresa=empresa)

    _crear_bitacora_entrega(
        orden,
        canal="WHATSAPP",
        request=request,
        usuario=request.user,
        destino=getattr(orden.paciente, "telefono", "") or "",
        observaciones="WhatsApp marcado como enviado desde logistica de entrega.",
    )

    meta = metadata_consentimiento_snapshot(orden.paciente) if orden.paciente_id else {}
    meta['origen'] = 'api_marcar_whatsapp_enviado'
    registrar_acceso_forense(
        request,
        ForenseAcceso.ACCION_WHATSAPP_ENVIO,
        paciente_id=orden.paciente_id,
        orden_id=orden.id,
        metadata=meta,
        es_publico=False,
        empresa=empresa,
    )

    return JsonResponse({"ok": True, "mensaje": "WhatsApp marcado correctamente"})
