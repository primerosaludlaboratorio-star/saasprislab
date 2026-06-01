"""
API del Cerebro Dual PRIS/LIA.
"""

import json

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods

from core.ai_brain import responder


@login_required
@require_http_methods(["POST"])
def api_ai_brain_preguntar(request):
    """
    POST /api/ai/brain/preguntar/
    Body: { pregunta: "..." }
    """
    try:
        data = json.loads(request.body)
        pregunta = (data.get("pregunta") or "").strip()
        if not pregunta:
            return JsonResponse({"status": "error", "mensaje": "Pregunta vacía."}, status=400)

        out = responder(request.user, pregunta)
        return JsonResponse({"status": "success", **out})
    except Exception as e:
        return JsonResponse({"status": "error", "mensaje": str(e)}, status=500)

