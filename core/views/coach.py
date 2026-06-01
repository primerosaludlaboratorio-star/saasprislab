"""
Vista de IA Coach Ejecutivo - Academia de Liderazgo.
Consultor experto en liderazgo clínico estilo Harvard Business Review.
Migrado a Google Gemini.
"""
import json
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_http_methods
from django.conf import settings

# Prompt del sistema para el Coach Ejecutivo
PROMPT_SISTEMA_COACH = """Eres un consultor experto en liderazgo clínico (estilo Harvard Business Review). 
Tu misión es ayudar al Director a resolver conflictos, mejorar procesos y crecer como líder. 
Sé directo, breve y estratégico. Proporciona consejos prácticos y accionables.
Enfócate en:
- Resolución de conflictos en entornos clínicos
- Mejora de procesos operativos
- Desarrollo de habilidades de liderazgo
- Gestión de equipos multidisciplinarios
- Optimización de recursos y tiempo
- Comunicación efectiva con personal médico y administrativo

Responde siempre en español y sé conciso (máximo 300 palabras por respuesta)."""


@login_required
def coach_ejecutivo(request):
    """Interfaz de chat para el Coach Ejecutivo IA."""
    empresa = getattr(request.user, 'empresa', None)
    
    # Lecturas recomendadas (estáticas por ahora)
    lecturas_recomendadas = [
        {
            'titulo': 'Harvard Business Review: Liderazgo en Salud',
            'link': 'https://hbr.org/topic/health-care',
            'descripcion': 'Artículos sobre gestión y liderazgo en el sector salud'
        },
        {
            'titulo': 'Gestión de Laboratorios Clínicos',
            'link': '#',
            'descripcion': 'Mejores prácticas en administración de laboratorios'
        },
        {
            'titulo': 'Resolución de Conflictos en Equipos Médicos',
            'link': '#',
            'descripcion': 'Técnicas para manejar conflictos en entornos clínicos'
        },
        {
            'titulo': 'Optimización de Procesos en Salud',
            'link': '#',
            'descripcion': 'Lean Healthcare y mejora continua'
        },
    ]
    
    return render(request, 'core/coach_ejecutivo.html', {
        'empresa': empresa,
        'lecturas_recomendadas': lecturas_recomendadas
    })


@login_required
@require_http_methods(["POST"])
def api_coach_preguntar(request):
    """
    API para enviar preguntas al Coach Ejecutivo.
    Body JSON: { pregunta: str }
    """
    try:
        data = json.loads(request.body)
        pregunta = (data.get("pregunta") or "").strip()

        if not pregunta:
            return JsonResponse({"status": "error", "mensaje": "Pregunta vacía."}, status=400)

        # Verificar si hay API key de Google
        api_key = getattr(settings, 'GOOGLE_API_KEY', '')
        if not api_key:
            return JsonResponse({
                "status": "error",
                "mensaje": "Google API Key no configurada. Contacte al administrador."
            }, status=500)

        # Usar cliente centralizado de Gemini (API v1 estable)
        from core.utils.gemini_client import get_gemini_model
        
        try:
            model = get_gemini_model('gemini-2.0-flash')
        except Exception as e:
            return JsonResponse({
                "status": "error",
                "mensaje": f"Error al inicializar Gemini: {str(e)}"
            }, status=500)
        
        # Crear prompt combinado (Gemini no usa system messages como OpenAI)
        prompt_completo = f"""{PROMPT_SISTEMA_COACH}

Pregunta del usuario: {pregunta}

Responde como consultor experto:"""
        
        from google.generativeai.types import GenerationConfig
        
        response = model.generate_content(
            prompt_completo,
            generation_config=GenerationConfig(
                temperature=0.7,
                max_output_tokens=500,
            )
        )
        
        respuesta = response.text if response.text else "No se pudo generar una respuesta."

        return JsonResponse({
            "status": "success",
            "respuesta": respuesta,
            "pregunta": pregunta
        })

    except Exception as e:
        return JsonResponse({
            "status": "error",
            "mensaje": f"Error al consultar al Coach: {str(e)}"
        }, status=500)
