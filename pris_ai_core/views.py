import json
import logging
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from .services.nlp_engine import nlp_engine
from .services.ocr_service import PRISOcrService

logger = logging.getLogger(__name__)

@login_required
@require_POST
def voice_command_api(request):
    try:
        body = json.loads(request.body or '{}')
        if not isinstance(body, dict):
            return JsonResponse({'success': False, 'error': 'Payload invalido.'}, status=400)
        command_text = str(body.get('command', '')).strip()
        if not command_text or len(command_text) > 2000:
            return JsonResponse({'success': False, 'error': 'Comando invalido.'}, status=400)
        return JsonResponse(nlp_engine.analyze_command(command_text))
    except (TypeError, ValueError, json.JSONDecodeError):
        return JsonResponse({'success': False, 'error': 'JSON invalido.'}, status=400)
    except Exception:
        logger.exception('Error en voice_command_api')
        return JsonResponse({'success': False, 'error': 'No fue posible procesar el comando.'}, status=400)

@login_required
@require_POST
def ocr_api(request):
    if len(request.body) > 12 * 1024 * 1024:
        return JsonResponse({'success': False, 'error': 'Imagen demasiado grande.'}, status=413)
    try:
        body = json.loads(request.body or '{}')
        if not isinstance(body, dict):
            return JsonResponse({'success': False, 'error': 'Payload invalido.'}, status=400)
        image_b64 = str(body.get('image', '')).strip()
        if not image_b64:
            return JsonResponse({'success': False, 'error': 'Imagen vacia.'}, status=400)
        return JsonResponse(PRISOcrService.procesar_receta(image_b64))
    except (TypeError, ValueError, json.JSONDecodeError):
        return JsonResponse({'success': False, 'error': 'JSON invalido.'}, status=400)
    except Exception:
        logger.exception('Error en ocr_api')
        return JsonResponse({'success': False, 'error': 'No fue posible procesar la imagen.'}, status=400)
