"""
PRISLAB V5 - Vistas PDF de Recetas Medicas
Motor de Recetas V1.0 sobre plantilla institucional.
"""
import logging

from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404

from core.models import ConsultaMedica
from core.services.motor_recetas import generar_receta_pdf

logger = logging.getLogger(__name__)


@login_required
def imprimir_receta_profesional(request, consulta_id):
    """
    Genera y retorna el PDF de receta medica.
    Usa recetario institucional como fondo + overlay de datos.

    Query params:
        descargar=1 -> Content-Disposition: attachment
    """
    empresa = getattr(request.user, 'empresa', None)
    if not empresa and not request.user.is_superuser:
        return HttpResponse("No autorizado", status=403)
    qs = ConsultaMedica.objects.select_related(
        'paciente', 'medico', 'signos_vitales', 'receta', 'empresa'
    )
    if empresa:
        qs = qs.filter(empresa=empresa)
    consulta = get_object_or_404(qs, id=consulta_id)

    # Requiere receta vinculada para generar PDF (integridad del flujo)
    if not consulta.receta_id:
        return HttpResponse("Esta consulta no tiene receta asociada.", status=404)

    try:
        pdf_bytes = generar_receta_pdf(consulta, request=request)
    except Exception as e:
        logger.error(f"Error generando receta para consulta {consulta_id}: {e}", exc_info=True)
        return HttpResponse(
            f"Error al generar la receta: {e}",
            status=500,
            content_type='text/plain'
        )

    folio = consulta.folio_consulta or f'C-{consulta.id}'
    filename = f"Receta_{folio}.pdf"

    response = HttpResponse(pdf_bytes, content_type='application/pdf')

    if request.GET.get('descargar') == '1':
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
    else:
        response['Content-Disposition'] = f'inline; filename="{filename}"'

    return response


@login_required
def api_generar_receta_pdf(request, consulta_id):
    """
    API: Genera receta PDF y retorna URL.
    Usado desde el frontend para impresion rapida.
    """
    empresa = getattr(request.user, 'empresa', None)
    if not empresa and not request.user.is_superuser:
        return JsonResponse({'status': 'error', 'mensaje': 'No autorizado'}, status=403)
    qs = ConsultaMedica.objects.select_related(
        'paciente', 'medico', 'signos_vitales', 'receta', 'empresa'
    )
    if empresa:
        qs = qs.filter(empresa=empresa)
    consulta = get_object_or_404(qs, id=consulta_id)
    if not consulta.receta_id:
        return JsonResponse({'status': 'error', 'mensaje': 'Esta consulta no tiene receta asociada.'}, status=404)

    try:
        pdf_bytes = generar_receta_pdf(consulta, request=request)

        # Guardar en storage si la receta tiene campo de archivo
        url = None
        if hasattr(consulta, 'receta') and consulta.receta:
            try:
                from django.core.files.base import ContentFile
                from django.utils import timezone as _tz
                filename = f"recetas_pdf/Receta_{consulta.folio_consulta}_{_tz.localtime(_tz.now()).strftime('%Y%m%d_%H%M%S')}.pdf"
                pdf_file = ContentFile(pdf_bytes)

                if hasattr(consulta.receta, 'url_drive_backup'):
                    # No guardar en drive_backup, solo retornar inline
                    pass
            except Exception:
                pass

        return JsonResponse({
            'status': 'success',
            'folio': consulta.folio_consulta,
            'paciente': consulta.paciente.nombre_completo,
            'pdf_url': f'/consultorio/pdf/receta/{consulta.id}/',
            'mensaje': 'Receta generada correctamente',
        })

    except Exception as e:
        logger.error(f"Error API receta {consulta_id}: {e}", exc_info=True)
        return JsonResponse({
            'status': 'error',
            'mensaje': f'Error generando receta: {str(e)}'
        }, status=500)
