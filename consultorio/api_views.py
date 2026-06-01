"""
API endpoints para procesamiento de audio médico en tiempo real.
Integración con Google Gemini para transcripción y análisis inteligente.
"""
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
import json
import logging

from core.services.ai_medico import procesar_consulta_medica, procesar_resultados_lab

logger = logging.getLogger('ia')


@login_required
@require_http_methods(["POST"])
@csrf_exempt
def procesar_audio_consulta(request):
    """
    Procesa audio de consulta médica y devuelve datos estructurados.
    
    POST /consultorio/api/procesar-audio-consulta/
    Body: multipart/form-data
        - audio: Archivo de audio (webm/ogg)
    
    Returns:
        JSON con datos estructurados de la consulta
    """
    try:
        # Verificar que se envió el audio
        if 'audio' not in request.FILES:
            return JsonResponse({
                'success': False,
                'error': 'No se recibió archivo de audio'
            }, status=400)
        
        audio_file = request.FILES['audio']
        
        logger.info(f"Procesando audio de consulta médica (Usuario: {request.user.username})")
        
        # Procesar audio con IA
        datos = procesar_consulta_medica(audio_file)
        
        logger.info(f"Audio procesado exitosamente: {datos.keys()}")
        
        return JsonResponse({
            'success': True,
            'datos': datos
        })
        
    except Exception as e:
        logger.error(f"Error al procesar audio de consulta: {e}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
@require_http_methods(["POST"])
@csrf_exempt
def procesar_audio_laboratorio(request):
    """
    Procesa audio de resultados de laboratorio y mapea valores.
    
    POST /laboratorio/api/procesar-audio-resultados/
    Body: multipart/form-data
        - audio: Archivo de audio (webm/ogg)
        - estudio_id: ID del estudio para obtener parámetros
    
    Returns:
        JSON con valores mapeados
    """
    try:
        # Verificar que se envió el audio
        if 'audio' not in request.FILES:
            return JsonResponse({
                'success': False,
                'error': 'No se recibió archivo de audio'
            }, status=400)
        
        audio_file = request.FILES['audio']
        estudio_id = request.POST.get('estudio_id')
        
        if not estudio_id:
            return JsonResponse({
                'success': False,
                'error': 'No se especificó el estudio'
            }, status=400)

        lista_parametros = []
        try:
            pk = int(estudio_id)
        except (TypeError, ValueError):
            return JsonResponse({
                'success': False,
                'error': 'ID de estudio o analito inválido'
            }, status=400)

        from lims.models import Analito
        an = Analito.objects.filter(pk=pk, activo=True).first()
        if an:
            kw = ' '.join(
                x for x in (an.nombre, an.codigo, an.abreviatura or '') if x
            ).strip()
            lista_parametros = [{'nombre': an.nombre, 'keywords': kw or an.nombre}]
        else:
            from laboratorio.models import Parametro
            lista_parametros = list(
                Parametro.objects.filter(estudio_id=pk).values('nombre', 'keywords')
            )

        if not lista_parametros:
            return JsonResponse({
                'success': False,
                'error': 'No se encontraron parámetros para este estudio o analito LIMS'
            }, status=400)
        
        logger.info(f"Procesando audio de laboratorio (Usuario: {request.user.username}, Estudio: {estudio_id})")
        
        # Procesar audio con IA
        datos = procesar_resultados_lab(audio_file, lista_parametros)
        
        logger.info(f"Audio de laboratorio procesado: {len(datos)} valores")
        
        return JsonResponse({
            'success': True,
            'valores': datos
        })
        
    except Exception as e:
        logger.error(f"Error al procesar audio de laboratorio: {e}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
@require_http_methods(["POST"])
def verificar_api_gemini(request):
    """
    Verifica que la API de Gemini esté configurada y funcionando.
    
    POST /api/verificar-gemini/
    
    Returns:
        JSON con estado de la API
    """
    try:
        from core.services.ai_medico import test_gemini_connection
        
        resultado = test_gemini_connection()
        
        return JsonResponse({
            'success': True,
            'conectado': resultado
        })
        
    except Exception as e:
        logger.error(f"Error al verificar API de Gemini: {e}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)
