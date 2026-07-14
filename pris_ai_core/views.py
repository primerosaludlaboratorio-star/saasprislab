import json
import logging
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from .services.nlp_engine import nlp_engine
from .services.ocr_service import PRISOcrService

logger = logging.getLogger(__name__)

@csrf_exempt
@login_required
def voice_command_api(request):
    if request.method == 'POST':
        try:
            body = json.loads(request.body)
            command_text = body.get('command', '')
            
            result = nlp_engine.analyze_command(command_text)
            return JsonResponse(result)
            
        except Exception:
            logger.exception("Error en voice_command_api")
            return JsonResponse({"success": False, "error": "No fue posible procesar el comando."}, status=400)
    return JsonResponse({"error": "Method not allowed"}, status=405)

@csrf_exempt
@login_required
def ocr_api(request):
    if request.method == 'POST':
        try:
            body = json.loads(request.body)
            image_b64 = body.get('image', '')
            
            result = PRISOcrService.procesar_receta(image_b64)
            return JsonResponse(result)
            
        except Exception:
            logger.exception("Error en ocr_api")
            return JsonResponse({"success": False, "error": "No fue posible procesar la imagen."}, status=400)
    return JsonResponse({"error": "Method not allowed"}, status=405)
