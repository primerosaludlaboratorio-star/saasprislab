"""
PRISLAB V5.0 - API DE PROCESAMIENTO DE AUDIO PARA CONSULTORIO
============================================================
Fecha: 1 de Febrero de 2026
Objetivo: Endpoint para procesar audio de consultas médicas con IA

FLUJO:
1. Recibe audio del frontend
2. Llama al servicio de IA
3. Retorna JSON estructurado para llenar formulario
"""

import logging
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required

from core.services.ai_medico import procesar_consulta_medica
from core.mixins import grupo_requerido

logger = logging.getLogger('ia')


@login_required
@grupo_requerido('MEDICOS', 'ENFERMERIA')
@require_http_methods(['POST'])
def procesar_audio_consulta(request):
    """
    Procesa audio de consulta médica y retorna datos estructurados.
    
    Request:
        - POST: Multipart/form-data con archivo 'audio'
        
    Response:
        - 200: JSON con datos de la consulta
        - 400: Error de validación
        - 500: Error del servidor
        
    Ejemplo de respuesta:
    {
        "success": true,
        "data": {
            "motivo": "Dolor de garganta de 3 días",
            "signos_vitales": {
                "temperatura": 38.5,
                "frecuencia_cardiaca": 85,
                "presion_arterial": "120/80",
                ...
            },
            "diagnostico": "Faringitis aguda",
            "tratamiento": "Amoxicilina 500mg c/8hrs x 7 días..."
        },
        "message": "Audio procesado exitosamente"
    }
    """
    try:
        # Validar que se envió el archivo
        if 'audio' not in request.FILES:
            return JsonResponse({
                'success': False,
                'error': 'No se recibió ningún archivo de audio'
            }, status=400)
        
        audio_file = request.FILES['audio']
        
        # Validar tamaño del archivo (máx 10 MB)
        max_size = 10 * 1024 * 1024  # 10 MB
        if audio_file.size > max_size:
            return JsonResponse({
                'success': False,
                'error': f'El archivo es demasiado grande ({audio_file.size / (1024*1024):.2f} MB). Máximo: 10 MB'
            }, status=400)
        
        # Validar formato
        allowed_formats = ['audio/webm', 'audio/wav', 'audio/mp3', 'audio/mpeg']
        if audio_file.content_type not in allowed_formats:
            logger.warning(f"Formato de audio no estándar: {audio_file.content_type}. Intentando procesar de todas formas...")
        
        logger.info(f"Procesando audio de consulta: {audio_file.name} ({audio_file.size} bytes)")
        
        # Procesar audio con IA
        datos_consulta = procesar_consulta_medica(audio_file)
        
        # Registrar en log
        logger.info(f"Consulta procesada por usuario: {request.user.username}")
        
        # Retornar respuesta
        return JsonResponse({
            'success': True,
            'data': datos_consulta,
            'message': 'Audio procesado exitosamente'
        })
        
    except Exception as e:
        logger.error(f"Error al procesar audio de consulta: {e}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)
