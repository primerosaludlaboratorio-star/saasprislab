"""
API endpoints para procesamiento de audio médico en tiempo real.
Integración con Google Gemini para transcripción y análisis inteligente.
"""
from django.db.models import Value
from django.db.models.functions import Coalesce
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
import logging

from core.services.ai_medico import procesar_consulta_medica, procesar_resultados_lab

logger = logging.getLogger('ia')

_ROLES_AUDIO_CONSULTA = {'DIRECTOR', 'ADMIN', 'ADMINISTRADOR', 'MEDICO'}
_ROLES_AUDIO_LAB = {'DIRECTOR', 'ADMIN', 'ADMINISTRADOR', 'QUIMICO', 'LABORATORIO'}
_GRUPOS_AUDIO_CONSULTA = {'MEDICOS', 'CONSULTORIO', 'GERENCIA_OPERATIVA'}
_GRUPOS_AUDIO_LAB = {'LABORATORIO', 'GERENCIA_OPERATIVA'}


def _has_audio_access(user, allowed_roles, allowed_groups):
    if not getattr(user, 'is_authenticated', False):
        return False
    if user.is_superuser or user.is_staff:
        return True
    rol = (getattr(user, 'rol', '') or '').upper().strip()
    if rol in allowed_roles:
        return True
    return user.groups.filter(name__in=allowed_groups).exists()


def _require_empresa(user):
    return getattr(user, 'empresa', None)


@login_required
@require_http_methods(["POST"])
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
        if not _has_audio_access(request.user, _ROLES_AUDIO_CONSULTA, _GRUPOS_AUDIO_CONSULTA):
            return JsonResponse({
                'success': False,
                'error': 'No autorizado para usar captura por audio en consultorio'
            }, status=403)

        if not _require_empresa(request.user):
            return JsonResponse({
                'success': False,
                'error': 'Usuario sin empresa asignada'
            }, status=403)

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
        if not _has_audio_access(request.user, _ROLES_AUDIO_LAB, _GRUPOS_AUDIO_LAB):
            return JsonResponse({
                'success': False,
                'error': 'No autorizado para usar captura por audio en laboratorio'
            }, status=403)

        empresa = _require_empresa(request.user)
        if not empresa:
            return JsonResponse({
                'success': False,
                'error': 'Usuario sin empresa asignada'
            }, status=403)

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
        an = Analito.objects.filter(pk=pk, activo=True, empresa=empresa).first()
        if an:
            kw = ' '.join(
                x for x in (an.nombre, an.codigo, an.abreviatura or '') if x
            ).strip()
            lista_parametros = [{'nombre': an.nombre, 'keywords': kw or an.nombre}]
        else:
            from laboratorio.models import Parametro
            lista_parametros = list(
                Parametro.objects.filter(estudio_id=pk).annotate(
                    keywords=Coalesce('abreviatura', Value(''))
                ).values('nombre', 'keywords')
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
