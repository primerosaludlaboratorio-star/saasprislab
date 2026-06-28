"""
Bot de Asistencia - Agente de Preparación
API para responder preguntas sobre preparación de estudios.
"""
import json
import re
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.db.models import Q

from laboratorio.models import Estudio, PerfilLaboratorio
import logging


@login_required
@require_http_methods(["POST"])
def api_bot_pregunta(request):
    """
    API del Bot de Asistencia - Responde preguntas sobre preparación de estudios.
    
    Ejemplo de pregunta: '¿Ayuno para Perfil Hepático?'
    """
    try:
        data = json.loads(request.body)
        pregunta = data.get('pregunta', '').strip().lower()
        
        if not pregunta:
            return JsonResponse({
                'status': 'error',
                'mensaje': 'Pregunta vacía'
            }, status=400)
        
        # Extraer palabras clave de la pregunta
        palabras_clave = {
            'ayuno': ['ayuno', 'ayunar', 'comida', 'alimento'],
            'perfil hepático': ['perfil hepático', 'hepatico', 'hepático', 'transaminasas'],
            'perfil lipídico': ['perfil lipídico', 'lipidico', 'colesterol', 'triglicéridos'],
            'perfil renal': ['perfil renal', 'urea', 'creatinina'],
            'química general': ['química general', 'quimica general', 'perfil general'],
            'biometría': ['biometría', 'biometria', 'hemograma', 'citometría'],
            'orina': ['orina', 'ego', 'examen general de orina'],
        }
        
        # Buscar estudios relacionados
        estudios_encontrados = []
        respuesta = None
        
        # Buscar por palabras clave
        for keyword, variantes in palabras_clave.items():
            if any(variante in pregunta for variante in variantes):
                # Buscar estudios
                if keyword == 'perfil hepático':
                    perfiles = PerfilLaboratorio.objects.filter(
                        nombre__icontains='hepático'
                    )
                    if perfiles.exists():
                        estudio = perfiles.first()
                        estudios_encontrados.append(estudio)
                elif keyword == 'perfil lipídico':
                    perfiles = PerfilLaboratorio.objects.filter(
                        nombre__icontains='lipídico'
                    )
                    if perfiles.exists():
                        estudio = perfiles.first()
                        estudios_encontrados.append(estudio)
                elif keyword == 'perfil renal':
                    perfiles = PerfilLaboratorio.objects.filter(
                        nombre__icontains='renal'
                    )
                    if perfiles.exists():
                        estudio = perfiles.first()
                        estudios_encontrados.append(estudio)
                else:
                    estudios = Estudio.objects.filter(
                        nombre__icontains=keyword
                    )[:5]
                    estudios_encontrados.extend(estudios)
        
        # Si no se encontró nada, buscar por palabras individuales
        if not estudios_encontrados:
            palabras = pregunta.split()
            for palabra in palabras:
                if len(palabra) > 4:  # Solo palabras significativas
                    estudios = Estudio.objects.filter(
                        Q(nombre__icontains=palabra) | 
                        Q(instrucciones_paciente__icontains=palabra)
                    )[:3]
                    estudios_encontrados.extend(estudios)
        
        # Construir respuesta
        if estudios_encontrados:
            # Tomar el primer estudio encontrado
            estudio = estudios_encontrados[0]
            
            # Buscar instrucciones
            if hasattr(estudio, 'instrucciones_paciente') and estudio.instrucciones_paciente:
                respuesta = estudio.instrucciones_paciente
            elif hasattr(estudio, 'indicaciones') and estudio.indicaciones:
                respuesta = estudio.indicaciones
            else:
                # Respuesta por defecto basada en tipo de estudio
                if 'hepático' in pregunta.lower() or 'lipídico' in pregunta.lower():
                    respuesta = "Para el Perfil Hepático/Lipídico: Ayuno de 8-12 horas. No consumir alimentos ni bebidas (excepto agua) antes de la toma de muestra."
                elif 'renal' in pregunta.lower():
                    respuesta = "Para el Perfil Renal: No se requiere ayuno. Puede tomar sus alimentos normalmente."
                elif 'glucosa' in pregunta.lower():
                    respuesta = "Para Glucosa: Ayuno de 8 horas. No consumir alimentos ni bebidas azucaradas antes de la toma."
                elif 'orina' in pregunta.lower():
                    respuesta = "Para Examen General de Orina: Recoger la primera orina de la mañana. Limpiar la zona genital antes de recolectar."
                else:
                    respuesta = f"Para {estudio.nombre}: Por favor, consulte con el personal de recepción para instrucciones específicas."
            
            return JsonResponse({
                'status': 'success',
                'respuesta': respuesta,
                'estudio': estudio.nombre,
                'tipo': 'perfil' if hasattr(estudio, 'pruebas') else 'estudio'
            })
        else:
            # Respuesta genérica
            return JsonResponse({
                'status': 'success',
                'respuesta': 'Por favor, proporcione más detalles sobre el estudio que necesita. Por ejemplo: "¿Ayuno para Perfil Hepático?" o "¿Cómo prepararse para Biometría?"',
                'estudio': None,
                'tipo': 'generico'
            })
    
    except Exception as e:
        logging.getLogger(__name__).exception("Error inesperado en api_bot_pregunta (bot.py)")
        return JsonResponse({
            'status': 'error',
            'mensaje': str(e)
        }, status=400)