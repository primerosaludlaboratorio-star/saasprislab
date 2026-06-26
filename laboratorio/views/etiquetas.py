"""
PRISLAB V5.0 - VISTAS DE IMPRESIÓN DE ETIQUETAS
===============================================
Fecha: 1 de Febrero de 2026
Objetivo: Endpoints para imprimir etiquetas térmicas de laboratorio
"""

import logging
from django.http import FileResponse, JsonResponse, HttpResponse
from django.shortcuts import get_object_or_404
from django.db.utils import DatabaseError
from django.core.exceptions import ValidationError
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods

from core.models import OrdenDeServicio
from laboratorio.utils.label_printer import (
    generar_etiqueta_tubo,
    generar_etiquetas_multiples,
    generar_etiqueta_con_qr
)
from core.mixins import grupo_requerido

logger = logging.getLogger('etiquetas')


@login_required
@grupo_requerido('LABORATORIO', 'RECEPCION')
@require_http_methods(['GET'])
def imprimir_etiqueta_tubo(request, orden_id):
    """
    Genera e imprime una etiqueta térmica para un tubo de muestra.
    
    Args:
        orden_id: ID de la orden de servicio
        
    Returns:
        FileResponse: PDF de la etiqueta
        
    URL: /laboratorio/etiqueta/<orden_id>/
    """
    try:
        empresa = getattr(request.user, 'empresa', None)
        if not empresa:
            return HttpResponse("Usuario sin empresa asignada", status=403)
        orden = get_object_or_404(OrdenDeServicio, id=orden_id, empresa=empresa)
        
        logger.info(f"Generando etiqueta para orden: {orden.folio_orden} por usuario: {request.user.username}")
        
        # Obtener datos necesarios
        folio = orden.folio_orden or f"ORD-{orden.id}"
        paciente_nombre = orden.paciente.nombre_completo if orden.paciente else "SIN PACIENTE"
        tipo_muestra = getattr(orden, 'tipo_muestra', 'Suero')
        fecha = orden.fecha_creacion
        
        # Generar PDF de etiqueta
        pdf_bytes = generar_etiqueta_tubo(
            folio_orden=folio,
            nombre_paciente=paciente_nombre,
            tipo_muestra=tipo_muestra,
            fecha=fecha
        )
        
        # Crear respuesta de archivo
        response = FileResponse(
            pdf_bytes,
            content_type='application/pdf',
            as_attachment=False,
            filename=f'etiqueta_{folio}.pdf'
        )
        
        # Headers adicionales para impresión directa
        response['Content-Disposition'] = f'inline; filename="etiqueta_{folio}.pdf"'
        
        logger.info(f"✓ Etiqueta generada para orden {folio}")
        return response
        
    except OrdenDeServicio.DoesNotExist:
        logger.error(f"Orden no encontrada: {orden_id}")
        return HttpResponse("Orden no encontrada", status=404)
        
    except (RuntimeError, ValueError, TypeError, ImportError) as e:
        logger.error(f"Error al generar etiqueta: {e}", exc_info=True)
        return HttpResponse(f"Error al generar etiqueta: {str(e)}", status=500)


@login_required
@grupo_requerido('LABORATORIO', 'RECEPCION')
@require_http_methods(['POST'])
def imprimir_etiquetas_lote(request):
    """
    Genera etiquetas para múltiples órdenes de una vez.
    
    Request POST:
        {
            "ordenes_ids": [1, 2, 3, ...]
        }
        
    Returns:
        FileResponse: PDF con múltiples etiquetas (una por página)
        
    URL: /laboratorio/etiquetas/lote/
    """
    try:
        import json
        try:
            body = json.loads(request.body or '{}')
        except json.JSONDecodeError:
            return JsonResponse({'error': 'JSON inválido'}, status=400)
        ordenes_ids = body.get('ordenes_ids', [])
        
        if not ordenes_ids:
            return JsonResponse({'error': 'No se proporcionaron IDs de órdenes'}, status=400)
        
        empresa = getattr(request.user, 'empresa', None)
        if not empresa:
            return JsonResponse({'error': 'Usuario sin empresa asignada'}, status=403)
        
        logger.info(f"Generando {len(ordenes_ids)} etiquetas en lote")
        
        # Obtener órdenes (solo de la empresa del usuario)
        ordenes = OrdenDeServicio.objects.filter(id__in=ordenes_ids, empresa=empresa).select_related('paciente')
        
        if not ordenes.exists():
            return JsonResponse({'error': 'No se encontraron órdenes'}, status=404)
        
        # Preparar datos para las etiquetas
        ordenes_data = []
        for orden in ordenes:
            ordenes_data.append({
                'folio_orden': orden.folio_orden or f"ORD-{orden.id}",
                'nombre_paciente': orden.paciente.nombre_completo if orden.paciente else "SIN PACIENTE",
                'tipo_muestra': getattr(orden, 'tipo_muestra', 'Suero'),
                'fecha': orden.fecha_creacion
            })
        
        # Generar PDF con múltiples etiquetas
        pdf_bytes = generar_etiquetas_multiples(ordenes_data)
        
        # Crear respuesta
        response = FileResponse(
            pdf_bytes,
            content_type='application/pdf',
            as_attachment=False,
            filename=f'etiquetas_lote_{len(ordenes)}.pdf'
        )
        
        logger.info(f"✓ {len(ordenes)} etiquetas generadas en lote")
        return response
        
    except (RuntimeError, ValueError, TypeError, ImportError, DatabaseError, ValidationError) as e:
        logger.error(f"Error al generar etiquetas en lote: {e}", exc_info=True)
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@grupo_requerido('LABORATORIO', 'RECEPCION')
@require_http_methods(['GET'])
def imprimir_etiqueta_qr(request, orden_id):
    """
    Genera una etiqueta con QR en lugar de código de barras.
    
    Args:
        orden_id: ID de la orden de servicio
        
    Returns:
        FileResponse: PDF de la etiqueta con QR
        
    URL: /laboratorio/etiqueta-qr/<orden_id>/
    """
    try:
        empresa = getattr(request.user, 'empresa', None)
        if not empresa:
            return HttpResponse("Usuario sin empresa asignada", status=403)
        orden = get_object_or_404(OrdenDeServicio, id=orden_id, empresa=empresa)
        
        logger.info(f"Generando etiqueta QR para orden: {orden.folio_orden}")
        
        folio = orden.folio_orden or f"ORD-{orden.id}"
        paciente_nombre = orden.paciente.nombre_completo if orden.paciente else "SIN PACIENTE"
        tipo_muestra = getattr(orden, 'tipo_muestra', 'Suero')
        fecha = orden.fecha_creacion
        
        # Generar PDF de etiqueta con QR
        pdf_bytes = generar_etiqueta_con_qr(
            folio_orden=folio,
            nombre_paciente=paciente_nombre,
            tipo_muestra=tipo_muestra,
            fecha=fecha
        )
        
        response = FileResponse(
            pdf_bytes,
            content_type='application/pdf',
            as_attachment=False,
            filename=f'etiqueta_qr_{folio}.pdf'
        )
        
        logger.info(f"✓ Etiqueta QR generada para orden {folio}")
        return response
        
    except (RuntimeError, ValueError, TypeError, ImportError) as e:
        logger.error(f"Error al generar etiqueta QR: {e}", exc_info=True)
        return HttpResponse(f"Error al generar etiqueta: {str(e)}", status=500)


@login_required
@grupo_requerido('LABORATORIO')
@require_http_methods(['GET'])
def vista_previa_etiqueta(request, orden_id):
    """
    Muestra una vista previa HTML de la etiqueta (sin generar PDF).
    
    Útil para: Verificar datos antes de imprimir
    
    URL: /laboratorio/etiqueta/preview/<orden_id>/
    """
    try:
        empresa = getattr(request.user, 'empresa', None)
        if not empresa:
            return HttpResponse("Usuario sin empresa asignada", status=403)
        orden = get_object_or_404(OrdenDeServicio, id=orden_id, empresa=empresa)
        
        context = {
            'orden': orden,
            'folio': orden.folio_orden or f"ORD-{orden.id}",
            'paciente': orden.paciente.nombre_completo if orden.paciente else "SIN PACIENTE",
            'tipo_muestra': getattr(orden, 'tipo_muestra', 'Suero'),
            'fecha': orden.fecha_creacion
        }
        
        from django.shortcuts import render
        return render(request, 'laboratorio/etiqueta_preview.html', context)
        
    except (RuntimeError, ValueError, TypeError, ImportError, DatabaseError, ValidationError) as e:
        logger.error(f"Error en vista previa: {e}", exc_info=True)
        return HttpResponse(f"Error: {str(e)}", status=500)
