"""
Cerebro Prislab (RAG) - UI de Chat Experto + API.
"""

import json

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import ensure_csrf_cookie

from core.models import DocumentoConocimiento
from core.utils.rag_engine import consultar_cerebro
import logging


@login_required
@ensure_csrf_cookie
def chat_experto(request):
    """
    Interfaz tipo chat (WhatsApp Web) para consultar la bóveda RAG.
    """
    empresa = getattr(request.user, 'empresa', None)
    
    if not empresa:
        from django.contrib import messages
        messages.error(request, 'Usuario no tiene empresa asignada.')
        from django.shortcuts import redirect
        return redirect('home')
    
    categorias = DocumentoConocimiento.CATEGORIA_CHOICES
    return render(
        request,
        "core/chat_experto.html",
        {
            "empresa": empresa,
            "categorias": categorias,
        },
    )


@login_required
@require_http_methods(["POST"])
def api_cerebro_preguntar(request):
    """
    API: /api/cerebro/preguntar/
    Body JSON: { pregunta: str, categoria: str }
    """
    try:
        data = json.loads(request.body)
        pregunta = (data.get("pregunta") or "").strip()
        categoria = (data.get("categoria") or DocumentoConocimiento.CATEGORIA_MANUAL).strip()

        if not pregunta:
            return JsonResponse({"status": "error", "mensaje": "Pregunta vacía."}, status=400)

        empresa = getattr(request.user, 'empresa', None)
        empresa_id = empresa.id if empresa else None
        
        if not empresa_id:
            return JsonResponse({"status": "error", "mensaje": "Usuario no tiene empresa asignada."}, status=400)
        
        resultado = consultar_cerebro(pregunta=pregunta, empresa_id=empresa_id, categoria=categoria)
        return JsonResponse({"status": "success", **resultado})
    except Exception as e:
        logging.getLogger(__name__).exception("Error inesperado en api_cerebro_preguntar (cerebro.py)")
        return JsonResponse({"status": "error", "mensaje": str(e)}, status=500)
