"""
Vista del Buzón de la Verdad - Quejas, Sugerencias y Felicitaciones.
"""
import json
import logging
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone

from core.models import BuzonQuejas, Empresa
from core.utils.empresa_request import empresa_efectiva_request
from core.utils.default_empresa import resolve_default_empresa_sistema

logger = logging.getLogger('core')


def tu_opinion(request):
    """
    Vista pública para que pacientes y empleados dejen quejas/sugerencias.
    URL: /tu-opinion/
    """
    # Resolución de empresa canónica: si el visitante está autenticado (empleado),
    # su tenant activo; si es anónimo (paciente), la empresa por defecto del sistema
    # (respeta PRISLAB_DEFAULT_EMPRESA_ID / única activa / pk=1). Antes asignaba
    # arbitrariamente la "primera empresa activa", mal en multi-tenant.
    empresa = empresa_efectiva_request(request) or resolve_default_empresa_sistema()
    
    if request.method == 'POST':
        tipo = request.POST.get('tipo', 'QUEJA')
        mensaje = request.POST.get('mensaje', '').strip()
        nombre = request.POST.get('nombre', '').strip()
        contacto = request.POST.get('contacto', '').strip()
        anonimo = request.POST.get('anonimo', 'false') == 'true'
        
        if not mensaje:
            return render(request, 'core/tu_opinion.html', {
                'empresa': empresa,
                'error': 'El mensaje es obligatorio'
            })
        
        if not empresa:
            return render(request, 'core/tu_opinion.html', {
                'empresa': None,
                'error': 'No hay empresa configurada'
            })
        
        BuzonQuejas.objects.create(
            empresa=empresa,
            tipo=tipo,
            mensaje=mensaje,
            nombre_remitente=nombre if not anonimo else None,
            contacto=contacto if not anonimo else None,
            anonimo=anonimo,
            estado='PENDIENTE'
        )
        
        return render(request, 'core/tu_opinion.html', {
            'empresa': empresa,
            'exito': True
        })
    
    return render(request, 'core/tu_opinion.html', {
        'empresa': empresa
    })


@login_required
def buzon_kanban(request):
    """Panel Kanban mejorado para gestión de reportes de fricción."""
    empresa = getattr(request.user, 'empresa', None)
    
    if not empresa:
        from django.contrib import messages
        messages.error(request, 'Usuario no tiene empresa asignada.')
        from django.shortcuts import redirect
        return redirect('home')
    
    try:
        # Obtener quejas agrupadas por estado
        quejas_nuevas = BuzonQuejas.objects.filter(
            empresa=empresa,
            estado='PENDIENTE'
        ).order_by('-fecha_creacion')
        
        quejas_investigando = BuzonQuejas.objects.filter(
            empresa=empresa,
            estado='EN_REVISION'
        ).order_by('-fecha_creacion')
        
        quejas_resueltas = BuzonQuejas.objects.filter(
            empresa=empresa,
            estado='RESUELTO'
        ).order_by('-fecha_resolucion')[:20]
        
        quejas_descartadas = BuzonQuejas.objects.filter(
            empresa=empresa,
            estado='DESCARTADO'
        ).order_by('-fecha_creacion')[:10]
        
        # Estadísticas
        total_quejas = BuzonQuejas.objects.filter(empresa=empresa).count()
        quejas_criticas = BuzonQuejas.objects.filter(empresa=empresa, sentimiento_ia='CRITICO').count()
        quejas_sin_analizar = BuzonQuejas.objects.filter(empresa=empresa, analizado_ia=False).count()
        
        # Agrupar por categoría IA
        por_categoria = {}
        for categoria in ['TIEMPOS', 'TRATO', 'PRECIOS', 'INSTALACIONES', 'LIMPIEZA', 'PROCESO', 'OTRO']:
            por_categoria[categoria] = BuzonQuejas.objects.filter(
                empresa=empresa,
                categoria_ia=categoria,
                estado='PENDIENTE'
            ).count()
    except Exception as e:
        logger.error(f"Error en buzon_kanban: {str(e)}", exc_info=True)
        quejas_nuevas = BuzonQuejas.objects.none()
        quejas_investigando = BuzonQuejas.objects.none()
        quejas_resueltas = BuzonQuejas.objects.none()
        quejas_descartadas = BuzonQuejas.objects.none()
        total_quejas = 0
        quejas_criticas = 0
        quejas_sin_analizar = 0
        por_categoria = {}
    
    return render(request, 'core/buzon_kanban.html', {
        'empresa': empresa,
        'quejas_nuevas': quejas_nuevas,
        'quejas_investigando': quejas_investigando,
        'quejas_resueltas': quejas_resueltas,
        'quejas_descartadas': quejas_descartadas,
        'total_quejas': total_quejas,
        'quejas_criticas': quejas_criticas,
        'quejas_sin_analizar': quejas_sin_analizar,
        'por_categoria': por_categoria,
    })


@login_required
@require_http_methods(["POST"])
def api_cambiar_estado_queja(request, queja_id):
    """
    API para cambiar el estado de una queja (drag & drop en Kanban).
    Body JSON: { estado: 'PENDIENTE'|'EN_REVISION'|'RESUELTO'|'DESCARTADO', notas_resolucion?: str }
    """
    empresa = getattr(request.user, 'empresa', None)
    if not empresa:
        return JsonResponse({'status': 'error', 'mensaje': 'Usuario sin empresa asignada'}, status=403)
    
    try:
        # .get() (no get_object_or_404): así el `except DoesNotExist` devuelve 404
        # limpio. Con get_object_or_404, el Http404 caía en `except Exception` -> 500.
        queja = BuzonQuejas.objects.get(id=queja_id, empresa=empresa)
        data = json.loads(request.body)
        nuevo_estado = data.get('estado', queja.estado)
        notas = data.get('notas_resolucion', '')
        
        if nuevo_estado not in [e[0] for e in BuzonQuejas.ESTADO_CHOICES]:
            return JsonResponse({'status': 'error', 'mensaje': 'Estado inválido'}, status=400)
        
        queja.estado = nuevo_estado
        notas_seguimiento = data.get('notas_seguimiento', '')
        
        if nuevo_estado == 'RESUELTO':
            queja.fecha_resolucion = timezone.now()
            queja.fecha_cierre = timezone.now()
            queja.resuelto_por = request.user
            if notas:
                queja.notas_resolucion = notas
        elif nuevo_estado == 'EN_REVISION':
            # Si se mueve a investigación, agregar notas de seguimiento
            if notas_seguimiento:
                queja.notas_seguimiento = notas_seguimiento
        else:
            # Si se cambia de RESUELTO a otro estado, limpiar datos
            if queja.estado == 'RESUELTO' and nuevo_estado != 'RESUELTO':
                queja.fecha_resolucion = None
                queja.fecha_cierre = None
                queja.resuelto_por = None
        
        if notas_seguimiento:
            queja.notas_seguimiento = notas_seguimiento
        
        queja.save()
        
        return JsonResponse({
            'status': 'success',
            'mensaje': f'Queja movida a {queja.get_estado_display()}',
            'queja_id': queja.id,
            'estado': queja.estado
        })
        
    except BuzonQuejas.DoesNotExist:
        return JsonResponse({'status': 'error', 'mensaje': 'Queja no encontrada'}, status=404)
    except Exception as e:
        return JsonResponse({'status': 'error', 'mensaje': str(e)}, status=500)


@login_required
@require_http_methods(["GET"])
def api_obtener_quejas(request):
    """API para obtener quejas agrupadas por estado (para refrescar Kanban)."""
    empresa = getattr(request.user, 'empresa', None)
    if not empresa:
        return JsonResponse({'resultados': []})
    estado = request.GET.get('estado', None)
    
    queryset = BuzonQuejas.objects.filter(empresa=empresa)
    if estado:
        queryset = queryset.filter(estado=estado)
    
    quejas = queryset.order_by('-fecha_creacion')[:50]
    
    resultados = []
    for q in quejas:
        resultados.append({
            'id': q.id,
            'tipo': q.tipo,
            'tipo_display': q.get_tipo_display(),
            'mensaje': q.mensaje[:200] + '...' if len(q.mensaje) > 200 else q.mensaje,
            'nombre': q.nombre_remitente if not q.anonimo else 'Anónimo',
            'anonimo': q.anonimo,
            'estado': q.estado,
            'estado_display': q.get_estado_display(),
            'fecha_creacion': q.fecha_creacion.strftime('%d/%m/%Y %H:%M'),
            'contacto': q.contacto if not q.anonimo else None,
            # Campos de análisis IA
            'sentimiento_ia': q.sentimiento_ia,
            'sentimiento_display': q.get_sentimiento_ia_display() if q.sentimiento_ia else 'Pendiente',
            'categoria_ia': q.categoria_ia,
            'categoria_display': q.get_categoria_ia_display() if q.categoria_ia else 'Pendiente',
            'resumen_causa': q.resumen_causa,
            'plan_accion_sugerido': q.plan_accion_sugerido,
            'analizado_ia': q.analizado_ia,
        })
    
    return JsonResponse({'status': 'success', 'quejas': resultados})
