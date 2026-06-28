"""
Generación de PDFs (hoja de trabajo, resultados), QR, etiquetas (deprecated).
"""
import io
import os
import base64
import logging
from datetime import timedelta
from decimal import Decimal

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, JsonResponse
from django.utils import timezone
from django.conf import settings
from django.core import signing
from django.urls import reverse

from core.models import (
    OrdenDeServicio,
    ForenseAcceso,
)
from core.lims_cart import detalle_orden_etiqueta
from core.services.audit_service import registrar_auditoria
from core.services.forense_service import metadata_consentimiento_snapshot, registrar_acceso_forense

from ._helpers import _detalle_codigo_lista

logger = logging.getLogger('core')
logger_core = logging.getLogger('core')

import qrcode


@login_required
def imprimir_hoja_trabajo_pdf(request):
    """
    GENERADOR DE HOJAS DE TRABAJO (Workflow)
    - PDF compacto filtrado por Departamento y Sucursal.
    - Agrupa analitos de forma compacta para facilitar anotación manual del químico.
    - QR dinámico que abre captura_resultados con todos los folios precargados.
    """
    empresa = getattr(request.user, 'empresa', None)
    if not empresa:
        return redirect('home')
    departamento = (request.GET.get("departamento") or "").strip()
    sucursal_id = request.GET.get("sucursal")
    fecha = (request.GET.get("fecha") or "").strip()

    fecha_invalida = False
    try:
        if fecha:
            from datetime import datetime as _dt
            fecha_dt = _dt.strptime(fecha, "%Y-%m-%d").date()
        else:
            fecha_dt = timezone.localtime(timezone.now()).date()
    except (ValueError, TypeError):
        logger.warning('hoja_trabajo_lab: fecha inválida recibida (%r), usando hoy', fecha)
        fecha_dt = timezone.localtime(timezone.now()).date()
        fecha_invalida = True

    from django.db.models import Q
    qs = (
        OrdenDeServicio.objects.filter(empresa=empresa, fecha_creacion__date=fecha_dt)
        .exclude(estado="ENTREGADO")
        .select_related("paciente", "sucursal")
        .prefetch_related("detalles__analito", "detalles__perfil_lims", "detalles__paquete_lims")
        .order_by("fecha_creacion")
    )

    if departamento:
        qs = qs.filter(
            Q(detalles__analito__departamento__icontains=departamento)
            | Q(detalles__perfil_lims__analitos__departamento__icontains=departamento)
            | Q(detalles__paquete_lims__analitos__departamento__icontains=departamento)
            | Q(detalles__paquete_lims__perfiles__analitos__departamento__icontains=departamento)
        ).distinct()

    # Filtro por sucursal
    if sucursal_id:
        try:
            qs = qs.filter(sucursal_id=int(sucursal_id))
        except (ValueError, TypeError):
            pass

    ordenes = list(qs[:500])
    orden_ids = [o.id for o in ordenes]

    token = signing.dumps(
        {"ids": orden_ids, "dep": departamento or "TODOS", "suc": sucursal_id or "TODOS", "fecha": str(fecha_dt)},
        salt="worklist",
    )

    qr_url = request.build_absolute_uri(reverse("abrir_worklist_qr", args=[token]))

    # Generar QR (PNG in-memory)
    qr = qrcode.QRCode(version=2, error_correction=qrcode.constants.ERROR_CORRECT_M, box_size=6, border=2)
    qr.add_data(qr_url)
    qr.make(fit=True)
    qr_img = qr.make_image(fill_color="black", back_color="white")
    qr_buf = io.BytesIO()
    qr_img.save(qr_buf, format="PNG")
    qr_buf.seek(0)

    # PDF (ReportLab) - Formato compacto con analitos agrupados
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.units import mm
    from reportlab.lib.utils import ImageReader

    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter

    # Header
    c.setFont("Helvetica-Bold", 14)
    c.drawString(20 * mm, height - 18 * mm, f"PRISLAB v5 | HOJA DE TRABAJO")
    c.setFont("Helvetica", 10)
    c.drawString(20 * mm, height - 24 * mm, f"Empresa: {empresa.nombre}")
    c.drawString(20 * mm, height - 29 * mm, f"Fecha: {fecha_dt.isoformat()}")
    c.drawString(20 * mm, height - 34 * mm, f"Departamento: {departamento or 'TODOS'}")
    if sucursal_id:
        from core.models import Sucursal
        try:
            suc = Sucursal.objects.get(id=sucursal_id, empresa=empresa)
            c.drawString(20 * mm, height - 39 * mm, f"Sucursal: {suc.nombre}")
        except Sucursal.DoesNotExist:
            pass

    # QR top-right
    c.drawImage(ImageReader(qr_buf), width - 42 * mm, height - 42 * mm, 30 * mm, 30 * mm, mask="auto")
    c.setFont("Helvetica", 8)
    c.drawRightString(width - 12 * mm, height - 44 * mm, "Escanea para abrir Captura (set de folios)")

    # Table header (formato compacto)
    y = height - 50 * mm
    c.setFont("Helvetica-Bold", 8)
    c.drawString(12 * mm, y, "FOLIO")
    c.drawString(35 * mm, y, "PACIENTE")
    c.drawString(90 * mm, y, "ANALITOS (COMPACTO)")
    c.drawString(170 * mm, y, "ESTADO")
    y -= 4 * mm
    c.line(10 * mm, y, width - 10 * mm, y)
    y -= 5 * mm

    c.setFont("Helvetica", 8)
    filas_por_pagina = 35  # Más filas por página (formato compacto)
    fila = 0

    for o in ordenes:
        if fila >= filas_por_pagina:
            c.showPage()
            width, height = letter
            y = height - 20 * mm
            c.setFont("Helvetica-Bold", 12)
            c.drawString(20 * mm, y, "PRISLAB v5 | HOJA DE TRABAJO (continuación)")
            y -= 10 * mm
            c.setFont("Helvetica-Bold", 8)
            c.drawString(12 * mm, y, "FOLIO")
            c.drawString(35 * mm, y, "PACIENTE")
            c.drawString(90 * mm, y, "ANALITOS (COMPACTO)")
            c.drawString(170 * mm, y, "ESTADO")
            y -= 4 * mm
            c.line(10 * mm, y, width - 10 * mm, y)
            y -= 5 * mm
            c.setFont("Helvetica", 8)
            fila = 0

        detalles_qs = o.detalles.select_related(
            'analito', 'perfil_lims', 'paquete_lims'
        ).all()
        if departamento:
            detalles_qs = detalles_qs.filter(analito__departamento__icontains=departamento)
        analitos = [_detalle_codigo_lista(d) for d in detalles_qs[:12]]
        analitos_txt = ", ".join(analitos)
        if detalles_qs.count() > 12:
            analitos_txt += f" (+{detalles_qs.count() - 12})"

        folio = o.folio_orden or f"ORD-{o.id}"
        paciente = (o.paciente.nombre_completo or "")[:30]

        c.drawString(12 * mm, y, folio[:14])
        c.drawString(35 * mm, y, paciente)
        c.drawString(90 * mm, y, analitos_txt[:50])
        c.drawString(170 * mm, y, o.estado[:12])

        y -= 5 * mm  # Menos espacio entre filas (compacto)
        fila += 1

    c.showPage()
    c.save()

    pdf = buffer.getvalue()
    buffer.close()

    nombre_suc = f"_Suc{sucursal_id}" if sucursal_id else ""
    filename = f"HojaDeTrabajo_{fecha_dt.strftime('%Y%m%d')}_{(departamento or 'TODOS').replace(' ', '_')}{nombre_suc}.pdf"
    resp = HttpResponse(pdf, content_type="application/pdf")
    resp["Content-Disposition"] = f'attachment; filename="{filename}"'
    return resp


@login_required
def abrir_worklist_qr(request, token: str):
    """
    Resuelve el QR de la hoja de trabajo:
    - Verifica el token (lista de folios)
    - Abre captura industrial del primer folio y limita la lista izquierda a ese set
    """
    try:
        payload = signing.loads(token, salt="worklist", max_age=60 * 60 * 24 * 7)
        ids = payload.get("ids") or []
        ids_limpios = [int(x) for x in ids if str(x).isdigit()]
        if not ids_limpios:
            return redirect("lista_trabajo_lab")

        primer_id = ids_limpios[0]
        return redirect(f"{reverse('captura_resultados', args=[primer_id])}?worklist={token}")
    except (signing.BadSignature, signing.SignatureExpired, ValueError, KeyError):
        return redirect("lista_trabajo_lab")


def generar_qr_orden(orden_id, folio_orden=None, url_verificacion=None):
    """
    Genera un código QR único para la orden de laboratorio.
    Si se provee url_verificacion, el QR apunta a esa URL pública.
    Retorna la imagen QR codificada en base64 para usar en el template.
    """
    qr_data = url_verificacion or f"ORDEN-{orden_id}-{folio_orden or orden_id}"

    # Crear instancia QR
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=4,
        border=2,
    )
    qr.add_data(qr_data)
    qr.make(fit=True)

    # Crear imagen
    img = qr.make_image(fill_color="black", back_color="white")

    # Convertir a base64
    buffer = io.BytesIO()
    img.save(buffer, format='PNG')
    img_str = base64.b64encode(buffer.getvalue()).decode()

    return img_str


@login_required
def imprimir_resultados_pdf(request, orden_id):
    """Vista para imprimir resultados formales de laboratorio (documento médico)."""
    empresa = getattr(request.user, 'empresa', None)
    if not empresa:
        from django.contrib import messages
        messages.error(request, 'Usuario sin empresa asignada.')
        return redirect('lista_trabajo_lab')

    # Obtener el modo de impresión (membrete o digital)
    modo_impresion = request.GET.get('modo', 'digital')  # 'membrete' o 'digital'

    # Obtener la orden o devolver 404
    orden = get_object_or_404(
        OrdenDeServicio.objects.select_related('paciente', 'empresa', 'responsable_ingreso'),
        id=orden_id,
        empresa=empresa
    )

    # Triple Llave de Envío: Validar 3 condiciones antes de permitir PDF
    # 1. Saldo de la orden igual a $0.00 (orden pagada completamente)
    saldo_pendiente = orden.total - orden.anticipo
    saldo_cero = saldo_pendiente <= Decimal('0.00')

    # 2. Validación técnica (solo core.OrdenDeServicio)
    esta_validado = orden.estado in ('RESULTADOS_LISTOS', 'ENTREGADO')

    # 3. Firma de aviso de privacidad y tratamiento de datos registrada.
    from core.utils.lfpdppp_resultados import paciente_autorizado_canal_digital_resultados
    firma_privacidad = paciente_autorizado_canal_digital_resultados(orden.paciente)

    # ── CANDADO FINANCIERO (TRIPLE LLAVE — Saldo) ────────────────────────────
    if not saldo_cero:
        from core.utils.candado_financiero import respuesta_retenida_html
        import logging as _log
        _log.getLogger(__name__).warning(
            "CANDADO: imprimir_resultados_pdf bloqueado por saldo — orden %s usuario %s saldo $%.2f",
            orden_id, request.user.username, saldo_pendiente
        )
        return respuesta_retenida_html(saldo_pendiente, folio=orden.folio_orden or str(orden_id))
    # ─────────────────────────────────────────────────────────────────────────

    if not esta_validado:
        from django.contrib import messages
        messages.error(request, '❌ TRIPLE LLAVE: Esta orden no está validada por el Químico. Solo se pueden enviar órdenes validadas.')
        return redirect('captura_resultados', orden_id=orden_id)

    if not firma_privacidad:
        from django.contrib import messages
        messages.error(request, '❌ TRIPLE LLAVE: El paciente no tiene registrada la firma de aviso de privacidad. Se requiere verificación de teléfono para enviar resultados.')
        return redirect('captura_resultados', orden_id=orden_id)

    from core.services.resultados_impresion_presentacion import construir_detalles_procesados_orden

    mayor_dias_entrega = 0
    fecha_creacion_local = timezone.localtime(orden.fecha_creacion)
    fecha_entrega = fecha_creacion_local + timedelta(days=mayor_dias_entrega)
    fecha_entrega = fecha_entrega.replace(hour=17, minute=0, second=0, microsecond=0)

    detalles_procesados, ultimo_validador = construir_detalles_procesados_orden(orden)

    # Generar QR único para esta orden con URL pública de verificación
    url_base = getattr(settings, 'SITE_URL', '') or os.environ.get('SITE_URL', 'http://localhost:8000')
    url_verificacion = f"{url_base}/validar/resultado/{orden.token_acceso}/"
    qr_image_base64 = generar_qr_orden(orden_id, orden.folio_orden, url_verificacion)

    # Integridad forense: usar snapshot de paciente en el documento (no datos actuales)
    paciente_nombre_documento = (orden.paciente_nombre_snapshot or '').strip()
    if not paciente_nombre_documento and orden.paciente_id:
        paciente_nombre_documento = orden.paciente.nombre_completo if orden.paciente else ''

    # Auditoría: registro de acceso a impresión de resultados (Flow 6)
    registrar_auditoria(
        accion='PRINT',
        modelo='OrdenDeServicio',
        objeto_id=str(orden.id),
        datos_nuevos={
            'accion': 'IMPRESION_RESULTADOS_PDF',
            'folio': orden.folio_orden or str(orden.id),
            'modo': modo_impresion,
        },
        request=request,
    )

    fmeta = metadata_consentimiento_snapshot(orden.paciente) if orden.paciente_id else {}
    fmeta['vista'] = 'imprimir_resultados_pdf'
    fmeta['modo_impresion'] = modo_impresion
    registrar_acceso_forense(
        request,
        ForenseAcceso.ACCION_PDF_STAFF,
        paciente_id=orden.paciente_id,
        orden_id=orden.id,
        metadata=fmeta,
        es_publico=False,
        empresa=empresa,
    )

    if (request.GET.get('formato') or '').lower() == 'pdf':
        pdf_bytes = None
        if orden.archivo_resultado and getattr(orden.archivo_resultado, 'name', None):
            try:
                with orden.archivo_resultado.open('rb') as archivo_pdf:
                    pdf_bytes = archivo_pdf.read()
            except (OSError, IOError, FileNotFoundError):
                logger_core.warning(
                    'imprimir_resultados_pdf: no se pudo leer PDF almacenado, se regenerara orden=%s',
                    orden.id,
                    exc_info=True,
                )

        if pdf_bytes is None:
            from core.services.motor_reportes_lab import (
                generar_reporte_pdf,
                generar_reporte_pdf_simple,
                guardar_reporte_en_storage,
            )
            try:
                pdf_bytes = generar_reporte_pdf(orden, request=request)
            except (RuntimeError, ValueError, OSError):
                logger_core.warning(
                    'imprimir_resultados_pdf: motor principal fallo, usando contingencia orden=%s',
                    orden.id,
                    exc_info=True,
                )
                pdf_bytes = generar_reporte_pdf_simple(orden, request=request)
            guardar_reporte_en_storage(orden, pdf_bytes)

        filename = f"resultados_{orden.folio_orden or orden.id}.pdf"
        response = HttpResponse(pdf_bytes, content_type='application/pdf')
        response['Content-Disposition'] = f'inline; filename="{filename}"'
        return response

    return render(request, 'core/resultados_print.html', {
        'orden': orden,
        'detalles': detalles_procesados,
        'paciente': orden.paciente,
        'paciente_nombre_documento': paciente_nombre_documento,
        'empresa': empresa,
        'fecha_entrega': fecha_entrega,
        'ultimo_validador': ultimo_validador,
        'fecha_impresion': timezone.localtime(timezone.now()),
        'modo_impresion': modo_impresion,
        'qr_image': qr_image_base64,
        'url_verificacion': url_verificacion,
    })


@login_required
def imprimir_etiquetas_lab(request, orden_id):
    """
    [DEPRECADO] Usa laboratorio.views.etiquetas.imprimir_etiqueta_tubo() en su lugar.

    Esta función se mantiene temporalmente por compatibilidad pero será eliminada.
    Redirige a la nueva implementación optimizada en laboratorio/views/etiquetas.py
    """
    import warnings
    from django.shortcuts import redirect
    from django.urls import reverse

    warnings.warn(
        "imprimir_etiquetas_lab está deprecada. Usa laboratorio.views.etiquetas.imprimir_etiqueta_tubo",
        DeprecationWarning,
        stacklevel=2
    )

    # Redirigir a la nueva vista
    return redirect(reverse('imprimir_etiqueta_tubo', args=[orden_id]))
