"""
PRISLAB V5 - Vistas de Reportes de Laboratorio
Motor de Reportes Institucionales V1.0

Genera PDFs de resultados usando portada institucional como fondo,
integra QR de validacion, y persiste en GCS.
"""
import logging
from datetime import datetime

from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_GET

from core.models import OrdenDeServicio, ForenseAcceso
from core.services.forense_service import metadata_consentimiento_snapshot, registrar_acceso_forense
from core.services.motor_reportes_lab import (
    generar_reporte_pdf,
    guardar_reporte_en_storage,
)
from core.utils.candado_financiero import ReportePdfSaldoPendienteError

logger = logging.getLogger(__name__)


@login_required
def imprimir_resultados(request, orden_id):
    """
    Genera y retorna el PDF de resultados de laboratorio.
    Usa portada institucional como fondo + overlay de datos.
    
    Query params:
        guardar=1  → Guarda automaticamente en storage (GCS/local)
        descargar=1 → Content-Disposition: attachment
    """
    orden = get_object_or_404(
        OrdenDeServicio.objects.select_related(
            'paciente', 'empresa', 'medico_referente'
        ),
        id=orden_id
    )
    
    # Verificar permisos
    if not request.user.is_superuser and getattr(request.user, 'empresa', None) != orden.empresa:
        return HttpResponse("No autorizado", status=403)

    # ── CANDADO FINANCIERO ────────────────────────────────────────────────────
    from core.utils.candado_financiero import tiene_saldo_pendiente, calcular_saldo, respuesta_retenida_html
    if tiene_saldo_pendiente(orden):
        logger.warning(
            "CANDADO: intento de imprimir resultados con saldo pendiente — orden %s usuario %s",
            orden_id, request.user.username
        )
        return respuesta_retenida_html(calcular_saldo(orden), folio=orden.folio_orden or str(orden_id))
    # ─────────────────────────────────────────────────────────────────────────

    # Generar PDF (candado de saldo también dentro del motor)
    try:
        pdf_bytes = generar_reporte_pdf(orden, request=request)
    except ReportePdfSaldoPendienteError as e:
        return respuesta_retenida_html(
            e.saldo_pendiente, folio=orden.folio_orden or str(orden_id)
        )
    except Exception as e:
        logger.error(f"Error generando reporte para orden {orden_id}: {e}", exc_info=True)
        return HttpResponse(
            f"Error al generar el reporte: {e}",
            status=500,
            content_type='text/plain'
        )
    
    # Guardar en storage si se solicita o si es produccion
    guardar = request.GET.get('guardar', '0') == '1'
    if guardar:
        url = guardar_reporte_en_storage(orden, pdf_bytes)
        if url:
            logger.info(f"PDF guardado en: {url}")
    
    # Retornar PDF
    folio = orden.folio_orden or f'ORD-{orden.id}'
    filename = f"Resultados_{folio}.pdf"
    
    response = HttpResponse(pdf_bytes, content_type='application/pdf')
    
    if request.GET.get('descargar') == '1':
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
    else:
        response['Content-Disposition'] = f'inline; filename="{filename}"'

    meta = metadata_consentimiento_snapshot(orden.paciente) if orden.paciente_id else {}
    meta['pdf_via'] = 'imprimir_resultados'
    meta['inline'] = request.GET.get('descargar') != '1'
    registrar_acceso_forense(
        request,
        ForenseAcceso.ACCION_PDF_STAFF,
        paciente_id=orden.paciente_id,
        orden_id=orden.id,
        metadata=meta,
        es_publico=False,
        empresa=orden.empresa,
    )

    return response


@login_required
def api_generar_y_guardar_reporte(request, orden_id):
    """
    API: Genera el PDF, lo guarda en storage, y retorna la URL.
    Usado por el monitor de produccion al marcar FINALIZADO.
    """
    orden = get_object_or_404(
        OrdenDeServicio.objects.select_related(
            'paciente', 'empresa', 'medico_referente'
        ),
        id=orden_id
    )
    
    if not request.user.is_superuser and getattr(request.user, 'empresa', None) != orden.empresa:
        return JsonResponse({'status': 'error', 'mensaje': 'No autorizado'}, status=403)
    
    try:
        pdf_bytes = generar_reporte_pdf(orden, request=request)
        url = guardar_reporte_en_storage(orden, pdf_bytes)
        
        return JsonResponse({
            'status': 'success',
            'url': url,
            'folio': orden.folio_orden,
            'paciente': orden.paciente.nombre_completo,
            'mensaje': f'Reporte generado y guardado correctamente'
        })
        
    except ReportePdfSaldoPendienteError as e:
        return JsonResponse(
            {
                'status': 'error',
                'codigo': 'SALDO_PENDIENTE_PDF',
                'mensaje': 'Saldo pendiente: no se genera PDF hasta liquidar la orden.',
                'saldo_pendiente': float(e.saldo_pendiente),
            },
            status=403,
        )
    except Exception as e:
        logger.error(f"Error API generar reporte orden {orden_id}: {e}", exc_info=True)
        return JsonResponse({
            'status': 'error',
            'mensaje': f'Error generando reporte: {str(e)}'
        }, status=500)


@require_GET
def validar_resultado(request, token):
    """
    Vista publica de validacion de resultados via QR.
    Permite a medicos externos verificar autenticidad del documento.
    No requiere login.
    """
    try:
        import uuid
        token_uuid = uuid.UUID(str(token))
    except (ValueError, AttributeError):
        return render(request, 'core/laboratorio/validacion_resultado.html', {
            'valido': False,
            'error': 'Token de validacion invalido',
        })

    try:
        orden = OrdenDeServicio.objects.select_related(
            'paciente', 'empresa', 'medico_referente'
        ).get(token_acceso=token_uuid)

        meta = metadata_consentimiento_snapshot(orden.paciente) if orden.paciente_id else {}
        meta['validacion_qr'] = True
        meta['resultado_valido'] = True
        registrar_acceso_forense(
            request,
            ForenseAcceso.ACCION_VALIDACION_TOKEN,
            paciente_id=orden.paciente_id,
            orden_id=orden.id,
            metadata=meta,
            es_publico=True,
            empresa=orden.empresa,
            token_str=str(token_uuid),
        )

        return render(request, 'core/laboratorio/validacion_resultado.html', {
            'valido': True,
            'orden': orden,
            'paciente_nombre': orden.paciente.nombre_completo,
            'folio': orden.folio_orden,
            'fecha': orden.fecha_creacion,
            'empresa': orden.empresa.nombre if orden.empresa else 'PRISLAB',
            'estado': orden.get_estado_clinico_display(),
        })

    except OrdenDeServicio.DoesNotExist:
        return render(request, 'core/laboratorio/validacion_resultado.html', {
            'valido': False,
            'error': 'No se encontro un resultado asociado a este codigo',
        })
