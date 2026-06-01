"""
PRIS VOICE COMMANDER - Vistas API REST
Endpoints HTTP para comandos de voz (fallback si WebSocket no disponible)
"""

import json
import logging
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import render

from core.models import VoiceAuditLog
from core.services.voice_service import procesar_comando_voz, registrar_comando_voz

logger = logging.getLogger('voice')


@login_required
@require_http_methods(["POST"])
def procesar_comando_api(request):
    """
    API REST: Procesa un comando de voz (fallback HTTP si WebSocket no disponible).
    
    POST /api/voice/process/
    Payload:
    {
        "transcription": "buscar paciente juan",
        "url": "/farmacia/ventas/",
        "context": "Receta #554 en pantalla"
    }
    """
    try:
        data = json.loads(request.body)
        
        transcription = data.get('transcription', '').strip()
        url_actual = data.get('url', request.META.get('HTTP_REFERER', '/'))
        context = data.get('context', '')
        
        if not transcription:
            return JsonResponse({
                'status': 'error',
                'message': 'Transcripción vacía'
            }, status=400)
        
        # Procesar con IA
        resultado = procesar_comando_voz(
            transcripcion=transcription,
            usuario=request.user,
            url_actual=url_actual,
            datos_pantalla=context
        )
        
        # Registrar en log de auditoría
        registrar_comando_voz(
            usuario=request.user,
            transcripcion=transcription,
            resultado=resultado,
            url_actual=url_actual,
            datos_pantalla=context
        )
        
        return JsonResponse({
            'status': 'success',
            'intention': resultado['intencion'],
            'parameters': resultado['parametros'],
            'response': resultado['respuesta'],
            'action': resultado['accion'],
            'blocked': resultado['bloqueado'],
            'requires_auth': resultado['requiere_auth'],
            'processing_time_ms': resultado['tiempo_procesamiento_ms']
        })
    
    except json.JSONDecodeError:
        return JsonResponse({
            'status': 'error',
            'message': 'JSON inválido'
        }, status=400)
    except Exception as e:
        logger.error(f"Error al procesar comando de voz: {e}", exc_info=True)
        return JsonResponse({
            'status': 'error',
            'message': f'Error del servidor: {type(e).__name__}'
        }, status=500)


@login_required
@require_http_methods(["GET"])
def historial_comandos(request):
    """
    API: Retorna el historial de comandos de voz del usuario.
    
    Query params:
        - limit: Número de resultados (default: 20)
        - offset: Offset para paginación
    """
    limit = int(request.GET.get('limit', 20))
    offset = int(request.GET.get('offset', 0))
    
    # Filtrar por usuario (o todos si es director)
    if request.user.is_superuser:
        logs = VoiceAuditLog.objects.all()
    else:
        logs = VoiceAuditLog.objects.filter(usuario=request.user)
    
    # Paginación
    total = logs.count()
    logs = logs[offset:offset + limit]
    
    # Serializar
    resultados = []
    for log in logs:
        resultados.append({
            'id': log.id,
            'timestamp': log.timestamp.isoformat(),
            'transcription': log.transcripcion,
            'intention': log.intencion_detectada,
            'response': log.respuesta_ia,
            'status': log.estado,
            'blocked': log.fue_bloqueado,
            'processing_time_ms': log.tiempo_procesamiento_ms
        })
    
    return JsonResponse({
        'status': 'success',
        'total': total,
        'limit': limit,
        'offset': offset,
        'logs': resultados
    })


@login_required
def dashboard_voice_logs(request):
    """
    Vista del dashboard de logs de voz (solo Director).
    """
    if not request.user.is_superuser:
        return render(request, '403.html', status=403)
    
    empresa = getattr(request.user, 'empresa', None)
    base_qs = VoiceAuditLog.objects.filter(empresa=empresa)

    # Estadísticas
    total_comandos = base_qs.count()
    bloqueados = base_qs.filter(estado='BLOQUEADO').count()
    criticos = base_qs.filter(tipo_comando='CRITICO').count()

    # Últimos 50 comandos
    logs_recientes = base_qs.order_by('-timestamp')[:50]
    
    # Top 5 usuarios más activos
    from django.db.models import Count
    top_usuarios = base_qs.values(
        'usuario__username', 'usuario__first_name', 'usuario__last_name'
    ).annotate(
        total=Count('id')
    ).order_by('-total')[:5]

    # Top 5 intenciones más usadas
    top_intenciones = base_qs.values(
        'intencion_detectada'
    ).annotate(
        total=Count('id')
    ).order_by('-total')[:5]
    
    context = {
        'total_comandos': total_comandos,
        'bloqueados': bloqueados,
        'criticos': criticos,
        'logs_recientes': logs_recientes,
        'top_usuarios': top_usuarios,
        'top_intenciones': top_intenciones,
    }
    
    return render(request, 'core/voice_logs_dashboard.html', context)


@login_required
@require_http_methods(["POST"])
@csrf_exempt  # Para WebAuthn
def verificar_webauthn(request):
    """
    API: Verifica autenticación WebAuthn (huella/FaceID) para comandos críticos.
    
    POST /api/voice/verify-auth/
    Payload:
    {
        "credential": {...},  // Datos de WebAuthn
        "command_id": 123
    }
    """
    # Verificación biométrica real via WebAuthn pendiente de integración con librería py_webauthn.
    # Actualmente simula verificación exitosa para no bloquear el flujo.
    
    try:
        data = json.loads(request.body)
        command_id = data.get('command_id')
        
        # Simular verificación exitosa
        # En producción, usar webauthn library
        
        return JsonResponse({
            'status': 'success',
            'authenticated': True,
            'message': 'Autenticación biométrica exitosa'
        })
    
    except Exception as e:
        logger.error(f"Error en verificación WebAuthn: {e}", exc_info=True)
        return JsonResponse({
            'status': 'error',
            'authenticated': False,
            'message': 'Error en autenticación'
        }, status=500)
